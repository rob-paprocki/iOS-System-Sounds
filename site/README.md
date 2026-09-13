# The website

A single page for finding a sound in this collection, hearing it, and
downloading it. Built to `docs/website-design-notes.md`; read that first for why
it looks and behaves the way it does. This file covers how to run it, how to
deploy it, and where the build had to depart from the notes.

No build step, no framework, no dependencies. Plain ES modules a browser loads
directly, two self-hosted open-licence fonts, and three static data files.

## Running it locally

Serve the repository root and open `/site/`. The defaults in `index.html`
already point at `/web/`, which is where `tools/make-web.py` puts the index and
the preview mirror.

    python3 -m http.server 8000
    open http://localhost:8000/site/

If `web/` does not exist yet, build it (needs ffmpeg), or unpack
`iOS-System-Sounds-web-bundle.zip` from the GitHub release into `web/`:

    python3 tools/make-web.py

## Deploying it

The hosting decision is in the design notes §11: Cloudflare Pages serves the
page, an R2 bucket on its own domain serves the audio. `tools/make-site.py`
stages both and rewrites the paths:

    python3 tools/make-site.py \
        --preview-base  https://audio.example.com/ \
        --original-base https://audio.example.com/originals/

That writes `_dist/site`, which is what Pages should publish. Upload to R2:

* `web/audio/**` so that `<preview-base>audio/Current/…/Tink.m4a` resolves
* the `Current/`, `Removed/` and `Spoken Content/` trees so that
  `<original-base>Current/…/Tink.caf` resolves

`site/_headers` sets the Pages cache policy: the HTML always revalidates, the
fonts are immutable, the index is good for a day.

To preview the whole thing from one origin, including audio:

    python3 tools/make-site.py --with-audio
    python3 -m http.server 8000 --directory _dist/site

## Configuration

One block at the top of `index.html`, because a static site should not need a
build to be pointed somewhere else. Three bases, because the index stores three
different kinds of path and in production they do not share an origin:

| Key | Joined to | Example stored value |
|---|---|---|
| `dataBase` | the index files | `index.core.json` |
| `previewBase` | `record.preview` | `audio/Current/UI Sounds/iPhone/Tink.m4a` |
| `originalBase` | `record.file` | `Current/UI Sounds/iPhone/Tink.caf` |

Each is joined verbatim, so keep the trailing slash. Path segments are
percent-encoded at use; the stored values are not encoded.

## How it is put together

| File | Does |
|---|---|
| `assets/worker.js` | Owns the corpus. Parses both index files off the main thread, packs the columns into typed arrays, and answers search / filter / sort / diff with an `Int32Array` of row indices. |
| `assets/store.js` | Shared state, the URL contract, formatting. |
| `assets/list.js` | The virtualised grid, row rendering, the inline detail. |
| `assets/glyph.js` | Canvas: waveform glyphs, lifespan bars, ruler, filmstrip. |
| `assets/player.js` | The single `<audio>` element. |
| `assets/ui.js` | Search field, ruler, facets, pills, sorting, About. |
| `assets/tray.js` | Selection tray, the client-side zip, the A/B compare. |
| `assets/zip.js` | A STORE-only ZIP writer, ~120 lines, no dependency. |

The list keeps about forty rows in the DOM whatever the match count. The
expanded detail is treated as one extra block of height that rows below are
offset by, so opening a row never navigates and never needs a second renderer.

## Departures from the design notes

The notes were written mid-ingest, against an assumed corpus. Where the real
data disagreed, the data won. Each of these is deliberate:

1. **"Tri-tone" and "Marimba" are not in this collection.** The notes use
   `tri-tone` as the headline example query and `shelves.json` asks for both by
   name. Neither title exists in the extracted set: Apple's classic text tone
   ships as `sms-received1.caf`, titled *SMS Received 1*, and Marimba is absent
   from the legacy ringtone block that is otherwise complete (Alarm, Ascending,
   Bark … Xylophone). The shelf silently skips names it cannot resolve, and the
   cycling placeholders were replaced with queries that actually return
   something. **This is worth chasing in the ingest**, not in the site.
2. **Scale.** 129 builds and 5,358 sounds, not the 106 and ~8,214 the notes
   estimated. 1,579 present, 3,779 removed.
3. **Variant MD5s are not in the row detail.** They exist in `sounds.json` but
   not in the web index, and §7.8 says to omit rather than invent. The detail
   shows what the index carries.
4. **The sort controls are a labelled button group, not grid column headers.**
   The notes ask for `aria-sort` on sortable headers. `aria-sort` is only valid
   on a `columnheader`, and axe-core flags it as a critical violation on a
   `button`; the header row also sits outside the grid, so claiming it as row 1
   would misreport `aria-rowindex`. The buttons use `aria-pressed` and put the
   direction in the accessible name, and the grid contains data rows only.
5. **The placeholder swaps rather than cross-fades.** A cross-fade needs an
   overlay element that can drift out of step with the real input value. It
   still freezes permanently on first focus, and never cycles under
   `prefers-reduced-motion`.
6. **The zero state has a way out.** Three hand-written shelves, as specified,
   plus a *Browse all 5,358 sounds* control, so the curated view is not a dead
   end for someone who wants to page through everything.
7. **Duration sorting is live.** The notes expected it disabled; 5,357 of 5,358
   records have a duration, so it is enabled. The column prints nothing rather
   than `0.00` for the one that does not, and the control disables itself
   automatically if coverage ever drops below half.

## Verified

Checked in a browser against the real 5,358-sound index:

* search ranking and all four operators (`category:`, `status:`, `format:`,
  `before:`/`after:`), including punctuation-insensitive matching so
  `sms-received3` finds *SMS Received 3*
* virtualisation: ~40 rows in the DOM across the full 3,419-row default view,
  correct row range, DOM order and offsets at every scroll position
* the release comparison: iOS 6.1.6 → iOS 7.0 reports 40 added, 25 removed and
  36 re-recorded, with `+` / `−` / `±` markers that do not rely on colour
* the client-side zip, round-tripped through `unzip -t` and Python's `zipfile`:
  CRCs verify and an extracted original is byte-identical to Apple's file
* axe-core 4.10: no violations, with the About panel and the tray open
* the layout down to a 500px viewport, with 44px rows and no horizontal scroll

Playback, selection, the A/B compare, keyboard navigation and URL round-tripping
were all exercised by hand.

## Not built

Deferred in the notes and still deferred: spectrograms, transcripts, dark mode,
saved favourites, per-variant byte diffing, index sharding, accounts.
