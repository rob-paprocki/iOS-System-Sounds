#!/usr/bin/env python3
"""Build everything the web front end needs. See docs/website-design-notes.md.

The collection is deliberately mixed-format because iOS is, and most of it
will not play in a browser: CAF is Safari-only, AIFF is effectively
Safari-only, and the Apple IMA4 ADPCM files play nowhere. A site that lets
people audition sounds therefore needs a second, web-safe copy. AAC in an MP4
container is the only format every current browser decodes.

Outputs, all under web/:

  audio/...m4a      AAC preview of every sound, mirroring the repository tree.
                    Preview quality, not archival. Playback uses this; download
                    always gives the original.
  index.core.json   what search and the list need, fetched on load.
  index.detail.json paths, per-release presence and provenance, fetched at idle.
  peaks.bin         48 amplitude bytes per sound, in index order. One fetch
                    draws a waveform for every row.
  shelves.json      the hand-written zero state.
  zips/             prebuilt per-category archives, each carrying the copyright
                    notice and a manifest.

Records in the two index files share one order, and peaks.bin is in that same
order, so the browser joins them by position rather than by key.

    python3 tools/make-web.py [--jobs 8] [--bitrate 96k] [--no-zips]
"""
import argparse
import collections
import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor

BUCKETS = 48
NOTICE = ("These sounds are Apple's copyright, collected here for reference, "
          "preservation and research. Downloading one does not give you a "
          "licence to use it.\n")

# The zero state. Editorial, not computed: the corpus is dominated by its
# least interesting parts, so raw counts must never choose what is shown.
SHELVES = [
    {'title': 'The ones everybody is looking for',
     'match': ['Tri Tone', 'Tritone', 'Sms Received 1', 'Sms Received 3',
               'Marimba', 'Old Phone', 'Sent Message', 'Received Message',
               'Lock', 'Unlock', 'Photo Shutter', 'Low Power', 'Charging',
               'Tink', 'Tock', 'Keyboard Press Clear']},
    {'title': 'Gone from iOS',
     'status': 'removed',
     'categories': ['UI Sounds', 'Ringtones & Alert Tones',
                    'Telephony & Messaging']},
    {'title': 'Unchanged since 2007',
     'first_build': 0,
     'status': 'present'},
]


def source_codec(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0',
                        '-show_entries', 'stream=codec_name', '-of',
                        'default=nw=1:nk=1', path], capture_output=True, text=True)
    return r.stdout.strip()


def encode(job):
    src, dst, bitrate = job
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
        return ('cached', src)

    # Roughly a third of the collection is already AAC, just sometimes in a CAF
    # container rather than an MP4 one. Re-encoding those would lose a
    # generation for nothing, so copy the stream and change the wrapper.
    if source_codec(src) == 'aac':
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:a:0',
                            '-c:a', 'copy', '-movflags', '+faststart', dst],
                           capture_output=True)
        if r.returncode == 0 and os.path.exists(dst):
            return ('copied', src)

    base = ['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:a:0',
            '-c:a', 'aac', '-b:a', bitrate, '-movflags', '+faststart', dst]
    if subprocess.run(base, capture_output=True).returncode == 0 and os.path.exists(dst):
        return ('ok', src)
    # ffmpeg cannot read Apple IMA4 ADPCM in CAF. Core Audio can, so decode
    # through it to a temporary WAV and encode that instead.
    if shutil.which('afconvert'):
        tmp = tempfile.mktemp(suffix='.wav')
        try:
            if subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16', src, tmp],
                              capture_output=True).returncode == 0:
                r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-map', '0:a:0',
                                    '-c:a', 'aac', '-b:a', bitrate,
                                    '-movflags', '+faststart', dst], capture_output=True)
                if r.returncode == 0 and os.path.exists(dst):
                    return ('ok-afconvert', src)
        finally:
            if os.path.exists(tmp):
                os.remove(tmp)
    return ('skipped', src)


def build_zips(records, out):
    """One archive per top-level category, plus the whole collection."""
    zdir = os.path.join(out, 'zips')
    os.makedirs(zdir, exist_ok=True)
    groups = {'all-sounds': records}
    for r in records:
        top = r['category'].split('/')[0]
        groups.setdefault(top.lower().replace(' & ', '-').replace(' ', '-'), []).append(r)

    made = []
    for name, items in sorted(groups.items()):
        path = os.path.join(zdir, name + '.zip')
        # Audio is already compressed; storing is faster and the same size.
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
            z.writestr('NOTICE.txt', NOTICE)
            z.writestr('manifest.json', json.dumps(
                [{'title': r['title'], 'category': r['category'],
                  'file': r['file'], 'format': r['format'],
                  'first_seen': r['first_seen'], 'last_seen': r['last_seen'],
                  'ipsw_dir': r['dir']} for r in items], indent=1))
            for r in items:
                if os.path.exists(r['file']):
                    z.write(r['file'], r['file'])
        made.append((name, len(items), os.path.getsize(path)))
    return made


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default='sounds.json')
    ap.add_argument('--store', default='_store')
    ap.add_argument('--out', default='web')
    ap.add_argument('--jobs', type=int, default=8)
    ap.add_argument('--bitrate', default='96k')
    ap.add_argument('--no-audio', action='store_true')
    ap.add_argument('--no-zips', action='store_true')
    args = ap.parse_args()

    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg not found on PATH')
    index = json.load(open(args.index))
    versions = sorted(index['versions'], key=lambda v: v['order'])
    vpos = {v['os']: i for i, v in enumerate(versions)}
    mpath = os.path.join(args.store, 'measure.json')
    measured = json.load(open(mpath)) if os.path.exists(mpath) else {}
    if not measured:
        print('no %s; run tools/measure.py first or the site gets no waveforms'
              % mpath, file=sys.stderr)

    jobs, rows, missing = [], [], 0
    for s in index['sounds']:
        if not os.path.exists(s['file']):
            missing += 1
            continue
        rel = os.path.splitext(s['file'])[0] + '.m4a'
        jobs.append((s['file'], os.path.join(args.out, 'audio', rel), args.bitrate))
        rows.append((s, rel))

    if args.no_audio:
        # The index must never list a preview that is not there, so when the
        # encode is skipped, fall back to what is already on disk.
        rows = [(s, rel) for s, rel in rows
                if os.path.exists(os.path.join(args.out, 'audio', rel))]
        print('reusing %d previews already built' % len(rows))
    else:
        os.makedirs(args.out, exist_ok=True)
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            results = list(ex.map(encode, jobs))
        for tag, path in results:
            if tag == 'skipped':
                print('no decodable audio: %s' % path, file=sys.stderr)
        playable = set(p for tag, p, in results if tag != 'skipped')
        rows = [(s, rel) for s, rel in rows if s['file'] in playable]
        tally = collections.Counter(tag for tag, _ in results)
        print('previews: %d total (%s)'
              % (len(rows), ', '.join('%d %s' % (n, t) for t, n in tally.most_common())))

    core, detail, peaks = [], [], bytearray()
    for s, rel in rows:
        m = measured.get(s['md5'], {})
        core.append({
            'id': s['md5'][:12],
            'title': s['title'],
            'category': s['category'],
            'status': s['status'],
            'format': s['format'],
            'duration': m.get('duration') or s.get('duration_sec'),
            'first': vpos.get(s['introduced_in']),
            'last': vpos.get(s['last_seen_in']),
            'original': s['original_filename'],
        })
        d = {'id': s['md5'][:12],
             'file': s['file'],
             'preview': 'audio/' + rel,
             'bytes': s['bytes'],
             'in': sorted(vpos[t] for t in s['versions'] if t in vpos),
             'dir': s['ipsw_dir']}
        if s.get('rerecorded'):
            d['rerecorded'] = True
            d['rerecorded_with'] = [h[:12] for h in s.get('rerecorded_with', [])]
            if s.get('replaced_by_in'):
                d['replaced_in'] = vpos.get(s['replaced_by_in'])
        detail.append(d)
        p = m.get('peaks')
        peaks.extend(bytes(p) if p and len(p) == BUCKETS else bytes(BUCKETS))

    os.makedirs(args.out, exist_ok=True)
    cats = {}
    for r in core:
        cats[r['category']] = cats.get(r['category'], 0) + 1

    def dump(name, obj):
        path = os.path.join(args.out, name)
        json.dump(obj, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
        return os.path.getsize(path)

    n_core = dump('index.core.json', {
        'versions': [{'os': v['os'], 'build': v['build'], 'device': v['device'],
                      'model': v['model']} for v in versions],
        'categories': [{'name': k, 'count': cats[k]} for k in sorted(cats)],
        'counts': {'total': len(core),
                   'present': sum(1 for r in core if r['status'] == 'present'),
                   'removed': sum(1 for r in core if r['status'] == 'removed')},
        'peaks': {'file': 'peaks.bin', 'buckets': BUCKETS},
        'sounds': core,
    })
    n_detail = dump('index.detail.json', {'sounds': detail})
    with open(os.path.join(args.out, 'peaks.bin'), 'wb') as fh:
        fh.write(bytes(peaks))
    dump('shelves.json', SHELVES)

    print('%d sounds, %d categories, %d builds' % (len(core), len(cats), len(versions)))
    print('  index.core.json   %.2f MB' % (n_core / 1e6))
    print('  index.detail.json %.2f MB' % (n_detail / 1e6))
    print('  peaks.bin         %.2f MB (%d x %d bytes)'
          % (len(peaks) / 1e6, len(core), BUCKETS))
    print('  with waveform     %d/%d' % (sum(1 for r in rows
                                             if measured.get(r[0]['md5'], {}).get('peaks')),
                                         len(rows)))
    print('  with duration     %d/%d' % (sum(1 for r in core if r['duration']), len(core)))

    if not args.no_zips:
        zrows = [{'title': s['title'], 'category': s['category'], 'file': s['file'],
                  'format': s['format'], 'first_seen': s['introduced_in'],
                  'last_seen': s['last_seen_in'], 'dir': s['ipsw_dir']}
                 for s, _ in rows]
        for name, n, size in build_zips(zrows, args.out):
            print('  zips/%-28s %5d files  %7.1f MB' % (name + '.zip', n, size / 1e6))

    if missing:
        print('%d index entries had no file on disk' % missing, file=sys.stderr)


if __name__ == '__main__':
    main()
