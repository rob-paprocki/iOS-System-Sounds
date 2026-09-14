# iOS System Sounds

Every audio file Apple shipped inside iOS, from the original iPhone in 2007 to iOS 26.6.1,
pulled out of 129 IPSW filesystems, de-duplicated across all of them, and sorted by function.

**5,359 distinct sounds from 129 builds, covering 98 release lines over 19 years.** 1,580 are
still in iOS today. The other 3,779 are gone.

Search, play and download them at **[ios-system-sounds.rpaprocki.com](https://ios-system-sounds.rpaprocki.com)**.

Other collections cover `System/Library/Audio/UISounds` and stop there. This one walks the
whole root filesystem, so it also has VoiceOver, Siri voice previews, the Photos Memories
soundtrack stems, haptic cues, carrier tones, Find My tones and a long tail of per-framework
one-offs.

## Layout

```
Current/         1,580 files, still in iOS 26.6.1
Removed/         1,840 files, shipped once and since dropped
Spoken Content/  1,939 files, Nike+ workout narration and similar bulk speech
sounds.json      every sound: category, format, duration, releases it shipped in
sounds.csv       the same thing as a spreadsheet
site/            the website
tools/           the pipeline that produces all of the above
docs/            release history, collection notes, design notes
```

Everything in those three trees is byte for byte what Apple shipped. Nothing is re-encoded at
any stage.

Formats are mixed because iOS is: 2,179 `.aiff`, 1,918 `.m4a`, 996 `.caf`, 260 `.wav`,
5 `.mp3` and 1 `.flac`. CAF and AIFF will not play in Chrome or Firefox, which is why
`tools/make-web.py` builds an AAC mirror for the site.

## Rebuilding it

```sh
python3 tools/plan.py         # derive the build matrix from the ipsw.me API
python3 tools/build-all.py    # download, extract and ingest every release
python3 tools/measure.py      # durations and waveform peaks
python3 tools/build-repo.py   # build the trees and the index
```

Roughly 580 GB of downloads and five hours on a fast connection, peaking at about 90 GB of
disk. You need `ipsw`, `ffmpeg` and `curl`. Releases before iOS 10 have an encrypted root
filesystem and also need `vfdecrypt` and `dmg2img`.

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
