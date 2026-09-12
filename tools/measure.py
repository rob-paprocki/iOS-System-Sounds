#!/usr/bin/env python3
"""Measure every file in the content-addressed store: duration and peaks.

Two things the corpus does not record at ingest time and the site needs:

  duration  Chromaprint only returns a duration for material long enough to
            fingerprint, which is a small minority here -- the median system
            sound is under half a second. So most entries have no duration at
            all. ffprobe gives one for everything.

  peaks     48 amplitude buckets per sound, scaled per sound so a quiet tap
            still draws a shape. The site renders a waveform for every row,
            which it cannot do by decoding thousands of files in the browser.

Results are cached by MD5 in _store/measure.json, so re-running only measures
files added since last time.

    python3 tools/measure.py [--store _store] [--jobs 8]
"""
import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundlib as S

BUCKETS = 48


def duration_of(path):
    r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                        '-of', 'default=nw=1:nk=1', path], capture_output=True, text=True)
    try:
        d = float(r.stdout.strip())
        return round(d, 3) if d > 0 else None
    except ValueError:
        return None


def peaks_of(path):
    """48 amplitude buckets, 0-255, normalised to this sound's own maximum."""
    pcm = S.norm_pcm(path, rate=8000, max_seconds=30)
    if not pcm or len(pcm) < BUCKETS:
        return None
    step = len(pcm) / float(BUCKETS)
    out, peak = [], 0
    for i in range(BUCKETS):
        lo, hi = int(i * step), max(int(i * step) + 1, int((i + 1) * step))
        v = max(abs(x) for x in pcm[lo:hi])
        out.append(v)
        peak = max(peak, v)
    if peak <= 0:
        return [0] * BUCKETS
    return [min(255, int(round(v * 255.0 / peak))) for v in out]


def measure(job):
    md5, path = job
    return md5, {'duration': duration_of(path), 'peaks': peaks_of(path)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--store', default='_store')
    ap.add_argument('--cache', default=None)
    ap.add_argument('--jobs', type=int, default=8)
    args = ap.parse_args()
    cache_path = args.cache or os.path.join(args.store, 'measure.json')

    cache = json.load(open(cache_path)) if os.path.exists(cache_path) else {}
    jobs = []
    for dirpath, _, names in os.walk(args.store):
        for n in names:
            md5, ext = os.path.splitext(n)
            if ext.lower() not in S.AUDIO_EXT or md5 in cache:
                continue
            jobs.append((md5, os.path.join(dirpath, n)))

    print('%d already measured, %d to do' % (len(cache), len(jobs)))
    if jobs:
        with ThreadPoolExecutor(max_workers=args.jobs) as ex:
            for i, (md5, data) in enumerate(ex.map(measure, jobs), 1):
                cache[md5] = data
                if i % 500 == 0:
                    print('  %d/%d' % (i, len(jobs)), flush=True)
                    json.dump(cache, open(cache_path, 'w'))
        json.dump(cache, open(cache_path, 'w'))

    got_d = sum(1 for v in cache.values() if v.get('duration') is not None)
    got_p = sum(1 for v in cache.values() if v.get('peaks'))
    print('%d files: %d with duration, %d with peaks -> %s'
          % (len(cache), got_d, got_p, cache_path))


if __name__ == '__main__':
    main()
