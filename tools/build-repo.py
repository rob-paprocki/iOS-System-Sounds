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
import csv
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SPOKEN_PREFIX = 'Spoken Content'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--corpus', default='corpus.json')
    ap.add_argument('--store', default='_store')
    ap.add_argument('--out', default='.')
    ap.add_argument('--matrix', default=os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                     'versions.json'))
    args = ap.parse_args()

    corpus = json.load(open(args.corpus))
    # Durations come from tools/measure.py, not from the corpus: Chromaprint
    # only reports one for material long enough to fingerprint, which most
    # system sounds are not.
    mpath = os.path.join(args.store, 'measure.json')
    measured = json.load(open(mpath)) if os.path.exists(mpath) else {}
    # Chronological rank is re-derived from the matrix every time. The matrix
    # grows as more releases are added, so a rank stored at ingest time goes
    # stale; the matrix is the single source of order.
    if os.path.exists(args.matrix):
        chrono = [v['build'] for v in json.load(open(args.matrix))['versions']]
        for v in corpus['versions']:
            if v['build'] in chrono:
                v['order'] = chrono.index(v['build'])
        json.dump(corpus, open(args.corpus, 'w'), indent=1)
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
            'duration_sec': (measured.get(rep['md5'], {}).get('duration')
                             or e.get('duration')),
            'original_filename': rep['original_name'],
            'ipsw_dir': rep['ipsw_dir'],
            'md5': rep['md5'],
            'variants': [{'md5': v['md5'], 'format': v['ext'].lstrip('.'),
                          'bytes': v['bytes'], 'versions': v['versions']}
                         for v in e['variants']],
        })

    # A sound that was re-recorded rather than deleted shows up as two entries
    # with the same category and title and different audio. Link them, so the
    # index can say "replaced in iOS 7" instead of showing an unexplained
    # removal next to an unexplained addition.
    groups = {}
    for d in index:
        groups.setdefault((d['category'], d['title']), []).append(d)
    for members in groups.values():
        if len(members) < 2:
            continue
        members.sort(key=lambda d: order.get(d['introduced_in'], 0))
        for i, d in enumerate(members):
            d['rerecorded'] = True
            d['rerecorded_with'] = [m['md5'] for m in members if m is not d]
            if i + 1 < len(members):
                d['replaced_by_in'] = members[i + 1]['introduced_in']

    index.sort(key=lambda d: d['file'])
    json.dump({'versions': versions,
               'counts': {'total': len(index),
                          'present': sum(1 for d in index if d['status'] == 'present'),
                          'removed': sum(1 for d in index if d['status'] == 'removed'),
                          'trees': counts},
               'sounds': index},
              open(os.path.join(args.out, 'sounds.json'), 'w'), indent=1, ensure_ascii=False)

    # The same data as a spreadsheet, for people who are not going to parse
    # JSON. One row per sound, one column per fact, releases as a list.
    with open(os.path.join(args.out, 'sounds.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['file', 'title', 'category', 'status', 'introduced_in',
                    'last_seen_in', 'releases', 'format', 'duration_sec',
                    'bytes', 'original_filename', 'ipsw_dir', 'rerecorded', 'md5'])
        for d in index:
            w.writerow([d['file'], d['title'], d['category'], d['status'],
                        d['introduced_in'], d['last_seen_in'],
                        '; '.join(d['versions']), d['format'],
                        d['duration_sec'] if d['duration_sec'] else '',
                        d['bytes'], d['original_filename'], d['ipsw_dir'],
                        'yes' if d.get('rerecorded') else '', d['md5']])

    print('versions: %s' % ', '.join(v['os'] for v in versions))
    for tree, n in counts.items():
        print('  %-16s %d files' % (tree + '/', n))
    print('  %d sounds total, %d no longer in %s'
          % (len(index), sum(1 for d in index if d['status'] == 'removed'), newest))
    print('  %d with a measured duration, %d in a re-recorded set'
          % (sum(1 for d in index if d.get('duration_sec')),
             sum(1 for d in index if d.get('rerecorded'))))


if __name__ == '__main__':
    main()
