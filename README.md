# iOS System Sounds

Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 26.6.1,
pulled out of 129 IPSW filesystems, de-duplicated across all of them, and sorted by function.

**5,425 distinct sounds · 129 builds · 98 release lines · 19 years**

Other collections cover `System/Library/Audio/UISounds` and stop there. This one walks the
whole root filesystem, so it also has VoiceOver, Siri voice previews, the Photos Memories
soundtrack stems, haptic cues, carrier tones, spatial audio, hearing and headphone assets,
Find My tones, emergency audio, and a long tail of per-framework one-offs.

Because it covers every release rather than one, it knows *when* each sound existed. 1,580
of these still ship. 3,845 do not.

## Layout

```
Current/         1,580 files - still present in iOS 26.6.1
Removed/         1,906 files - shipped once, no longer in iOS
Spoken Content/  1,939 files - Nike+ workout narration and similar bulk speech,
                               kept separate so it does not swamp the system sounds
sounds.json      every sound: category, format, duration, which releases it shipped in
sounds.csv       the same thing as a spreadsheet
tools/           the pipeline that produces all of the above
docs/            the researched release history, and design notes for a web front end
```

Everything under those three trees is byte-for-byte what Apple shipped. Nothing was
re-encoded at any point.

## What is in it

| Category | Files |
|---|---:|
| Spoken Content (Nike+ workout narration) | 1,939 |
| Photos Memories (soundtrack stems) | 1,845 |
| Siri & Voices (voice previews, voice assets, Siri interface) | 541 |
| UI Sounds (iPhone, Watch, New, Modern) | 371 |
| System Frameworks (one folder per originating framework) | 252 |
| Accessibility (VoiceOver, Magnifier, Live Speech, Personal Audio) | 230 |
| Audio & Headphones | 69 |
| Ringtones & Alert Tones | 47 |
| Telephony & Messaging | 36 |
| Haptics | 34 |
| Find My | 21 |
| Home & Devices | 16 |
| Camera & Photos | 11 |
| Soundscapes | 7 |
| Safety & Emergency | 6 |

The trees are mixed-format because iOS is:

| `.aiff` | `.m4a` | `.caf` | `.wav` | `.voc` | `.mp3` | `.flac` |
|---:|---:|---:|---:|---:|---:|---:|
| 2,179 | 1,918 | 996 | 260 | 66 | 5 | 1 |

Extensions are taken from the container magic, not from Apple's filename, because a number
of files shipped mislabelled. Worth knowing before you build anything on these: CAF and AIFF
do not play in Chrome or Firefox, and a handful of CAF files use Apple IMA4 ADPCM, which
ffmpeg cannot parse at all. `tools/make-web.py` exists for that reason.

## Which releases were extracted

`tools/versions.json` is the matrix, and it is derived rather than hand-written. Four rules,
all in `tools/plan.py`:

- **one IPSW per major.minor line**, iOS 1.0 through 26.6 — 98 of them. The first build of
  each line, because that is where a release's new audio first appears, taken from the newest
  hardware generation that received it.
- **every iPhone launch build**, because a phone's launch build is often exclusive to it.
- **patch releases where audio is documented to have changed**, from `tools/extra-builds.json`.
- **every build Apple published for exactly one iPhone.** If one model alone received an
  image, that image is the only place anything specific to it could exist.

Re-derive it at any time with `python3 tools/plan.py`, which reads the ipsw.me firmware API.

Two builds the research wanted cannot be acquired by anyone: 21A327 (iPhone 15 / 15 Pro) and
22D8063 (iPhone 16e) were preinstalled only and never published as restore images.

## What changed, and when

Counted from the index, not from the documentation. Only core system sounds here: UI, alert
and ringtones, telephony, haptics, camera, Find My, emergency, soundscapes, Home. Voice
assets and spoken content are excluded because their churn is an order of magnitude larger
and would drown everything else.

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

Two of these are worth calling out because the files and the documentary record agree
independently. iOS 4.2.1 introduces exactly 17 core sounds, which is exactly the number of
text tones Apple's press coverage described. iOS 4.3 then adds 10 and drops 10: the same
tones, re-recorded shorter after complaints, which is visible here as ten simultaneous
replacements.

`docs/release-timeline.md` has the researched account of all of this, with sources, and an
explicit list of what the research could not establish.

## Things that turned out not to be true

**Device-specific builds almost never carry unique audio.** The premise for extracting them
was that hardware-specific sounds would live in hardware-specific images. Across all the
single-device builds extracted, exactly one contributed anything: iOS 9.0 build 13A343, the
iPhone 6s Plus launch image, which has 8 sounds that the 6s build does not. Every other
device-exclusive build, including the iPhone 14 Pro-only 16.0.1 and the iPhone 17 Pro
preinstall of 26.0, was audio-identical to its general-release sibling. Hardware-gated sounds
ship in the shared image and are selected at runtime.

**Minor releases rarely change audio before iOS 13.** iOS 15.1 through 15.8 added nothing at
all. The changes concentrate in `.0` releases, with iOS 10.3 and 4.2.1 the notable exceptions.

## How identity is decided

De-duplication runs at four levels, strongest first:

1. file MD5 — the same bytes
2. decoded-PCM MD5 — the same audio, re-wrapped or losslessly re-encoded
3. Chromaprint — the same audio re-encoded lossily, where it is long enough to fingerprint
4. PCM correlation — the same, for short sounds

Levels 3 and 4 only ever compare files that already share an Apple filename, so a similarity
score can never merge two unrelated sounds. In practice they barely matter: across the whole
corpus, tiers 3 and 4 account for a handful of merges against tens of thousands of exact
matches. The release history rests almost entirely on byte identity.

Where a sound was re-recorded rather than deleted, the two versions are linked in the index
rather than appearing as an unexplained removal next to an unexplained addition. 323 sounds
are part of such a set.

## Rebuilding it

```sh
python3 tools/plan.py         # derive the matrix from the ipsw.me API
python3 tools/build-all.py    # download, extract and ingest every release
python3 tools/measure.py      # durations and waveform peaks
python3 tools/build-repo.py   # build the trees and the index
```

`build-all.py` downloads ahead of extraction within a disk budget, deletes each IPSW as soon
as its audio is out, and resumes cleanly if interrupted. A full run is about 580 GB of
downloads and takes roughly five hours on a fast connection. Peak disk use is around 90 GB;
the retained store is 375 MB.

Needs `ipsw`, `ffmpeg` and `curl`. Releases before iOS 10 have an encrypted root filesystem
and additionally need `vfdecrypt` and `dmg2img` (`brew install dmg2img` ships both); the
decryption keys are public and fetched automatically.

Two further scripts produce things that are not committed:

```sh
python3 tools/make-wav.py     # uncompressed WAV mirror, see Releases
python3 tools/make-web.py     # AAC preview mirror and index for a web front end
```

## Caveats

Siri and VoiceOver voices are often delivered as on-demand assets after setup rather than
baked into the IPSW, so the voice inventory here is what shipped in the image, not everything
a release could download.

A sound's "dropped in" release is accurate to one minor release. Every release line is
covered, but not every patch within it, so a sound removed in 16.5.1 is recorded as gone by
16.6.

`Audio & Headphones/Empty.m4a` is a 258-byte placeholder with a zero-length audio track,
shipped that way by Apple. 68 files have no measurable duration for similar reasons.

## Licence

Two kinds of material, two sets of terms. [NOTICE.md](NOTICE.md) has the full statement.

The audio files are Apple Inc.'s copyrighted work. No licence to them is granted or implied
here. They are collected for reference, preservation and research. If you are Apple and would
like this taken down, open an issue.

The scripts, index files and documentation are original work under the [MIT licence](LICENSE).

## Prior art

[extratone/iOSSystemSounds](https://github.com/extratone/iOSSystemSounds), covering `UISounds`
in the current release across several formats.
