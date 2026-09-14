/* ===========================================================================
   The transport.

   A docked bar that says what is playing, how far through it is, and offers
   the one control that always applies: stop. It is the design's centrepiece
   and it earns its place — until now the only sign that something was playing
   was a row scrolled somewhere off screen.

   It shares the bottom edge with the selection tray, so whichever are open,
   both stay reachable and neither covers the list's last row.
   =========================================================================== */

import { data, on, topLevel } from './store.js';
import * as player from './player.js';

/* Compact enough to sit in a bar: tenths under a minute, m:ss over it. */
function clock(s) {
  if (!Number.isFinite(s)) return '';
  if (s < 60) return s.toFixed(1) + 's';
  return Math.floor(s / 60) + ':' + String(Math.round(s % 60)).padStart(2, '0');
}

const bar = document.getElementById('transport');
const tray = document.getElementById('tray');
const titleEl = document.getElementById('now-title');
const metaEl = document.getElementById('now-meta');
const fillEl = document.getElementById('transport-fill');
const timeEl = document.getElementById('transport-time');
const trackEl = document.getElementById('transport-track');

/* The bar stays up after a sound finishes, showing what it was, with the
   control flipped to replay. Nearly everything in this corpus is under a
   second: a transport that vanished on 'ended' would be a flicker, and the
   thing you most want after hearing a 0.2s tick is to hear it again. */
let showing = -1;
let playing = false;

const ICON_STOP = '<svg viewBox="0 0 16 16" aria-hidden="true"><rect x="3.5" y="3.5" width="9" height="9" rx="1"/></svg>';
const ICON_PLAY = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 2.5v11l9-5.5z"/></svg>';

/* Both bars are fixed, so the page needs padding equal to whatever is docked,
   and the transport needs to know how tall the tray under it is. */
export function syncBottomInset() {
  const trayH = tray.hidden ? 0 : tray.offsetHeight;
  const barH = bar.hidden ? 0 : bar.offsetHeight;
  document.documentElement.style.setProperty('--tray-h', trayH + 'px');
  document.body.classList.toggle('has-tray', trayH > 0);
  document.body.style.paddingBottom = (trayH + barH) ? (trayH + barH + 16) + 'px' : '';
}

function syncButton() {
  const b = document.getElementById('transport-stop');
  b.innerHTML = playing ? ICON_STOP : ICON_PLAY;
  b.setAttribute('aria-label', playing
    ? `Stop ${data.titles[showing] || ''}`
    : `Play ${data.titles[showing] || ''} again`);
}

function show(i) {
  // Stopping keeps the bar and the sound it was on; only a fresh index moves it.
  if (i < 0) {
    playing = false;
    if (showing >= 0) { fillEl.style.width = '0%'; syncButton(); }
    return;
  }

  playing = true;
  if (i !== showing) {
    showing = i;
    titleEl.textContent = data.titles[i];
    const bits = [topLevel(data.cats[i])];
    const fmt = data.formats[data.fmtId[i]];
    if (fmt) bits.push(fmt.toUpperCase());
    bits.push(data.status[i] === 1 ? 'still shipping' : 'removed');
    metaEl.textContent = bits.join(' · ');
  }

  const wasHidden = bar.hidden;
  bar.hidden = false;
  syncButton();
  if (wasHidden) syncBottomInset();
}

function progress(p) {
  if (showing < 0 || !p) return;
  const pct = p.d ? Math.min(100, (p.t / p.d) * 100) : 0;
  fillEl.style.width = pct.toFixed(2) + '%';
  timeEl.textContent = p.d ? `${clock(p.t)} / ${clock(p.d)}` : clock(data.duration[showing]);
}

export function initTransport() {
  document.getElementById('transport-stop').addEventListener('click', () => {
    if (playing) player.stopSequence();
    else if (showing >= 0) player.play(showing);
  });

  // Click anywhere on the track to seek within the sound that is playing.
  trackEl.addEventListener('click', (ev) => {
    if (showing < 0) return;
    const r = trackEl.getBoundingClientRect();
    player.seek(showing, (ev.clientX - r.left) / r.width);
  });

  on('play', (i) => show(i == null ? -1 : i));
  on('progress', progress);
  on('playerror', () => show(-1));
  window.addEventListener('resize', syncBottomInset);
}
