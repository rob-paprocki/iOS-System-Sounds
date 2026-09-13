/* ===========================================================================
   Playback.

   Exactly one <audio> element exists for the life of the page. It is created
   inside the first user gesture, because iOS will not play audio from an
   element it did not see a gesture create, and its src is swapped per play.
   Nothing is preloaded and no audio request is made until a play button is
   pressed — a large part of this corpus is alert and emergency tones.
   =========================================================================== */

import { data, previewURL, emit, announce, spokenDuration } from './store.js';

let el = null;
let current = -1;     // sound index currently loaded
let raf = 0;
let seq = null;       // queued indices, played back to back
let seqI = 0;

function ensure() {
  if (el) return el;
  el = new Audio();
  el.preload = 'none';
  el.addEventListener('ended', () => {
    // A queued sequence — the A/B pair, or a Memories soundtrack — rolls on.
    if (seq && seqI + 1 < seq.length) {
      seqI += 1;
      play(seq[seqI], true);
      return;
    }
    seq = null;
    stopTicking();
    current = -1;
    emit('play', null);
    announce('Stopped');
  });
  el.addEventListener('pause', () => { stopTicking(); emit('play', playing() ? current : null); });
  el.addEventListener('playing', () => { startTicking(); emit('play', current); });
  el.addEventListener('error', () => {
    stopTicking();
    const i = current; current = -1;
    emit('play', null);
    emit('playerror', i);
    announce('That preview could not be played');
  });
  return el;
}

function startTicking() {
  cancelAnimationFrame(raf);
  const tick = () => {
    if (!el || el.paused) return;
    emit('progress', { i: current, t: el.currentTime, d: el.duration });
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
}

function stopTicking() {
  cancelAnimationFrame(raf);
  raf = 0;
  emit('progress', { i: current, t: 0, d: 0 });
}

function playing() {
  return !!el && !el.paused && current >= 0;
}

export function currentIndex() {
  return playing() ? current : -1;
}

export function progressFor(i) {
  if (!playing() || current !== i || !el.duration) return null;
  return Math.min(1, el.currentTime / el.duration);
}

/** Toggle: pressing play on the row that is already playing stops it. */
export function toggle(i) {
  const a = ensure();
  if (current === i && !a.paused) {
    a.pause();
    current = -1;
    emit('play', null);
    announce('Stopped');
    return;
  }
  play(i);
}

export function play(i, keepSequence = false) {
  const a = ensure();
  if (!keepSequence) seq = null;          // a direct press abandons any queue
  const url = previewURL(i);
  if (!url) { emit('playerror', i); return; }

  if (current !== i) {
    a.pause();
    a.src = url;
    current = i;
  }
  a.currentTime = 0;
  const p = a.play();
  if (p && p.catch) p.catch(() => { /* surfaced by the error listener */ });
  emit('play', i);
  announce(`Playing ${data.titles[i]}, ${spokenDuration(data.duration[i])}`);
}

export function seek(i, fraction) {
  const a = ensure();
  if (current !== i) { play(i); }
  if (a.duration) a.currentTime = Math.max(0, Math.min(1, fraction)) * a.duration;
  if (a.paused) a.play().catch(() => {});
}

/**
 * Play a list of sounds back to back: the A/B compare, or a Memories soundtrack
 * assembled from its stems. Pressing play on any single row abandons the queue,
 * so an unfinished sequence can never surprise someone later.
 */
export function playSequence(list) {
  if (!list || !list.length) return;
  ensure();
  seq = list.slice();
  seqI = 0;
  play(seq[0], true);
}

export function stopSequence() {
  seq = null;
  if (el && !el.paused) { el.pause(); current = -1; emit('play', null); }
}

/** Play one sound, then the other, for the A/B compare. */
export function playPair(i, j) {
  playSequence([i, j]);
}
