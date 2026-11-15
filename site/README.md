# The website

Four screens for finding a sound in this collection, hearing it, seeing where it came from and downloading it.

The look is dark-first. The dark theme uses its own colour tokens, and the light theme mirrors them from the same neutral and accent ramps. A few details carry through the whole site:

* Rules fade to transparent at both ends: section rules, table rows and every row in the list.
* Corners use 4, 8 and 14px radii, never square.
* Buttons are outlines that tint on hover.
* Kickers are 11px uppercase with wide tracking, in the accent colour.
* The header and transport bar are blurred and translucent over a gradient ground.

The data colours don't follow the system. Green means a sound still ships and rust means it has gone, in both themes.

There is no build step, no framework and no dependencies. The site is plain ES modules a browser loads directly, two self-hosted open-license fonts and three static data files.

## The screens

| Screen | URL | What it is |
|---|---|---|
| Overview | `/site/` | The collection in numbers, a shelf of the sounds people come looking for, the eight releases that changed the most, and how the archive was built |
| Sounds | `?view=sounds` | The search tool: facets, a release ruler, a virtualised grid, inline provenance, comparison, A/B and the selection tray |
| Memories | `?view=memories` | The 1,845 Photos Memories stems by soundtrack and role, with a sequencer that plays a soundtrack back the way iOS assembles it |
| Contents | `?view=contents` | Every category with its present and removed split, the repository layout, the index format and every download link |

All state lives in the query string: the screen, the query, the facets, the release range and the open row. Any view can be linked, and the back button works.

## How it is hosted

One Cloudflare Worker serves everything from one origin.

* **The page.** `site/` is uploaded as-is as Workers static assets. A request that matches a file there is served without running any code.
* **The index.** `site/data/` holds the four small files the page fetches (3.4 MB). They are generated but committed, so a clean clone can be served and deployed without ffmpeg or a build.
* **The audio.** 191 MB of previews and 355 MB of originals sit in an R2 bucket. Requests that match no asset fall through to `worker/index.js`, which maps `/audio/*` and `/originals/*` onto R2 keys.

A single origin means no CORS preflight before each play, no second domain to keep alive, and Range requests that work, so seeking works. Safari won't play an `<audio>` source that can't answer a range request.

Workers Builds only has to run `wrangler deploy`, so nothing in the build image can break.

## Running it locally

```bash
python3 tools/sync-site-data.py   # once, if site/data/ is empty
python3 tools/serve-dev.py
```

Then open `http://localhost:8000/`.

`tools/serve-dev.py` routes the way the Worker does. `site/` is the document root, `/audio/*` comes from `web/audio/`, `/originals/*` comes from the repository trees, and Range requests work. Because the routing matches, `index.html` needs no separate development configuration.

To run the real Worker against a simulated R2 bucket:

```bash
npx wrangler dev
```

## Deploying it

```bash
npx wrangler r2 bucket create ios-system-sounds-audio   # once
npx wrangler deploy
```

The page works at that point, but nothing plays until the audio is in the bucket. Uploading needs an R2 API token with Object Read & Write, which you create in the Cloudflare dashboard under R2, API, Manage API tokens:

```bash
export R2_ACCOUNT_ID=<ACCOUNT_ID>
export R2_ACCESS_KEY_ID=<ACCESS_KEY_ID>
export R2_SECRET_ACCESS_KEY=<SECRET_ACCESS_KEY>
python3 tools/upload-audio.py --limit 5 --verbose   # smoke test
python3 tools/upload-audio.py                       # 10,716 files, 542 MB
```

`tools/upload-audio.py` speaks S3 using only the standard library, so there is no rclone or boto3 to install. Re-runs skip any file whose size and MD5 already match, so an interrupted upload resumes. Its SigV4 signing is checked against AWS's published test vectors by `tools/tests/test_sigv4.py`.

> [!WARNING]
> Don't use `wrangler r2 object put` for the corpus. It percent-encodes the key it parses out of `bucket/key`, so `UI Sounds` is stored as `UI%20Sounds`, and the Worker looks up the decoded, literal key and never finds it. Almost every path in this collection contains a space.

`site/_headers` still applies, because Workers parses it natively. It doesn't apply to responses the Worker generates, so the audio path sets its own caching headers in `worker/index.js`.

After a corpus rebuild:

```bash
python3 tools/make-web.py          # regenerate web/
python3 tools/sync-site-data.py    # copy the index into site/data/
python3 tools/upload-audio.py      # push changed audio to R2
git add site/data && git commit
```

## Configuration

One block at the top of `index.html` sets three bases, because the index stores three kinds of path:

| Key | Joined to | Example stored value |
|---|---|---|
| `dataBase` | the index files | `index.core.json` |
| `previewBase` | `record.preview` | `audio/Current/UI Sounds/iPhone/Tink.m4a` |
| `originalBase` | `record.file` | `Current/UI Sounds/iPhone/Tink.caf` |

Each is joined verbatim, so keep the trailing slash. Path segments are percent-encoded when used, and the stored values are not.

All three are absolute and identical in development and production, because `site/` is the document root in both. `dataBase` has to be absolute because the index is fetched inside a Web Worker, where a relative URL would resolve against the worker script in `/assets/` instead of the page.

## How it is put together

| File | Does |
|---|---|
| `assets/worker.js` | Owns the corpus. Parses both index files off the main thread, packs the columns into typed arrays, and answers search, filter, sort and diff with an `Int32Array` of row indices. |
| `assets/store.js` | Shared state, the URL contract and formatting. |
| `assets/list.js` | The virtualised grid, row rendering, the inline detail, and the short static row lists the other screens reuse. |
| `assets/screens.js` | Overview, Contents, Memories and the stem sequencer. |
| `assets/glyph.js` | Canvas drawing: waveform glyphs, lifespan bars, the ruler and the filmstrip. |
| `assets/theme.js` | System, light or dark, persisted. |
| `assets/player.js` | The single `<audio>` element and sequence playback. |
| `assets/transport.js` | The docked now-playing bar, and the bottom inset it shares with the tray. |
| `assets/ui.js` | Nav, search field, ruler, facets, pills and sorting. |
| `assets/tray.js` | Selection tray, the client-side zip and the A/B compare. |
| `assets/zip.js` | A STORE-only ZIP writer, about 120 lines, no dependency. |
| `../worker/index.js` | Serves `/audio/*` and `/originals/*` out of R2 with Range and conditional requests. Everything else falls through to the assets binding. |

The list keeps about forty rows in the DOM whatever the match count. An expanded detail counts as one extra block of height that the rows below are offset by, so opening a row never navigates and doesn't need a second renderer.

Canvas can't read CSS custom properties, so `glyph.js` reads the palette off the root element and caches it. A theme change drops the cache and repaints.

Search has a few details worth knowing. The placeholder text swaps instead of cross-fading, because a cross-fade needs an overlay that can drift out of step with the real input. It freezes for good on first focus and never cycles under `prefers-reduced-motion`. Sort controls are a labelled button group rather than grid column headers, since `aria-sort` is only valid on a `columnheader` and axe-core flags it as a critical violation on a button. The release-change table leaves out Spoken Content: counted raw, it is 1,939 Nike+ workout clips arriving in iOS 3 and leaving in iOS 8, and every real change to the system sounds disappears underneath.

## Checked

Tested in a browser against the full sound index:

* Search ranking and all four operators (`category:`, `status:`, `format:`, `before:` and `after:`), including punctuation-insensitive matching, so `sms-received3` finds *SMS Received 3*.
* Virtualisation: about 40 rows in the DOM across the full default list, with the right row range, DOM order and offsets at every scroll position.
* The release comparison: iOS 6.1.6 to iOS 7.0 reports 40 added, 25 removed and 36 re-recorded, with `+`, `−` and `±` markers that don't rely on colour.
* The overview's change table, which surfaces iOS 7.0 and the +782 haptics wave in 10.0.1.
* The Memories sequencer: picking one stem per role and playing it back runs them in role order, each advancing at its real length.
* The client-side zip, round-tripped through `unzip -t` and Python's `zipfile`. CRCs verify, and an extracted original is byte-identical to Apple's file.
* Theme: light, dark and system, persisted, with the canvases repainting.
* The transport: it holds the last sound after playback ends and offers replay. Most of this corpus is under a second, so a bar that vanished on `ended` would only flicker.
* axe-core 4.10: no violations on any of the four screens, in both themes, with the row detail, tray, transport and A/B panel open. The light theme's muted ink is one step darker than the dark theme's mirrored value, because 600 fails contrast at 10 to 12px on this ground.
* The layout down to a 500px viewport, with 44px rows and no horizontal scroll.

Playback, selection, keyboard navigation and URL round-tripping were exercised by hand.

## Not built

Spectrograms, transcripts, saved favourites, per-variant byte diffing, index sharding and accounts.
