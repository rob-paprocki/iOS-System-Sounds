/* ===========================================================================
   The selection tray: what you have picked, how big it is, and the two things
   you can do with it — compare exactly two, or download the lot as a zip.

   The zip is assembled in the browser from the original files, never from the
   previews, and carries the same manifest and copyright notice the prebuilt
   release archives do. Over MAX_CLIENT_ZIP files it stops and points at the
   prebuilt category archive instead, which is the honest answer.
   =========================================================================== */

import {
  CFG, data, state, emit, on,
  fmtInt, fmtBytes, fmtDuration, versionName, originalURL,
  announce, topLevel, MAX_CLIENT_ZIP
} from './store.js';
import { makeZip } from './zip.js';
import { drawWave } from './glyph.js';
import { syncBottomInset } from './transport.js';
import * as player from './player.js';

const tray = document.getElementById('tray');
const trayCount = document.getElementById('tray-count');
const btnCompare = document.getElementById('tray-compare');
const btnDownload = document.getElementById('tray-download');
const btnClear = document.getElementById('tray-clear');

let abPanel = null;
let abObserver = null;
let busy = false;

export function syncTray() {
  const n = state.picked.size;
  tray.hidden = n === 0;
  syncBottomInset();                       // the transport docks above this
  if (!n) { closeAB(); return; }

  let total = 0;
  if (data.detailReady) for (const i of state.picked) total += data.bytes[i];

  trayCount.textContent = busy
    ? trayCount.textContent
    : `${fmtInt(n)} selected${total ? ' · ' + fmtBytes(total) : ''}`;

  btnCompare.disabled = n !== 2;
  btnDownload.disabled = busy || !data.detailReady;

  if (n > MAX_CLIENT_ZIP) {
    btnDownload.disabled = true;
    const cats = new Set([...state.picked].map(i => topLevel(data.cats[i])));
    const hint = cats.size === 1
      ? ` Download the prebuilt ${[...cats][0]} archive instead.`
      : ' Narrow the selection, or take the prebuilt category archives from Contents.';
    trayCount.textContent = `${fmtInt(n)} selected. That is too many to zip here; the limit is ${MAX_CLIENT_ZIP}.${hint}`;
  }
}

export function togglePick(i) {
  if (state.picked.has(i)) state.picked.delete(i); else state.picked.add(i);
  syncTray();
}

export function clearPicks() {
  state.picked.clear();
  closeAB();
  syncTray();
}

/* --- zip -------------------------------------------------------------------- */

function manifestFor(list) {
  return list.map(i => ({
    title: data.titles[i],
    category: data.cats[i],
    status: data.status[i] === 1 ? 'present' : 'removed',
    first_seen: versionName(data.first[i]),
    last_seen: versionName(data.last[i]),
    releases: data.detailReady ? Array.from(data.inVals.subarray(data.inOff[i], data.inOff[i + 1])).map(versionName) : [],
    format: data.formats[data.fmtId[i]],
    bytes: data.bytes ? data.bytes[i] : null,
    duration_sec: Number.isNaN(data.duration[i]) ? null : data.duration[i],
    original_filename: data.originals[i],
    ipsw_dir: data.dirs[i] || '',
    path: data.files[i]
  }));
}

/* Six at a time: enough to saturate a connection, few enough not to trip a
   browser's per-origin request cap on a 200 file selection. */
async function fetchAll(list, onProgress) {
  const out = new Array(list.length);
  let next = 0, done = 0;

  async function worker() {
    for (;;) {
      const k = next++;
      if (k >= list.length) return;
      const i = list[k];
      const res = await fetch(originalURL(i));
      if (!res.ok) throw new Error(`${res.status} on ${data.files[i]}`);
      out[k] = new Uint8Array(await res.arrayBuffer());
      onProgress(++done);
    }
  }

  await Promise.all(Array.from({ length: Math.min(6, list.length) }, worker));
  return out;
}

async function downloadSelection() {
  if (busy) return;
  const list = [...state.picked];
  if (!list.length || list.length > MAX_CLIENT_ZIP) return;

  busy = true;
  btnDownload.disabled = true;
  const enc = new TextEncoder();

  try {
    const bodies = await fetchAll(list, (done) => {
      trayCount.textContent = `Fetching ${done} of ${list.length}…`;
    });
    trayCount.textContent = 'Building the zip…';

    const entries = list.map((i, k) => ({ name: data.files[i], data: bodies[k] }));
    entries.push({ name: 'manifest.json', data: enc.encode(JSON.stringify(manifestFor(list), null, 2)) });
    entries.push({ name: 'NOTICE.txt', data: enc.encode(CFG.notice + '\n') });

    const blob = makeZip(entries);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `ios-system-sounds-${list.length}-files.zip`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    setTimeout(() => URL.revokeObjectURL(url), 30000);
    announce(`Downloaded ${list.length} sounds`);
  } catch (err) {
    trayCount.textContent = `Could not build the zip: ${err.message}`;
    announce('The zip could not be built');
    busy = false;
    btnDownload.disabled = false;
    return;
  }

  busy = false;
  syncTray();
}

/* --- A/B compare ------------------------------------------------------------ */

function closeAB() {
  if (abObserver) { abObserver.disconnect(); abObserver = null; }
  if (abPanel) { abPanel.remove(); abPanel = null; }
  state.ab = null;
}

function openAB() {
  const list = [...state.picked];
  if (list.length !== 2) return;
  closeAB();
  state.ab = list;

  const [i, j] = list;
  abPanel = document.createElement('section');
  abPanel.className = 'ab';
  abPanel.setAttribute('aria-label', 'Compare two sounds');
  abPanel.innerHTML = `
    <h3>Comparing two sounds</h3>
    <div class="ab-pair">
      ${[i, j].map((k, n) => `
        <div>
          <p class="ab-meta"><b>${n === 0 ? 'A' : 'B'}</b> · ${esc(data.titles[k])} ·
             ${esc(data.cats[k])} · ${esc(versionName(data.first[k]))} to ${esc(versionName(data.last[k]))} ·
             ${esc(fmtDuration(data.duration[k]) || 'length unknown')}</p>
          <div class="ab-one">
            <canvas data-ab="${k}" height="48" role="img" aria-label="Waveform of ${esc(data.titles[k])}"></canvas>
            <button type="button" class="btn" data-play="${k}">Play ${n === 0 ? 'A' : 'B'}</button>
          </div>
        </div>`).join('')}
    </div>
    <div class="ab-actions">
      <button type="button" class="btn primary" id="ab-both">Play A then B</button>
      <button type="button" class="btn" id="ab-close">Close</button>
    </div>`;

  const listBlock = document.querySelector('.list-block');
  listBlock.parentNode.insertBefore(abPanel, listBlock);

  abPanel.querySelectorAll('[data-play]').forEach(b =>
    b.addEventListener('click', () => player.toggle(parseInt(b.dataset.play, 10))));
  abPanel.querySelector('#ab-both').addEventListener('click', () => player.playPair(i, j));
  abPanel.querySelector('#ab-close').addEventListener('click', closeAB);

  // Redraw whenever the panel actually has its width. A single frame callback
  // is not enough: the canvases can still be at their intrinsic 300px when it
  // runs, which then gets stretched to the column width and looks soft.
  abObserver = new ResizeObserver(drawAB);
  abObserver.observe(abPanel);
  drawAB();
  announce(`Comparing ${data.titles[i]} with ${data.titles[j]}`);
}

function drawAB() {
  if (!abPanel) return;
  abPanel.querySelectorAll('[data-ab]').forEach(c => {
    const k = parseInt(c.dataset.ab, 10);
    drawWave(c, k, player.progressFor(k), c.getBoundingClientRect().width, 48);
  });
}

function esc(s) {
  return String(s).replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
}

/* --- init ------------------------------------------------------------------- */

export function initTray() {
  btnClear.addEventListener('click', clearPicks);
  btnCompare.addEventListener('click', openAB);
  btnDownload.addEventListener('click', downloadSelection);
  on('progress', drawAB);
  on('detail', syncTray);
  window.addEventListener('resize', drawAB);
  syncTray();
}

/* Open the A/B view directly, used when a row detail links to a re-recording. */
export function compareWith(a, b) {
  state.picked.clear();
  state.picked.add(a);
  state.picked.add(b);
  syncTray();
  openAB();
  emit('picked');
}
