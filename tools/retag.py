#!/usr/bin/env python3
"""Bring corpus release tags into line with tools/versions.json.

A release is recorded in the corpus by a human-readable tag ("iOS 8.0"), and
that tag is the key every sound's presence list is written against. When the
matrix grows, a tag that used to be unique may stop being: iOS 8.0 shipped as
both 12A365 and 12A366 on the same day, so both need the build in the tag.

This rewrites the tags in place. Where two ingested builds ended up sharing a
tag, their presence data was merged at ingest time and cannot be separated
here, so the loser is dropped from the corpus and must be re-ingested under
its corrected tag; the script says which.

    python3 tools/retag.py [--apply]
"""
import argparse
import collections
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default=os.path.join(ROOT, 'corpus.json'))
    ap.add_argument('--matrix', default=os.path.join(HERE, 'versions.json'))
    ap.add_argument('--apply', action='store_true', help='write the changes')
    args = ap.parse_args()

    corpus = json.load(open(args.corpus))
    want = {v['build']: v['os'] for v in json.load(open(args.matrix))['versions']}

    shared = collections.defaultdict(list)
    for v in corpus['versions']:
        shared[v['os']].append(v)

    rename, drop = {}, []
    for old, versions in shared.items():
        if len(versions) == 1:
            v = versions[0]
            new = want.get(v['build'])
            if new and new != old:
                rename[old] = new
            continue
        # Two builds wrote to one tag. The first ingested owns the data; the
        # rest contributed nothing that can be told apart and are dropped.
        versions.sort(key=lambda v: v['order'])
        keeper = versions[0]
        if want.get(keeper['build']):
            rename[old] = want[keeper['build']]
        drop.extend(versions[1:])

    print('%d tags to rename, %d versions to drop and re-ingest'
          % (len(rename), len(drop)))
    for old, new in sorted(rename.items()):
        print('  %-22s -> %s' % (old, new))
    for v in drop:
        print('  DROP %s (%s) -- re-ingest with: python3 tools/build-all.py --only %s'
              % (v['os'], v['build'], v['build']))
    if not args.apply:
        print('\nnothing written; re-run with --apply')
        return

    dropped = {v['build'] for v in drop}
    corpus['versions'] = [v for v in corpus['versions'] if v['build'] not in dropped]
    for v in corpus['versions']:
        v['os'] = rename.get(v['os'], v['os'])

    def fix(tags):
        return [rename.get(t, t) for t in tags]

    for e in corpus['entries']:
        e['versions'] = fix(e['versions'])
        for var in e['variants']:
            var['versions'] = fix(var['versions'])

    tags = [v['os'] for v in corpus['versions']]
    if len(set(tags)) != len(tags):
        sys.exit('tags are still not unique after rewriting; refusing to save')
    json.dump(corpus, open(args.corpus, 'w'), indent=1)
    print('\nwrote %s: %d versions, all tags unique' % (args.corpus, len(tags)))


if __name__ == '__main__':
    main()
