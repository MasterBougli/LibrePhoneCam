// Picking a capture mode from what the camera actually reports.
//
// Kept free of DOM and WebRTC so the decision logic can be tested on its own.

const clamp = (n, lo, hi) => Math.min(hi, Math.max(lo, n));

/**
 * Choose a streaming mode from a track's capabilities.
 *
 * Deliberately capped at 1080p: phone sensors happily report 4032x3024, but
 * nothing downstream wants a 4K browser source, and the extra pixels cost
 * battery and wifi headroom for no visible gain at typical stream sizes.
 */
export function chooseMode(caps = {}, settings = {}) {
  const maxW = caps.width?.max ?? settings.width ?? 1280;
  const maxH = caps.height?.max ?? settings.height ?? 720;
  const maxFps = caps.frameRate?.max ?? settings.frameRate ?? 30;

  // Phone sensors report their native portrait orientation, so the short side
  // is what caps the landscape height.
  const shortSide = Math.min(maxW, maxH);

  let height;
  if (shortSide >= 1080) height = 1080;
  else if (shortSide >= 720) height = 720;
  else height = Math.floor(shortSide / 2) * 2; // keep it even for the encoder

  const width = Math.round((height * 16) / 9 / 2) * 2;

  let fps;
  if (maxFps >= 60) fps = 60;
  else if (maxFps >= 30) fps = 30;
  else fps = Math.max(15, Math.round(maxFps));

  return { width, height, fps };
}

/**
 * Bitrate that suits a given mode, in kbps.
 *
 * Bits-per-pixel-per-frame is the standard way to size a stream; 0.09 sits in
 * the "visually clean" band for VP8/H.264 at these resolutions.
 */
export function autoBitrate(width, height, fps) {
  const kbps = (width * height * fps * 0.09) / 1000;
  return clamp(Math.round(kbps / 500) * 500, 1500, 20000);
}

/** Human-readable summary of what the sensor can do. */
export function describeSensor(caps = {}, settings = {}) {
  const w = caps.width?.max ?? settings.width;
  const h = caps.height?.max ?? settings.height;
  const fps = caps.frameRate?.max ?? settings.frameRate;
  if (!w || !h) return 'camera capabilities unavailable';
  const long = Math.max(w, h);
  const short = Math.min(w, h);
  const mp = ((w * h) / 1e6).toFixed(1);
  return `${long}x${short} (${mp} MP)` + (fps ? ` up to ${Math.round(fps)} fps` : '');
}
