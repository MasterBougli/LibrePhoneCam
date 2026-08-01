// Capture-mode selection, checked against what real sensors report.
// Run with: node tests/test_camera.mjs
//
// The module is loaded from source through a data: URL so the browser file
// stays a plain .js without needing a package.json to mark it as ESM.

import { readFileSync } from 'node:fs';
import assert from 'node:assert/strict';

const src = readFileSync(new URL('../web/static/camera.js', import.meta.url), 'utf8');
const { chooseMode, autoBitrate, describeSensor } = await import(
  'data:text/javascript;base64,' + Buffer.from(src).toString('base64')
);

const cases = [
  {
    name: 'iPhone rear camera (48 MP, 60 fps)',
    caps: { width: { max: 4032 }, height: { max: 3024 }, frameRate: { max: 60 } },
    expect: { width: 1920, height: 1080, fps: 60 },
  },
  {
    name: 'iPhone front camera (1080p30)',
    caps: { width: { max: 1920 }, height: { max: 1080 }, frameRate: { max: 30 } },
    expect: { width: 1920, height: 1080, fps: 30 },
  },
  {
    name: 'older phone capped at 720p',
    caps: { width: { max: 1280 }, height: { max: 720 }, frameRate: { max: 30 } },
    expect: { width: 1280, height: 720, fps: 30 },
  },
  {
    name: 'low-end 640x480 webcam',
    caps: { width: { max: 640 }, height: { max: 480 }, frameRate: { max: 30 } },
    expect: { width: 854, height: 480, fps: 30 },
  },
  {
    name: 'portrait-native sensor, short side still decides',
    caps: { width: { max: 1080 }, height: { max: 1920 }, frameRate: { max: 60 } },
    expect: { width: 1920, height: 1080, fps: 60 },
  },
  {
    name: 'getCapabilities unsupported, falls back to getSettings',
    caps: {},
    settings: { width: 1280, height: 720, frameRate: 30 },
    expect: { width: 1280, height: 720, fps: 30 },
  },
  {
    name: 'nothing reported at all, safe default',
    caps: {},
    settings: {},
    expect: { width: 1280, height: 720, fps: 30 },
  },
  {
    name: 'odd frame rate is never below 15',
    caps: { width: { max: 1920 }, height: { max: 1080 }, frameRate: { max: 12 } },
    expect: { width: 1920, height: 1080, fps: 15 },
  },
];

let failed = 0;
for (const c of cases) {
  const got = chooseMode(c.caps, c.settings ?? {});
  try {
    assert.deepEqual(got, c.expect);
    const kbps = autoBitrate(got.width, got.height, got.fps);
    console.log(
      `  ok  ${c.name.padEnd(46)} -> ${got.width}x${got.height}@${got.fps} ${kbps} kbps`
    );
  } catch {
    failed++;
    console.log(`  FAIL ${c.name}\n       expected ${JSON.stringify(c.expect)}\n       got      ${JSON.stringify(got)}`);
  }
}

// Bitrate must stay inside the clamp at both extremes.
const extremes = [
  ['tiny', autoBitrate(160, 120, 15), 1500],
  ['huge', autoBitrate(3840, 2160, 60), 20000],
];
for (const [label, got, want] of extremes) {
  if (got !== want) {
    failed++;
    console.log(`  FAIL bitrate clamp (${label}): expected ${want}, got ${got}`);
  } else {
    console.log(`  ok  bitrate clamp (${label}) -> ${got} kbps`);
  }
}

// Every chosen mode must be even-dimensioned; encoders reject odd sizes.
for (const c of cases) {
  const m = chooseMode(c.caps, c.settings ?? {});
  if (m.width % 2 || m.height % 2) {
    failed++;
    console.log(`  FAIL odd dimensions for ${c.name}: ${m.width}x${m.height}`);
  }
}

console.log(`  ok  describeSensor -> "${describeSensor(cases[0].caps)}"`);

if (failed) {
  console.log(`\n${failed} failure(s)`);
  process.exit(1);
}
console.log('\ncamera mode selection: OK');
