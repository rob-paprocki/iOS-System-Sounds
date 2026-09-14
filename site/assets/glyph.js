/* ===========================================================================
   Canvas drawing: waveform glyphs, lifespan bars, the release ruler and the
   per-sound filmstrip.

   The waveform is fixed width, not true-to-duration. Most of this corpus is
   under half a second; drawn to scale, nine rows in ten would be a hairline.
   Amplitude is normalised per sound so a quiet tap still has a shape, and the
   real length is printed as a number in the next column instead.
   =========================================================================== */

import { data, buildsOf } from './store.js';

/* Canvas cannot read CSS custom properties, so the palette is pulled off the
   root element once and cached. themeChanged() drops the cache; the light and
   dark ledgers use the same token names, so nothing else here changes. */
const TOKENS = ['ink', 'ink-muted', 'rule', 'ground', 'present', 'removed', 'signal', 'wash'];
let C = null;

export function themeChanged() { C = null; }

function palette() {
  if (C) return C;
  const cs = getComputedStyle(document.documentElement);
  C = {};
  for (const name of TOKENS) {
    const key = name === 'ink-muted' ? 'muted' : name;
    C[key] = cs.getPropertyValue('--' + name).trim() || '#000';
  }
  return C;
}

/* A translucent tint of a token, for the played-baseline and similar. */
function tint(colour, alpha) {
  return `color-mix(in srgb, ${colour} ${Math.round(alpha * 100)}%, transparent)`;
}

/* Size a canvas to its CSS box at device resolution. Returns the 2D context
   already scaled, so all drawing below is in CSS pixels. */
function setup(canvas, cssW, cssH) {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const w = Math.max(1, Math.round(cssW));
  const h = Math.max(1, Math.round(cssH));
  if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
    canvas.width = w * dpr;
    canvas.height = h * dpr;
  }
  const ctx = canvas.getContext('2d');
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  ctx.clearRect(0, 0, w, h);
  return { ctx, w, h };
}

/* The 48 amplitude buckets for one sound, normalised to 0..1. */
export function peaksOf(i) {
  const n = data.buckets;
  if (!data.peaks || data.peaks.length < (i + 1) * n) return null;
  const slice = data.peaks.subarray(i * n, (i + 1) * n);
  let max = 0;
  for (let k = 0; k < n; k++) if (slice[k] > max) max = slice[k];
  if (!max) return null;
  const out = new Float32Array(n);
  for (let k = 0; k < n; k++) out[k] = slice[k] / max;
  return out;
}

/**
 * Row waveform. `progress` is 0..1 while this sound is playing, else null.
 * Present sounds read as a solid fill, removed sounds as an outline on a
 * dashed baseline — colour, and also shape, so it survives greyscale.
 */
export function drawWave(canvas, i, progress = null, cssW = 0, cssH = 0) {
  const rect = canvas.getBoundingClientRect();
  const { ctx, w, h } = setup(canvas, cssW || rect.width || 120, cssH || rect.height || 24);
  const c = palette();
  const present = data.status[i] === 1;
  const colour = present ? c.present : c.removed;
  const peaks = peaksOf(i);
  const mid = h / 2;

  // Baseline: solid for present, dashed for removed.
  ctx.strokeStyle = present ? tint(c.present, 0.35) : c.removed;
  ctx.lineWidth = 1;
  if (!present) ctx.setLineDash([2, 2]);
  ctx.beginPath();
  ctx.moveTo(0, Math.round(mid) + 0.5);
  ctx.lineTo(w, Math.round(mid) + 0.5);
  ctx.stroke();
  ctx.setLineDash([]);

  if (!peaks) {
    // No peak data for this sound: a flat bar, never a fake shape.
    ctx.fillStyle = c.rule;
    ctx.fillRect(0, mid - 1, w, 2);
    return;
  }

  const n = peaks.length;
  const step = w / n;
  const bw = Math.max(1, step - 1);
  const playedX = progress == null ? -1 : progress * w;

  for (let k = 0; k < n; k++) {
    const x = k * step;
    const amp = Math.max(1, peaks[k] * (h / 2 - 1));
    const y = mid - amp;
    const bh = amp * 2;
    const played = playedX >= 0 && x < playedX;

    if (present || played) {
      ctx.fillStyle = played ? c.ink : colour;
      ctx.fillRect(x, y, bw, bh);
    } else {
      ctx.strokeStyle = colour;
      ctx.lineWidth = 1;
      ctx.strokeRect(x + 0.5, y + 0.5, Math.max(1, bw - 1), Math.max(1, bh - 1));
    }
  }

  if (playedX >= 0) {
    ctx.fillStyle = c.ink;
    ctx.fillRect(Math.min(playedX, w - 1), 0, 1, h);
  }
}

/**
 * Lifespan bar: the same ordinal scale as the ruler above the list, with a mark
 * for every build this sound shipped in. A gap in the middle means it was
 * removed and later reinstated, which is the most interesting thing this
 * corpus knows, so it has to be visible without opening anything.
 */
export function drawLifespan(canvas, i, cssW = 0, cssH = 0) {
  const rect = canvas.getBoundingClientRect();
  const { ctx, w, h } = setup(canvas, cssW || rect.width || 90, cssH || rect.height || 14);
  const c = palette();
  const V = data.versions.length;
  if (!V) return;

  ctx.fillStyle = c.rule;
  ctx.fillRect(0, h - 1, w, 1);

  const builds = buildsOf(i);
  if (!builds) return;                       // detail index has not arrived yet

  ctx.fillStyle = data.status[i] === 1 ? c.present : c.removed;
  const step = w / V;
  const bw = Math.max(1, step);
  for (let k = 0; k < builds.length; k++) {
    ctx.fillRect(builds[k] * step, 1, bw, h - 2);
  }
}

/**
 * The release ruler. 129 ticks spaced by release order, not by date, so that
 * 2007–2012 is not crushed against the recent quarterly cadence. Tick height
 * is how many sounds are alive at that build.
 */
export function drawRuler(canvas, from, to, hover = -1) {
  const rect = canvas.getBoundingClientRect();
  const { ctx, w, h } = setup(canvas, rect.width || 600, rect.height || 40);
  const c = palette();
  const V = data.versions.length;
  if (!V) return;

  const counts = data.aliveCounts;
  let max = 1;
  if (counts) for (let k = 0; k < V; k++) if (counts[k] > max) max = counts[k];

  const step = w / V;
  const bw = Math.max(1, Math.min(step - 1, 6));

  for (let k = 0; k < V; k++) {
    const inRange = k >= from && k <= to;
    const val = counts ? counts[k] / max : 0.35;
    const bh = Math.max(2, val * (h - 4));
    ctx.fillStyle = k === hover ? c.signal : inRange ? c.ink : c.rule;
    ctx.fillRect(k * step + (step - bw) / 2, h - bh, bw, bh);
  }
}

/** Full-width filmstrip for the row detail: every build, marked where present. */
export function drawFilmstrip(canvas, i) {
  const rect = canvas.getBoundingClientRect();
  const { ctx, w, h } = setup(canvas, rect.width || 400, rect.height || 26);
  const c = palette();
  const V = data.versions.length;
  if (!V) return;

  const step = w / V;
  ctx.fillStyle = c.rule;
  ctx.fillRect(0, h - 1, w, 1);

  const builds = buildsOf(i);
  if (!builds) return;

  const set = new Set(Array.from(builds));
  ctx.fillStyle = data.status[i] === 1 ? c.present : c.removed;
  for (let k = 0; k < V; k++) {
    if (set.has(k)) ctx.fillRect(k * step, 2, Math.max(1, step - 0.5), h - 4);
  }
}

/** Large scrubbable waveform for the row detail and the A/B compare. */
export function drawBigWave(canvas, i, progress = null) {
  const rect = canvas.getBoundingClientRect();
  drawWave(canvas, i, progress, rect.width || 400, rect.height || 64);
}
