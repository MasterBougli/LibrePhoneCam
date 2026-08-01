// Phone side: grab the camera and offer it to every viewer that shows up.
//
// One RTCPeerConnection per viewer, all sharing the same MediaStreamTrack, so
// the Streamlabs source and any preview tab can watch at the same time.

import { Signaling } from './signaling.js';
import { autoBitrate, chooseMode, describeSensor } from './camera.js';
import * as i18n from './i18n.js';
import * as theme from './theme.js';

const $ = (id) => document.getElementById(id);
const els = {
  video: $('preview'),
  start: $('start'),
  stop: $('stop'),
  flip: $('flip'),
  torch: $('torch'),
  resolution: $('resolution'),
  fps: $('fps'),
  bitrate: $('bitrate'),
  setup: $('setup'),
  controls: $('controls'),
  live: $('live'),
  livebar: $('livebar'),
  dot: $('dot'),
  state: $('state'),
  viewers: $('viewers'),
  stats: $('stats'),
  error: $('error'),
  rotate: $('rotate'),
  detected: $('detected'),
  theme: $('theme'),
  lang: $('lang'),
};

const RESOLUTIONS = {
  720: { width: 1280, height: 720 },
  1080: { width: 1920, height: 1080 },
  1440: { width: 2560, height: 1440 },
};

const sig = new Signaling('sender');
const peers = new Map(); // viewerId -> RTCPeerConnection

let stream = null;
let facing = 'environment';
let wakeLock = null;
let statsTimer = null;
let lastBytes = 0;
let lastStatsAt = 0;

let lang = i18n.detectLang();
let currentTheme = theme.detectTheme();

// What we are actually capturing, filled in once the camera is open. The
// selects say what was *asked* for; a camera is free to answer with something
// else, so every downstream decision reads this instead.
let active = { width: 1920, height: 1080, fps: 60, maxBitrate: 12_000_000 };

// Kept so switching language can redraw text that was built at runtime.
let statusState = { kind: 'idle', key: 'stopped' };
let viewerCount = 0;
let errorState = null;
let detectedState = null;

// --- language and theme --------------------------------------------------

function setLang(next) {
  lang = next;
  i18n.saveLang(next);
  i18n.applyDom(next);
  els.lang.textContent = i18n.other(next).toUpperCase();
  renderStatus();
  renderViewers();
  renderError();
  renderDetected();
}

function setTheme(next) {
  currentTheme = next;
  theme.applyTheme(next);
  theme.saveTheme(next);
  els.theme.textContent = theme.icon(next);
}

els.lang.onclick = () => setLang(i18n.other(lang));
els.theme.onclick = () => setTheme(theme.other(currentTheme));

// --- rendering -----------------------------------------------------------

function renderStatus() {
  els.dot.className = `dot ${statusState.kind}`;
  els.state.textContent = i18n.t(lang, statusState.key);
}

function setStatus(kind, key) {
  statusState = { kind, key };
  renderStatus();
}

function renderViewers() {
  els.viewers.textContent = i18n.t(lang, 'viewers', viewerCount);
}

function renderError() {
  els.error.hidden = errorState === null;
  if (errorState) {
    els.error.textContent = i18n.t(lang, errorState.key, errorState.arg);
  }
}

function showError(key, arg) {
  errorState = key ? { key, arg } : null;
  renderError();
}

function renderDetected() {
  if (!detectedState) {
    els.detected.textContent = '';
    return;
  }
  const mbps = (active.maxBitrate / 1e6).toFixed(1).replace(/\.0$/, '');
  const chosen = `${active.width}x${active.height} · ${active.fps} fps · ${mbps} Mbps`;
  els.detected.textContent = detectedState.isAuto
    ? `${i18n.t(lang, 'auto')} · ${detectedState.sensor} -> ${chosen}`
    : chosen;
}

// --- camera --------------------------------------------------------------

function requested() {
  if (els.resolution.value === 'auto') {
    // Ask for far more than we intend to keep: the answer reveals the
    // sensor's ceiling, which is what chooseMode() needs.
    return { auto: true, width: 3840, height: 2160, fps: 60 };
  }
  const res = RESOLUTIONS[els.resolution.value];
  return {
    auto: false,
    ...res,
    fps: els.fps.value === 'auto' ? 60 : Number(els.fps.value),
  };
}

async function openCamera() {
  const req = requested();

  // No contentHint anywhere on purpose: it would pull against the explicit
  // degradationPreference set on the sender.
  const next = await navigator.mediaDevices.getUserMedia({
    audio: false,
    video: {
      facingMode: { ideal: facing },
      width: { ideal: req.width },
      height: { ideal: req.height },
      frameRate: { ideal: req.fps },
    },
  });

  const track = next.getVideoTracks()[0];
  const caps = track.getCapabilities ? track.getCapabilities() : {};
  const sensor = describeSensor(caps, track.getSettings());

  if (req.auto) {
    const mode = chooseMode(caps, track.getSettings());
    try {
      await track.applyConstraints({
        width: { ideal: mode.width },
        height: { ideal: mode.height },
        frameRate: { ideal: mode.fps },
      });
    } catch {
      // Some cameras refuse a second pass of constraints. Whatever the first
      // getUserMedia handed back is still perfectly usable.
    }
  }

  // Report what the camera settled on, never what we asked for.
  const got = track.getSettings();
  active = {
    width: got.width || req.width,
    height: got.height || req.height,
    fps: Math.round(got.frameRate || req.fps),
    maxBitrate: 0,
  };
  active.maxBitrate =
    els.bitrate.value === 'auto'
      ? autoBitrate(active.width, active.height, active.fps) * 1000
      : Number(els.bitrate.value) * 1000;

  detectedState = { isAuto: req.auto, sensor };
  renderDetected();
  return next;
}

async function start() {
  showError(null);
  els.start.disabled = true;

  try {
    stream = await openCamera();
  } catch (err) {
    els.start.disabled = false;
    if (err.name === 'NotAllowedError') showError('errDenied');
    else if (err.name === 'NotReadableError') showError('errBusy');
    else showError('errOpen', err.message);
    return;
  }

  els.video.srcObject = stream;
  els.video.classList.toggle('mirrored', facing === 'user');
  setRunning(true);

  await requestWakeLock();
  updateTorchButton();
  startStats();
  sig.connect();
}

async function stop() {
  sig.disconnect();
  for (const pc of peers.values()) pc.close();
  peers.clear();

  if (stream) stream.getTracks().forEach((t) => t.stop());
  stream = null;
  els.video.srcObject = null;

  releaseWakeLock();
  stopStats();

  setRunning(false);
  els.start.disabled = false;
  setStatus('idle', 'stopped');
  viewerCount = 0;
  renderViewers();
}

function setRunning(running) {
  els.setup.hidden = running;
  els.controls.hidden = !running;
  els.live.hidden = !running;
  els.livebar.hidden = !running;
  document.body.classList.toggle('running', running);
}

// --- peer plumbing -------------------------------------------------------

async function callViewer(viewerId) {
  if (peers.has(viewerId) || !stream) return;

  const pc = new RTCPeerConnection({ iceServers: sig.iceServers });
  peers.set(viewerId, pc);

  for (const track of stream.getTracks()) pc.addTrack(track, stream);
  await applyBitrate(pc);

  pc.onicecandidate = (e) => {
    if (e.candidate) {
      sig.send({ type: 'ice', to: viewerId, candidate: e.candidate.toJSON() });
    }
  };

  pc.onconnectionstatechange = () => {
    if (pc.connectionState === 'failed') {
      // ICE gave up, so drop it and let the viewer's reconnect trigger a
      // fresh offer rather than sitting on a dead connection.
      pc.close();
      peers.delete(viewerId);
    }
    refreshViewerCount();
  };

  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  sig.send({ type: 'offer', to: viewerId, sdp: pc.localDescription.sdp });
}

async function applyBitrate(pc) {
  const { maxBitrate } = active;
  for (const sender of pc.getSenders()) {
    if (!sender.track || sender.track.kind !== 'video') continue;
    const params = sender.getParameters();
    if (!params.encodings || params.encodings.length === 0) params.encodings = [{}];
    params.encodings[0].maxBitrate = maxBitrate;
    // Without this the encoder answers congestion by shrinking the picture,
    // so a 1080p source silently becomes 480x270. Hold the resolution and let
    // the frame rate absorb the pressure instead.
    params.degradationPreference = 'maintain-resolution';
    try {
      await sender.setParameters(params);
    } catch {
      // Older Safari rejects setParameters before the first frame; the stream
      // still works, it just runs at the browser's own bitrate.
    }
  }
}

function dropViewer(viewerId) {
  const pc = peers.get(viewerId);
  if (pc) pc.close();
  peers.delete(viewerId);
  refreshViewerCount();
}

function refreshViewerCount() {
  viewerCount = [...peers.values()].filter((pc) => pc.connectionState === 'connected').length;
  renderViewers();
  setStatus(viewerCount > 0 ? 'live' : 'waiting', viewerCount > 0 ? 'live' : 'waitingViewer');
}

sig.on('welcome', (msg) => {
  msg.peers.forEach(callViewer);
  refreshViewerCount();
});
sig.on('peer-joined', (msg) => msg.role === 'viewer' && callViewer(msg.id));
sig.on('peer-left', (msg) => dropViewer(msg.id));
sig.on('disconnected', () => setStatus('idle', 'reconnecting'));
sig.on('superseded', () => {
  showError('errSuperseded');
  stop();
});

sig.on('answer', async (msg) => {
  const pc = peers.get(msg.from);
  if (!pc) return;
  await pc.setRemoteDescription({ type: 'answer', sdp: msg.sdp });
  await applyBitrate(pc);
});

sig.on('ice', async (msg) => {
  const pc = peers.get(msg.from);
  if (!pc || !msg.candidate) return;
  try {
    await pc.addIceCandidate(msg.candidate);
  } catch {
    // A candidate arriving before the answer is set is expected and harmless.
  }
});

// --- camera controls -----------------------------------------------------

async function reopenCamera() {
  const previous = stream;
  let next;
  try {
    next = await openCamera();
  } catch (err) {
    showError('errSwitch', err.message);
    return;
  }

  stream = next;
  els.video.srcObject = next;
  els.video.classList.toggle('mirrored', facing === 'user');

  // replaceTrack swaps the source without renegotiating, so viewers see no
  // interruption beyond a frame or two.
  const track = next.getVideoTracks()[0];
  for (const pc of peers.values()) {
    for (const sender of pc.getSenders()) {
      if (sender.track && sender.track.kind === 'video') await sender.replaceTrack(track);
    }
    await applyBitrate(pc);
  }

  if (previous) previous.getTracks().forEach((t) => t.stop());
  updateTorchButton();
}

els.flip.onclick = async () => {
  facing = facing === 'user' ? 'environment' : 'user';
  await reopenCamera();
};

for (const el of [els.resolution, els.fps, els.bitrate]) {
  el.onchange = () => {
    if (stream) reopenCamera();
  };
}

function torchCapable() {
  const track = stream && stream.getVideoTracks()[0];
  return Boolean(track && track.getCapabilities && track.getCapabilities().torch);
}

function updateTorchButton() {
  els.torch.hidden = !torchCapable();
  els.torch.classList.remove('on');
}

els.torch.onclick = async () => {
  const track = stream.getVideoTracks()[0];
  const on = !els.torch.classList.contains('on');
  try {
    await track.applyConstraints({ advanced: [{ torch: on }] });
    els.torch.classList.toggle('on', on);
  } catch {
    els.torch.hidden = true;
  }
};

// --- keep the screen alive ----------------------------------------------

async function requestWakeLock() {
  if (!('wakeLock' in navigator)) return;
  try {
    wakeLock = await navigator.wakeLock.request('screen');
  } catch {
    // Denied in low-power mode; the stream still runs until the screen locks.
  }
}

function releaseWakeLock() {
  if (wakeLock) wakeLock.release().catch(() => {});
  wakeLock = null;
}

document.addEventListener('visibilitychange', () => {
  // Phones drop the wake lock whenever the tab is backgrounded, and never
  // restore it on their own.
  if (document.visibilityState === 'visible' && stream && !wakeLock) requestWakeLock();
});

// --- stats ---------------------------------------------------------------

function startStats() {
  stopStats();
  statsTimer = setInterval(updateStats, 1000);
}

function stopStats() {
  if (statsTimer) clearInterval(statsTimer);
  statsTimer = null;
  lastBytes = 0;
  lastStatsAt = 0;
  els.stats.textContent = '';
}

async function updateStats() {
  const track = stream && stream.getVideoTracks()[0];
  if (!track) return;

  const s = track.getSettings();
  const parts = [];
  if (s.width && s.height) parts.push(`${s.width}x${s.height}`);

  let bytes = 0;
  let fps = null;
  for (const pc of peers.values()) {
    const report = await pc.getStats();
    report.forEach((r) => {
      if (r.type === 'outbound-rtp' && r.kind === 'video') {
        bytes += r.bytesSent || 0;
        if (r.framesPerSecond) fps = r.framesPerSecond;
      }
    });
  }

  if (fps) parts.push(`${Math.round(fps)} fps`);
  const now = performance.now();
  if (lastStatsAt && bytes >= lastBytes) {
    const kbps = ((bytes - lastBytes) * 8) / (now - lastStatsAt);
    parts.push(`${Math.round(kbps)} kbps`);
  }
  lastBytes = bytes;
  lastStatsAt = now;

  els.stats.textContent = parts.join('  ·  ');
  els.rotate.hidden = !(s.height > s.width);
}

// --- boot ----------------------------------------------------------------

els.start.onclick = start;
els.stop.onclick = stop;

setTheme(currentTheme);
setLang(lang);
setStatus('idle', 'connecting');

if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
  showError(location.protocol === 'https:' ? 'errNoCamera' : 'errInsecure');
  els.start.disabled = true;
}
