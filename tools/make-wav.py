#!/usr/bin/env python3
"""Rebuild the WAV/ mirror from Source/.

Every file in Source/ is decoded to an uncompressed WAV at the same relative
path. Sample rate and channel count are preserved; bit depth follows the
input (16-bit stays 16-bit, 24-bit inputs and all lossy decodes go to 24-bit)
rather than being flattened to a single depth.

Requires ffmpeg. On macOS, afconvert is used as a fallback for the handful of
CAF files that use Apple IMA4 ADPCM, which ffmpeg cannot parse.

    python3 tools/make-wav.py [--src Source] [--dst WAV] [--jobs 8]
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

# ffmpeg sample_fmt -> output PCM codec
DEPTH = {'u8': 'pcm_s16le', 's16': 'pcm_s16le', 's16p': 'pcm_s16le',
         'flt': 'pcm_s24le', 'fltp': 'pcm_s24le', 'dbl': 'pcm_s24le', 'dblp': 'pcm_s24le'}


def probe(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-select_streams', 'a:0', '-show_entries',
                        'stream=sample_fmt,bits_per_raw_sample', '-of', 'json', path],
                       capture_output=True, text=True)
    try:
        return json.loads(r.stdout)['streams'][0]
    except (ValueError, KeyError, IndexError):
        return None


def codec_for(stream):
    fmt = stream.get('sample_fmt', '')
    if fmt in DEPTH:
        return DEPTH[fmt]
    if fmt in ('s32', 's32p'):
        return 'pcm_s24le' if str(stream.get('bits_per_raw_sample')) == '24' else 'pcm_s32le'
    return 'pcm_s24le'


def convert(job):
    src, dst = job
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    stream = probe(src)
    if stream:
        r = subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', src, '-map', '0:a:0',
                            '-c:a', codec_for(stream), '-rf64', 'auto', dst],
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(dst):
            return ('ok', src, '')
    # ffmpeg could not read it (e.g. Apple IMA4 ADPCM in CAF) -- try Core Audio
    if shutil.which('afconvert'):
        r = subprocess.run(['afconvert', '-f', 'WAVE', '-d', 'LEI16', src, dst],
                           capture_output=True, text=True)
        if r.returncode == 0 and os.path.exists(dst):
            return ('ok-afconvert', src, '')
    return ('skipped', src, 'no decodable audio stream')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default='Source')
    ap.add_argument('--dst', default='WAV')
    ap.add_argument('--jobs', type=int, default=8)
    args = ap.parse_args()

    if not shutil.which('ffmpeg'):
        sys.exit('ffmpeg not found on PATH')

    jobs = [(os.path.join(dp, f),
             os.path.join(args.dst, os.path.relpath(dp, args.src),
                          os.path.splitext(f)[0] + '.wav'))
            for dp, _, fn in os.walk(args.src) for f in sorted(fn)]
    if not jobs:
        sys.exit('no files found under %s/' % args.src)

    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        results = list(ex.map(convert, jobs))

    for tag, path, why in results:
        if tag == 'skipped':
            print('skipped: %s (%s)' % (path, why), file=sys.stderr)
    done = sum(1 for r in results if r[0].startswith('ok'))
    print('converted %d/%d into %s/' % (done, len(jobs), args.dst))


if __name__ == '__main__':
    main()
