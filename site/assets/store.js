/* ===========================================================================
   Shared state, the corpus columns, and the URL contract.

   Every view in this site is reachable as a URL, so the query string is the
   single source of truth for anything a person would want to link to or step
   back through.
   =========================================================================== */

export const CFG = Object.assign({
  dataBase: '/web/',
  previewBase: '/web/',
  originalBase: '/',
  releaseBase: '',
  repoUrl: '#',
  notice: "These sounds are Apple's copyright, collected here for reference, preservation and research. Downloading one does not give you a licence to use it."
}, window.SOUNDS_CONFIG || {});

/* Editorial order, from the design notes. Never sorted by size: sorting by size
   would put 1,939 Nike+ workout clips in front of Tri-tone. */
export const CATEGORY_ORDER = [
  'UI Sounds',
  'Ringtones & Alert Tones',
  'Telephony & Messaging',
  'Camera & Photos',
  'Haptics',
  'Accessibility',
  'Safety & Emergency',
  'Find My',
  'Home & Devices',
  'Audio & Headphones',
  'Soundscapes',
  'Siri & Voices',
  'System Frameworks',
  'Photos Memories',
  'Spoken Content'
];

/* Excluded from every default view. It is 36% of the corpus and none of it is
   what anyone came here for. The chip says so and one click undoes it. */
export const EXCLUDED_BY_DEFAULT = 'Spoken Content';

export const MAX_CLIENT_ZIP = 200;

/* --- data ------------------------------------------------------------------ */

export const data = {
  ready: false,
  detailReady: false,
  versions: [], categories: [], counts: null, formats: [], buckets: 48,
  ids: [], titles: [], originals: [], cats: [],
  status: null, catId: null, fmtId: null, duration: null, first: null, last: null,
  peaks: null,
  files: [], previews: [], dirs: [], bytes: null,
  inOff: null, inVals: null, aliveCounts: null,
  tops: []          // [{ name, count }] in editorial order
};

export const result = {
  ids: new Int32Array(0),
  fields: new Uint8Array(0),
  marks: null,
  summary: null
};

export const shelves = { list: null };

/* --- state ----------------------------------------------------------------- */

/* The four screens. "home" is the landing: an overview with the tool one click
   away. That departs from the written notes (§1 wants the tool and nothing
   else) and was settled in the design. */
export const VIEWS = ['home', 'sounds', 'contents', 'memories'];

export const state = {
  view: 'home',
  memSet: '',        // which Memories soundtrack is open
  slots: {},         // role -> sound index, the stem sequence being built
  q: '',
  cats: new Set(),
  status: 'all',
  from: 0,
  to: 0,
  sort: null,
  dir: 'asc',
  open: null,        // sound index of the expanded row
  diffMode: false,   // the ruler's two handles become a comparison bracket
  browse: false,     // step past the curated zero state into the whole list
  dense: false,
  picked: new Set(),
  ab: null           // [i, j] for the two-sound compare
};

/* --- events ---------------------------------------------------------------- */

const subs = new Map();
export function on(ev, fn) {
  if (!subs.has(ev)) subs.set(ev, new Set());
  subs.get(ev).add(fn);
}
export function emit(ev, payload) {
  const s = subs.get(ev);
  if (s) for (const fn of s) fn(payload);
}

/* --- formatting ------------------------------------------------------------ */

export function fmtInt(n) { return n.toLocaleString('en-US'); }

export function fmtDuration(d) {
  if (d == null || Number.isNaN(d)) return '';       // never print 0.00 for unknown
  if (d < 10) return d.toFixed(2) + ' s';
  if (d < 60) return d.toFixed(1) + ' s';
  const m = Math.floor(d / 60), s = Math.round(d % 60);
  return m + ':' + String(s).padStart(2, '0');
}

export function spokenDuration(d) {
  if (d == null || Number.isNaN(d)) return 'length unknown';
  if (d < 60) return `${d.toFixed(2)} seconds`;
  return `${Math.floor(d / 60)} minutes ${Math.round(d % 60)} seconds`;
}

export function fmtBytes(b) {
  if (!b) return '';
  if (b < 1024) return b + ' B';
  if (b < 1024 * 1024) return Math.round(b / 1024) + ' KB';
  return (b / 1048576).toFixed(1) + ' MB';
}

export function versionName(i) {
  const v = data.versions[i];
  return v ? v.os : '';
}

export function versionLabel(i) {
  const v = data.versions[i];
  if (!v) return '';
  return `${v.os} · ${v.build} · ${v.model}`;
}

export function topLevel(path) {
  const i = path.indexOf('/');
  return i === -1 ? path : path.slice(0, i);
}

export function previewURL(i) {
  const p = data.previews[i];
  return p ? CFG.previewBase + encodePath(p) : '';
}

export function originalURL(i) {
  const f = data.files[i];
  return f ? CFG.originalBase + encodePath(f) : '';
}

/* Paths contain spaces, "&" and "+". Encode each segment but keep the slashes. */
export function encodePath(p) {
  return p.split('/').map(encodeURIComponent).join('/');
}

export function baseName(p) {
  return p.slice(p.lastIndexOf('/') + 1);
}

/* The build indices a sound shipped in. */
export function buildsOf(i) {
  if (!data.detailReady) return null;
  return data.inVals.subarray(data.inOff[i], data.inOff[i + 1]);
}

/* --- URL ------------------------------------------------------------------- */

export function readURL() {
  const p = new URLSearchParams(location.search);
  state.view = VIEWS.includes(p.get('view')) ? p.get('view') : 'home';
  state.memSet = p.get('set') || '';
  state.q = p.get('q') || '';
  state.cats = new Set((p.get('cat') || '').split(',').filter(Boolean));
  state.status = ['present', 'removed'].includes(p.get('status')) ? p.get('status') : 'all';
  state.sort = p.get('sort') || null;
  state.dir = p.get('dir') === 'desc' ? 'desc' : 'asc';
  state.dense = p.get('dense') === '1';
  state.browse = p.get('all') === '1';

  const last = Math.max(0, data.versions.length - 1);
  const from = parseInt(p.get('from'), 10);
  const to = parseInt(p.get('to'), 10);
  state.from = Number.isFinite(from) ? Math.min(Math.max(0, from), last) : 0;
  state.to = Number.isFinite(to) ? Math.min(Math.max(state.from, to), last) : last;

  state.diffMode = p.get('diff') === '1' && state.from !== state.to;

  const id = p.get('id');
  state.open = id ? (data.ids.indexOf(id) >= 0 ? data.ids.indexOf(id) : null) : null;
}

export function writeURL(push) {
  const p = new URLSearchParams();
  if (state.view !== 'home') p.set('view', state.view);
  if (state.view === 'memories' && state.memSet) p.set('set', state.memSet);
  if (state.q) p.set('q', state.q);
  if (state.cats.size) p.set('cat', [...state.cats].join(','));
  if (state.status !== 'all') p.set('status', state.status);
  if (state.from > 0) p.set('from', state.from);
  if (state.to < data.versions.length - 1) p.set('to', state.to);
  if (state.sort) { p.set('sort', state.sort); p.set('dir', state.dir); }
  if (state.diffMode) p.set('diff', '1');
  if (state.browse) p.set('all', '1');
  if (state.dense) p.set('dense', '1');
  if (state.open != null && data.ids[state.open]) p.set('id', data.ids[state.open]);

  const url = location.pathname + (p.toString() ? '?' + p : '');
  if (push) history.pushState(null, '', url);
  else history.replaceState(null, '', url);
}

export function rangeActive() {
  return state.from > 0 || state.to < data.versions.length - 1;
}

export function filtersActive() {
  return !!state.q || state.cats.size > 0 || state.status !== 'all' || rangeActive() || state.diffMode;
}

/* --- live region ------------------------------------------------------------ */

let liveTimer = 0;
export function announce(msg) {
  const el = document.getElementById('live');
  if (!el) return;
  clearTimeout(liveTimer);
  liveTimer = setTimeout(() => { el.textContent = msg; }, 180);
}
