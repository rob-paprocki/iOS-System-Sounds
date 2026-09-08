#!/usr/bin/env python3
"""Fold one extracted iOS version into the cross-version corpus.

A sound is identified at four levels, strongest first:

  1. file MD5           exactly the same bytes
  2. decoded-PCM MD5    same audio, re-wrapped or losslessly re-encoded
  3. Chromaprint        same audio re-encoded lossily, for material long
                        enough to fingerprint (roughly 3 seconds and up)
  4. PCM correlation    the same, for short sounds. System sounds have a
                        median duration under half a second, far below what
                        Chromaprint can use, so without this tier a lossily
                        re-encoded alert would look like the old one being
                        deleted and a new one appearing.

Levels 3 and 4 only ever compare files that share an original filename, so a
similarity score can never merge two unrelated sounds.

    python3 tools/ingest.py --extract _work/extract-8A293 --os "iOS 4.0" \
        --build 8A293 --device iPhone3,1 --model "iPhone 4"
"""
import argparse
import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import soundlib as S

FP_THRESHOLD = 0.85        # Chromaprint bit agreement
PCM_THRESHOLD = 0.75       # correlation; a 64k AAC re-encode scores ~0.86,
                           # unrelated sounds score 0.00


def load(path):
    if os.path.exists(path):
        return json.load(open(path))
    return {'versions': [], 'entries': []}


def store_path(store, md5, ext):
    return os.path.join(store, md5[:2], md5 + ext)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--extract', required=True)
    ap.add_argument('--os', dest='osname', required=True)
    ap.add_argument('--build', required=True)
    ap.add_argument('--device', required=True)
    ap.add_argument('--model', default='')
    ap.add_argument('--corpus', default='corpus.json')
    ap.add_argument('--store', default='_store')
    args = ap.parse_args()

    corpus = load(args.corpus)
    if any(v['build'] == args.build for v in corpus['versions']):
        sys.exit('build %s is already in the corpus' % args.build)
    # Chronological rank comes from the canonical matrix, not ingest order,
    # so versions can be ingested or re-ingested in any sequence.
    matrix = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'versions.json')
    chrono = [v['build'] for v in json.load(open(matrix))['versions']]
    rank = chrono.index(args.build) if args.build in chrono else len(chrono)
    corpus['versions'].append({'os': args.osname, 'build': args.build,
                               'device': args.device, 'model': args.model,
                               'order': rank})
    tag = args.osname

    by_md5, by_pcm, by_name = {}, {}, {}
    for e in corpus['entries']:
        for v in e['variants']:
            by_md5[v['md5']] = (e, v)
            by_name.setdefault(v['original_name'].lower(), []).append(e)
        if e.get('pcm_md5'):
            by_pcm[e['pcm_md5']] = e

    os.makedirs(args.store, exist_ok=True)
    pcm_cache = {}

    def cached_pcm(entry):
        """Decode an existing entry's stored file, for tier-4 comparison."""
        key = id(entry)
        if key not in pcm_cache:
            rep = entry['variants'][0]
            p = store_path(args.store, rep['md5'], rep['ext'])
            pcm_cache[key] = S.norm_pcm(p) if os.path.exists(p) else None
        return pcm_cache[key]

    stats = dict(files=0, exact=0, pcm=0, fp=0, corr=0, new=0, undecodable=0)

    for full, rel in S.walk_audio(args.extract):
        stats['files'] += 1
        name = os.path.basename(rel)
        stem, ext = os.path.splitext(name)
        md5 = S.file_md5(full)

        hit = by_md5.get(md5)
        if hit:
            entry, variant = hit
            for coll in (variant['versions'], entry['versions']):
                if tag not in coll:
                    coll.append(tag)
            stats['exact'] += 1
            continue

        pcm = S.pcm_md5(full)
        if pcm is None:
            stats['undecodable'] += 1
        entry = by_pcm.get(pcm) if pcm else None
        fp = None
        if entry:
            stats['pcm'] += 1
        else:
            candidates = by_name.get(name.lower(), [])
            if candidates:
                fp = S.fingerprint(full)
                if fp:
                    for cand in candidates:
                        if cand.get('fp') and \
                                S.fp_similarity(fp[1], cand['fp']) >= FP_THRESHOLD:
                            entry = cand
                            stats['fp'] += 1
                            break
                if entry is None:
                    mine = S.norm_pcm(full)
                    if mine:
                        for cand in candidates:
                            theirs = cached_pcm(cand)
                            if theirs and S.pcm_similarity(mine, theirs) >= PCM_THRESHOLD:
                                entry = cand
                                stats['corr'] += 1
                                break

        real_ext = S.real_extension(full, ext)
        # Category and title are recorded per variant: a sound can move between
        # directories across releases, and the newest location is the useful one.
        vcat = S.category(rel, name)
        variant = {'md5': md5, 'ext': real_ext, 'bytes': os.path.getsize(full),
                   'original_name': name, 'ipsw_dir': os.path.dirname(rel),
                   'category': vcat, 'title': S.title_for(vcat, stem),
                   'versions': [tag]}

        if entry is None:
            cat = vcat
            entry = {'category': cat, 'title': S.title_for(cat, stem),
                     'pcm_md5': pcm, 'fp': fp[1] if fp else None,
                     'duration': fp[0] if fp else None,
                     'versions': [tag], 'variants': [variant]}
            corpus['entries'].append(entry)
            if pcm:
                by_pcm[pcm] = entry
            stats['new'] += 1
        else:
            entry['variants'].append(variant)
            if tag not in entry['versions']:
                entry['versions'].append(tag)

        by_md5[md5] = (entry, variant)
        by_name.setdefault(name.lower(), []).append(entry)

        dest = store_path(args.store, md5, real_ext)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            shutil.copy2(full, dest)

    json.dump(corpus, open(args.corpus, 'w'), indent=1)
    print('%s (%s): %d files scanned' % (args.osname, args.build, stats['files']))
    for label, key in (('new sounds', 'new'), ('exact duplicates', 'exact'),
                       ('matched by PCM hash', 'pcm'), ('matched by fingerprint', 'fp'),
                       ('matched by correlation', 'corr'), ('undecodable', 'undecodable')):
        print('  %-24s %d' % (label, stats[key]))
    print('corpus: %d sounds across %d versions'
          % (len(corpus['entries']), len(corpus['versions'])))


if __name__ == '__main__':
    main()
