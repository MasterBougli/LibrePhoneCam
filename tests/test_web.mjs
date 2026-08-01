// Guards on the web pages that a browser would only reveal at runtime.
// Run with: node tests/test_web.mjs

import { readFileSync } from 'node:fs';

const root = new URL('../web/', import.meta.url);
const read = (p) => readFileSync(new URL(p, root), 'utf8');

const src = read('static/i18n.js');
const { STRINGS, t } = await import(
  'data:text/javascript;base64,' + Buffer.from(src).toString('base64')
);

const failures = [];
const check = (label, ok, detail = '') => {
  if (ok) console.log(`  ok  ${label}${detail ? ' -> ' + detail : ''}`);
  else { failures.push(label); console.log(`  FAIL ${label} ${detail}`); }
};

const langs = Object.keys(STRINGS);
check('two languages available', langs.length === 2, langs.join(', '));

// A key present in one language but not the other shows a raw identifier in
// the interface the moment someone switches.
const [a, b] = langs;
const onlyA = Object.keys(STRINGS[a]).filter((k) => !(k in STRINGS[b]));
const onlyB = Object.keys(STRINGS[b]).filter((k) => !(k in STRINGS[a]));
check('translation keys match', onlyA.length === 0 && onlyB.length === 0,
  [...onlyA.map((k) => `${a}:${k}`), ...onlyB.map((k) => `${b}:${k}`)].join(', '));

// Same shape too: a plain string where the other has a function means one
// language would print "[object Function]".
const shapeMismatch = Object.keys(STRINGS[a])
  .filter((k) => typeof STRINGS[a][k] !== typeof STRINGS[b][k]);
check('value types match', shapeMismatch.length === 0, shapeMismatch.join(', '));

// Every key the markup asks for must exist.
const html = ['index.html', 'view.html'].map(read).join('\n');
const wanted = new Set([
  ...[...html.matchAll(/data-i18n="([^"]+)"/g)].map((m) => m[1]),
  ...[...html.matchAll(/data-i18n-title="([^"]+)"/g)].map((m) => m[1]),
]);
const missing = [...wanted].filter((k) => !(k in STRINGS[a]));
check('markup keys all defined', missing.length === 0, missing.join(', '));
check('markup actually uses translations', wanted.size > 5, `${wanted.size} keys`);

// Keys referenced from the scripts as t(lang, 'key').
const js = ['static/sender.js', 'static/viewer.js'].map(read).join('\n');
const fromJs = new Set([...js.matchAll(/\bt\(\s*lang\s*,\s*'([^']+)'/g)].map((m) => m[1]));
const missingJs = [...fromJs].filter((k) => !(k in STRINGS[a]));
check('script keys all defined', missingJs.length === 0, missingJs.join(', '));

// Plural helpers must actually vary.
check('viewer count pluralises', t('en', 'viewers', 1) !== t('en', 'viewers', 2),
  `${t('en', 'viewers', 1)} / ${t('en', 'viewers', 2)}`);
check('french differs from english', t('fr', 'startCamera') !== t('en', 'startCamera'),
  t('fr', 'startCamera'));

// Attribution: present in both languages, and linking to the real profile.
const AUTHOR = 'SER-PICO';
check('credit names the author in both languages',
  langs.every((l) => t(l, 'credit').includes(AUTHOR)),
  langs.map((l) => t(l, 'credit')).join(' / '));
check('credit links to the author on github',
  read('index.html').includes(`https://github.com/${AUTHOR}/`));

// House style: no em or en dashes anywhere in the web sources.
const files = ['index.html', 'view.html', 'static/i18n.js', 'static/theme.js',
  'static/sender.js', 'static/viewer.js', 'static/camera.js',
  'static/signaling.js', 'static/style.css'];
const dashed = files.filter((f) => /[–—]/.test(read(f)));
check('no em or en dashes', dashed.length === 0, dashed.join(', '));

// Both themes must define the same custom properties, or switching leaves a
// variable undefined and the colour silently falls back.
const css = read('static/style.css');
const block = (selector) => {
  const i = css.indexOf(selector);
  return css.slice(i, css.indexOf('}', i));
};
const varsOf = (sel) => new Set([...block(sel).matchAll(/(--[a-z-]+):/g)].map((m) => m[1]));
const dark = varsOf(':root,');
const light = varsOf(':root[data-theme="light"]');
const diff = [...dark].filter((v) => !light.has(v)).concat([...light].filter((v) => !dark.has(v)));
check('themes define the same variables', diff.length === 0 && dark.size > 5,
  diff.length ? diff.join(', ') : `${dark.size} variables`);

if (failures.length) {
  console.log(`\n${failures.length} failure(s)`);
  process.exit(1);
}
console.log('\nweb pages: OK');
