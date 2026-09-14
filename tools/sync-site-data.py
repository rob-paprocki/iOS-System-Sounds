#!/usr/bin/env python3
"""Copy the generated index into the site, where it ships as a static asset.

`web/` is gitignored — it holds a 191 MB preview mirror alongside the index, and
none of that belongs in git. But the index itself is small and the site cannot
render a single row without it, so the four files below are committed under
`site/data/` and deployed with the page.

Run this after any corpus rebuild, then commit what changes:

    python3 tools/make-web.py        # regenerates web/
    python3 tools/sync-site-data.py  # copies the index into site/data/
    git add site/data && git commit
"""

from __future__ import annotations

import filecmp
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WEB = ROOT / "web"
DEST = ROOT / "site" / "data"

# Everything the page fetches at runtime. The preview mirror is not here.
FILES = ["index.core.json", "index.detail.json", "peaks.bin", "shelves.json"]


def main() -> None:
    missing = [f for f in FILES if not (WEB / f).exists()]
    if missing:
        sys.exit(
            "sync-site-data: missing from web/: " + ", ".join(missing)
            + "\n  Build it first with: python3 tools/make-web.py"
            + "\n  Or unpack iOS-System-Sounds-web-bundle.zip from the release into web/."
        )

    DEST.mkdir(parents=True, exist_ok=True)
    changed, total = [], 0

    for name in FILES:
        src, dst = WEB / name, DEST / name
        if dst.exists() and filecmp.cmp(src, dst, shallow=False):
            pass
        else:
            shutil.copy2(src, dst)
            changed.append(name)
        total += dst.stat().st_size

    for name in changed:
        print(f"  updated  {name}")
    if not changed:
        print("  already up to date")

    print(f"\n{DEST.relative_to(ROOT)}: {len(FILES)} files, {total / 1e6:.2f} MB")
    if changed:
        print("Commit these so a clean clone can build and deploy without ffmpeg.")


if __name__ == "__main__":
    main()
