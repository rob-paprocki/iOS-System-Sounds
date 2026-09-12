#!/usr/bin/env python3
"""Download one IPSW and extract every audio file from its root filesystem.

Two eras need different handling:

  iOS 10 and later   the root filesystem is unencrypted, so
                     `ipsw extract --files` reads it directly.

  iOS 9 and earlier  the root filesystem is an `encrcdsa` image encrypted
                     with a raw AES key. hdiutil cannot open these; handed
                     one, macOS pops a passphrase dialog that can never
                     succeed. This script therefore checks the container
                     magic and refuses to mount anything still encrypted,
                     decrypting with vfdecrypt first.

    python3 tools/fetch-version.py --device iPhone3,1 --build 8A293 --os "iOS 4.0"

Needs: ipsw, ffmpeg. Legacy versions additionally need vfdecrypt and dmg2img
(`brew install dmg2img`, which ships both).
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
MATRIX = os.path.join(HERE, 'versions.json')

AUDIO_RE = (r'.*\.(mp3|mp2|mp1|mpa|wav|wave|flac|aac|ogg|oga|m4a|m4b|m4p|wma|'
            r'opus|alac|aiff|aif|aifc|mid|midi|amr|awb|caf|dff|dsf|mka|ra|rm|'
            r'snd|voc|weba|tta|wv)$')
AUDIO_EXT = tuple('.' + e for e in AUDIO_RE.split('(')[1].split(')')[0].split('|'))
ENCRYPTED_MAGIC = b'encrcdsa'


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def api_meta(device, build, attempts=6):
    """ipsw.me rate-limits hard. A run that asks about a hundred builds will
    be told 429, so back off rather than failing the version."""
    url = 'https://api.ipsw.me/v4/device/%s' % device
    for i in range(attempts):
        try:
            data = json.load(urllib.request.urlopen(url, timeout=60))
        except urllib.error.HTTPError as e:
            if e.code in (429, 503) and i + 1 < attempts:
                time.sleep(5 * (i + 1))
                continue
            raise
        for f in data['firmwares']:
            if f['buildid'] == build:
                return f
        sys.exit('build %s not listed for %s' % (build, device))
    sys.exit('ipsw.me kept rate-limiting for %s %s' % (device, build))


def firmware_meta(device, build):
    """Prefer the matrix. It already carries the version, size and URL, so a
    normal run never needs to touch the API at all."""
    if os.path.exists(MATRIX):
        for v in json.load(open(MATRIX))['versions']:
            if v['build'] == build and v['device'] == device:
                return {'version': v['version'], 'filesize': v['bytes'],
                        'url': v['url'], 'buildid': build}
    return api_meta(device, build)


def download_url(url, target, expect_bytes=0):
    """Fetch a known URL straight from Apple, resuming a partial file.

    Going direct keeps the whole run independent of the ipsw.me API, which
    rate-limits and is not needed once the matrix has the URL.
    """
    part = target + '.part'
    for attempt in range(4):
        r = subprocess.run(['curl', '-sSL', '--fail', '--retry', '3',
                            '--retry-delay', '5', '-C', '-', '-o', part, url])
        if r.returncode == 0 and os.path.exists(part):
            if expect_bytes and os.path.getsize(part) != expect_bytes:
                time.sleep(5)
                continue
            os.rename(part, target)
            return target
        time.sleep(5 * (attempt + 1))
    return None


def md5_of(path):
    m = hashlib.md5()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b''):
            m.update(chunk)
    return m.hexdigest()


def download(device, build, work, meta):
    """Fetch the IPSW, tolerating ipsw.me's occasionally wrong SHA1 records."""
    target = os.path.join(work, '%s_%s_%s_Restore.ipsw' % (device, meta['version'], build))
    if os.path.exists(target):
        print('  already downloaded')
        return target
    if meta.get('url'):
        got = download_url(meta['url'], target, meta.get('filesize', 0))
        if got:
            return got
        print('  direct download failed, falling back to ipsw', file=sys.stderr)
    base = ['ipsw', 'download', 'ipsw', '--device', device, '--build', build, '-y', '-o', work]
    r = run(base)
    hits = glob.glob(os.path.join(work, '*%s*.ipsw' % build))
    if hits:
        return hits[0]

    part = glob.glob(os.path.join(work, '*%s*.ipsw.part' % build))
    if part and 'sha1 mismatch' in (r.stderr + r.stdout):
        # The bytes may still be correct: ipsw.me's SHA1 is wrong for some old
        # firmwares. Only accept them if the independent MD5 matches.
        got = md5_of(part[0])
        published = meta.get('md5sum') or api_meta(device, build).get('md5sum')
        if published and got == published:
            print('  SHA1 record mismatched but MD5 matches ipsw.me (%s); accepting' % got[:12])
            r = run(base + ['--ignore-sha1'])
            hits = glob.glob(os.path.join(work, '*%s*.ipsw' % build))
            if hits:
                return hits[0]
        else:
            sys.exit('  download corrupt: MD5 %s != published %s' % (got, published))
    sys.exit('  download failed: %s' % (r.stderr.strip()[-300:] or r.stdout.strip()[-300:]))


def filesystem_dmg(ipsw, build, work):
    """Unpack the root filesystem DMG. This only reads the IPSW zip; it does
    not mount anything, so it is safe to call before knowing the era.

    `ipsw extract --dmg fs` reads BuildManifest.plist to find the filesystem.
    IPSWs from before iOS 4 have no BuildManifest, only a Restore.plist, so
    when that fails the largest DMG in the zip is taken instead -- in every
    iPhone IPSW that is the root filesystem, the others being the tiny
    ramdisks.
    """
    dmgdir = os.path.join(work, 'dmg-%s' % build)
    shutil.rmtree(dmgdir, ignore_errors=True)
    r = run(['ipsw', 'extract', '--dmg', 'fs', '-o', dmgdir, ipsw])
    dmgs = glob.glob(os.path.join(dmgdir, '**', '*.dmg'), recursive=True)
    if not dmgs:
        os.makedirs(dmgdir, exist_ok=True)
        try:
            with zipfile.ZipFile(ipsw) as z:
                names = [n for n in z.namelist() if n.lower().endswith('.dmg')]
                if names:
                    biggest = max(names, key=lambda n: z.getinfo(n).file_size)
                    out = os.path.join(dmgdir, os.path.basename(biggest))
                    with z.open(biggest) as src, open(out, 'wb') as dst:
                        shutil.copyfileobj(src, dst, 1 << 22)
                    dmgs = [out]
        except (zipfile.BadZipFile, OSError) as e:
            return None, None, 'zip fallback failed: %s' % e
    if not dmgs:
        shutil.rmtree(dmgdir, ignore_errors=True)
        return None, None, r.stderr.strip()[-300:]
    return max(dmgs, key=os.path.getsize), dmgdir, ''


def is_encrypted(path):
    with open(path, 'rb') as fh:
        return fh.read(8) == ENCRYPTED_MAGIC


def extract_modern(ipsw, outdir):
    """Only ever called once the filesystem is known not to be encrcdsa.

    `ipsw extract --files` mounts the filesystem internally. Handed an
    encrypted image it triggers a macOS passphrase dialog that can never be
    satisfied, so the caller must check first.
    """
    r = run(['ipsw', 'extract', '--files', '--pattern', AUDIO_RE, '--output', outdir, ipsw])
    n = sum(1 for p in glob.iglob(os.path.join(outdir, '**', '*'), recursive=True)
            if os.path.isfile(p))
    return (n > 0), r.stderr.strip()[-300:]


def rootfs_key(device, build, dmg_name):
    """Pull the vfdecrypt key for the filesystem DMG off theiphonewiki."""
    r = run(['ipsw', 'download', 'keys', '--device', device, '--build', build])
    text = r.stdout
    block = None
    for chunk in re.split(r'\n(?=\S*\s*‣)', text):
        if dmg_name in chunk:
            block = chunk
            break
    if not block:
        return None
    m = re.search(r'Key:\s*([0-9a-fA-F]{40,})', block)
    return m.group(1) if m else None


def extract_legacy(enc, dmgdir, device, build, outdir):
    """Decrypt an encrcdsa filesystem, then mount the decrypted result.

    hdiutil is never shown the encrypted image, so macOS never prompts.
    """
    name = os.path.basename(enc)
    key = rootfs_key(device, build, name)
    if not key:
        sys.exit('  %s is encrypted and no key is published for %s' % (name, build))
    print('  encrypted (encrcdsa); decrypting %s with the published key' % name)
    dec = os.path.join(dmgdir, 'decrypted.dmg')
    if run(['vfdecrypt', '-i', enc, '-k', key, '-o', dec]).returncode != 0 \
            or not os.path.exists(dec):
        sys.exit('  vfdecrypt failed')
    raw = os.path.join(dmgdir, 'rootfs.img')
    if run(['dmg2img', '-i', dec, '-o', raw]).returncode != 0 or not os.path.exists(raw):
        sys.exit('  dmg2img failed')
    os.remove(dec)
    if is_encrypted(raw):
        sys.exit('  refusing to mount: image is still encrypted after decryption')

    mountable = raw
    r = run(['hdiutil', 'attach', '-nobrowse', '-readonly', '-noverify', mountable],
            stdin=subprocess.DEVNULL)
    mount = None
    for line in r.stdout.splitlines():
        if '/Volumes/' in line:
            mount = line.split('\t')[-1].strip()
    if not mount:
        sys.exit('  mount failed: %s' % (r.stderr.strip() or r.stdout.strip())[-300:])
    print('  mounted at %s' % mount)
    try:
        dest = os.path.join(outdir, '%s__%s' % (build, device))
        n = 0
        for dirpath, _, filenames in os.walk(mount):
            for fn in filenames:
                if not fn.lower().endswith(AUDIO_EXT):
                    continue
                src = os.path.join(dirpath, fn)
                rel = os.path.relpath(src, mount)
                dst = os.path.join(dest, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                try:
                    shutil.copy2(src, dst)
                    n += 1
                except OSError:
                    pass
        return n
    finally:
        run(['hdiutil', 'detach', mount, '-force'], stdin=subprocess.DEVNULL)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--device', required=True)
    ap.add_argument('--build', required=True)
    ap.add_argument('--os', dest='osname', required=True)
    ap.add_argument('--work', default='_work')
    ap.add_argument('--keep-ipsw', action='store_true')
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    outdir = os.path.join(args.work, 'extract-%s' % args.build)
    if os.path.isdir(outdir) and any(os.scandir(outdir)):
        print('%s: already extracted at %s' % (args.osname, outdir))
        return

    meta = firmware_meta(args.device, args.build)
    print('%s (%s, %s) %.2f GB' % (args.osname, args.build, args.device,
                                   meta['filesize'] / 1e9))
    ipsw = download(args.device, args.build, args.work, meta)

    # Decide the era BEFORE anything can mount. `ipsw extract --files` attaches
    # the filesystem internally, so it must not be reached with an encrypted one.
    fsdmg, dmgdir, err = filesystem_dmg(ipsw, args.build, args.work)
    if fsdmg is None or dmgdir is None:
        sys.exit('  could not unpack the filesystem DMG: %s' % err)

    if is_encrypted(fsdmg):
        try:
            n = extract_legacy(fsdmg, dmgdir, args.device, args.build, outdir)
        finally:
            shutil.rmtree(dmgdir, ignore_errors=True)
    else:
        shutil.rmtree(dmgdir, ignore_errors=True)
        ok, err = extract_modern(ipsw, outdir)
        if not ok:
            sys.exit('  extraction failed: %s' % err)
        n = sum(1 for p in glob.iglob(os.path.join(outdir, '**', '*'), recursive=True)
                if os.path.isfile(p))

    print('  extracted %d audio files -> %s' % (n, outdir))
    if not args.keep_ipsw:
        os.remove(ipsw)
        print('  removed IPSW')


if __name__ == '__main__':
    main()
