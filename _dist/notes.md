Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 26.6.1: **5,359 distinct sounds** pulled from 129 IPSW filesystems and de-duplicated across all of them, so each sound carries the list of releases it actually appeared in.

1,580 are still in iOS today. The other 3,779 are gone.

This replaces v1.0.0, which was a snapshot of one release.

## Downloads

The per-category archives hold Apple's original files, byte-for-byte, with a `manifest.json` listing the title, category, iOS range and original filesystem path of every file.

| Archive | Files |
|---|---:|
| `all-sounds.zip` | 5,359 |
| `ui-sounds.zip` | 371 |
| `ringtones-alert-tones.zip` | 47 |
| `siri-voices.zip` | 541 |
| `photos-memories.zip` | 1,845 |
| `spoken-content.zip` | 1,939 |
| `accessibility.zip` | 230 |
| plus 9 smaller categories | |

## For building a site

`iOS-System-Sounds-web-bundle.zip` (184 MB) has everything a front end needs and requires no ffmpeg to use:

- `audio/` — an AAC preview of all 5,358 playable sounds. Most of this collection is CAF or AIFF, which only Safari decodes, and a few CAF files use Apple IMA4 ADPCM that ffmpeg cannot read at all. Where the source was already AAC, 1,982 files, the stream is copied rather than re-encoded, so those are bit-identical to Apple's.
- `index.core.json` (1.07 MB) — title, category, status, format, duration and release range per sound. Enough for search and a list.
- `index.detail.json` (2.09 MB) — file paths, per-release presence, filesystem provenance, re-recording links.
- `peaks.bin` (0.26 MB) — 48 amplitude bytes per sound, in index order, for drawing a waveform per row without decoding anything client side.
- `shelves.json` — a hand-written zero state.

Play the preview, download the original. They are never the same file.

## No WAV mirror this time

v1.0.0 shipped a 1.5 GB WAV archive that was downloaded once. At full coverage it would be 3 to 5 GB, past GitHub's per-asset limit, and every audio editor opens CAF and AIFF anyway. `tools/make-wav.py` is still in the repository if you want to build one.

## Licence

The audio is Apple Inc.'s copyrighted work and no licence to it is granted here. It is collected for reference, preservation and research. `NOTICE.txt` is inside every archive.
