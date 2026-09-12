# iOS System Sounds

Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 26.6.1,
pulled out of 129 IPSW filesystems, de-duplicated across all of them, and sorted by function.

**5,359 distinct sounds, from 129 builds covering 98 release lines over 19 years.**

Other collections cover `System/Library/Audio/UISounds` and stop there. This one walks the
whole root filesystem, so it also has VoiceOver, Siri voice previews, the Photos Memories
soundtrack stems, haptic cues, carrier tones, spatial audio, hearing and headphone assets,
Find My tones, emergency audio, and a long tail of per-framework one-offs.

Covering every release rather than one means each sound carries the list of versions it
actually appeared in. 1,580 of them are still in iOS today. The other 3,779 are gone.

## Layout

```
Current/         1,580 files - still present in iOS 26.6.1
Removed/         1,840 files - shipped once, no longer in iOS
Spoken Content/  1,939 files - Nike+ workout narration and similar bulk speech,
                               kept separate so it does not swamp the system sounds
sounds.json      every sound: category, format, duration, which releases it shipped in
sounds.csv       the same thing as a spreadsheet
tools/           the pipeline that produces all of the above
docs/            the researched release history, and design notes for a web front end
```

Everything in those three trees is byte-for-byte what Apple shipped, with no re-encoding at
any stage.

## What is in it

| Category | Files |
|---|---:|
| Spoken Content (Nike+ workout narration) | 1,939 |
| Photos Memories (soundtrack stems) | 1,845 |
| Siri & Voices (voice previews, voice assets, Siri interface) | 541 |
| UI Sounds (iPhone, Watch, New, Modern) | 371 |
| Accessibility (VoiceOver, Magnifier, Live Speech, Personal Audio) | 230 |
| System Frameworks (one folder per originating framework) | 186 |
| Audio & Headphones | 69 |
| Ringtones & Alert Tones | 47 |
| Telephony & Messaging | 36 |
| Haptics | 34 |
| Find My | 21 |
| Home & Devices | 16 |
| Camera & Photos | 11 |
| Soundscapes | 7 |
| Safety & Emergency | 6 |

The trees are mixed format because iOS is:

| `.aiff` | `.m4a` | `.caf` | `.wav` | `.mp3` | `.flac` |
|---:|---:|---:|---:|---:|---:|
| 2,179 | 1,918 | 996 | 260 | 5 | 1 |

Extensions come from the container magic rather than from Apple's filename, because a number
of files shipped mislabelled. Two things to know before building anything on these: CAF and
AIFF do not play in Chrome or Firefox, and a handful of CAF files use Apple IMA4 ADPCM, which
ffmpeg cannot parse at all. That is what `tools/make-web.py` is for.

## Which releases were extracted

`tools/versions.json` is the matrix, and it is derived rather than hand-written. Four rules,
all in `tools/plan.py`:

- One IPSW per iOS major.minor line, 1.0 through 26.6, which comes to 98 of them. The first
  build of each line, because that is where a release's new audio first appears, taken from
  the newest hardware generation that received it.
- Every iPhone launch build, since a launch build is often exclusive to that phone.
- Any patch release where audio is documented to have changed, listed in
  `tools/extra-builds.json`.
- Every build Apple published for exactly one iPhone. If a single model received an image,
  that image is the only place anything specific to it could exist.

Re-derive the matrix with `python3 tools/plan.py`, which reads the ipsw.me firmware API.

Two builds the research asked for cannot be acquired by anyone. 21A327 (iPhone 15 and 15 Pro)
and 22D8063 (iPhone 16e) were preinstalled only and never published as restore images.

## What changed, and when

These counts come from the index rather than from Apple's release notes. They cover core
system sounds only: UI, alert and ringtones, telephony, haptics, camera, Find My, emergency,
soundscapes, Home. Voice assets and spoken content are left out because their churn is an
order of magnitude larger and would drown everything else.

| Release | Added | Dropped | |
|---|---:|---:|---|
| iOS 1.0 | 58 | 0 | the original set |
| iOS 1.1.1 | 10 | 24 | |
| iOS 4.2.1 | 17 | 0 | the new text tones |
| iOS 4.3 | 10 | 10 | the same tones, re-edited shorter |
| iOS 7.0 | 56 | 39 | the flat-design sound overhaul |
| iOS 9.0 | 93 | 0 | |
| iOS 10.0.1 | 27 | 5 | |
| iOS 12.0 | 26 | 9 | |
| iOS 13.0 | 19 | 4 | |
| iOS 16.0 | 18 | 5 | |
| iOS 17.0 | 35 | 3 | new ringtones, default alert changes to Rebound |
| iOS 18.0 | 20 | 0 | |
| iOS 26.0 | 7 | 0 | |

Two rows are worth pointing at, because the files and the documentary record arrived at the
same answer separately. iOS 4.2.1 introduces exactly 17 core sounds, which is the number of
text tones Apple's press coverage described at the time. iOS 4.3 then adds 10 and drops 10:
the same tones, re-recorded shorter after complaints, showing up here as ten simultaneous
replacements.

`docs/release-timeline.md` has the researched account of all of this, with sources, and an
explicit list of what the research could not establish.

## Things that turned out not to be true

Device-specific builds almost never carry unique audio. The premise for extracting them was
that hardware-specific sounds would live in hardware-specific images. Of all the single-device
builds here, exactly one contributed anything: iOS 9.0 build 13A343, the iPhone 6s Plus launch
image, which has 8 sounds the 6s build does not. Every other device-exclusive build, including
the iPhone 14 Pro-only 16.0.1 and the iPhone 17 Pro preinstall of 26.0, was audio-identical to
its general-release sibling. Hardware-gated sounds ship in the shared image and get selected
at runtime.

Minor releases also change audio far less often than expected. iOS 15.1 through 15.8 added
nothing at all. Changes cluster in `.0` releases, with iOS 10.3 and 4.2.1 the notable
exceptions.

## How identity is decided

De-duplication runs at four levels, strongest first:

1. file MD5, meaning the same bytes
2. decoded-PCM MD5, the same audio re-wrapped or losslessly re-encoded
3. Chromaprint, for audio re-encoded lossily and long enough to fingerprint
4. PCM correlation, which does the same job for short sounds

Levels 3 and 4 only ever compare files that already share an Apple filename, so a similarity
score can never merge two unrelated sounds. In practice they hardly come up. Across the whole
corpus they account for a handful of merges against tens of thousands of exact matches, so
the release history rests almost entirely on byte identity.

Where a sound was re-recorded rather than deleted, the index links the two versions instead of
showing an unexplained removal next to an unexplained addition. 323 sounds belong to such a
set.

## Rebuilding it

```sh
python3 tools/plan.py         # derive the matrix from the ipsw.me API
python3 tools/build-all.py    # download, extract and ingest every release
python3 tools/measure.py      # durations and waveform peaks
python3 tools/build-repo.py   # build the trees and the index
```

`build-all.py` downloads ahead of extraction within a disk budget, deletes each IPSW as soon
as its audio is out, and resumes cleanly if interrupted. A full run is about 580 GB of
downloads and takes roughly five hours on a fast connection. Peak disk use is around 90 GB,
and the store it keeps afterwards is 375 MB.

You need `ipsw`, `ffmpeg` and `curl`. Releases before iOS 10 have an encrypted root filesystem
and also need `vfdecrypt` and `dmg2img` (`brew install dmg2img` ships both). The decryption
keys are public and get fetched automatically.

Two more scripts produce things that are not committed:

```sh
python3 tools/make-wav.py     # uncompressed WAV mirror, if you want one locally
python3 tools/make-web.py     # AAC preview mirror, index and per-category archives
```

`make-web.py` exists because most of this collection cannot be played in a browser. It writes
an AAC copy of every sound, stream-copying rather than re-encoding the 1,982 files that were
already AAC, alongside a split index and one file of waveform peaks. That output is published
as a bundle on the [latest release](../../releases/latest), so a site can be built from it
without needing ffmpeg.

## Caveats

Siri and VoiceOver voices are often delivered as on-demand assets after setup rather than
baked into the IPSW, so the voice inventory here is what shipped in the image, not everything
a release could download.

A sound's "dropped in" release is accurate to one minor release. Every release line is
covered, but not every patch inside it, so a sound removed in 16.5.1 is recorded as gone by
16.6.

`Audio & Headphones/Empty.m4a` is a 258-byte placeholder with a zero-length audio track,
shipped that way by Apple. It and one other file have no measurable duration.

Not everything with an audio extension is audio. iOS ships Siri speech-recognition
vocabularies as `.voc`, which is also a Creative Labs audio format, and those 66 files are
data rather than sound, so they are excluded. If you extend the extension list in
`tools/soundlib.py`, check what you caught.

## Licence

Two kinds of material, two sets of terms. [NOTICE.md](NOTICE.md) has the full statement.

The audio files are Apple Inc.'s copyrighted work. No licence to them is granted or implied
here. They are collected for reference, preservation and research. If you are Apple and would
like this taken down, open an issue.

The scripts, index files and documentation are original work under the [MIT licence](LICENSE).

## Inspired by

This collection was modelled on
[extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds), which covers
`UISounds` in the current release across several formats.
