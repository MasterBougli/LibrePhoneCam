// Receiving end: the Streamlabs browser source, or any tab used as a preview.
//
// Purely reactive. It answers whatever the phone offers and paints the track
// into a full-bleed <video>. No language or theme buttons here, since this
// page is a video source rather than something anyone interacts with.

import { Signaling } from './signaling.js';
import * as i18n from './i18n.js';
import * as theme from './theme.js';

const video = document.getElementById('stage');
const overlay = document.getElementById('overlay');
const message = document.getElementById('message');

const params = new URLSearchParams(location.search);
// `?bare=1` hides the placeholder entirely, for when the source is already
// composited into a live scene and you do not want text on stream.
const bare = params.has('bare');
// `?fit=contain` letterboxes instead of cropping to fill the source.
if (params.get('fit') === 'contain') video.style.objectFit = 'contain';
// `?lang=fr` overrides, since a browser source has no button to press.
const lang = params.get('lang') || i18n.detectLang();

theme.applyTheme(params.get('theme') || theme.detectTheme());
i18n.applyDom(lang);

const sig = new Signaling('viewer');
let pc = null;
let placeholder = 'waitingPhone';

function setPlaceholder(key) {
  placeholder = key;
  if (bare || !key) {
    overlay.hidden = true;
    return;
  }
  message.textContent = i18n.t(lang, key);
  overlay.hidden = false;
}

function teardown() {
  if (pc) pc.close();
  pc = null;
  video.srcObject = null;
}

sig.on('welcome', (msg) => {
  setPlaceholder(msg.peers.length ? 'connecting' : 'waitingPhone');
});

sig.on('offer', async (msg) => {
  // A fresh offer always supersedes whatever we had; the phone only re-offers
  // after its own connection died.
  teardown();

  pc = new RTCPeerConnection({ iceServers: sig.iceServers });

  pc.ontrack = (event) => {
    video.srcObject = event.streams[0];
    // Autoplay is only permitted while muted, and there is no audio track
    // anyway.
    video.play().catch(() => {});
  };

  pc.onicecandidate = (e) => {
    if (e.candidate) {
      sig.send({ type: 'ice', to: msg.from, candidate: e.candidate.toJSON() });
    }
  };

  pc.onconnectionstatechange = () => {
    if (!pc) return;
    if (pc.connectionState === 'connected') setPlaceholder(null);
    if (pc.connectionState === 'failed') {
      teardown();
      setPlaceholder('connectionLost');
    }
  };

  await pc.setRemoteDescription({ type: 'offer', sdp: msg.sdp });
  const answer = await pc.createAnswer();
  await pc.setLocalDescription(answer);
  sig.send({ type: 'answer', to: msg.from, sdp: pc.localDescription.sdp });
});

sig.on('ice', async (msg) => {
  if (!pc || !msg.candidate) return;
  try {
    await pc.addIceCandidate(msg.candidate);
  } catch {
    // Candidates can arrive before setRemoteDescription lands; harmless.
  }
});

sig.on('peer-left', (msg) => {
  if (msg.role !== 'sender') return;
  teardown();
  setPlaceholder('waitingPhone');
});

sig.on('peer-joined', (msg) => {
  if (msg.role === 'sender') setPlaceholder('connecting');
});

sig.on('disconnected', () => {
  teardown();
  setPlaceholder('serverOffline');
});

setPlaceholder(placeholder);
sig.connect();
