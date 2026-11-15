#!/usr/bin/env python3
"""Recover corpus.json and _store/ from a clean clone.

corpus.json and _store/ are ingest working state and are not committed, so a
fresh clone cannot ingest a new release without re-running every IPSW. This
rebuilds both from what is committed: sounds.json says which variants exist and
where each one shipped, and the Current/, Removed/ and Spoken Content/ trees
hold each sound's representative file byte for byte.

What cannot be recovered is the bytes of a sound's older, non-representative
variants. Their MD5s are kept, so a new release that ships one of them still
counts as an exact match; build-repo.py only ever copies the representative.
The PCM hash and Chromaprint fingerprint are recomputed from the
representative file.

    python3 tools/rebuild-corpus.py
    python3 tools/measure.py
    python3 tools/build-repo.py     # should reproduce sounds.json unchanged
"""
import argparse
import json
import os
import re
import shutil
import sys
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundlib as S

SUFFIX = re.compile(r'^(.*) \((\d+)\)$')


def order_key(sound):
    # build-repo.py names collisions "Title (2)" in corpus order, so the
    # unsuffixed file must come first to be reproduced under the same name.
    folder, name = os.path.split(sound['file'])
    stem = os.path.splitext(name)[0]
    m = SUFFIX.match(stem)
    return (folder.lower(), (m.group(1) if m else stem).lower(),
            int(m.group(2)) if m else 1)


def rebuild(job):
    sound, root, store = job
    src = os.path.join(root, sound['file'])
    ext = '.' + sound['format']
    if S.file_md5(src) != sound['md5']:
        sys.exit('%s does not match its md5 in sounds.json' % sound['file'])
    dest = os.path.join(store, sound['md5'][:2], sound['md5'] + ext)
    if not os.path.exists(dest):
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        shutil.copy2(src, dest)

    def variant(v):
        return {'md5': v['md5'], 'ext': '.' + v['format'], 'bytes': v['bytes'],
                'original_name': sound['original_filename'],
                'ipsw_dir': sound['ipsw_dir'], 'category': sound['category'],
                'title': sound['title'], 'versions': v['versions']}

    fp = S.fingerprint(src)
    return {'category': sound['category'], 'title': sound['title'],
            'pcm_md5': S.pcm_md5(src), 'fp': fp[1] if fp else None,
            'duration': fp[0] if fp else None, 'versions': sound['versions'],
            'variants': [variant(v) for v in sound['variants']]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--index', default='sounds.json')
    ap.add_argument('--root', default='.')
    ap.add_argument('--corpus', default='corpus.json')
    ap.add_argument('--store', default='_store')
    ap.add_argument('--jobs', type=int, default=8)
    args = ap.parse_args()

    if os.path.exists(args.corpus):
        sys.exit('%s already exists; not overwriting it' % args.corpus)
    index = json.load(open(args.index, encoding='utf-8'))
    sounds = sorted(index['sounds'], key=order_key)
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        entries = list(ex.map(rebuild, [(s, args.root, args.store) for s in sounds]))

    json.dump({'versions': index['versions'], 'entries': entries},
              open(args.corpus, 'w'), indent=1)
    print('corpus: %d sounds across %d versions, store at %s'
          % (len(entries), len(index['versions']), args.store))


if __name__ == '__main__':
    main()
