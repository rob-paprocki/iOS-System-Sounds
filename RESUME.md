# Resume notes

Paused 2026-09-08 with 14 of 17 versions ingested. Nothing needs redoing.

## To continue

```sh
python3 tools/build-all.py
```

It skips every version already in `corpus.json`, resumes the part-downloaded
IPSW, and rebuilds the trees at the end. Three versions remain:

| iOS | Build | Device | Download |
|---|---|---|---|
| 17.0.2 | 21A350 | iPhone15,4 | 8.0 GB (3.9 GB already fetched) |
| 18.0 | 22A3354 | iPhone17,3 | 9.1 GB |
| 26.0 | 23A345 | iPhone18,2 | 10.9 GB |

Roughly 24 GB left to download and about 30 minutes of ingest.

## State on disk

Two things carry all the work. **Do not delete either**, or the only way back
is re-downloading ~78 GB of IPSWs:

- **`_store/`** (334 MB) — content-addressed copy of every unique audio file
  found across all 14 versions so far.
- **`corpus.json`** (4.1 MB) — which sound appeared in which release, the
  identity hashes, and per-variant category and title.

Both are gitignored, so they are not on GitHub. They live only in this
working directory.

Also present but disposable:

- `_work/iPhone15,4_17.0.2_21A350_Restore.ipsw.part` (3.9 GB) — a partial
  download that `ipsw` will resume. Safe to delete; costs a re-download.

Per-version extraction directories under `_work/` are deleted automatically
once ingested.

## Ingested so far

iOS 4.0, 5.0, 6.0, 7.0.1, 8.0, 9.0, 10.0.1, 11.0, 12.0, 13.0, 14.1, 15.0,
16.0, and 26.6.1 — 5,244 distinct sounds.

## Not yet done

- `Current/`, `Removed/` and `Spoken Content/` have not been committed. The
  published repo is still the iOS 26-only snapshot under `Source/`.
- The README still describes the single-version layout and needs rewriting
  for the cross-version structure once the last three versions land.
- Decide what happens to `Source/`: it is iOS 26.6.1 only, and every file in
  it is already represented in the corpus.

## Open questions

- Nike+ `SportsWorkout` prompts currently go to their own `Spoken Content/`
  tree rather than into `Removed/`. Chosen to stop ~2,000 files of workout
  narration swamping the system sounds; one mapping rule in
  `tools/soundlib.py` reverses it.
- Chromaprint contributes almost nothing: system sounds have a median
  duration under half a second, well below what it can fingerprint. The PCM
  correlation tier does that work instead.
