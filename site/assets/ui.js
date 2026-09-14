/* ===========================================================================
   Page chrome: the section nav, the readout, the search field, the release
   ruler, the facet chips, the active-filter pills and sorting.
   =========================================================================== */

import {
  CFG, data, state, result, on,
  CATEGORY_ORDER, EXCLUDED_BY_DEFAULT,
  fmtInt, topLevel, versionName, versionLabel, rangeActive, filtersActive, announce
} from './store.js';
import { drawRuler } from './glyph.js';

const $ = (id) => document.getElementById(id);

const qInput = $('q');
const readout = $('readout');
const qCount = $('q-count');
const chipsBox = $('chips');
const pillsBox = $('pills');
const rulerCanvas = $('ruler-canvas');
const rulerTrack = $('ruler-track');
const rulerSel = $('ruler-sel');
const hFrom = $('ruler-from');
const hTo = $('ruler-to');
const rulerTip = $('ruler-tip');
const rulerReadout = $('ruler-readout');
const rulerReset = $('ruler-reset');
const fromSelect = $('from-select');
const toSelect = $('to-select');
const diffBar = $('diff-bar');
const diffSummary = $('diff-summary');

let notify = () => {};

/* Half-remembered phrasings, the way people actually arrive here. Every one of
   these is checked against the corpus: a placeholder that suggests a query
   returning nothing is the site lying to you. The design notes proposed
   "tri-tone" and "marimba", but neither name exists in the extracted set —
   Apple's classic text tone ships as sms-received1.caf. */
const PLACEHOLDERS = [
  'Try: the old text tone',
  'Try: camera shutter',
  'Try: old phone',
  'Try: sms received'
];

/* Which section is showing. The wordmark also goes home, but it is not a nav
   item and never takes the current-page marker. */
export function syncNav() {
  document.querySelectorAll('.nav [data-goto]').forEach(b => {
    const on_ = b.dataset.goto === state.view;
    b.setAttribute('aria-pressed', String(on_));
    if (on_) b.setAttribute('aria-current', 'page');
    else b.removeAttribute('aria-current');
  });
}

export function slugFor(name) {
  return name.toLowerCase().replace(/&/g, ' ').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
}

/* --- top-level categories --------------------------------------------------- */

export function buildTops() {
  const counts = new Map();
  for (const c of data.categories) {
    const t = topLevel(c.name);
    counts.set(t, (counts.get(t) || 0) + c.count);
  }
  const known = CATEGORY_ORDER.filter(n => counts.has(n));
  const rest = [...counts.keys()].filter(n => !CATEGORY_ORDER.includes(n)).sort();
  data.tops = [...known, ...rest].map(name => ({ name, count: counts.get(name) }));
}

/* --- chips ------------------------------------------------------------------ */

export function renderChips() {
  chipsBox.innerHTML = '';
  for (const { name, count } of data.tops) {
    const on_ = state.cats.has(name);
    const excluded = name === EXCLUDED_BY_DEFAULT && !on_;
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'chip' + (excluded ? ' excluded' : '');
    b.setAttribute('aria-pressed', String(on_));
    // The exclusion is visible, and one click undoes it.
    b.innerHTML = `${excluded ? '+ ' : ''}${escapeText(name)}<span class="n">${fmtInt(count)}</span>`;
    b.addEventListener('click', () => {
      if (state.cats.has(name)) state.cats.delete(name); else state.cats.add(name);
      renderChips();
      notify(true);
    });
    chipsBox.appendChild(b);
  }
}

function escapeText(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* --- status ----------------------------------------------------------------- */

function initStatus() {
  document.querySelectorAll('.status-toggle button').forEach(b => {
    b.addEventListener('click', () => {
      state.status = b.dataset.status;
      syncStatus();
      notify(true);
    });
  });
}

function syncStatus() {
  document.querySelectorAll('.status-toggle button').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.status === state.status));
  });
}

/* --- pills ------------------------------------------------------------------ */

export function renderPills() {
  pillsBox.innerHTML = '';
  const add = (label, clear) => {
    const b = document.createElement('button');
    b.type = 'button';
    b.className = 'pill';
    b.innerHTML = `${escapeText(label)}<span class="x" aria-hidden="true">×</span>`;
    b.setAttribute('aria-label', `Remove filter: ${label}`);
    b.addEventListener('click', () => { clear(); notify(true); });
    pillsBox.appendChild(b);
  };

  if (state.q) add(`"${state.q}"`, () => { state.q = ''; qInput.value = ''; });
  for (const c of state.cats) add(c, () => { state.cats.delete(c); renderChips(); });
  if (state.status !== 'all') add(state.status === 'present' ? 'Present only' : 'Removed only', () => { state.status = 'all'; syncStatus(); });
  if (rangeActive() && !state.diffMode) {
    add(`${versionName(state.from)} to ${versionName(state.to)}`, () => {
      state.from = 0; state.to = data.versions.length - 1; syncRuler();
    });
  }
  if (state.diffMode) {
    add(`Comparing ${versionName(state.from)} with ${versionName(state.to)}`, () => { state.diffMode = false; syncDiffBar(); });
  }
}

/* --- readout ---------------------------------------------------------------- */

export function renderReadout() {
  if (!data.ready) return;
  const n = result.ids.length;
  const total = data.counts.total;

  let present = 0;
  for (let k = 0; k < n; k++) if (data.status[result.ids[k]] === 1) present++;

  const span = `iOS ${versionName(0).replace(/^iOS /, '')} to ${versionName(data.versions.length - 1).replace(/^iOS /, '')}`;
  const head = filtersActive() ? `${fmtInt(n)} of ${fmtInt(total)} sounds` : `${fmtInt(total)} sounds`;
  readout.textContent = `${head} · ${fmtInt(present)} present · ${data.versions.length} builds · ${span}`;

  qCount.textContent = filtersActive() ? `${fmtInt(n)} of ${fmtInt(total)}` : fmtInt(total);
}

/* --- search ----------------------------------------------------------------- */

function initSearch() {
  let cycle = 0;
  let timer = 0;
  const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  qInput.placeholder = PLACEHOLDERS[0];
  if (!reduce) {
    timer = setInterval(() => {
      cycle = (cycle + 1) % PLACEHOLDERS.length;
      qInput.placeholder = PLACEHOLDERS[cycle];
    }, 3200);
  }
  // It freezes the moment you focus or type, permanently.
  const freeze = () => { clearInterval(timer); qInput.placeholder = 'Search every sound'; };
  qInput.addEventListener('focus', freeze, { once: true });

  // Instant, client side, no submit button and no debounce.
  qInput.addEventListener('input', () => {
    state.q = qInput.value;
    notify(false);
  });

  qInput.addEventListener('keydown', (ev) => {
    if (ev.key === 'Escape') {
      if (qInput.value) { qInput.value = ''; state.q = ''; notify(false); }
      else qInput.blur();
      ev.preventDefault();
    }
  });

  $('tips-toggle').addEventListener('click', () => {
    const t = $('tips');
    t.hidden = !t.hidden;
    $('tips-toggle').setAttribute('aria-expanded', String(!t.hidden));
  });
}

/* --- ruler ------------------------------------------------------------------ */

function pct(v) {
  const V = data.versions.length;
  return ((v + 0.5) / V) * 100;
}

function vFromX(clientX) {
  const V = data.versions.length;
  const r = rulerTrack.getBoundingClientRect();
  const f = (clientX - r.left) / r.width;
  return Math.max(0, Math.min(V - 1, Math.round(f * V - 0.5)));
}

export function syncRuler(hover = -1) {
  if (!data.versions.length) return;
  const V = data.versions.length;
  drawRuler(rulerCanvas, state.from, state.to, hover);

  hFrom.style.left = pct(state.from) + '%';
  hTo.style.left = pct(state.to) + '%';
  rulerSel.style.left = pct(state.from) + '%';
  rulerSel.style.width = (pct(state.to) - pct(state.from)) + '%';

  for (const [h, v] of [[hFrom, state.from], [hTo, state.to]]) {
    h.setAttribute('aria-valuemax', String(V - 1));
    h.setAttribute('aria-valuenow', String(v));
    h.setAttribute('aria-valuetext', versionLabel(v));
  }

  rulerReadout.textContent = state.diffMode
    ? `${versionName(state.from)} → ${versionName(state.to)}`
    : `${versionLabel(state.from)}  to  ${versionLabel(state.to)}`;

  rulerReset.hidden = !rangeActive();
  if (fromSelect.value !== String(state.from)) fromSelect.value = String(state.from);
  if (toSelect.value !== String(state.to)) toSelect.value = String(state.to);
}

function initRuler() {
  const V = data.versions.length;
  for (const sel of [fromSelect, toSelect]) {
    sel.innerHTML = '';
    for (let i = 0; i < V; i++) {
      const o = document.createElement('option');
      o.value = String(i);
      o.textContent = `${data.versions[i].os} (${data.versions[i].build})`;
      sel.appendChild(o);
    }
  }
  fromSelect.addEventListener('change', () => {
    state.from = Math.min(parseInt(fromSelect.value, 10), state.to);
    syncRuler(); notify(true);
  });
  toSelect.addEventListener('change', () => {
    state.to = Math.max(parseInt(toSelect.value, 10), state.from);
    syncRuler(); notify(true);
  });

  let dragging = null;
  const startDrag = (which) => (ev) => {
    dragging = which;
    ev.target.setPointerCapture(ev.pointerId);
    ev.preventDefault();
  };
  hFrom.addEventListener('pointerdown', startDrag('from'));
  hTo.addEventListener('pointerdown', startDrag('to'));

  const move = (ev) => {
    if (!dragging) return;
    const v = vFromX(ev.clientX);
    if (dragging === 'from') state.from = Math.min(v, state.to);
    else state.to = Math.max(v, state.from);
    syncRuler();
    notify(false);
  };
  hFrom.addEventListener('pointermove', move);
  hTo.addEventListener('pointermove', move);

  const end = () => {
    if (!dragging) return;
    dragging = null;
    notify(true);
    announce(`Showing ${versionName(state.from)} to ${versionName(state.to)}`);
  };
  hFrom.addEventListener('pointerup', end);
  hTo.addEventListener('pointerup', end);
  hFrom.addEventListener('pointercancel', end);
  hTo.addEventListener('pointercancel', end);

  // Click the track to move the nearer handle.
  rulerTrack.addEventListener('pointerdown', (ev) => {
    if (ev.target === hFrom || ev.target === hTo) return;
    const v = vFromX(ev.clientX);
    if (Math.abs(v - state.from) <= Math.abs(v - state.to)) state.from = Math.min(v, state.to);
    else state.to = Math.max(v, state.from);
    syncRuler();
    notify(true);
  });

  rulerTrack.addEventListener('pointermove', (ev) => {
    if (dragging) return;
    const v = vFromX(ev.clientX);
    rulerTip.hidden = false;
    rulerTip.textContent = versionLabel(v);
    const r = rulerTrack.getBoundingClientRect();
    rulerTip.style.left = Math.max(0, Math.min(r.width - 190, ev.clientX - r.left - 60)) + 'px';
    syncRuler(v);
  });
  rulerTrack.addEventListener('pointerleave', () => { rulerTip.hidden = true; syncRuler(); });

  const key = (which) => (ev) => {
    const V2 = data.versions.length - 1;
    let v = which === 'from' ? state.from : state.to;
    let handled = true;
    switch (ev.key) {
      case 'ArrowLeft': case 'ArrowDown': v -= 1; break;
      case 'ArrowRight': case 'ArrowUp': v += 1; break;
      case 'PageDown': v -= 10; break;
      case 'PageUp': v += 10; break;
      case 'Home': v = which === 'from' ? 0 : state.from; break;
      case 'End': v = which === 'from' ? state.to : V2; break;
      default: handled = false;
    }
    if (!handled) return;
    ev.preventDefault();
    v = Math.max(0, Math.min(V2, v));
    if (which === 'from') state.from = Math.min(v, state.to);
    else state.to = Math.max(v, state.from);
    syncRuler();
    notify(true);
    announce(versionLabel(which === 'from' ? state.from : state.to));
  };
  hFrom.addEventListener('keydown', key('from'));
  hTo.addEventListener('keydown', key('to'));

  rulerReset.addEventListener('click', () => {
    state.from = 0;
    state.to = data.versions.length - 1;
    syncRuler();
    notify(true);
  });

  $('diff-enter').addEventListener('click', () => {
    if (!data.detailReady) return;
    if (state.from === state.to) { state.from = 0; state.to = data.versions.length - 1; }
    state.diffMode = true;
    syncDiffBar(); syncRuler(); notify(true);
  });
  $('diff-exit').addEventListener('click', () => {
    state.diffMode = false;
    syncDiffBar(); syncRuler(); notify(true);
  });

  window.addEventListener('resize', () => syncRuler());
}

export function syncDiffBar() {
  diffBar.hidden = !state.diffMode;
  const enter = $('diff-enter');
  enter.hidden = state.diffMode;
  enter.disabled = !data.detailReady;
  if (!state.diffMode) return;
  const s = result.summary;
  diffSummary.textContent = s
    ? `${versionName(state.from)} → ${versionName(state.to)}: ${fmtInt(s.added)} added · ${fmtInt(s.removed)} removed · ${fmtInt(s.rerecorded)} re-recorded`
    : `${versionName(state.from)} → ${versionName(state.to)}`;
}

/* --- sorting ---------------------------------------------------------------- */

function initSorts() {
  document.querySelectorAll('[data-sort]').forEach(b => {
    b.addEventListener('click', () => {
      const key = b.dataset.sort;
      if (key === 'duration' && !durationSortable()) return;
      if (state.sort === key) state.dir = state.dir === 'asc' ? 'desc' : 'asc';
      else { state.sort = key; state.dir = 'asc'; }
      syncSorts();
      notify(true);
    });
  });
}

function durationSortable() {
  // Disabled while the pipeline has not filled duration in; never sorts on a
  // column that is mostly blank.
  let known = 0;
  for (let i = 0; i < data.duration.length; i++) if (!Number.isNaN(data.duration[i])) known++;
  return known > data.duration.length * 0.5;
}

export function syncSorts() {
  document.querySelectorAll('[data-sort]').forEach(b => {
    const active = state.sort === b.dataset.sort;
    const name = b.dataset.label || (b.dataset.label = b.textContent.trim());

    // These are sort controls in a labelled group, not grid column headers, so
    // the state is aria-pressed and the direction goes in the accessible name.
    // aria-sort belongs only on a columnheader and is invalid on a button.
    b.setAttribute('aria-pressed', String(active));
    b.setAttribute('aria-label', active
      ? `Sorted by ${name}, ${state.dir === 'asc' ? 'ascending' : 'descending'}. Activate to reverse.`
      : `Sort by ${name}`);

    if (active) b.dataset.dir = state.dir;
    else delete b.dataset.dir;

    if (b.dataset.sort === 'duration' && data.ready && !durationSortable()) {
      b.disabled = true;
      b.title = 'Length is not yet recorded for most sounds, so sorting by it would be misleading.';
    }
    if (b.dataset.sort === 'bytes' && !data.detailReady) b.disabled = true;
    else if (b.dataset.sort === 'bytes') b.disabled = false;
  });
}

/* --- init ------------------------------------------------------------------- */

export function initUI(onChange) {
  notify = onChange;
  $('footer-notice').textContent = CFG.notice;
  $('tray-notice').textContent = CFG.notice;
  $('repo-link').href = CFG.repoUrl;

  initSearch();
  initStatus();
  initSorts();

  $('dense').addEventListener('change', (ev) => {
    state.dense = ev.target.checked;
    document.body.classList.toggle('dense', state.dense);
    notify(false);
  });

  on('core', () => {
    buildTops();
    renderChips();
    initRuler();
    syncRuler();
    syncStatus();
    syncSorts();
    syncDiffBar();
    qInput.value = state.q;
    $('dense').checked = state.dense;
    document.body.classList.toggle('dense', state.dense);
  });

  on('detail', () => { syncRuler(); syncSorts(); syncDiffBar(); });

  on('result', () => {
    renderReadout();
    renderPills();
    syncDiffBar();
  });
}
