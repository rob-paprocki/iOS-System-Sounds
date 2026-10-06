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

## Layout

```
Current/         2,171 files, still in iOS 27.0
Removed/         1,892 files, shipped once and since dropped
Spoken Content/  1,939 files, Nike+ workout narration and similar bulk speech
sounds.json      every sound: category, format, duration, releases it shipped in
sounds.csv       the same thing as a spreadsheet
site/            the website
tools/           the pipeline that produces all of the above
docs/            release history, collection notes, design notes
```

Everything in those three trees is byte for byte what Apple shipped. Nothing is re-encoded at
any stage.

Formats are mixed because iOS is: 2,181 `.aiff`, 1,919 `.m4a`, 1,630 `.caf`, 266 `.wav`,
5 `.mp3` and 1 `.flac`. CAF and AIFF will not play in Chrome or Firefox, which is why
`tools/make-web.py` builds an AAC mirror for the site.

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
