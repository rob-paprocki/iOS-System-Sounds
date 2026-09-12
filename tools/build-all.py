#!/usr/bin/env python3
"""Run the whole pipeline over tools/versions.json: fetch, extract, ingest.

Downloading is network-bound and extraction is disk- and CPU-bound, so they
run at the same time: a prefetch pool keeps the next few IPSWs arriving while
the main loop extracts and ingests the current one. Each IPSW is deleted as
soon as its audio has been pulled out, and the prefetch pool blocks when the
staged IPSWs would exceed the disk budget.

Safe to interrupt and re-run. Versions already in the corpus are skipped,
extractions already on disk are reused, and a part-downloaded IPSW resumes.

    python3 tools/build-all.py
    python3 tools/build-all.py --only 8A293 14A403
    python3 tools/build-all.py --prefetch 3 --budget-gb 80
"""
import argparse
import json
import os
import queue
import shutil
import subprocess
import sys
import threading
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def ipsw_path(work, v):
    return os.path.join(work, '%s_%s_%s_Restore.ipsw' % (v['device'], v['version'], v['build']))


class Downloader(object):
    """Shared prefetch state: one work queue, one set of in-flight builds.

    The main loop and the prefetch threads must never download the same build
    at once, so anything in flight is announced here and the main loop waits
    for it rather than starting a second download of the same file.
    """

    def __init__(self, plan, work, budget, log):
        self.q = queue.Queue()
        for v in plan:
            self.q.put(v)
        self.work, self.budget, self.log = work, budget, log
        self.lock = threading.Lock()
        self.cond = threading.Condition(self.lock)
        self.inflight = set()
        self.stop = threading.Event()

    def staged_bytes(self):
        total = 0
        for name in os.listdir(self.work):
            if name.endswith('.ipsw'):
                try:
                    total += os.path.getsize(os.path.join(self.work, name))
                except OSError:
                    pass
        return total

    def wait_for(self, build):
        """Block while a prefetch thread is downloading this build."""
        with self.cond:
            while build in self.inflight:
                self.cond.wait(timeout=15)

    def claim(self, build):
        with self.cond:
            if build in self.inflight:
                return False
            self.inflight.add(build)
            return True

    def release(self, build):
        with self.cond:
            self.inflight.discard(build)
            self.cond.notify_all()

    def worker(self):
        while not self.stop.is_set():
            try:
                v = self.q.get_nowait()
            except queue.Empty:
                return
            if os.path.exists(ipsw_path(self.work, v)):
                continue
            while self.staged_bytes() + v['bytes'] > self.budget:
                if self.stop.is_set():
                    return
                time.sleep(20)
            if not self.claim(v['build']):
                continue
            self.log('   [prefetch] %s (%s) %.1f GB' % (v['os'], v['build'], v['bytes'] / 1e9))
            try:
                target = ipsw_path(self.work, v)
                if v.get('url'):
                    # Straight from Apple, using the URL already in the matrix.
                    # ipsw.me rate-limits a run this size, and nothing here
                    # needs it once the matrix is built.
                    subprocess.run(['curl', '-sSL', '--fail', '--retry', '3',
                                    '--retry-delay', '5', '-C', '-',
                                    '-o', target + '.part', v['url']])
                    if (os.path.exists(target + '.part')
                            and os.path.getsize(target + '.part') == v['bytes']):
                        os.rename(target + '.part', target)
                else:
                    subprocess.run(['ipsw', 'download', 'ipsw', '--device', v['device'],
                                    '--build', v['build'], '-y', '-o', self.work],
                                   capture_output=True, text=True)
            finally:
                self.release(v['build'])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--matrix', default=os.path.join(HERE, 'versions.json'))
    ap.add_argument('--corpus', default=os.path.join(ROOT, 'corpus.json'))
    ap.add_argument('--store', default=os.path.join(ROOT, '_store'))
    ap.add_argument('--work', default=os.path.join(ROOT, '_work'))
    ap.add_argument('--only', nargs='*', help='limit to these build IDs')
    ap.add_argument('--prefetch', type=int, default=2, help='parallel downloads running ahead')
    ap.add_argument('--budget-gb', type=float, default=70.0,
                    help='most disk the staged IPSWs may occupy')
    ap.add_argument('--keep-extracts', action='store_true')
    ap.add_argument('--no-build', action='store_true', help='skip rebuilding the trees at the end')
    args = ap.parse_args()

    os.makedirs(args.work, exist_ok=True)
    plan = json.load(open(args.matrix))['versions']
    if args.only:
        plan = [v for v in plan if v['build'] in args.only]

    done = set()
    if os.path.exists(args.corpus):
        done = {v['build'] for v in json.load(open(args.corpus))['versions']}
    todo = [v for v in plan if v['build'] not in done]

    def log(msg):
        print(msg, flush=True)

    log('%d of %d versions already ingested; %d to go, %.0f GB to download'
        % (len(plan) - len(todo), len(plan), len(todo), sum(v['bytes'] for v in todo) / 1e9))

    dl = Downloader(todo, args.work, args.budget_gb * 1e9, log)
    threads = [threading.Thread(target=dl.worker, daemon=True)
               for _ in range(max(1, args.prefetch))]
    for t in threads:
        t.start()

    started = time.time()
    ok = fail = 0
    for n, v in enumerate(todo, 1):
        log('\n== [%d/%d] %s  %s  %s  (%.1f GB, tier %s: %s)'
            % (n, len(todo), v['os'], v['build'], v['model'], v['bytes'] / 1e9,
               v['tier'], v['reason']))
        extract = os.path.join(args.work, 'extract-%s' % v['build'])

        if not (os.path.isdir(extract) and any(os.scandir(extract))):
            dl.wait_for(v['build'])
            r = subprocess.run([sys.executable, os.path.join(HERE, 'fetch-version.py'),
                                '--device', v['device'], '--build', v['build'],
                                '--os', v['os'], '--work', args.work])
            if r.returncode != 0:
                log('   FETCH FAILED, skipping %s' % v['build'])
                fail += 1
                continue

        r = subprocess.run([sys.executable, os.path.join(HERE, 'ingest.py'),
                            '--extract', extract, '--os', v['os'], '--build', v['build'],
                            '--device', v['device'], '--model', v.get('model', ''),
                            '--corpus', args.corpus, '--store', args.store])
        if r.returncode != 0:
            log('   INGEST FAILED for %s' % v['build'])
            fail += 1
            continue
        ok += 1
        if not args.keep_extracts:
            shutil.rmtree(extract, ignore_errors=True)
        rate = (time.time() - started) / n
        log('   %d ok, %d failed, %.1f min/version, ~%.1f h left'
            % (ok, fail, rate / 60, rate * (len(todo) - n) / 3600))

    dl.stop.set()

    if not args.no_build:
        log('\n== building trees')
        subprocess.run([sys.executable, os.path.join(HERE, 'build-repo.py'),
                        '--corpus', args.corpus, '--store', args.store])


if __name__ == '__main__':
    main()
