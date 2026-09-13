# The website

Four screens for finding a sound in this collection, hearing it, understanding
where it came from, and downloading it.

Two documents shaped it. `docs/website-design-notes.md` is the written design
handoff: it still governs what the tool *does*, its data rules, its density and
its copyright terms. The Claude Design project *Sound preview website design* is
the later pass and governs how it *looks* — it settled the overview landing, the
Memories stem sequencer, the dark mode, and the visual system underneath all of
it. Where they disagree the design project wins; where the real data disagrees
with either, the data wins. Both sets of departures are listed below.

The visual system is **Nocturne**, the design system bound to that project.
Nocturne is dark-native, so the dark theme is its own tokens and the light theme
is mirrored out of its neutral and accent ramps rather than invented. Its
signatures, and where they land here:

* rules that fade to transparent at both ends — section rules, table rows, and
  every row in the list
* 4 / 8 / 14px radii, never square
* outline buttons that tint on hover, never filled slabs
* 11px uppercase kickers with wide tracking, in the accent
* a blurred translucent header and transport over a gradient ground

The data colours deliberately do not follow the system: green means a sound
still ships, rust means it has oxidised out, and those hold in both themes.

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

## How it is hosted

One Cloudflare Worker, on one origin.

* **The page** — `site/` is uploaded verbatim as Workers static assets. A
  request that matches a file there is served without invoking any code.
* **The index** — `site/data/` holds the four small files the page fetches
  (3.4 MB). They are generated, but committed, so a clean clone can be served
  and deployed with no build step and no ffmpeg.
* **The audio** — 191 MB of previews and 355 MB of originals live in an R2
  bucket. Requests that match no asset fall through to `worker/index.js`, which
  maps `/audio/*` and `/originals/*` onto R2 keys.

Same origin is the point: no CORS preflight before every play, no second domain
to keep alive, and Range requests answered properly so seeking works — Safari
will not play an `<audio>` source that cannot serve a range.

There is deliberately **no build step**. Workers Builds only has to run
`wrangler deploy`, so nothing in the build image can break it.

## Running it locally

    python3 tools/sync-site-data.py   # once, if site/data/ is empty
    python3 tools/serve-dev.py
    open http://localhost:8000/

`tools/serve-dev.py` routes exactly like the Worker — `site/` is the document
root, `/audio/*` comes from `web/audio/`, `/originals/*` from the repository
trees — and serves Range requests. Because the routing matches, `index.html`
needs no separate development configuration.

To run the real Worker instead, with a simulated R2 bucket:

    npx wrangler dev

## Deploying it

    npx wrangler r2 bucket create ios-system-sounds-audio   # once
    ./tools/upload-audio.sh                                 # once, and after any re-ingest
    npx wrangler deploy

`tools/upload-audio.sh` uses rclone against R2's S3 API. **Do not** use
`wrangler r2 object put` for the corpus: it percent-encodes the key it parses
out of `bucket/key`, so `UI Sounds` is stored as `UI%20Sounds` and the Worker —
which looks up the decoded, literal key — will never find it. Almost every path
in this collection contains a space.

`site/_headers` still applies; Workers parses it natively. Note that it does
*not* apply to responses the Worker generates, so the audio path sets its own
caching headers in `worker/index.js`.

After a corpus rebuild:

    python3 tools/make-web.py         # regenerate web/
    python3 tools/sync-site-data.py   # copy the index into site/data/
    ./tools/upload-audio.sh           # push changed audio to R2
    git add site/data && git commit

## Configuration

One block at the top of `index.html`. Three bases, because the index stores
three different kinds of path:

| Key | Joined to | Example stored value |
|---|---|---|
| `dataBase` | the index files | `index.core.json` |
| `previewBase` | `record.preview` | `audio/Current/UI Sounds/iPhone/Tink.m4a` |
| `originalBase` | `record.file` | `Current/UI Sounds/iPhone/Tink.caf` |

Each is joined verbatim, so keep the trailing slash. Path segments are
percent-encoded at use; the stored values are not.

All three are **absolute**, and the same in development and production, because
`site/` is the document root in both. `dataBase` in particular must be absolute:
the index is fetched inside a Web Worker, where a relative URL would resolve
against the worker script in `/assets/` rather than against the page.

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
| `assets/transport.js` | The docked now-playing bar, and the bottom inset it shares with the tray. |
| `assets/ui.js` | Nav, search field, ruler, facets, pills, sorting. |
| `assets/tray.js` | Selection tray, the client-side zip, the A/B compare. |
| `assets/zip.js` | A STORE-only ZIP writer, ~120 lines, no dependency. |
| `../worker/index.js` | Serves `/audio/*` and `/originals/*` out of R2, with Range and conditional requests. Everything else falls through to the assets binding. |

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
   dark palette and a three-way toggle, so both exist.
3. **The "records ledger" look is superseded.** §6 asks for ink on paper: zero
   radius, no shadows, hairlines doing all the structural work. The site is on
   Nocturne now — rounded, carded, gradient-grounded, with rules that fade at
   their ends. What survives from §6 is the part that carries meaning: green for
   a sound still in service, rust for one that has gone, status triple-coded by
   colour *and* shape *and* label, and a monospace face for data that aligns.
4. **The type is Inter and IBM Plex Mono**, not Public Sans and Fragment Mono.
5. **`signal` is a blurple**, `#9184D9` on dark and `#5D5294` on light, not the
   notes' blue. It is Nocturne's accent and its accent-700 respectively.
6. **Variant MD5s are not in the row detail.** They exist in `sounds.json` but
   not in the web index, and §7.8 says omit rather than invent.
7. **The sort controls are a labelled button group, not grid column headers.**
   `aria-sort` is only valid on a `columnheader` and axe-core flags it as a
   critical violation on a `button`; the header row also sits outside the grid,
   so claiming it as row 1 would misreport `aria-rowindex`.

**From the Claude Design project:**

8. **Diff, A/B compare and the lifespan bar are built.** Its `github.md` lists
   all three as not built this pass. They were already working here, and they
   are the part of the corpus that is actually interesting, so they stayed.
9. **Data comes from the split index, not live `sounds.json`.** The design
   fetches the 9.6 MB `sounds.json` from jsDelivr and decodes waveforms in the
   browser, which means only the ~2,184 originals a browser can decode play at
   all — its own notes say so. Here, every one of the 5,358 has an AAC preview
   and 5,341 have precomputed peaks.
10. **Shelves and placeholders use names that resolve.** The design's
   `SHELF_TITLES` lead with *Tri Tone*, *Tritone* and *Marimba*, and its
   placeholder suggests `tri-tone`. None of those exist in the extracted set:
   Apple's classic text tone ships as `sms-received1.caf`, titled *SMS Received
   1*, and Marimba is absent from an otherwise complete legacy ringtone block
   (Alarm, Ascending, Bark … Xylophone). **Worth chasing in the ingest** — a
   missing Marimba looks like an extraction gap, not an Apple fact.
11. **The release-change table excludes Spoken Content.** Counted raw it is
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
* the transport: it holds the last sound after playback ends and offers replay,
  rather than vanishing — most of this corpus is under a second, and a bar that
  disappeared on `ended` would only ever flicker
* axe-core 4.10: no violations on any of the four screens, in **both** themes,
  with the row detail, the tray, the transport and the A/B panel open. The light
  theme's muted ink is Nocturne's neutral-700 rather than the -600 the dark
  theme mirrors, because -600 fails contrast at 10–12px on this ground.
* the layout down to a 500px viewport, with 44px rows and no horizontal scroll

Playback, selection, keyboard navigation and URL round-tripping were exercised
by hand.

## Not built

Deferred in the notes and still deferred: spectrograms, transcripts, saved
favourites, per-variant byte diffing, index sharding, accounts.
