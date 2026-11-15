# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and versions follow
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-11-15
**Upgrading:** nothing to do.

### Changed

- The README lists the worker and research folders in its layout table and has a Limits section.
- The README now has badges, a requirements table and a quick start.
- The download notice on the website and in the web bundle now spells "license" the way the rest of the project does.
- The website's download links point at this release. The files are the same as in 2.1.0.

### Fixed

- The links to the Releases page in `NOTICE.md` and the collection notes now work outside GitHub's own file view.

## [2.1.0] - 2026-10-07

**Upgrading:** nothing to do.

### Added

- The website: search, play and download every sound, served from a Cloudflare Worker with the audio in R2.
- iOS 27.0 (`24A437`). The collection is now 6,002 distinct sounds from 130 IPSW filesystems, of which 2,171 are still in iOS and 3,831 are gone.
- 643 sounds appear for the first time in 27.0, 629 of them Siri: 326 voice previews and 303 TTS audio hint files across ten locales (before this, only ja-JP). 52 sounds dropped out, 49 of them older voice previews.
- New in 27.0: four App Store "Angle" sounds and a success sound, Accessibility Drill In and Drill Out, two Home pairing sounds, and Call Waiting Tone Low Priority in the Watch UI sounds.

### Changed

- Photos Sharing Post Tone was re-recorded in 27.0.
- The website's downloads point at this release. The web bundle is 282 MB.
- The generic Screen Locked haptic is gone from 27.0 and now sits under `Removed/`.

## [2.0.0] - 2026-09-12

**Upgrading:** **Breaking.** The layout changed. `Source/` is replaced by `Current/`, `Removed/` and `Spoken Content/`, and the WAV mirror is no longer published. Re-clone or re-download, and update any paths. `tools/make-wav.py` still builds a WAV mirror if you need one.

### Added

- A cross-version collection from iOS 1.0 (2007) to iOS 26.6.1: 5,359 distinct sounds from 129 IPSW filesystems, de-duplicated across all of them, so each sound lists the releases it appeared in. 1,580 were still in iOS at the time and 3,779 were gone.
- The ingest pipeline in `tools/`, and `sounds.json` and `sounds.csv` as the index.
- Per-category release archives, each with a `manifest.json`, and a web bundle with an AAC preview of every playable sound, the split index, waveform peaks and a hand-written zero state.

### Changed

- Siri vocabulary `.voc` files are excluded, because they are not audio here.

### Removed

- The WAV mirror release asset. At full coverage it would be 3 to 5 GB, past GitHub's per-asset limit, and every audio editor opens CAF and AIFF anyway.

## [1.0.0] - 2026-09-07

**Upgrading:** nothing to do.

### Added

- Every sound file shipped in iOS 26 (build `23G83`), extracted from the iPhone 18,2 IPSW: 1,613 sounds, 2h 20m of audio, in 14 functional categories.
- Files de-duplicated by MD5 rather than filename (167 redundant copies removed), with 9 mislabelled extensions corrected.
- `iOS-System-Sounds-WAV.zip`, the collection converted to uncompressed WAV with sample rate and channel count preserved, built by `tools/make-wav.py`.
- License terms split into a pristine MIT `LICENSE` and a `NOTICE.md` that covers Apple's copyright on the audio.

[Unreleased]: https://github.com/rob-paprocki/iOS-System-Sounds/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/rob-paprocki/iOS-System-Sounds/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/rob-paprocki/iOS-System-Sounds/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/rob-paprocki/iOS-System-Sounds/releases/tag/v1.0.0
