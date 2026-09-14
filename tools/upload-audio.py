#!/usr/bin/env python3
"""Push the audio to R2, where the Worker serves it from.

    web/audio/**       ->  audio/**              the AAC preview mirror (191 MB)
    Current/**         ->  originals/Current/**  \\
    Removed/**         ->  originals/Removed/**   |  as Apple shipped them (355 MB)
    Spoken Content/**  ->  originals/Spoken…/**  /

Those prefixes are what worker/index.js maps URL paths onto, so the layout is
not cosmetic. Keys are stored literally, spaces and all — the Worker looks up
the decoded path, so "UI Sounds" must be "UI Sounds" and not "UI%20Sounds".

Speaks S3 directly with nothing but the standard library, so there is no rclone
or boto3 to install first. Re-runs are cheap: an object whose size and MD5
already match on the far end is skipped.

Credentials come from the environment, never from the command line, so they
stay out of your shell history:

    export R2_ACCOUNT_ID=...            # the 32-hex account id
    export R2_ACCESS_KEY_ID=...         # from an R2 API token
    export R2_SECRET_ACCESS_KEY=...
    python3 tools/upload-audio.py

Create the token at Cloudflare dashboard -> R2 -> API -> Manage API tokens,
with Object Read & Write on the bucket. Start with a smoke test:

    python3 tools/upload-audio.py --limit 5 --verbose

The signing is checked against AWS's published SigV4 vectors in
tools/tests/test_sigv4.py. If it ever misbehaves anyway, rclone against the same
endpoint writes the same layout, and stores keys literally too:

    rclone copy web/audio "r2:$R2_BUCKET/audio" --checksum --transfers 32
    rclone copy Current  "r2:$R2_BUCKET/originals/Current" --checksum --transfers 32

Do NOT reach for `wrangler r2 object put` here: it percent-encodes the key it
parses out of bucket/key, so "UI Sounds" is stored as "UI%20Sounds" and the
Worker, which looks up the decoded path, never finds it. Almost every path in
this collection has a space in it.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import datetime as dt
import hashlib
import hmac
import http.client
import os
import sys
import threading
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# (local directory, key prefix in the bucket)
SOURCES = [
    (ROOT / "web" / "audio", "audio"),
    (ROOT / "Current", "originals/Current"),
    (ROOT / "Removed", "originals/Removed"),
    (ROOT / "Spoken Content", "originals/Spoken Content"),
]

# Matches the fallbacks in worker/index.js.
TYPES = {
    ".m4a": "audio/mp4",
    ".caf": "audio/x-caf",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
}

UNRESERVED = "/-._~"          # RFC 3986 unreserved, keeping path separators
ALGORITHM = "AWS4-HMAC-SHA256"
REGION = "auto"               # R2 is region-less; SigV4 still wants a value
SERVICE = "s3"

_local = threading.local()
_print_lock = threading.Lock()


# --- signing ----------------------------------------------------------------

def _sign(key: bytes, msg: str) -> bytes:
    return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()


def _signing_key(secret: str, datestamp: str,
                 region: str = REGION, service: str = SERVICE) -> bytes:
    k = _sign(("AWS4" + secret).encode("utf-8"), datestamp)
    k = _sign(k, region)
    k = _sign(k, service)
    return _sign(k, "aws4_request")


def canonical_request(method: str, uri: str, headers: dict[str, str],
                      payload_hash: str) -> tuple[str, str]:
    """The canonical request and its signed-header list.

    Split out from authorize() so it can be checked against AWS's published
    SigV4 vectors — see tools/tests/test_sigv4.py.
    """
    signed = ";".join(sorted(headers))
    canonical_headers = "".join(f"{k}:{headers[k]}\n" for k in sorted(headers))
    return "\n".join([method, uri, "", canonical_headers, signed, payload_hash]), signed


def string_to_sign(amz_date: str, scope: str, creq: str) -> str:
    return "\n".join([
        ALGORITHM, amz_date, scope,
        hashlib.sha256(creq.encode("utf-8")).hexdigest(),
    ])


def encode_key(key: str) -> str:
    """Percent-encode a key for the URL, leaving the separators alone.

    The canonical request and the request line have to agree exactly, so both
    go through this.
    """
    return urllib.parse.quote(key, safe=UNRESERVED)


def authorize(method: str, host: str, canonical_uri: str, payload_hash: str,
              content_type: str | None, akid: str, secret: str) -> dict[str, str]:
    now = dt.datetime.now(dt.timezone.utc)
    amz_date = now.strftime("%Y%m%dT%H%M%SZ")
    datestamp = now.strftime("%Y%m%d")

    headers = {
        "host": host,
        "x-amz-content-sha256": payload_hash,
        "x-amz-date": amz_date,
    }
    if content_type:
        headers["content-type"] = content_type

    creq, signed = canonical_request(method, canonical_uri, headers, payload_hash)
    scope = f"{datestamp}/{REGION}/{SERVICE}/aws4_request"
    signature = hmac.new(
        _signing_key(secret, datestamp),
        string_to_sign(amz_date, scope, creq).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    out = dict(headers)
    out["Authorization"] = (
        f"{ALGORITHM} Credential={akid}/{scope}, "
        f"SignedHeaders={signed}, Signature={signature}"
    )
    return out


# --- transport --------------------------------------------------------------

def connection(host: str) -> http.client.HTTPSConnection:
    """One keep-alive connection per thread; 10,000 handshakes is the slow part."""
    conn = getattr(_local, "conn", None)
    if conn is None:
        conn = http.client.HTTPSConnection(host, timeout=120)
        _local.conn = conn
    return conn


def request(host: str, method: str, canonical_uri: str, body: bytes | None,
            payload_hash: str, content_type: str | None, cfg) -> tuple[int, dict, bytes]:
    headers = authorize(method, host, canonical_uri, payload_hash,
                        content_type, cfg.akid, cfg.secret)
    if body is not None:
        headers["Content-Length"] = str(len(body))

    for attempt in range(3):
        try:
            conn = connection(host)
            conn.request(method, canonical_uri, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read()
            return resp.status, dict(resp.getheaders()), data
        except (http.client.HTTPException, OSError):
            # A reused connection can be closed under us; drop it and retry.
            stale = getattr(_local, "conn", None)
            if stale is not None:
                try:
                    stale.close()
                except Exception:  # noqa: BLE001 - it is already going away
                    pass
            _local.conn = None
            if attempt == 2:
                raise
    raise RuntimeError("unreachable")


# --- the work ---------------------------------------------------------------

class Config:
    def __init__(self, account: str, akid: str, secret: str, bucket: str):
        self.host = f"{account}.r2.cloudflarestorage.com"
        self.akid = akid
        self.secret = secret
        self.bucket = bucket


def collect() -> list[tuple[Path, str]]:
    items: list[tuple[Path, str]] = []
    for base, prefix in SOURCES:
        if not base.is_dir():
            continue
        for path in sorted(base.rglob("*")):
            if not path.is_file() or path.name == ".DS_Store":
                continue
            rel = path.relative_to(base).as_posix()
            items.append((path, f"{prefix}/{rel}"))
    return items


def already_there(key: str, size: int, digest: str, cfg: Config) -> bool:
    uri = "/" + encode_key(f"{cfg.bucket}/{key}")
    empty = hashlib.sha256(b"").hexdigest()
    status, headers, _ = request(cfg.host, "HEAD", uri, None, empty, None, cfg)
    if status != 200:
        return False
    if int(headers.get("Content-Length", -1)) != size:
        return False
    etag = (headers.get("ETag") or "").strip('"')
    # A single-part PUT stores the MD5 as the ETag; anything else we re-upload.
    return etag == digest


def put(path: Path, key: str, cfg: Config, args) -> str:
    body = path.read_bytes()
    digest = hashlib.md5(body).hexdigest()

    if not args.force and already_there(key, len(body), digest, cfg):
        return "skip"
    if args.dry_run:
        return "would-upload"

    uri = "/" + encode_key(f"{cfg.bucket}/{key}")
    ctype = TYPES.get(path.suffix.lower(), "application/octet-stream")
    status, _, data = request(
        cfg.host, "PUT", uri, body,
        hashlib.sha256(body).hexdigest(), ctype, cfg
    )
    if status not in (200, 201):
        raise RuntimeError(f"{status} on {key}: {data[:300].decode('utf-8', 'replace')}")
    return "upload"


def main() -> None:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--bucket", default=os.environ.get("R2_BUCKET", "ios-system-sounds-audio"))
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="stop after N files (smoke test)")
    ap.add_argument("--dry-run", action="store_true", help="say what would go, send nothing")
    ap.add_argument("--force", action="store_true", help="re-upload even if it matches")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    account = os.environ.get("R2_ACCOUNT_ID", "")
    akid = os.environ.get("R2_ACCESS_KEY_ID", "")
    secret = os.environ.get("R2_SECRET_ACCESS_KEY", "")

    items = collect()
    if args.limit:
        items = items[:args.limit]
    if not items:
        sys.exit("Nothing to upload. Is web/audio/ built? python3 tools/make-web.py")

    total_bytes = sum(p.stat().st_size for p, _ in items)
    print(f"{len(items):,} files, {total_bytes / 1e6:.0f} MB")
    for base, prefix in SOURCES:
        if base.is_dir():
            print(f"  {base.relative_to(ROOT)}/ -> {prefix}/")

    if args.dry_run and not (account and akid and secret):
        print("\n--dry-run without credentials: listing only, nothing contacted.")
        for _, k in items[:10]:
            print(f"  {k}")
        if len(items) > 10:
            print(f"  … and {len(items) - 10:,} more")
        return

    missing = [n for n, v in [("R2_ACCOUNT_ID", account), ("R2_ACCESS_KEY_ID", akid),
                              ("R2_SECRET_ACCESS_KEY", secret)] if not v]
    if missing:
        sys.exit("\nNot set: " + ", ".join(missing)
                 + "\nSee the header of this file for how to create the token.")

    cfg = Config(account, akid, secret, args.bucket)
    counts = {"upload": 0, "skip": 0, "would-upload": 0}
    failures: list[str] = []
    done = 0

    def work(item):
        path, key = item
        return key, put(path, key, cfg, args)

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as pool:
        for future in concurrent.futures.as_completed(
                [pool.submit(work, i) for i in items]):
            done += 1
            try:
                key, result = future.result()
                counts[result] += 1
                if args.verbose:
                    with _print_lock:
                        print(f"  {result:12s} {key}")
            except Exception as exc:  # noqa: BLE001 - report and keep going
                failures.append(str(exc))
            if not args.verbose and done % 250 == 0:
                with _print_lock:
                    print(f"  {done:,} / {len(items):,}", flush=True)

    print(f"\nuploaded {counts['upload']:,} · unchanged {counts['skip']:,}"
          + (f" · would upload {counts['would-upload']:,}" if args.dry_run else ""))
    if failures:
        print(f"\n{len(failures)} failed:", file=sys.stderr)
        for f in failures[:20]:
            print("  " + f, file=sys.stderr)
        sys.exit(1)

    print("\nSpot-check through the Worker:")
    print("  curl -I 'https://<your-domain>/audio/Current/UI%20Sounds/iPhone/Tink.m4a'")
    print("Expect 200 with Accept-Ranges: bytes.")


if __name__ == "__main__":
    main()
