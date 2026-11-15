#!/usr/bin/env python3
"""Regenerate tools/versions.json -- the matrix of IPSWs this repository extracts.

The matrix is derived, not hand-written, so it can be re-derived when Apple
ships more releases. It comes from the ipsw.me firmware API and has two tiers:

  A  one IPSW per iOS major.minor line, from 1.0 to the present. The FIRST
     build of each line, because that is where a release's new audio first
     appears. Where several devices received that build, the newest hardware
     generation wins, and the largest image within that generation -- a
     Pro-class image carries assets a small-storage or older model does not.

  B  every iPhone launch build not already picked up by tier A. A phone's
     launch build is frequently exclusive to that phone, and it is the only
     place hardware-specific audio (Action Button, Camera Control, MagSafe,
     Face ID, Taptic) exists.

  C  extra patch-level builds named in tools/extra-builds.json, for the
     x.y.z releases where audio demonstrably changed mid-cycle.

  D  every build Apple published for exactly one iPhone. If only one model
     ever received an image, that image is the only place anything specific
     to it exists. Computed, not listed: it falls straight out of the
     firmware table.

Builds already present in corpus.json are kept as-is, on the device they were
originally taken from, so re-deriving the matrix never invalidates prior work.

    python3 tools/plan.py                 # rewrite tools/versions.json
    python3 tools/plan.py --check         # HEAD every URL, report dead ones
"""
import argparse
import collections
import concurrent.futures as cf
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
API = 'https://api.ipsw.me/v4'


def vkey(v):
    p = re.findall(r'\d+', v)
    return tuple(int(x) for x in (p + ['0', '0', '0'])[:3])


def generation(device):
    return int(device[len('iPhone'):].split(',')[0])


def fetch_all(cache):
    if os.path.exists(cache):
        return json.load(open(cache))
    devices = json.load(urllib.request.urlopen(API + '/devices', timeout=60))
    out = {}
    for d in devices:
        ident = d['identifier']
        if not ident.startswith('iPhone'):
            continue
        for attempt in range(4):
            try:
                out[ident] = json.load(urllib.request.urlopen(
                    '%s/device/%s' % (API, ident), timeout=60))
                break
            except Exception:
                pass
        else:
            print('could not fetch %s' % ident, file=sys.stderr)
    json.dump(out, open(cache, 'w'))
    return out


def flatten(data):
    rows = []
    for dev, d in data.items():
        for f in d.get('firmwares', []):
            rows.append({'device': dev, 'model': d.get('name', ''),
                         'version': f['version'], 'build': f['buildid'],
                         'date': (f.get('releasedate') or '')[:10],
                         'size': f['filesize'], 'url': f['url']})
    return rows


def choose(candidates):
    """Newest hardware generation, then the largest image in it."""
    return max(candidates, key=lambda r: (generation(r['device']), r['size']))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cache', default=os.path.join(ROOT, 'research', 'ipswme-iphone.json'))
    ap.add_argument('--corpus', default=os.path.join(ROOT, 'corpus.json'))
    ap.add_argument('--extra', default=os.path.join(HERE, 'extra-builds.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'versions.json'))
    ap.add_argument('--check', action='store_true', help='HEAD every chosen URL')
    args = ap.parse_args()

    rows = flatten(fetch_all(args.cache))

    ingested = {}
    if os.path.exists(args.corpus):
        for v in json.load(open(args.corpus))['versions']:
            ingested[v['build']] = v['device']

    by_minor = collections.defaultdict(list)
    for r in rows:
        by_minor['%d.%d' % vkey(r['version'])[:2]].append(r)

    picked, seen = [], set()

    def add(row, tier, reason):
        if row['build'] in seen:
            return
        seen.add(row['build'])
        picked.append(dict(row, tier=tier, reason=reason))

    for line in sorted(by_minor, key=lambda s: tuple(int(x) for x in s.split('.'))):
        items = by_minor[line]
        done = [r for r in items if r['build'] in ingested]
        if done:
            build, reason = done[0]['build'], 'already ingested'
        else:
            build = min(items, key=lambda r: (vkey(r['version']), r['date'] or '9999'))['build']
            reason = 'first build of the %s line' % line
        cands = [r for r in items if r['build'] == build]
        if build in ingested:
            cands = [r for r in cands if r['device'] == ingested[build]] or cands
            row = cands[0]
        else:
            row = choose(cands)
        add(row, 'A', reason)

    by_device = collections.defaultdict(list)
    for r in rows:
        if r['date']:
            by_device[r['device']].append(r)
    for dev in sorted(by_device, key=generation):
        first = min(by_device[dev], key=lambda r: (vkey(r['version']), r['date']))
        add(first, 'B', 'launch build, %s' % first['model'])

    if os.path.exists(args.extra):
        wanted = json.load(open(args.extra))
        by_build = collections.defaultdict(list)
        for r in rows:
            by_build[r['build']].append(r)
        for e in wanted.get('builds', []):
            cands = by_build.get(e['build'])
            if not cands:
                print('extra build %s is not listed for any iPhone' % e['build'], file=sys.stderr)
                continue
            add(choose(cands), 'C', e.get('reason', 'audio changed in this patch'))

    by_build_devices = collections.defaultdict(set)
    for r in rows:
        by_build_devices[r['build']].add(r['device'])
    for build, devices in by_build_devices.items():
        if len(devices) != 1:
            continue
        row = next(r for r in rows if r['build'] == build)
        add(row, 'D', 'only %s ever received this build' % row['model'])

    # Anything already ingested must appear in the matrix even if no rule
    # would have chosen it, or its tag is computed against an incomplete set
    # and can collide with another build of the same version.
    for build, device in ingested.items():
        if build in seen:
            continue
        cands = [r for r in rows if r['build'] == build]
        if not cands:
            continue
        row = next((r for r in cands if r['device'] == device), cands[0])
        add(row, 'A', 'ingested before the current matrix rules')

    picked.sort(key=lambda r: (vkey(r['version']), r['date'] or '', r['build']))

    # Tags must be unique: two devices can share a version string on different
    # builds (iOS 8.0 shipped as 12A365 and 12A366 on the same day).
    counts = collections.Counter(r['version'] for r in picked)
    for r in picked:
        r['os'] = 'iOS %s%s' % (r['version'],
                                ' (%s)' % r['build'] if counts[r['version']] > 1 else '')
    assert len({r['os'] for r in picked}) == len(picked), 'matrix tags are not unique'
    for build, device in ingested.items():
        for r in picked:
            if r['build'] == build:
                r['device'] = device
                break

    if args.check:
        def head(r):
            try:
                req = urllib.request.Request(r['url'], method='HEAD')
                with urllib.request.urlopen(req, timeout=45) as resp:
                    return r, resp.status
            except Exception as e:
                return r, getattr(e, 'code', 0) or str(e)[:40]
        with cf.ThreadPoolExecutor(12) as ex:
            for r, status in ex.map(head, picked):
                if status != 200:
                    print('UNREACHABLE %-9s %-9s %s' % (r['version'], r['build'], status))

    total = sum(r['size'] for r in picked)
    remaining = sum(r['size'] for r in picked if r['build'] not in ingested)
    json.dump({
        'note': ('Derived by tools/plan.py from the ipsw.me firmware API. '
                 'Tier A is one IPSW per iOS major.minor line, tier B is every '
                 'iPhone launch build, tier C is extra patch releases where audio '
                 'is known to have changed.'),
        'generated_from': API,
        'totals': {'ipsws': len(picked), 'bytes': total,
                   'lines': len(by_minor), 'devices': len(by_device)},
        'versions': [{'os': r['os'], 'version': r['version'], 'build': r['build'],
                      'device': r['device'], 'model': r['model'], 'date': r['date'],
                      'bytes': r['size'], 'tier': r['tier'], 'reason': r['reason'],
                      'url': r['url']} for r in picked],
    }, open(args.out, 'w'), indent=1)

    tiers = collections.Counter(r['tier'] for r in picked)
    print('%d IPSWs (%s), %.0f GB total, %.0f GB still to download'
          % (len(picked), ' '.join('%s=%d' % kv for kv in sorted(tiers.items())),
             total / 1e9, remaining / 1e9))
    print('written to %s' % args.out)


if __name__ == '__main__':
    main()
