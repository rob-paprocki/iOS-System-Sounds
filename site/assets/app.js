/* ===========================================================================
   Bootstrap and wiring.

   Starts the worker, keeps the URL and the view in step, dispatches queries,
   and owns the keyboard grammar. Everything here is orchestration; the work
   happens in worker.js, list.js, ui.js and tray.js.
   =========================================================================== */

import {
  CFG, data, state, result, shelves, VIEWS,
  on, emit, readURL, writeURL, filtersActive, fmtInt, announce, EXCLUDED_BY_DEFAULT
} from './store.js';
import * as list from './list.js';
import * as ui from './ui.js';
import * as tray from './tray.js';
import * as player from './player.js';
import * as screens from './screens.js';
import { initTheme } from './theme.js';
import { initTransport } from './transport.js';

const worker = new Worker(new URL('./worker.js', import.meta.url), { type: 'module' });

const gridEl = document.getElementById('list');
const shelvesEl = document.getElementById('shelves');
const toolbarEl = document.querySelector('.list-toolbar');

const screenEls = {
  home: document.getElementById('screen-home'),
  contents: document.getElementById('screen-contents'),
  memories: document.getElementById('screen-memories'),
  sounds: document.getElementById('screen-sounds')
};

/* Screens are built on first visit and kept. The overview is invalidated when
   late-arriving data would change it — the shelves and the release history both
   land after first paint. */
const built = { home: false, contents: false };

let token = 0;
let selAnchor = -1;
let pendingOpenScroll = false;

/* --- query ------------------------------------------------------------------ */

function runQuery() {
  if (!data.ready) return;
  list.setQueryTerms(state.q);
  worker.postMessage({
    type: 'query',
    token: ++token,
    q: state.q,
    cats: [...state.cats],
    exclude: state.cats.has(EXCLUDED_BY_DEFAULT) ? [] : [EXCLUDED_BY_DEFAULT],
    status: state.status,
    from: state.from,
    to: state.to,
    sort: state.sort,
    dir: state.dir,
    diff: state.diffMode && data.detailReady ? { a: state.from, b: state.to } : null
  });
}

/* Called by every control that changes state. `push` adds a history entry;
   typing does not, so the back button leaves the page rather than replaying
   every keystroke. */
function changed(push) {
  writeURL(push);
  runQuery();
}

/* --- screens ----------------------------------------------------------------- */

function showView() {
  for (const [name, el] of Object.entries(screenEls)) el.hidden = name !== state.view;
  ui.syncNav();
  if (!data.ready) return;

  if (state.view === 'home' && !built.home) {
    screens.renderHome(screenEls.home);
    built.home = true;
  }
  if (state.view === 'contents' && !built.contents) {
    screens.renderContents(screenEls.contents);
    built.contents = true;
  }
  if (state.view === 'memories') screens.renderMemories(screenEls.memories);
  if (state.view === 'sounds') { syncZeroState(); list.render(); }

  list.refreshShelfRows();
}

function goTo(view, push = true) {
  if (!VIEWS.includes(view) || view === state.view) return;
  state.view = view;
  writeURL(push);
  showView();
  window.scrollTo(0, 0);
}

/* --- zero state -------------------------------------------------------------- */

function syncZeroState() {
  const showShelves = data.ready && !filtersActive() && !state.browse;

  // Dropping back to the shelves hides the grid, so an expanded row would
  // linger in the URL pointing at something nobody can see.
  if (showShelves && state.open != null) {
    state.open = null;
    list.syncDetail();
    writeURL(false);
  }

  shelvesEl.hidden = !showShelves || !shelves.list;
  gridEl.hidden = showShelves;
  toolbarEl.hidden = showShelves;
  document.getElementById('empty').hidden = showShelves || result.ids.length > 0;

  if (showShelves && shelves.list) {
    list.renderShelves(shelves.list);
    addBrowseAll();
  }
}

function addBrowseAll() {
  if (document.getElementById('browse-all')) return;
  const p = document.createElement('p');
  p.className = 'shelf';
  p.innerHTML = `<button type="button" class="btn" id="browse-all">Browse all ${fmtInt(data.counts.total)} sounds</button>`;
  shelvesEl.appendChild(p);
  document.getElementById('browse-all').addEventListener('click', () => {
    state.browse = true;
    state.sort = state.sort || 'title';
    ui.syncSorts();
    changed(true);
    syncZeroState();
    list.render();
  });
}

/* --- worker messages --------------------------------------------------------- */

worker.onmessage = (e) => {
  const m = e.data;

  if (m.type === 'core') {
    Object.assign(data, {
      versions: m.versions, categories: m.categories, counts: m.counts,
      formats: m.formats, buckets: m.buckets, ids: m.ids,
      titles: m.titles, originals: m.originals, cats: m.cats,
      status: m.status, catId: m.catId, fmtId: m.fmtId,
      duration: m.duration, first: m.first, last: m.last, peaks: m.peaks,
      ready: true
    });
    readURL();
    emit('core');
    showView();
    runQuery();
    return;
  }

  if (m.type === 'detail') {
    Object.assign(data, {
      files: m.files, previews: m.previews, dirs: m.dirs, bytes: m.bytes,
      inOff: m.inOff, inVals: m.inVals, aliveCounts: m.aliveCounts,
      detailReady: true
    });
    emit('detail');
    list.render();
    list.refreshShelfRows();
    list.syncDetail();
    // The overview's release-change table is computed from in[], which has only
    // just arrived, so rebuild it.
    built.home = false;
    if (state.view === 'home') showView();
    // Re-run: comparison, size sorting and searching the IPSW path all need the
    // detail index, and the first query ran before it had arrived.
    runQuery();
    return;
  }

  if (m.type === 'shelves') {
    shelves.list = m.shelves;
    built.home = false;                       // the overview leads with a shelf
    if (state.view === 'home') showView();
    if (state.view === 'sounds') syncZeroState();
    return;
  }

  if (m.type === 'result') {
    if (m.token !== token) return;              // a newer keystroke already won
    result.ids = m.ids;
    result.fields = m.fields;
    result.marks = m.marks || null;
    result.summary = m.summary || null;
    emit('result');
    if (state.view === 'sounds') {
      syncZeroState();
      list.syncDetail();
      list.render();
    }
    if (pendingOpenScroll) { pendingOpenScroll = false; scrollOpenIntoView(); }
    announce(`${fmtInt(result.ids.length)} of ${fmtInt(data.counts.total)} sounds`);
    return;
  }

  if (m.type === 'error') {
    console.warn('data worker:', m.where, m.message);
  }
};

worker.postMessage({ type: 'init', base: CFG.dataBase });

/* --- row actions -------------------------------------------------------------- */

list.wire((action, i, ev) => {
  if (action === 'play') { player.toggle(i); return; }

  if (action === 'download') return;             // a plain anchor; let it be

  if (action === 'pick') {
    if (ev) ev.stopPropagation();
    tray.togglePick(i);
    list.render();
    list.refreshShelfRows();
    return;
  }

  if (action === 'open') {
    // Opening a sound from a shelf steps out of the curated zero state, so the
    // detail expands inside the real list rather than under a hidden grid.
    if (!shelvesEl.hidden) {
      state.browse = true;
      state.open = i;
      syncZeroState();
    } else {
      state.open = state.open === i ? null : i;
    }
    writeURL(true);
    list.syncDetail();
    list.render();
    if (state.open != null) scrollOpenIntoView();
  }
});

function scrollOpenIntoView() {
  const pos = [...result.ids].indexOf(state.open);
  if (pos >= 0) list.setFocus(pos, { focus: false });
}

on('opensibling', (k) => {
  if (state.open == null) return;
  tray.compareWith(state.open, k);
  list.render();
});

on('play', () => { list.render(); list.refreshShelfRows(); });

on('playerror', (i) => {
  if (i >= 0 && data.titles[i]) announce(`No preview available for ${data.titles[i]}`);
});

/* --- keyboard ----------------------------------------------------------------- */

const TYPING = (el) => el && /^(INPUT|TEXTAREA|SELECT)$/.test(el.tagName);

document.addEventListener('keydown', (ev) => {
  const t = ev.target;

  if (ev.key === '/' && !TYPING(t)) {
    ev.preventDefault();
    document.getElementById('q').focus();
    return;
  }

  if (ev.key === 'Escape') {
    if (state.open != null) {
      state.open = null;
      writeURL(true);
      list.syncDetail();
      list.render();
      ev.preventDefault();
    }
    return;
  }

  if (TYPING(t) || t.classList?.contains('ruler-handle')) return;

  const pos = list.getFocus();
  const n = result.ids.length;
  if (!n) return;

  switch (ev.key) {
    case 'ArrowDown':
      ev.preventDefault();
      moveFocus(pos < 0 ? 0 : pos + 1, ev.shiftKey);
      break;
    case 'ArrowUp':
      ev.preventDefault();
      moveFocus(pos < 0 ? 0 : pos - 1, ev.shiftKey);
      break;
    case 'Home':
      ev.preventDefault(); moveFocus(0, ev.shiftKey); break;
    case 'End':
      ev.preventDefault(); moveFocus(n - 1, ev.shiftKey); break;
    case 'PageDown':
      ev.preventDefault(); moveFocus(Math.min(n - 1, (pos < 0 ? 0 : pos) + 12), ev.shiftKey); break;
    case 'PageUp':
      ev.preventDefault(); moveFocus(Math.max(0, (pos < 0 ? 0 : pos) - 12), ev.shiftKey); break;

    case 'ArrowRight': case 'ArrowLeft': {
      if (pos < 0) return;
      const row = list.rowAt(pos);
      if (!row) return;
      const controls = [row._play, row._dl, row._pick].filter(Boolean);
      const at = controls.indexOf(document.activeElement);
      const next = ev.key === 'ArrowRight'
        ? Math.min(controls.length - 1, at + 1)
        : at <= 0 ? -1 : at - 1;
      ev.preventDefault();
      if (next < 0) row.focus({ preventScroll: true });
      else controls[next].focus({ preventScroll: true });
      break;
    }

    case 'Enter':
      if (pos < 0) return;
      ev.preventDefault();
      {
        const i = result.ids[pos];
        state.open = state.open === i ? null : i;
        writeURL(true);
        list.syncDetail();
        list.render();
      }
      break;

    case ' ':
      if (pos < 0) return;
      ev.preventDefault();
      player.toggle(result.ids[pos]);
      break;

    case 'x': case 'X':
      if (pos < 0) return;
      ev.preventDefault();
      tray.togglePick(result.ids[pos]);
      list.render();
      break;

    case 'd': case 'D': {
      if (pos < 0) return;
      ev.preventDefault();
      const row = list.rowAt(pos);
      if (row && row._dl.href) row._dl.click();
      break;
    }
  }
});

function moveFocus(to, extend) {
  const n = result.ids.length;
  const target = Math.max(0, Math.min(n - 1, to));
  if (extend) {
    if (selAnchor < 0) selAnchor = list.getFocus() < 0 ? target : list.getFocus();
    const lo = Math.min(selAnchor, target), hi = Math.max(selAnchor, target);
    for (let p = lo; p <= hi; p++) state.picked.add(result.ids[p]);
    tray.syncTray();
  } else {
    selAnchor = target;
  }
  list.setFocus(target);
}

/* --- scroll, resize, history --------------------------------------------------- */

window.addEventListener('scroll', () => list.renderOnScroll(), { passive: true });
window.addEventListener('resize', () => { list.syncDetail(); list.render(); });

window.addEventListener('popstate', () => {
  readURL();
  document.getElementById('q').value = state.q;
  ui.renderChips();
  ui.syncRuler();
  ui.syncSorts();
  ui.syncDiffBar();
  document.body.classList.toggle('dense', state.dense);
  showView();
  runQuery();
});

/* --- cross-screen jumps --------------------------------------------------------- */

screens.wireScreens(
  (view) => goTo(view),

  // A category in the contents table opens the tool filtered to it.
  (name) => {
    state.cats = new Set([name]);
    state.q = '';
    state.browse = true;
    document.getElementById('q').value = '';
    ui.renderChips();
    goTo('sounds');
    changed(false);
    announce(`Showing ${name}`);
  },

  // A release in the overview's change table opens it against the one before.
  (v) => {
    state.from = Math.max(0, v - 1);
    state.to = v;
    state.diffMode = true;
    state.browse = true;
    ui.syncRuler();
    ui.syncDiffBar();
    goTo('sounds');
    changed(false);
  }
);

on('memset', () => { writeURL(false); showView(); });
on('memslots', () => screens.refreshSequencer());

/* Canvas colours are baked in at draw time, so a theme flip has to repaint. */
on('theme', () => {
  list.render();
  list.refreshShelfRows();
  ui.syncRuler();
});

/* --- go ------------------------------------------------------------------------ */

initTheme();
initTransport();
ui.initUI(changed);
tray.initTray();
