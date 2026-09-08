#!/usr/bin/env python3
"""Build the browsable Current/ and Removed/ trees from the corpus.

A sound is "current" if it is present in the newest ingested version and
"removed" if it is not, whatever release it last appeared in. Bulk spoken-word
content (Nike+ workout prompts and the like) is kept in its own top-level tree
so it does not swamp the system sounds; its removal status lives in the index.

    python3 tools/build-repo.py [--corpus corpus.json] [--store _store]
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SPOKEN_PREFIX = 'Spoken Content'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default='corpus.json')
    ap.add_argument('--store', default='_store')
    ap.add_argument('--out', default='.')
    args = ap.parse_args()

    corpus = json.load(open(args.corpus))
    versions = sorted(corpus['versions'], key=lambda v: v['order'])
    order = {v['os']: v['order'] for v in versions}
    newest = versions[-1]['os']

    for tree in ('Current', 'Removed', SPOKEN_PREFIX):
        shutil.rmtree(os.path.join(args.out, tree), ignore_errors=True)

    index, taken, counts = [], set(), {'Current': 0, 'Removed': 0, SPOKEN_PREFIX: 0}

    for e in corpus['entries']:
        seen = sorted(e['versions'], key=lambda t: order.get(t, 0))
        present = newest in e['versions']
        rep = max(e['variants'],
                  key=lambda v: max(order.get(t, 0) for t in v['versions']))
        cat = rep.get('category', e['category'])
        title = rep.get('title', e['title'])
        spoken = cat.startswith(SPOKEN_PREFIX)

        if spoken:
            root, rel_cat = SPOKEN_PREFIX, cat[len(SPOKEN_PREFIX):].lstrip('/')
        else:
            root, rel_cat = ('Current' if present else 'Removed'), cat

        folder = os.path.join(root, rel_cat) if rel_cat else root
        name, n = title + rep['ext'], 2
        while os.path.join(folder, name).lower() in taken:
            name = '%s (%d)%s' % (title, n, rep['ext'])
            n += 1
        taken.add(os.path.join(folder, name).lower())

        src = os.path.join(args.store, rep['md5'][:2], rep['md5'] + rep['ext'])
        dst = os.path.join(args.out, folder, name)
        if not os.path.exists(src):
            print('missing from store: %s (%s)' % (title, rep['md5']), file=sys.stderr)
            continue
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        counts[root] += 1

        index.append({
            'file': os.path.join(folder, name),
            'title': title,
            'category': cat,
            'status': 'present' if present else 'removed',
            'introduced_in': seen[0],
            'last_seen_in': seen[-1],
            'versions': seen,
            'format': rep['ext'].lstrip('.'),
            'bytes': rep['bytes'],
            'duration_sec': e.get('duration'),
            'original_filename': rep['original_name'],
            'ipsw_dir': rep['ipsw_dir'],
            'md5': rep['md5'],
            'variants': [{'md5': v['md5'], 'format': v['ext'].lstrip('.'),
                          'bytes': v['bytes'], 'versions': v['versions']}
                         for v in e['variants']],
        })

    index.sort(key=lambda d: d['file'])
    json.dump({'versions': versions,
               'counts': {'total': len(index),
                          'present': sum(1 for d in index if d['status'] == 'present'),
                          'removed': sum(1 for d in index if d['status'] == 'removed'),
                          'trees': counts},
               'sounds': index},
              open(os.path.join(args.out, 'sounds.json'), 'w'), indent=1, ensure_ascii=False)

    print('versions: %s' % ', '.join(v['os'] for v in versions))
    for tree, n in counts.items():
        print('  %-16s %d files' % (tree + '/', n))
    print('  %d sounds total, %d no longer in %s'
          % (len(index), sum(1 for d in index if d['status'] == 'removed'), newest))


if __name__ == '__main__':
    main()
