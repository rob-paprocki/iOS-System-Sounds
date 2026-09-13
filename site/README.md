# The website

Four screens for finding a sound in this collection, hearing it, understanding
where it came from, and downloading it.

Two documents shaped it. `docs/website-design-notes.md` is the written design
handoff and still governs the tool screen — its palette, its density, its
copyright rules. The Claude Design project *Sound preview website design* is the
later pass, and it settled the things the notes left open or got wrong: a dark
mode, an overview landing, a Memories stem sequencer, and the typography. Where
they disagree, the design project wins; where the real data disagrees with
either, the data wins. Both sets of departures are listed below.

No build step, no framework, no dependencies. Plain ES modules a browser loads
directly, two self-hosted open-licence fonts, and three static data files.

## The screens

| Screen | URL | What it is |
|---|---|---|
| Overview | `/site/` | What the collection is, in numbers; a shelf of the sounds people come for; the eight releases that changed the most; how the archive was built |
| Sounds | `?view=sounds` | The tool: search, facets, the release ruler, the virtualised grid, inline provenance, comparison, A/B, the selection tray |
| Memories | `?view=memories` | The 1,845 Photos Memories stems, by soundtrack and role, with a sequencer that plays a soundtrack back the way iOS assembles it |
| Contents | `?view=contents` | Every category with its present/removed split, the repository layout, the index format, and every download link |

All state is in the query string — the screen, the query, the facets, the
release range, the open row — so any view is linkable and the back button works.

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

Cloudflare Pages serves the page, an R2 bucket on its own domain serves the
audio. `tools/make-site.py` stages both and rewrites the paths:

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
| `assets/list.js` | The virtualised grid, row rendering, the inline detail, and the short static row lists the other screens reuse. |
| `assets/screens.js` | Overview, Contents, Memories, and the stem sequencer. |
| `assets/glyph.js` | Canvas: waveform glyphs, lifespan bars, ruler, filmstrip. |
| `assets/theme.js` | System / light / dark, persisted. |
| `assets/player.js` | The single `<audio>` element, and sequence playback. |
| `assets/ui.js` | Nav, search field, ruler, facets, pills, sorting. |
| `assets/tray.js` | Selection tray, the client-side zip, the A/B compare. |
| `assets/zip.js` | A STORE-only ZIP writer, ~120 lines, no dependency. |

The list keeps about forty rows in the DOM whatever the match count. The
expanded detail is treated as one extra block of height that rows below are
offset by, so opening a row never navigates and never needs a second renderer.

Canvas cannot read CSS custom properties, so `glyph.js` pulls the palette off
the root element and caches it; a theme change drops the cache and repaints.

## Departures, and why

**From the written notes** (`docs/website-design-notes.md`):

1. **There is a landing page.** §1 wants the tool and nothing else. The design
   project made an overview the landing with the tool one click away, and that
   is what is built. The search field is reachable from every screen with `/`.
2. **There is a dark mode.** §9 defers it. The design project specified a full
   dark palette and a three-way toggle, so both exist. Light is still the ground
   state and the roles never swap — green for in service, rust for oxidised out.
3. **The type is Inter and IBM Plex Mono**, not Public Sans and Fragment Mono.
   The design project did not adopt the notes' pairing.
4. **`signal` is `#5D5294`**, a purple, not the notes' blue. Everything else in
   the palette is the notes' exactly.
5. **Variant MD5s are not in the row detail.** They exist in `sounds.json` but
   not in the web index, and §7.8 says omit rather than invent.
6. **The sort controls are a labelled button group, not grid column headers.**
   `aria-sort` is only valid on a `columnheader` and axe-core flags it as a
   critical violation on a `button`; the header row also sits outside the grid,
   so claiming it as row 1 would misreport `aria-rowindex`.

**From the Claude Design project:**

7. **Diff, A/B compare and the lifespan bar are built.** Its `github.md` lists
   all three as not built this pass. They were already working here, and they
   are the part of the corpus that is actually interesting, so they stayed.
8. **Data comes from the split index, not live `sounds.json`.** The design
   fetches the 9.6 MB `sounds.json` from jsDelivr and decodes waveforms in the
   browser, which means only the ~2,184 originals a browser can decode play at
   all — its own notes say so. Here, every one of the 5,358 has an AAC preview
   and 5,341 have precomputed peaks.
9. **Shelves and placeholders use names that resolve.** The design's
   `SHELF_TITLES` lead with *Tri Tone*, *Tritone* and *Marimba*, and its
   placeholder suggests `tri-tone`. None of those exist in the extracted set:
   Apple's classic text tone ships as `sms-received1.caf`, titled *SMS Received
   1*, and Marimba is absent from an otherwise complete legacy ringtone block
   (Alarm, Ascending, Bark … Xylophone). **Worth chasing in the ingest** — a
   missing Marimba looks like an extraction gap, not an Apple fact.
10. **The release-change table excludes Spoken Content.** Counted raw it is
    1,939 Nike+ workout clips arriving in iOS 3 and leaving in iOS 8, and every
    real change to the system sounds vanishes underneath. §7.7 and §10.7 both
    say Spoken Content never drives a default view.

**From both:** the placeholder swaps rather than cross-fades — a cross-fade
needs an overlay that can drift out of step with the real input value. It still
freezes permanently on first focus and never cycles under
`prefers-reduced-motion`.

## Verified

Checked in a browser against the real 5,358-sound index:

* search ranking and all four operators (`category:`, `status:`, `format:`,
  `before:`/`after:`), including punctuation-insensitive matching so
  `sms-received3` finds *SMS Received 3*
* virtualisation: ~40 rows in the DOM across the full 3,419-row default view,
  correct row range, DOM order and offsets at every scroll position
* the release comparison: iOS 6.1.6 → iOS 7.0 reports 40 added, 25 removed and
  36 re-recorded, with `+` / `−` / `±` markers that do not rely on colour
* the overview's change table, reached from the same numbers — iOS 7.0, and the
  +782 haptics wave in 10.0.1
* the Memories sequencer: picking one stem per role and playing it back runs
  them in role order, advancing at each stem's real length
* the client-side zip, round-tripped through `unzip -t` and Python's `zipfile`:
  CRCs verify and an extracted original is byte-identical to Apple's file
* theme: light, dark and system, persisted, with the canvases repainting
* axe-core 4.10: no violations on any of the four screens, including with the
  row detail, the tray and the A/B panel open
* the layout down to a 500px viewport, with 44px rows and no horizontal scroll

Playback, selection, keyboard navigation and URL round-tripping were exercised
by hand.

## Not built

Deferred in the notes and still deferred: spectrograms, transcripts, saved
favourites, per-variant byte diffing, index sharding, accounts.
