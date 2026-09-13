#!/usr/bin/env python3
"""Local development server that routes exactly like the deployed Worker.

    python3 tools/serve-dev.py
    open http://localhost:8000/

`site/` is the document root, as it is in production. The two audio prefixes
that R2 answers for in production are answered here from local directories:

    /audio/<path>      ->  web/audio/<path>        the AAC preview mirror
    /originals/<path>  ->  <repo>/<path>           Current/, Removed/, Spoken Content/
    everything else    ->  site/<path>             the page and its committed index

Because the routing matches, site/index.html needs no separate development
configuration — the same three path bases work in both places.

Range requests are served properly, since that is what the browser uses to seek
within a sound and what the Worker does in production.
"""

from __future__ import annotations

import argparse
import mimetypes
import re
import sys
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"

TYPES = {
    ".m4a": "audio/mp4",
    ".caf": "audio/x-caf",
    ".aiff": "audio/aiff",
    ".aif": "audio/aiff",
    ".wav": "audio/wav",
    ".mp3": "audio/mpeg",
    ".flac": "audio/flac",
}

RANGE_RE = re.compile(r"^bytes=(\d*)-(\d*)$")


class Handler(SimpleHTTPRequestHandler):
    """Serves site/, with the Worker's two R2 prefixes mapped to local trees."""

    def translate_path(self, path: str) -> str:
        clean = unquote(path.split("?", 1)[0].split("#", 1)[0])
        parts = [p for p in clean.split("/") if p not in ("", ".", "..")]

        if parts and parts[0] == "audio":
            return str(ROOT / "web" / "audio" / Path(*parts[1:])) if len(parts) > 1 else str(ROOT)
        if parts and parts[0] == "originals":
            return str(ROOT / Path(*parts[1:])) if len(parts) > 1 else str(ROOT)
        return str(SITE / Path(*parts)) if parts else str(SITE / "index.html")

    def guess_type(self, path):
        ext = Path(path).suffix.lower()
        if ext in TYPES:
            return TYPES[ext]
        return super().guess_type(path)

    def do_GET(self):  # noqa: N802 - http.server's naming
        target = Path(self.translate_path(self.path))
        if target.is_dir():
            target = target / "index.html"
        if not target.is_file():
            self.send_error(404, "Not found")
            return

        rng = self.headers.get("Range")
        if not rng:
            self._send_whole(target)
            return

        m = RANGE_RE.match(rng.strip())
        size = target.stat().st_size
        if not m:
            self._send_whole(target)
            return

        start_s, end_s = m.group(1), m.group(2)
        if start_s == "":                       # bytes=-N, the last N bytes
            length = int(end_s or 0)
            start, end = max(0, size - length), size - 1
        else:
            start = int(start_s)
            end = int(end_s) if end_s else size - 1
        end = min(end, size - 1)

        if start > end or start >= size:
            self.send_response(416)
            self.send_header("Content-Range", f"bytes */{size}")
            self.end_headers()
            return

        self.send_response(206)
        self._common(target)
        self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.send_header("Content-Length", str(end - start + 1))
        self.end_headers()
        with target.open("rb") as fh:
            fh.seek(start)
            self.wfile.write(fh.read(end - start + 1))

    def _send_whole(self, target: Path) -> None:
        self.send_response(200)
        self._common(target)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(target.read_bytes())

    def _common(self, target: Path) -> None:
        self.send_header("Content-Type", self.guess_type(str(target)))
        self.send_header("Accept-Ranges", "bytes")
        # Never cache in development; editing a module should take effect.
        self.send_header("Cache-Control", "no-store, must-revalidate")

    def log_message(self, format, *args):  # noqa: A002 - matches the base signature
        pass


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--port", type=int, default=8000)
    args = ap.parse_args()

    if not (SITE / "data" / "index.core.json").exists():
        print("warning: site/data/index.core.json is missing — the page will not render.\n"
              "         Run: python3 tools/sync-site-data.py\n", file=sys.stderr)

    mimetypes.init()
    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), partial(Handler))
    print(f"serving {SITE} on http://127.0.0.1:{args.port}/")
    print("  /audio/*      -> web/audio/")
    print("  /originals/*  -> repository trees")
    httpd.serve_forever()


if __name__ == "__main__":
    main()
