# iOS System Sounds

Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 27.0,
pulled out of 130 IPSW filesystems, de-duplicated across all of them, and sorted by function.

**6,002 distinct sounds from 130 builds, covering 99 release lines over 19 years.** 2,171 are
still in iOS today. The other 3,831 are gone.

Search, play and download them at **[ios-system-sounds.rpaprocki.com](https://ios-system-sounds.rpaprocki.com)**.

Other collections cover `System/Library/Audio/UISounds` and stop there. This one walks the
whole root filesystem, so it also has VoiceOver, Siri voice previews, the Photos Memories
soundtrack stems, haptic cues, carrier tones, Find My tones and a long tail of per-framework
one-offs.

## Start here

- To listen to or download sounds, use the site above. Its Contents screen links every
  download. In git, browse `Current/`, `Removed/` and `Spoken Content/`, or open `sounds.json`
  or `sounds.csv` to look a sound up. [Layout](#layout) shows what each holds.
- To rebuild the corpus from nothing, you need Python 3 on macOS, Windows or Linux, roughly
  600 GB of downloads, and the tools listed under [Rebuilding it](#rebuilding-it), which also
  has the commands. To add a newer iOS release to a clone of this repo, go to
  [Adding a new release](#adding-a-new-release), which recovers the ingest state from the
  committed files first.
- To run or deploy the site, read [site/README.md](site/README.md). Settings live in three
  places. The config block at the top of `site/index.html` sets where the page finds the index
  and the audio, and `site/README.md` documents it under Configuration. `wrangler.jsonc` sets
  the Worker, its assets folder and the R2 bucket binding. `tools/upload-audio.py` reads
  `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID` and `R2_SECRET_ACCESS_KEY` from the environment.

## Layout

```
Current/         2,171 files, still in iOS 27.0
Removed/         1,892 files, shipped once and since dropped
Spoken Content/  1,939 files, Nike+ workout narration and similar bulk speech
sounds.json      every sound: category, format, duration, releases it shipped in
sounds.csv       the same thing as a spreadsheet
site/            the website
worker/          the Cloudflare Worker that serves audio from R2
wrangler.jsonc   Worker config: site/ as static assets, the R2 bucket binding
tools/           the pipeline that produces all of the above
research/        the ipsw.me firmware snapshot and the release-history research
docs/            release history, collection notes, design notes
```

Everything in those three trees is byte for byte what Apple shipped. Nothing is re-encoded at
any stage.

Formats are mixed because iOS is: 2,181 `.aiff`, 1,919 `.m4a`, 1,630 `.caf`, 266 `.wav`,
5 `.mp3` and 1 `.flac`. CAF and AIFF will not play in Chrome or Firefox, which is why
`tools/make-web.py` builds an AAC mirror for the site.

The repo does not use Git LFS (`.gitattributes` has no LFS filters), so a normal clone
fetches the audio and the index files like any other git files.

## Limits

The Caveats section of [docs/collection-notes.md](docs/collection-notes.md) has the full
list. The main ones:

- Siri and VoiceOver voices that iOS downloads after setup are not here, only what shipped in
  the IPSW images.
- A sound's "dropped in" release is accurate to one minor release, not to a patch release.
- Files with the `.voc` extension are left out, because the ones iOS ships are speech
  recognition data.
- The site does not have every feature planned for it. The end of `site/README.md` lists what
  is not built.

## Rebuilding it

```sh
python3 tools/plan.py         # derive the build matrix from the ipsw.me API
python3 tools/build-all.py    # download, extract and ingest every release
python3 tools/measure.py      # durations and waveform peaks
python3 tools/build-repo.py   # build the trees and the index
```

Roughly 600 GB of downloads and five hours on a fast connection, peaking at about 90 GB of
disk. You need `ipsw`, `ffmpeg`, `fpcalc` and `curl`. Releases before iOS 10 have an encrypted
root filesystem and also need `vfdecrypt` and `dmg2img`. Without `hdiutil` (Windows, Linux)
the filesystem images are read unmounted, which needs `pip install dissect.apfs`.

### Adding a new release

`corpus.json` and `_store/` are ingest state and are not committed, but a clean clone can
recover both from the trees and `sounds.json` instead of re-running every release:

```sh
python3 tools/rebuild-corpus.py   # recover corpus.json and _store/ (a few minutes)
python3 tools/measure.py
python3 tools/build-repo.py       # should leave sounds.json unchanged
python3 tools/plan.py             # delete research/ipswme-iphone.json first to refresh it
python3 tools/build-all.py        # ingests only the builds that are new
python3 tools/measure.py && python3 tools/build-repo.py
```

## More

[docs/collection-notes.md](docs/collection-notes.md) covers which releases were extracted and
why, how identity is decided, what changed in each release, and the caveats.
[site/README.md](site/README.md) covers the website.

## Licence

The audio files are Apple Inc.'s copyrighted work. No licence to them is granted or implied
here. They are collected for reference, preservation and research. If you are Apple and would
like this taken down, open an issue.

The scripts, index files and documentation are original work under the
[MIT licence](LICENSE). [NOTICE.md](NOTICE.md) has the full statement.

## Inspired by

[extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds), which covers
`UISounds` in the current release across several formats.
