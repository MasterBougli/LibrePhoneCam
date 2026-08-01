// Light / dark switching for both web pages.
//
// The palette itself lives in style.css; this only decides which one is
// active and remembers the choice.

const STORAGE_KEY = 'lpc-theme';

export function detectTheme() {
  const saved = localStorage.getItem(STORAGE_KEY);
  if (saved === 'light' || saved === 'dark') return saved;
  // No stored choice means follow the phone's own setting.
  return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
}

export function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  const meta = document.querySelector('meta[name="theme-color"]');
  if (meta) meta.content = theme === 'light' ? '#f4f6f9' : '#0b0d10';
}

export function saveTheme(theme) {
  localStorage.setItem(STORAGE_KEY, theme);
}

export function other(theme) {
  return theme === 'light' ? 'dark' : 'light';
}

/** Glyph for the button: show where the tap will take you. */
export function icon(theme) {
  return theme === 'light' ? '☾' : '☀';
}
