#!/usr/bin/env python3
"""Run the whole pipeline: fetch, extract and ingest every version in order.

Safe to re-run. Versions already in the corpus are skipped, and extractions
already on disk are reused, so an interrupted run picks up where it stopped.
Each IPSW is deleted once its audio has been extracted.

    python3 tools/build-all.py              # everything in tools/versions.json
    python3 tools/build-all.py --only 8A293 14A403
    python3 tools/build-all.py --keep-extracts
"""
import argparse
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matrix', default=os.path.join(HERE, 'versions.json'))
    ap.add_argument('--corpus', default='corpus.json')
    ap.add_argument('--store', default='_store')
    ap.add_argument('--work', default='_work')
    ap.add_argument('--only', nargs='*', help='limit to these build IDs')
    ap.add_argument('--keep-extracts', action='store_true',
                    help='keep per-version extractions after ingest')
    args = ap.parse_args()

    plan = json.load(open(args.matrix))['versions']
    if args.only:
        plan = [v for v in plan if v['build'] in args.only]

    done = set()
    if os.path.exists(args.corpus):
        done = {v['build'] for v in json.load(open(args.corpus))['versions']}

    for v in plan:
        if v['build'] in done:
            print('== %s (%s): already in corpus, skipping' % (v['os'], v['build']))
            continue
        print('== %s (%s, %s)' % (v['os'], v['build'], v['device']))
        extract = os.path.join(args.work, 'extract-%s' % v['build'])

        if not (os.path.isdir(extract) and any(os.scandir(extract))):
            r = subprocess.run([sys.executable, os.path.join(HERE, 'fetch-version.py'),
                                '--device', v['device'], '--build', v['build'],
                                '--os', v['os'], '--work', args.work])
            if r.returncode != 0:
                print('   fetch failed, skipping %s' % v['build'], file=sys.stderr)
                continue

        r = subprocess.run([sys.executable, os.path.join(HERE, 'ingest.py'),
                            '--extract', extract, '--os', v['os'], '--build', v['build'],
                            '--device', v['device'], '--model', v.get('model', ''),
                            '--corpus', args.corpus, '--store', args.store])
        if r.returncode != 0:
            print('   ingest failed for %s' % v['build'], file=sys.stderr)
            continue
        if not args.keep_extracts:
            subprocess.run(['rm', '-rf', extract])

    print('\n== building trees')
    subprocess.run([sys.executable, os.path.join(HERE, 'build-repo.py'),
                    '--corpus', args.corpus, '--store', args.store])


if __name__ == '__main__':
    main()
