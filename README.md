# iOS System Sounds

Every sound file shipped in **iOS 26** (build `23G83`, iPhone 18,2), extracted from the
IPSW filesystem, de-duplicated, organised by function, and given human-readable names.

**1,613 sounds · 2h 20m of audio · 176 origin directories · 208 MB**

Where earlier collections of this kind cover only `System/Library/Audio/UISounds`, this
one sweeps the whole filesystem — VoiceOver, Siri voice previews, Photos Memories
soundtrack stems, haptic cues, carrier tones, spatial audio, hearing and headphone
assets, and the per-framework one-offs.

---

## Contents

| Category | Files | Subfolders |
|---|---:|---|
| Photos Memories | 486 | `CR/`, `FT/`, `GWB/`, `HE/`, `MEM2/`, `MU/`, `xgame/`, `Misc/` — each split into `Intro`, `Body`, `Transition`, `Crossfade`, `Outro` |
| Siri & Voices | 371 | `Voice Previews`, `Voice Previews (Accessibility)`, `Voice Previews (Interactive)`, `Voice Assets`, `Siri Interface` |
| UI Sounds | 278 | `iPhone`, `Watch`, `New`, `Modern` |
| Accessibility | 217 | `VoiceOver`, `Magnifier`, `Live Speech`, `Personal Audio`, `Other` |
| Audio & Headphones | 69 | — |
| System Frameworks | 39 | one folder per originating framework |
| Telephony & Messaging | 36 | `Carrier` |
| Haptics | 33 | `System`, `Generic` |
| Find My | 23 | — |
| Ringtones & Alert Tones | 21 | `Alert Tones`, `Encore Infinitum` |
| Home & Devices | 16 | — |
| Camera & Photos | 11 | — |
| Soundscapes | 7 | — |
| Safety & Emergency | 6 | — |

## Layout

```
Source/        1,613 files, exactly as Apple shipped them (byte-identical)
WAV/           the same tree converted to uncompressed WAV — see Releases
sounds.json    machine-readable index of every sound
_manifest.csv  the same data as CSV, including every path a file was found at
tools/         script to regenerate WAV/ from Source/
```

`Source/` is mixed-format because iOS itself is:

| Format | Files |
|---|---:|
| `.caf` | 714 |
| `.m4a` | 523 |
| `.aiff` | 216 |
| `.wav` | 157 |
| `.mp3` | 2 |
| `.flac` | 1 |

### The WAV mirror

`WAV/` is **not committed** — 1.6 GB of uncompressed audio does not belong in git
history. Download it from [Releases](../../releases), or rebuild it yourself:

```sh
python3 tools/make-wav.py          # needs ffmpeg on PATH
```

It mirrors `Source/` exactly: same folders, same names, `.wav` extension. Sample rate
and channel count are preserved, and bit depth follows the input rather than being
flattened — 530 files at 16-bit, 1,079 at 24-bit, 1 at 32-bit.

## The index

`sounds.json` describes every file — codec, sample rate, channels, duration, size, MD5,
the original Apple filename, and the full list of IPSW paths it was found at:

```json
{
  "file": "UI Sounds/iPhone/SMS Received 3.caf",
  "title": "SMS Received 3",
  "category": "UI Sounds",
  "subcategory": "iPhone",
  "format": "caf",
  "codec": "pcm_s16le",
  "sample_rate": 44100,
  "channels": 2,
  "duration_sec": 1.511,
  "wav": "UI Sounds/iPhone/SMS Received 3.wav",
  "original_filename": "sms-received3.caf",
  "ipsw_paths": ["System/Library/Audio/UISounds"],
  "duplicate_copies_removed": 0,
  "md5": "..."
}
```

## How this was built

1. **Extracted** the filesystem from the iOS 26 IPSW for iPhone 18,2 (build `23G83`).
2. **Collected** all 1,780 audio files by extension across the whole tree.
3. **De-duplicated by MD5**, not by name — 167 redundant copies removed. Where a file
   shipped in several places, the canonical system path was kept over staged or
   mounted-disk-image copies, and every origin path is recorded in the index.
4. **Corrected 9 mislabelled extensions.** Nine files named `.caf` were not CAF at all:
   five RIFF/WAVE, two M4A, two FLAC. They now carry their true extension. Three `.aif`
   files were normalised to `.aiff`.
5. **Renamed** from Apple's internal asset names to readable titles
   (`sms-received3.caf` → `SMS Received 3.caf`), keeping locale tags and internal cue
   codes intact where they carry meaning.
6. **Organised** into the category tree above, derived from each file's origin directory.

No audio was re-encoded at any point. Everything in `Source/` is byte-for-byte what
Apple shipped.

## Notes and caveats

- **Photos Memories folder names** (`GWB`, `FT`, `MU`, `HE`, `CR`, `MEM2`, `xgame`) are
  the internal code prefixes Apple uses in the filenames. The soundtracks ship with no
  name metadata, so these are not invented titles.
- **`Audio & Headphones/Empty.m4a`** is a 258-byte placeholder with a zero-length audio
  track, shipped that way in `MediaPlaybackCore.framework`. It has no WAV counterpart
  because there is nothing to decode.
- **`Siri & Voices/Siri Interface/Begin Sae Short.caf`** uses Apple IMA4 ADPCM, which
  ffmpeg cannot parse. The conversion script falls back to `afconvert` on macOS.
- **AAC durations** in `Source/` are marginally longer than their WAV counterparts. That
  is correct gapless trimming of encoder priming samples, verified to be
  sample-identical between ffmpeg and Core Audio. No audio is lost.
- **Two `FMRSSI Level` sounds appear twice** under `Find My/`, suffixed `(Find My app)`
  and `(Finding UI)`. They are genuinely different recordings that share a filename in
  different frameworks.

## Licence

The **audio files are Apple Inc.'s copyrighted work** and are not covered by any open
licence. They are collected here for reference, preservation, and research. If you are
Apple and would like this taken down, open an issue.

The **scripts, index, and documentation** in this repository are released under the MIT
licence — see [LICENSE](LICENSE).

## Prior art

- [extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds) — the
  collection this one is modelled on, covering `UISounds` across several formats.
