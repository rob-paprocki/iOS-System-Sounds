/* ===========================================================================
   Light, dark, or whatever the machine is set to.

   Three states, not two. "System" is the default and stamps nothing on the
   root element, so prefers-color-scheme decides and keeps deciding if the
   machine flips at sunset. An explicit choice stamps data-theme and wins in
   both directions.

   The canvas glyphs cannot read CSS custom properties, so every change has to
   tell them to re-read the palette and repaint.
   =========================================================================== */

import { emit } from './store.js';
import { themeChanged } from './glyph.js';

const KEY = 'ios-system-sounds:theme';
const MODES = ['system', 'light', 'dark'];

let mode = 'system';
const dark = window.matchMedia('(prefers-color-scheme: dark)');

/* Storage can throw in a private window or with site data blocked, and it can
   come back with something we never wrote. Neither should break the page. */
function read() {
  try {
    const v = localStorage.getItem(KEY);
    return MODES.includes(v) ? v : 'system';
  } catch { return 'system'; }
}

function write(v) {
  try { localStorage.setItem(KEY, v); } catch { /* nothing to do about it */ }
}

function apply() {
  const root = document.documentElement;
  if (mode === 'system') root.removeAttribute('data-theme');
  else root.setAttribute('data-theme', mode);

  // The palette changed under the canvases; make them re-read and repaint.
  themeChanged();
  emit('theme', resolved());
}

export function current() { return mode; }

export function resolved() {
  return mode === 'system' ? (dark.matches ? 'dark' : 'light') : mode;
}

export function set(next) {
  if (!MODES.includes(next)) return;
  mode = next;
  write(next);
  apply();
  syncButtons();
}

function syncButtons() {
  document.querySelectorAll('[data-theme-mode]').forEach(b => {
    b.setAttribute('aria-pressed', String(b.dataset.themeMode === mode));
  });
}

export function initTheme() {
  mode = read();
  apply();

  document.querySelectorAll('[data-theme-mode]').forEach(b => {
    b.addEventListener('click', () => set(b.dataset.themeMode));
  });
  syncButtons();

  // Only meaningful while following the system, but harmless otherwise.
  dark.addEventListener('change', () => { if (mode === 'system') apply(); });
}
