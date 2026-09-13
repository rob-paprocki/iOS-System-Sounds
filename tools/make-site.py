#!/usr/bin/env python3
"""Assemble a deployable copy of the site.

The site source in ``site/`` is static and has no build step: it is plain ES
modules that a browser loads directly. What it cannot do is reach the data,
because ``web/`` is gitignored and the audio does not live next to the page in
production. This script stages both and rewrites the three path bases in
``index.html`` to match wherever you are deploying.

Typical use, matching the hosting decision in docs/website-design-notes.md
(Cloudflare Pages for the page, an R2 bucket on its own domain for the audio):

    python3 tools/make-site.py \\
        --preview-base  https://audio.example.com/ \\
        --original-base https://audio.example.com/originals/

Then point Cloudflare Pages at ``_dist/site``.

To preview the whole thing locally with the audio served from the same origin:

    python3 tools/make-site.py --with-audio
    python3 -m http.server 8000 --directory _dist/site

During development you do not need this script at all. Serve the repository
root and open ``/site/`` — the defaults in index.html already point at ``/web/``:

    python3 -m http.server 8000
    open http://localhost:8000/site/
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
WEB = ROOT / "web"

# Built by tools/make-web.py. Without these the page has nothing to show.
DATA_FILES = ["index.core.json", "index.detail.json", "peaks.bin", "shelves.json"]

# The original trees, as Apple shipped them. Only copied with --with-audio.
ORIGINAL_TREES = ["Current", "Removed", "Spoken Content"]


def rewrite_config(html: str, bases: dict[str, str]) -> str:
    """Point the three path bases at the deployment.

    Only the values inside the SOUNDS_CONFIG block are touched; the surrounding
    comment explaining what each base means is left in place so the deployed
    page still documents itself.
    """
    for key, value in bases.items():
        pattern = re.compile(rf"^(\s*{key}:\s*)'[^']*'(,?)$", re.MULTILINE)
        html, n = pattern.subn(rf"\g<1>'{value}'\g<2>", html)
        if n != 1:
            sys.exit(f"make-site: expected exactly one '{key}' line in index.html, found {n}")
    return html


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", default=str(ROOT / "_dist" / "site"),
                    help="output directory (default: _dist/site)")
    ap.add_argument("--data-base", default="/data/",
                    help="where index.core.json and friends are served from")
    ap.add_argument("--preview-base", default="/media/",
                    help="base for record.preview, which begins 'audio/'")
    ap.add_argument("--original-base", default="/media/originals/",
                    help="base for record.file, which begins 'Current/' or 'Removed/'")
    ap.add_argument("--with-audio", action="store_true",
                    help="also copy the preview mirror and the original trees "
                         "(about 550 MB) so the whole site works from one origin")
    args = ap.parse_args()

    if not SITE.is_dir():
        sys.exit("make-site: site/ not found")
    missing = [f for f in DATA_FILES if not (WEB / f).exists()]
    if missing:
        sys.exit("make-site: missing from web/: " + ", ".join(missing)
                 + "\n  Build it first with: python3 tools/make-web.py")

    out = Path(args.out)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)

    # The page and its assets. README.md documents the source, not the deploy.
    shutil.copytree(SITE, out, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("README.md", ".DS_Store"))

    bases = {
        "dataBase": args.data_base,
        "previewBase": args.preview_base,
        "originalBase": args.original_base,
    }
    if args.with_audio:
        bases["previewBase"] = "/media/"
        bases["originalBase"] = "/media/originals/"

    index = out / "index.html"
    index.write_text(rewrite_config(index.read_text(), bases))

    # The index, the peaks and the shelves.
    data_dir = out / args.data_base.strip("/") if args.data_base.startswith("/") else out / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for f in DATA_FILES:
        shutil.copy2(WEB / f, data_dir / f)
        total += (WEB / f).stat().st_size

    print(f"site      -> {out}")
    print(f"data      -> {data_dir}  ({total / 1e6:.2f} MB, {len(DATA_FILES)} files)")

    if args.with_audio:
        media = out / "media"
        if (WEB / "audio").is_dir():
            shutil.copytree(WEB / "audio", media / "audio")
            print(f"previews  -> {media / 'audio'}")
        else:
            print("previews  -- web/audio not found, skipped")
        for tree in ORIGINAL_TREES:
            src = ROOT / tree
            if src.is_dir():
                shutil.copytree(src, media / "originals" / tree)
        print(f"originals -> {media / 'originals'}")
    else:
        print(f"previews  -- not copied; served from {bases['previewBase']}")
        print(f"originals -- not copied; served from {bases['originalBase']}")

    print("\nDeploy the contents of", out)


if __name__ == "__main__":
    main()
