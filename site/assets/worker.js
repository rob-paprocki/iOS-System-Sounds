/* ===========================================================================
   Data worker.

   Owns the corpus. Parses the two index files, packs everything the list needs
   into columnar typed arrays, and answers query/filter/sort/diff requests with
   an Int32Array of row indices. The main thread never parses JSON and never
   walks 5,358 objects to filter.

   Protocol
     in   { type:'init',  base }
     out  { type:'core',  ... }      core index ready, list can paint
     out  { type:'detail', ... }     detail index ready, lifespan + diff unlock
     out  { type:'shelves', shelves } resolved zero-state shelves
     in   { type:'query', token, ... }
     out  { type:'result', token, ids, fields, marks, total }
   =========================================================================== */

let base = '';

/* Core columns */
let N = 0;
let versions = [], categories = [], counts = null;
let titles = [], originals = [], cats = [];
let lcTitle = [], sqTitle = [], lcOrig = [], lcCat = [];
let statusCol = null, catId = null, fmtId = null, formats = [];
let duration = null, first = null, last = null;
let peaks = null;

/* Detail columns (arrive later) */
let files = [], previews = [], dirs = [];
let bytes = null, inOff = null, inVals = null;
let aliveCounts = null;
let hasDetail = false;

/* --- helpers -------------------------------------------------------------- */

const lc = (s) => s.toLowerCase();
const squash = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, '');

/* Words we drop from a query because people type them as glue, not as terms.
   "tone", "sound", "alert" stay: they are real words in this corpus. */
const STOP = new Set(['the', 'a', 'an', 'of', 'for', 'my', 'and', 'that', 'this', 'is', 'in', 'on', 'to']);

function topLevel(path) {
  const i = path.indexOf('/');
  return i === -1 ? path : path.slice(0, i);
}

/* First version index belonging to a major release, e.g. "ios7" -> index of iOS 7.0 */
function versionIndexFor(spec) {
  const want = spec.toLowerCase().replace(/[^0-9.]/g, '');
  if (!want) return -1;
  for (let i = 0; i < versions.length; i++) {
    const num = versions[i].os.replace(/[^0-9.]/g, '');
    if (num === want || num.startsWith(want + '.')) return i;
  }
  // Not an exact line; fall back to the first release at or past that number.
  const wantMajor = parseFloat(want);
  for (let i = 0; i < versions.length; i++) {
    if (parseFloat(versions[i].os.replace(/[^0-9.]/g, '')) >= wantMajor) return i;
  }
  return -1;
}

/* Is sound i present in build b? Binary search over its ascending in[] slice. */
function inBuild(i, b) {
  if (!hasDetail) return b >= first[i] && b <= last[i];
  let lo = inOff[i], hi = inOff[i + 1] - 1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const v = inVals[mid];
    if (v === b) return true;
    if (v < b) lo = mid + 1; else hi = mid - 1;
  }
  return false;
}

/* --- load ----------------------------------------------------------------- */

async function loadDetail() {
  const detail = await (await fetch(base + 'index.detail.json')).json();
  const rows = detail.sounds;

  // The detail index is in the same order as the core index, but key by id
  // rather than trusting that, so a pipeline change cannot silently misalign
  // a sound with another sound's file path.
  const byId = new Map();
  for (const r of rows) byId.set(r.id, r);

  files = new Array(N); previews = new Array(N); dirs = new Array(N);
  bytes = new Int32Array(N);
  inOff = new Int32Array(N + 1);

  let total = 0;
  const ordered = new Array(N);
  for (let i = 0; i < N; i++) {
    const r = byId.get(coreIds[i]) || rows[i];
    ordered[i] = r;
    total += (r && r.in ? r.in.length : 0);
  }

  inVals = new Int16Array(total);
  aliveCounts = new Int32Array(versions.length);

  let w = 0;
  for (let i = 0; i < N; i++) {
    const r = ordered[i] || {};
    files[i] = r.file || '';
    previews[i] = r.preview || '';
    dirs[i] = r.dir || '';
    bytes[i] = r.bytes || 0;
    inOff[i] = w;
    const arr = r.in || [];
    for (let k = 0; k < arr.length; k++) {
      inVals[w++] = arr[k];
      aliveCounts[arr[k]]++;
    }
  }
  inOff[N] = w;
  hasDetail = true;

  postMessage({ type: 'detail', files, previews, dirs, bytes, inOff, inVals, aliveCounts });
}

let coreIds = [];

async function loadShelves() {
  let spec;
  try {
    spec = await (await fetch(base + 'shelves.json')).json();
  } catch { return; }

  const out = [];
  for (const sh of spec) {
    let ids = [];

    if (sh.match) {
      // Hand-written list of names, in the order they were written.
      const seen = new Set();
      for (const name of sh.match) {
        const want = squash(name);
        let best = -1, bestScore = -1;
        for (let i = 0; i < N; i++) {
          if (seen.has(i)) continue;
          if (sqTitle[i] !== want) continue;
          // Prefer a sound still shipping, and a shallower category path.
          const score = (statusCol[i] ? 100 : 0) - cats[i].split('/').length;
          if (score > bestScore) { bestScore = score; best = i; }
        }
        if (best >= 0) { ids.push(best); seen.add(best); }
      }
    } else {
      const wantStatus = sh.status === 'removed' ? 0 : sh.status === 'present' ? 1 : -1;
      const tops = sh.categories ? new Set(sh.categories) : null;
      const pool = [];
      for (let i = 0; i < N; i++) {
        if (wantStatus !== -1 && statusCol[i] !== wantStatus) continue;
        if (tops && !tops.has(topLevel(cats[i]))) continue;
        if (sh.first_build != null && first[i] !== sh.first_build) continue;
        pool.push(i);
      }
      // Most recently gone first for a removal shelf; alphabetical otherwise.
      if (wantStatus === 0) pool.sort((a, b) => last[b] - last[a] || lcTitle[a].localeCompare(lcTitle[b]));
      else pool.sort((a, b) => lcTitle[a].localeCompare(lcTitle[b]));
      ids = pool.slice(0, 14);
    }

    if (ids.length) out.push({ title: sh.title, ids });
  }
  postMessage({ type: 'shelves', shelves: out });
}

/* --- query ---------------------------------------------------------------- */

/* Field codes reported back so a row can disclose why it matched. */
const F_TITLE = 0, F_ORIG = 1, F_CAT = 2, F_DIR = 3;

function parseQuery(raw) {
  const ops = { category: null, status: null, format: null, before: null, after: null };
  const terms = [];
  const rest = [];

  for (const tok of raw.trim().split(/\s+/)) {
    if (!tok) continue;
    const m = tok.match(/^(category|cat|status|format|before|after):(.+)$/i);
    if (m) {
      const k = m[1].toLowerCase();
      const v = m[2];
      if (k === 'cat' || k === 'category') ops.category = lc(v);
      else if (k === 'status') ops.status = lc(v);
      else if (k === 'format') ops.format = lc(v);
      else if (k === 'before') ops.before = versionIndexFor(v);
      else if (k === 'after') ops.after = versionIndexFor(v);
      continue;
    }
    rest.push(tok);
  }

  for (const t of rest) {
    const l = lc(t);
    if (STOP.has(l)) continue;
    terms.push({ lc: l, sq: squash(t) });
  }
  // A query made only of stopwords still deserves to search for them.
  if (!terms.length && rest.length) {
    for (const t of rest) terms.push({ lc: lc(t), sq: squash(t) });
  }

  return { ops, terms, phrase: lc(rest.join(' ')), phraseSq: squash(rest.join(' ')) };
}

/* Best score for one term against one sound, plus which field produced it. */
function scoreTerm(i, term) {
  const t = term.lc, sq = term.sq;
  const ti = lcTitle[i];

  if (ti === t || (sq && sqTitle[i] === sq)) return [1000, F_TITLE];
  if (ti.startsWith(t) || (sq && sqTitle[i].startsWith(sq))) return [600, F_TITLE];
  // Word-start inside the title, e.g. "received" in "SMS Received 3".
  if (ti.includes(' ' + t)) return [450, F_TITLE];
  if (ti.includes(t) || (sq && sqTitle[i].includes(sq))) return [300, F_TITLE];

  if (lcOrig[i].includes(t)) return [120, F_ORIG];
  if (sq && squash(lcOrig[i]).includes(sq)) return [110, F_ORIG];

  if (lcCat[i].includes(t)) return [60, F_CAT];
  if (hasDetail && dirs[i] && lc(dirs[i]).includes(t)) return [20, F_DIR];

  return [0, -1];
}

function runQuery(msg) {
  const { ops, terms, phrase, phraseSq } = parseQuery(msg.q || '');

  const catFilter = msg.cats && msg.cats.length ? new Set(msg.cats) : null;
  const exclude = msg.exclude && msg.exclude.length ? new Set(msg.exclude) : null;
  const wantStatus = ops.status || msg.status || 'all';
  const from = msg.from | 0;
  const to = msg.to | 0;
  const rangeActive = from > 0 || to < versions.length - 1;

  const scores = [];
  const fields = [];

  const strict = [];   // every term matched
  const loose = [];    // at least one matched, used only if strict is empty

  for (let i = 0; i < N; i++) {
    // --- structural filters, cheapest first
    if (wantStatus === 'present' && statusCol[i] !== 1) continue;
    if (wantStatus === 'removed' && statusCol[i] !== 0) continue;
    const top = topLevel(cats[i]);
    if (catFilter && !catFilter.has(top)) continue;
    if (exclude && !catFilter && exclude.has(top)) continue;
    if (ops.category && !lcCat[i].includes(ops.category)) continue;
    if (ops.format && formats[fmtId[i]] !== ops.format) continue;
    if (ops.before != null && ops.before >= 0 && last[i] >= ops.before) continue;
    if (ops.after != null && ops.after >= 0 && first[i] < ops.after) continue;

    if (rangeActive) {
      // Keep a sound if it existed anywhere inside the selected range.
      if (last[i] < from || first[i] > to) continue;
      if (hasDetail) {
        let any = false;
        for (let k = inOff[i]; k < inOff[i + 1]; k++) {
          const v = inVals[k];
          if (v >= from && v <= to) { any = true; break; }
        }
        if (!any) continue;
      }
    }

    // --- text
    if (!terms.length) {
      strict.push(i); scores.push(0); fields.push(F_TITLE);
      continue;
    }

    let total = 0, matched = 0, bestField = F_TITLE, bestScore = -1;
    for (const term of terms) {
      const [sc, f] = scoreTerm(i, term);
      if (sc > 0) {
        matched++; total += sc;
        if (sc > bestScore) { bestScore = sc; bestField = f; }
      }
    }
    if (!matched) continue;

    // Whole-phrase bonus, so "sms received" beats a row matching each word apart.
    if (terms.length > 1) {
      if (lcTitle[i].includes(phrase)) total += 500;
      else if (phraseSq && sqTitle[i].includes(phraseSq)) total += 400;
    }

    if (matched === terms.length) { strict.push(i); scores.push(total); fields.push(bestField); }
    else loose.push([i, total + matched * 10, bestField]);
  }

  let ids, sc, fl;
  if (strict.length) {
    ids = strict; sc = scores; fl = fields;
  } else {
    loose.sort((a, b) => b[1] - a[1]);
    ids = loose.map(x => x[0]); sc = loose.map(x => x[1]); fl = loose.map(x => x[2]);
  }

  // --- diff mode: replace the result with the difference between two builds
  let marks = null;
  let summary = null;
  if (msg.diff && hasDetail) {
    const a = msg.diff.a, b = msg.diff.b;
    const added = [], removed = [];
    const keep = new Set(ids);
    for (const i of keep) {
      const inA = inBuild(i, a), inB = inBuild(i, b);
      if (!inA && inB) added.push(i);
      else if (inA && !inB) removed.push(i);
    }
    // A title that survives with different audio shows up as one sound leaving
    // and another with the same name arriving. That pair is a re-recording.
    const key = (i) => titles[i] + ' ' + cats[i];
    const addedBy = new Map();
    for (const i of added) {
      const k = key(i);
      if (!addedBy.has(k)) addedBy.set(k, []);
      addedBy.get(k).push(i);
    }
    const rerec = new Set();
    for (const i of removed) {
      const k = key(i);
      if (addedBy.has(k) && addedBy.get(k).length) {
        rerec.add(i);
        rerec.add(addedBy.get(k).pop());
      }
    }

    const out = [], outMarks = [], outFields = [];
    const pos = new Map();
    ids.forEach((id, n) => pos.set(id, n));
    const push = (i, mark) => { out.push(i); outMarks.push(mark); outFields.push(fl[pos.get(i)] ?? F_TITLE); };

    let nAdd = 0, nDel = 0, nRR = 0;
    for (const i of added) {
      if (rerec.has(i)) { push(i, 3); nRR++; } else { push(i, 1); nAdd++; }
    }
    for (const i of removed) {
      if (rerec.has(i)) { push(i, 3); } else { push(i, 2); nDel++; }
    }
    ids = out; fl = outFields; marks = outMarks;
    sc = ids.map(() => 0);
    summary = { added: nAdd, removed: nDel, rerecorded: nRR };
  }

  // --- sort
  const sortKey = msg.sort;
  const dir = msg.dir === 'desc' ? -1 : 1;
  const order = ids.map((_, n) => n);

  const cmp = {
    title: (x, y) => lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]),
    category: (x, y) => lcCat[ids[x]].localeCompare(lcCat[ids[y]]) || lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]),
    first: (x, y) => first[ids[x]] - first[ids[y]] || lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]),
    status: (x, y) => statusCol[ids[y]] - statusCol[ids[x]] || lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]),
    duration: (x, y) => {
      const a = duration[ids[x]], b = duration[ids[y]];
      const an = Number.isNaN(a), bn = Number.isNaN(b);
      if (an && bn) return 0;
      if (an) return 1;          // nulls always last, whichever direction
      if (bn) return -1;
      return a - b;
    },
    bytes: (x, y) => (bytes ? bytes[ids[x]] - bytes[ids[y]] : 0)
  }[sortKey];

  if (cmp) {
    order.sort((x, y) => {
      const r = cmp(x, y);
      return (sortKey === 'duration' && (Number.isNaN(duration[ids[x]]) || Number.isNaN(duration[ids[y]])))
        ? r : r * dir;
    });
  } else if (terms.length) {
    order.sort((x, y) => sc[y] - sc[x] || lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]));
  } else {
    order.sort((x, y) => lcTitle[ids[x]].localeCompare(lcTitle[ids[y]]) * dir);
  }

  const outIds = new Int32Array(order.length);
  const outFields = new Uint8Array(order.length);
  const outMarks = marks ? new Uint8Array(order.length) : null;
  for (let n = 0; n < order.length; n++) {
    const k = order[n];
    outIds[n] = ids[k];
    outFields[n] = fl[k] ?? 0;
    if (outMarks) outMarks[n] = marks[k];
  }

  postMessage(
    { type: 'result', token: msg.token, ids: outIds, fields: outFields, marks: outMarks, summary },
    outMarks ? [outIds.buffer, outFields.buffer, outMarks.buffer] : [outIds.buffer, outFields.buffer]
  );
}

/* --- message pump --------------------------------------------------------- */

onmessage = async (e) => {
  const msg = e.data;

  if (msg.type === 'init') {
    base = msg.base;
    const core = await (await fetch(base + 'index.core.json')).json();
    coreIds = core.sounds.map(s => s.id);
    // Re-use the parsed object rather than fetching twice.
    await hydrate(core);
    loadShelves();
    loadDetail().catch(err => postMessage({ type: 'error', where: 'detail', message: String(err) }));
    return;
  }

  if (msg.type === 'query') runQuery(msg);
};

/* Split out of loadCore so init can hand it an already-parsed object. */
async function hydrate(core) {
  versions = core.versions;
  categories = core.categories;
  counts = core.counts;
  const snd = core.sounds;
  N = snd.length;

  const catIndex = new Map();
  categories.forEach((c, i) => catIndex.set(c.name, i));
  const fmtIndex = new Map();

  titles = new Array(N); originals = new Array(N); cats = new Array(N);
  lcTitle = new Array(N); sqTitle = new Array(N); lcOrig = new Array(N); lcCat = new Array(N);
  statusCol = new Uint8Array(N);
  catId = new Uint16Array(N);
  fmtId = new Uint8Array(N);
  duration = new Float32Array(N);
  first = new Int16Array(N);
  last = new Int16Array(N);

  for (let i = 0; i < N; i++) {
    const s = snd[i];
    titles[i] = s.title;
    originals[i] = s.original || '';
    cats[i] = s.category;
    lcTitle[i] = lc(s.title);
    sqTitle[i] = squash(s.title);
    lcOrig[i] = lc(originals[i]);
    lcCat[i] = lc(s.category);
    statusCol[i] = s.status === 'present' ? 1 : 0;
    catId[i] = catIndex.has(s.category) ? catIndex.get(s.category) : 0;
    if (!fmtIndex.has(s.format)) { fmtIndex.set(s.format, formats.length); formats.push(s.format); }
    fmtId[i] = fmtIndex.get(s.format);
    duration[i] = s.duration == null ? NaN : s.duration;
    first[i] = s.first;
    last[i] = s.last;
  }

  const buckets = (core.peaks && core.peaks.buckets) || 48;
  const peakFile = (core.peaks && core.peaks.file) || 'peaks.bin';
  try {
    const buf = await (await fetch(base + peakFile)).arrayBuffer();
    peaks = new Uint8Array(buf);
  } catch {
    peaks = new Uint8Array(0);
  }

  postMessage({
    type: 'core',
    versions, categories, counts, formats, buckets, ids: coreIds,
    titles, originals, cats,
    status: statusCol, catId, fmtId, duration, first, last, peaks
  });
}
