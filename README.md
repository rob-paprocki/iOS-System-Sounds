# iOS System Sounds

Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 27.0, extracted from 130 IPSWs, de-duplicated across all of them and sorted by function.

[![Release](https://img.shields.io/github/v/release/rob-paprocki/iOS-System-Sounds)](https://github.com/rob-paprocki/iOS-System-Sounds/releases)
[![CI](https://img.shields.io/github/actions/workflow/status/rob-paprocki/iOS-System-Sounds/ci.yml?branch=main&label=CI)](https://github.com/rob-paprocki/iOS-System-Sounds/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/rob-paprocki/iOS-System-Sounds?label=code%20license)](LICENSE)
[![Website](https://img.shields.io/badge/website-search%20and%20play-blue)](https://ios-system-sounds.rpaprocki.com)

**6,002 distinct sounds from 130 builds, covering 99 release lines over 19 years.** 2,171 are still in iOS today. The other 3,831 are gone. Each sound lists the releases it actually shipped in.

Search, play and download them at **[ios-system-sounds.rpaprocki.com](https://ios-system-sounds.rpaprocki.com)**.

## Why

- Other collections cover `System/Library/Audio/UISounds` and stop there. This one walks the whole root filesystem, so it also has VoiceOver, Siri voice previews, the Photos Memories soundtrack stems, haptic cues, carrier tones, Find My tones and a long tail of per-framework one-offs.
- Everything is byte for byte what Apple shipped. Nothing is re-encoded at any stage.
- `sounds.json` and `sounds.csv` give category, format, duration and release range for every sound.
- The pipeline that produced it is in the repository, so a new iOS release can be added.

**Does not:** grant any right to the audio. It is Apple's copyrighted work, collected for reference, preservation and research. See [License](#license).

## Requirements

| Use | Needs |
|-----|-------|
| Browse and download | A browser, or `git` and about 420 MB of disk for the audio trees |
| Rebuild everything | Python 3, `ipsw`, `ffmpeg`, `fpcalc`, `curl`, roughly 600 GB of downloads and 90 GB of peak disk |
| Releases before iOS 10 | Also `vfdecrypt` and `dmg2img`, because the root filesystem is encrypted |
| Windows or Linux | `pip install dissect.apfs`, because the filesystem images are read unmounted without `hdiutil` |

## Install

```bash
git clone https://github.com/rob-paprocki/iOS-System-Sounds.git
cd iOS-System-Sounds
```

Or skip the clone: the [releases](https://github.com/rob-paprocki/iOS-System-Sounds/releases) carry per-category zip archives, each with a `manifest.json`.

## Quick start

Look up a sound in the index, then open the file it points to:

```bash
python3 -c "import json; print(len(json.load(open('sounds.json'))['sounds']), 'sounds')"
```

```text
6002 sounds
```

## Layout

| Path | Holds |
|------|-------|
| `Current/` | 2,171 files, still in iOS 27.0 |
| `Removed/` | 1,892 files, shipped once and since dropped |
| `Spoken Content/` | 1,939 files, Nike+ workout narration and similar bulk speech |
| `sounds.json`, `sounds.csv` | Every sound: category, format, duration, releases it shipped in |
| `site/` | The website, plain ES modules with no build step |
| `worker/`, `wrangler.jsonc` | The Cloudflare Worker that serves audio from R2, and its config |
| `tools/` | The pipeline that produces all of the above |
| `research/` | The ipsw.me firmware snapshot and the release-history research |
| `docs/` | Release history and collection notes |

Formats are mixed because iOS is: 2,181 `.aiff`, 1,919 `.m4a`, 1,630 `.caf`, 266 `.wav`, 5 `.mp3` and 1 `.flac`. CAF and AIFF won't play in Chrome or Firefox, which is why `tools/make-web.py` builds an AAC mirror for the site.

The repo doesn't use Git LFS, so a normal clone fetches the audio and the index files like any other git files.

## Limits

The Caveats section of [docs/collection-notes.md](docs/collection-notes.md) has the full list. The main ones:

- Siri and VoiceOver voices that iOS downloads after setup are not here, only what shipped in the IPSW images.
- A sound's "dropped in" release is accurate to one minor release, not to a patch release.
- Files with the `.voc` extension are left out, because the ones iOS ships are speech recognition data.
- The site doesn't have every feature planned for it. The end of `site/README.md` lists what is not built.

## Rebuilding it

```bash
python3 tools/plan.py         # derive the build matrix from the ipsw.me API
python3 tools/build-all.py    # download, extract and ingest every release
python3 tools/measure.py      # durations and waveform peaks
python3 tools/build-repo.py   # build the trees and the index
```

That takes roughly five hours on a fast connection.

<details>
<summary>Adding a new release</summary>

`corpus.json` and `_store/` are ingest state and aren't committed, but a clean clone can recover both from the trees and `sounds.json` instead of re-running every release:

```bash
python3 tools/rebuild-corpus.py   # recover corpus.json and _store/ (a few minutes)
python3 tools/measure.py
python3 tools/build-repo.py       # should leave sounds.json unchanged
python3 tools/plan.py             # delete research/ipswme-iphone.json first to refresh it
python3 tools/build-all.py        # ingests only the builds that are new
python3 tools/measure.py && python3 tools/build-repo.py
```

</details>

## Documentation

[docs/collection-notes.md](docs/collection-notes.md) covers which releases were extracted and why, how identity is decided, what changed in each release, and the caveats. [site/README.md](site/README.md) covers the website.

## Help and contributing

Development happens in a separate repository; this one is updated when a release ships.

Questions and bug reports go in [Issues](https://github.com/rob-paprocki/iOS-System-Sounds/issues).

## Changelog

See [CHANGELOG.md](CHANGELOG.md).

## License

The audio files are Apple Inc.'s copyrighted work. No license to them is granted or implied here. They are collected for reference, preservation and research. If you are Apple and would like this taken down, open an issue.

The scripts, index files and documentation are original work under the [MIT license](LICENSE). [NOTICE.md](NOTICE.md) has the full statement.

## Inspired by

[extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds), which covers `UISounds` in the current release across several formats.
