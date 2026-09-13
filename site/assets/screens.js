/* ===========================================================================
   The three screens that are not the tool.

     home      an overview, with the tool one click away
     contents  what is actually in the collection, and how to take it
     memories  the Photos Memories stems, and a sequencer to hear a soundtrack
               assembled from them

   Each is rendered once, on first visit, and cached. They read the same
   columns the list does; nothing here fetches anything.
   =========================================================================== */

import {
  CFG, data, state, shelves, emit,
  fmtInt, fmtDuration, versionName, topLevel, announce
} from './store.js';
import { buildRowList } from './list.js';
import { slugFor } from './ui.js';
import * as player from './player.js';

const ROLES = ['Intro', 'Body', 'Transition', 'Crossfade', 'Outro'];
const MEMORIES = 'Photos Memories';

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* --- release change table ---------------------------------------------------- */

/* Added and dropped per build, walked straight off the packed in[] runs: a
   sound is added at the start of every run it has, and dropped at the build
   after each run ends. One pass over ~160k entries.

   Spoken Content is left out, for the same reason it is excluded everywhere
   else by default. Counted raw, this table is 1,939 Nike+ workout clips
   arriving in iOS 3 and leaving in iOS 8, and every actual change to the
   system sounds disappears underneath them. */
let changeCache = null;
export function releaseChanges() {
  if (changeCache || !data.detailReady) return changeCache;
  const V = data.versions.length;
  const added = new Int32Array(V);
  const dropped = new Int32Array(V);

  for (let i = 0; i < data.titles.length; i++) {
    if (topLevel(data.cats[i]) === 'Spoken Content') continue;
    const from = data.inOff[i], to = data.inOff[i + 1];
    if (from === to) continue;
    for (let k = from; k < to; k++) {
      const v = data.inVals[k];
      if (k === from || data.inVals[k - 1] !== v - 1) added[v]++;
      const isRunEnd = k === to - 1 || data.inVals[k + 1] !== v + 1;
      if (isRunEnd && v + 1 < V) dropped[v + 1]++;
    }
  }
  changeCache = { added, dropped };
  return changeCache;
}

/* --- home -------------------------------------------------------------------- */

export function renderHome(host) {
  const c = data.counts;
  const span = `${versionName(0)} to ${versionName(data.versions.length - 1)}`;

  host.innerHTML = `
    <section class="lede">
      <!-- Kicker and tally labels are uppercased by the design system, so they
           avoid "iOS" — it would come out as "IOS". -->
      <p class="kicker">Extracted from Apple IPSW filesystems</p>
      <h2>Every sound file that ships inside iOS, and every one that used to.</h2>
      <p>Each release carries a few hundred audio files: the alert you
        half-remember, the lock click that changed in 2013, a thousand stems for
        Memories soundtracks nobody hears separately. This is all of them,
        ${esc(span)}, pulled from the root filesystem of ${data.versions.length}
        builds and de-duplicated by audio identity, so every entry knows exactly
        which releases it shipped in.</p>
      <dl class="tally">
        <div><dt>Distinct sounds</dt><dd>${fmtInt(c.total)}</dd></div>
        <div><dt>Still shipping</dt><dd>${fmtInt(c.present)}</dd></div>
        <div><dt>Gone</dt><dd>${fmtInt(c.removed)}</dd></div>
        <div><dt>Builds examined</dt><dd>${data.versions.length}</dd></div>
      </dl>
      <p class="cta-row">
        <button type="button" class="btn primary" data-goto="sounds">Search every sound</button>
        <button type="button" class="btn" data-goto="memories">Memories stems</button>
        <button type="button" class="btn" data-goto="contents">What is in the collection</button>
      </p>
    </section>

    <hr class="hr-fade">

    <section class="home-shelves" id="home-shelves">
      <p class="kicker">Tap to play</p>
      <h2>Start with the ones you know</h2>
      <p class="section-note">Nothing here plays on its own.</p>
    </section>

    <hr class="hr-fade">

    <section class="changes">
      <p class="kicker">Release history</p>
      <h2>What changed, and when</h2>
      <p class="section-note" id="changes-note">Reading the release history…</p>
      <div id="changes-table"></div>
    </section>

    <hr class="hr-fade">

    <section class="built">
      <p class="kicker">The pipeline</p>
      <h2>How the archive was built</h2>
      <ol class="steps">
        <li><b>Fetch</b> one IPSW per iOS release line, plus every iPhone launch build.</li>
        <li><b>Mount</b> the root filesystem and walk it for audio, wherever it hides —
          <code>UISounds</code>, framework bundles, accessibility bundles, ringtones.</li>
        <li><b>De-duplicate</b> across all builds by four escalating identity tests, so a
          file that never changed is one entry that knows its whole run.</li>
        <li><b>Split</b> into <code>Current/</code> for what still ships and
          <code>Removed/</code> for what does not, with the bulk spoken-word assets
          kept aside so they do not swamp the system sounds.</li>
      </ol>
      <p>The pipeline is four Python scripts in <code>tools/</code>. Everything the
        site reads is generated by them; nothing is fetched at runtime but static files.</p>
    </section>

    <hr class="hr-fade">

    <section class="download-shape">
      <p class="kicker">What you get</p>
      <h2>What a download contains</h2>
      <p>Apple's original file, byte for byte, in the format Apple shipped it in —
        <code>.caf</code>, <code>.aiff</code>, <code>.wav</code>, <code>.m4a</code>.
        Never a re-encode. The AAC previews exist only so the browser has something
        it can play, because <code>.caf</code> and <code>.aiff</code> do not decode
        outside Safari.</p>
      <p>Every archive carries a <code>manifest.json</code> naming each sound, its
        category, its release range and its path inside the IPSW, and a
        <code>NOTICE.txt</code> with the line below.</p>
      <p class="notice">${esc(CFG.notice)}</p>
    </section>`;

  if (shelves.list && shelves.list.length) {
    const sec = host.querySelector('#home-shelves');
    const first = shelves.list[0];
    sec.appendChild(buildRowList(first.ids, first.title));
  }

  fillChanges(host);
}

/* The eight builds that moved the most, which is a fair summary of 20 years:
   the iOS 7 redesign dwarfs everything else. */
function fillChanges(host) {
  const ch = releaseChanges();
  const note = host.querySelector('#changes-note');
  const box = host.querySelector('#changes-table');
  if (!ch || !box) return;

  const rows = [];
  for (let v = 0; v < data.versions.length; v++) {
    rows.push({ v, a: ch.added[v], d: ch.dropped[v] });
  }
  rows.sort((x, y) => (y.a + y.d) - (x.a + x.d));
  const top = rows.slice(0, 8).sort((x, y) => x.v - y.v);

  note.textContent = 'The eight releases that changed the most, in order. '
    + 'Spoken Content is left out: counted raw it is the only thing this table shows.';
  box.innerHTML = `
    <table class="data-table">
      <thead><tr><th scope="col">Release</th><th scope="col">Build</th>
        <th scope="col" class="num">Added</th><th scope="col" class="num">Dropped</th></tr></thead>
      <tbody>
        ${top.map(r => `
          <tr>
            <td><button type="button" class="linkish" data-diff="${r.v}">${esc(versionName(r.v))}</button></td>
            <td class="mono">${esc(data.versions[r.v].build)}</td>
            <td class="num mono mark-add">${r.a ? '+' + fmtInt(r.a) : '—'}</td>
            <td class="num mono mark-del">${r.d ? '−' + fmtInt(r.d) : '—'}</td>
          </tr>`).join('')}
      </tbody>
    </table>
    <p class="section-note">Pick a release to open it against the one before it.</p>`;
}

/* --- contents ---------------------------------------------------------------- */

export function renderContents(host) {
  const c = data.counts;

  // Per top-level category, split by whether it still ships.
  const tally = new Map();
  for (let i = 0; i < data.titles.length; i++) {
    const t = topLevel(data.cats[i]);
    if (!tally.has(t)) tally.set(t, { present: 0, removed: 0 });
    tally.get(t)[data.status[i] === 1 ? 'present' : 'removed']++;
  }
  const rows = data.tops.map(t => ({ name: t.name, ...(tally.get(t.name) || { present: 0, removed: 0 }) }));

  host.innerHTML = `
    <section class="lede">
      <p class="kicker">The archive</p>
      <h2>What is in the collection</h2>
      <p>${fmtInt(c.total)} distinct sounds across ${data.versions.length} builds,
        ${fmtInt(c.present)} of which are still in the newest iOS.
        The category tree is Apple's own folder structure — nothing here is invented,
        merged or renamed to make the list tidier.</p>
    </section>

    <section>
      <h3>Categories</h3>
      <table class="data-table">
        <thead><tr><th scope="col">Category</th><th scope="col" class="num">Still shipping</th>
          <th scope="col" class="num">Removed</th><th scope="col" class="num">Total</th>
          <th scope="col">Archive</th></tr></thead>
        <tbody>
          ${rows.map(r => `
            <tr>
              <td><button type="button" class="linkish" data-cat="${esc(r.name)}">${esc(r.name)}</button></td>
              <td class="num mono">${fmtInt(r.present)}</td>
              <td class="num mono">${fmtInt(r.removed)}</td>
              <td class="num mono">${fmtInt(r.present + r.removed)}</td>
              <td><a class="mono" href="${CFG.releaseBase}${slugFor(r.name)}.zip">${slugFor(r.name)}.zip</a></td>
            </tr>`).join('')}
        </tbody>
      </table>
    </section>

    <section>
      <h3>Repository layout</h3>
      <dl class="facts wide">
        <div><dt>Current/</dt><dd>sounds that still ship in the newest build</dd></div>
        <div><dt>Removed/</dt><dd>sounds that shipped once and no longer do</dd></div>
        <div><dt>Spoken Content/</dt><dd>bulk spoken-word assets, kept apart so they do not swamp the system sounds</dd></div>
        <div><dt>tools/</dt><dd>the ingest, de-duplication and build pipeline</dd></div>
        <div><dt>sounds.json</dt><dd>the full public index, one record per distinct sound</dd></div>
        <div><dt>web/</dt><dd>generated: AAC previews, the split index, waveform peaks, per-category archives</dd></div>
      </dl>
    </section>

    <section>
      <h3>The index format</h3>
      <p>This page reads three static files and calls nothing at runtime.
        <code>index.core.json</code> carries what search and the list need,
        <code>index.detail.json</code> carries paths, sizes and the full release
        history, and <code>peaks.bin</code> is ${data.buckets} bytes of amplitude
        peaks per sound in index order. All three come from
        <code>tools/make-web.py</code>.</p>
      <table class="data-table">
        <thead><tr><th scope="col">Field</th><th scope="col">Means</th></tr></thead>
        <tbody>
          ${[['id', 'first 12 hex of the representative file MD5; the permalink key'],
             ['title', 'human-readable name'],
             ['category', 'slash path, Apple’s own folder structure'],
             ['status', 'present or removed'],
             ['format', 'the original’s format, not the preview’s'],
             ['duration', 'seconds, or null where the pipeline has not filled it'],
             ['first / last', 'index into versions[] of the earliest and latest build'],
             ['in[]', 'every build index it shipped in; gaps are real'],
             ['file', 'repo-relative path to the original'],
             ['preview', 'path to the AAC preview'],
             ['dir', 'the directory inside the IPSW it came from']]
            .map(([k, v]) => `<tr><td class="mono">${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}
        </tbody>
      </table>
    </section>

    <section>
      <h3>Taking all of it</h3>
      <p><a class="btn" href="${CFG.releaseBase}all-sounds.zip">The whole collection (355 MB)</a>
         <a class="btn" href="${esc(CFG.repoUrl)}">The repository</a></p>
      <p class="section-note">Per-category archives are in the table above. The AAC
        preview mirror ships as <code>iOS-System-Sounds-web-bundle.zip</code> on the
        same release, so the site can be built without ffmpeg.</p>
    </section>

    <section>
      <h3>Copyright</h3>
      <p class="notice">${esc(CFG.notice)}</p>
      <p class="section-note">The tooling and this site are MIT licensed. The audio is not.</p>
    </section>`;
}

/* --- memories ---------------------------------------------------------------- */

/* "Photos Memories/Sentimental/Outro" -> set "Sentimental", role "Outro". */
function memParts(i) {
  const rest = data.cats[i].slice(MEMORIES.length + 1);
  const cut = rest.indexOf('/');
  return cut === -1 ? { set: rest, role: '' } : { set: rest.slice(0, cut), role: rest.slice(cut + 1) };
}

let memIndex = null;
function memoriesIndex() {
  if (memIndex) return memIndex;
  const sets = new Map();
  for (let i = 0; i < data.titles.length; i++) {
    if (!data.cats[i].startsWith(MEMORIES + '/')) continue;
    const { set, role } = memParts(i);
    if (!set) continue;
    if (!sets.has(set)) sets.set(set, new Map());
    const byRole = sets.get(set);
    const key = role || 'Stems';
    if (!byRole.has(key)) byRole.set(key, []);
    byRole.get(key).push(i);
  }
  memIndex = sets;
  return sets;
}

export function renderMemories(host) {
  const sets = memoriesIndex();
  const names = [...sets.keys()].sort((a, b) => a.localeCompare(b));
  if (!state.memSet || !sets.has(state.memSet)) state.memSet = names[0] || '';

  const total = [...sets.values()].reduce((n, m) => n + [...m.values()].reduce((k, a) => k + a.length, 0), 0);

  host.innerHTML = `
    <section class="lede">
      <p class="kicker">Photos Memories</p>
      <h2>Memories stems</h2>
      <p>The soundtracks behind Photos Memories do not ship as finished tracks. They
        ship as stems: an intro, a run of interchangeable body sections, transitions
        and crossfades to stitch them, and an outro. iOS assembles one on the fly to
        fit however long your memory happens to be.</p>
      <p>${fmtInt(total)} stems across ${names.length} soundtracks — more than a third
        of this whole collection, and the part of it nobody ever hears named. Pick a
        soundtrack, choose one stem per role, and play the sequence back.</p>
    </section>

    <section>
      <h3>Soundtracks</h3>
      <div class="set-picker" id="set-picker" role="group" aria-label="Soundtracks">
        ${names.map(n => {
          const count = [...sets.get(n).values()].reduce((k, a) => k + a.length, 0);
          return `<button type="button" class="chip" data-set="${esc(n)}"
                    aria-pressed="${n === state.memSet}">${esc(n)}<span class="n">${count}</span></button>`;
        }).join('')}
      </div>
    </section>

    <section id="seq-section"></section>`;

  renderSequencer(host);
}

function renderSequencer(host) {
  const sets = memoriesIndex();
  const byRole = sets.get(state.memSet);
  const sec = host.querySelector('#seq-section');
  if (!byRole || !sec) return;

  const roleKeys = ROLES.filter(r => byRole.has(r));
  const keys = roleKeys.length ? roleKeys : [...byRole.keys()];

  sec.innerHTML = `
    <h3>${esc(state.memSet)}</h3>
    <p class="section-note">One stem per role. Roles this soundtrack does not ship are not shown.</p>
    <div class="seq-bar" id="seq-bar"></div>
    <p class="cta-row">
      <button type="button" class="btn primary" id="seq-play">Play sequence</button>
      <button type="button" class="btn" id="seq-clear">Clear</button>
    </p>
    <div class="role-cols">
      ${keys.map(role => `
        <div class="role-col">
          <h4>${esc(role)} <span class="n mono">${byRole.get(role).length}</span></h4>
          <div class="role-list" data-role="${esc(role)}"></div>
        </div>`).join('')}
    </div>`;

  for (const role of keys) {
    const list = sec.querySelector(`.role-list[data-role="${CSS.escape(role)}"]`);
    const ids = byRole.get(role).slice().sort((a, b) => (data.duration[a] || 0) - (data.duration[b] || 0));
    for (const i of ids) {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'stem';
      b.dataset.stem = String(i);
      b.dataset.role = role;
      b.setAttribute('aria-pressed', String(state.slots[role] === i));
      const label = data.titles[i].replace(state.memSet + ' ', '');
      b.innerHTML = `<span class="stem-t">${esc(label)}</span>` +
        `<span class="stem-d mono">${esc(fmtDuration(data.duration[i]))}</span>`;
      list.appendChild(b);
    }
  }

  drawSeqBar(sec);
}

function drawSeqBar(sec) {
  const bar = sec.querySelector('#seq-bar');
  if (!bar) return;
  const chosen = sequence();
  if (!chosen.length) {
    bar.innerHTML = '<p class="seq-empty">Nothing chosen yet. Pick a stem from any role below.</p>';
    return;
  }
  const totalDur = chosen.reduce((n, i) => n + (data.duration[i] || 1), 0);
  bar.innerHTML = chosen.map(i => {
    const share = ((data.duration[i] || 1) / totalDur) * 100;
    const role = memParts(i).role || 'Stem';
    return `<span class="seq-block" style="width:${share.toFixed(2)}%" title="${esc(data.titles[i])}">
      <b>${esc(role)}</b><span class="mono">${esc(fmtDuration(data.duration[i]))}</span></span>`;
  }).join('') + `<p class="seq-total mono">${chosen.length} stems · ${fmtDuration(totalDur)}</p>`;
}

/* The chosen stems in role order — that is the order iOS would play them. */
function sequence() {
  const sets = memoriesIndex();
  const byRole = sets.get(state.memSet);
  if (!byRole) return [];
  const keys = ROLES.filter(r => byRole.has(r));
  const order = keys.length ? keys : [...byRole.keys()];
  return order.map(r => state.slots[r]).filter(i => i != null);
}

/* --- wiring ------------------------------------------------------------------ */

export function wireScreens(onGoto, onCategory, onDiff) {
  const main = document.querySelector('main');

  // Section links live in the header nav, the footer and inside the screens
  // themselves, so this one is delegated from the document rather than <main>.
  document.addEventListener('click', (ev) => {
    const goto = ev.target.closest('[data-goto]');
    if (goto) onGoto(goto.dataset.goto);
  });

  main.addEventListener('click', (ev) => {
    const cat = ev.target.closest('[data-cat]');
    if (cat) { onCategory(cat.dataset.cat); return; }

    const diff = ev.target.closest('[data-diff]');
    if (diff) { onDiff(parseInt(diff.dataset.diff, 10)); return; }

    const set = ev.target.closest('[data-set]');
    if (set) {
      state.memSet = set.dataset.set;
      state.slots = {};
      player.stopSequence();
      emit('memset');
      return;
    }

    const stem = ev.target.closest('[data-stem]');
    if (stem) {
      const i = parseInt(stem.dataset.stem, 10);
      const role = stem.dataset.role;
      // A second press on the chosen stem clears the slot rather than replaying.
      if (state.slots[role] === i) delete state.slots[role];
      else state.slots[role] = i;
      emit('memslots');
      player.toggle(i);
      return;
    }

    if (ev.target.closest('#seq-play')) { playSequence(); return; }
    if (ev.target.closest('#seq-clear')) {
      state.slots = {};
      player.stopSequence();
      emit('memslots');
    }
  });
}

function playSequence() {
  const chosen = sequence();
  if (!chosen.length) { announce('Choose at least one stem first'); return; }
  player.playSequence(chosen);
  announce(`Playing ${chosen.length} stems from ${state.memSet}`);
}

/** Re-render just the stem buttons and the bar after a slot changes. */
export function refreshSequencer() {
  const host = document.getElementById('screen-memories');
  if (!host) return;
  const sec = host.querySelector('#seq-section');
  if (!sec) return;
  sec.querySelectorAll('[data-stem]').forEach(b => {
    b.setAttribute('aria-pressed', String(state.slots[b.dataset.role] === parseInt(b.dataset.stem, 10)));
  });
  drawSeqBar(sec);
}
