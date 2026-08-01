// Thin websocket client over the Python hub, with reconnect.
//
// Both pages talk to the same `/ws` endpoint and differ only by `role`. The
// hub addresses peers by id, so every relayed message carries `from` on the way
// in and `to` on the way out.

export class Signaling {
  constructor(role) {
    this.role = role;
    this.ws = null;
    this.id = null;
    this.iceServers = [];
    this.listeners = new Map();
    this.retryDelay = 500;
    this.closed = false;
  }

  on(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, []);
    this.listeners.get(type).push(fn);
    return this;
  }

  emit(type, payload) {
    for (const fn of this.listeners.get(type) || []) fn(payload);
  }

  connect() {
    this.closed = false;
    const scheme = location.protocol === 'https:' ? 'wss' : 'ws';
    const ws = new WebSocket(`${scheme}://${location.host}/ws?role=${this.role}`);
    this.ws = ws;

    ws.onopen = () => {
      this.retryDelay = 500;
    };

    ws.onmessage = (event) => {
      let msg;
      try {
        msg = JSON.parse(event.data);
      } catch {
        return;
      }
      if (msg.type === 'welcome') {
        this.id = msg.id;
        this.iceServers = msg.iceServers || [];
      }
      if (msg.type === 'superseded') {
        // Another phone took our slot. Reconnecting would kick it straight
        // back off, so stand down instead.
        this.closed = true;
      }
      this.emit(msg.type, msg);
    };

    ws.onclose = () => {
      this.emit('disconnected', null);
      if (this.closed) return;
      // Exponential backoff, capped: the server may just be restarting.
      setTimeout(() => this.connect(), this.retryDelay);
      this.retryDelay = Math.min(this.retryDelay * 2, 5000);
    };

    ws.onerror = () => ws.close();
  }

  send(msg) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  disconnect() {
    this.closed = true;
    if (this.ws) this.ws.close();
  }
}
