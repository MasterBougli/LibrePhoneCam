"""WebRTC signaling hub.

This process never sees a video frame. It only carries SDP offers/answers and
ICE candidates between the phone (the *sender*) and one or more *viewers* --
the Streamlabs browser source, plus any preview tab. Once ICE completes, media
flows peer-to-peer across the LAN and this server goes idle.
"""

from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

from aiohttp import web

log = logging.getLogger(__name__)

Role = Literal["sender", "viewer"]

# Message types a client is allowed to have forwarded to another peer. Anything
# else is dropped, so a hostile page on the LAN cannot use the hub to push
# arbitrary payloads into the Streamlabs browser source.
RELAYABLE = frozenset({"offer", "answer", "ice"})


@dataclass
class Peer:
    id: str
    role: Role
    ws: web.WebSocketResponse
    label: str = ""

    async def send(self, payload: dict[str, Any]) -> None:
        if self.ws.closed:
            return
        try:
            await self.ws.send_json(payload)
        except (ConnectionResetError, RuntimeError):
            # The socket died between the closed() check and the write; the
            # disconnect path will clean it up.
            pass


@dataclass
class Hub:
    ice_servers: list[dict[str, Any]] = field(default_factory=list)
    on_change: Callable[[], None] | None = None

    sender: Peer | None = None
    viewers: dict[str, Peer] = field(default_factory=dict)

    def _notify(self) -> None:
        if self.on_change:
            self.on_change()

    def _peer(self, peer_id: str) -> Peer | None:
        if self.sender and self.sender.id == peer_id:
            return self.sender
        return self.viewers.get(peer_id)

    async def join(self, role: Role, ws: web.WebSocketResponse, label: str) -> Peer:
        peer = Peer(id=secrets.token_hex(4), role=role, ws=ws, label=label)

        if role == "sender":
            # Last sender wins. A phone that dropped off wifi leaves a socket
            # the OS has not reaped yet; refusing the new connection would lock
            # the user out until that stale socket timed out.
            if self.sender is not None:
                stale = self.sender
                self.sender = None
                await stale.send({"type": "superseded"})
                await stale.ws.close()
                log.info("sender %s replaced by a new connection", stale.id)
            self.sender = peer
            await peer.send(self._welcome(peer, [v.id for v in self.viewers.values()]))
            for viewer in self.viewers.values():
                await viewer.send({"type": "peer-joined", "id": peer.id, "role": "sender"})
        else:
            self.viewers[peer.id] = peer
            await peer.send(
                self._welcome(peer, [self.sender.id] if self.sender else [])
            )
            if self.sender:
                await self.sender.send(
                    {"type": "peer-joined", "id": peer.id, "role": "viewer"}
                )

        log.info("%s connected (id=%s, %s)", role, peer.id, label)
        self._notify()
        return peer

    def _welcome(self, peer: Peer, peers: list[str]) -> dict[str, Any]:
        return {
            "type": "welcome",
            "id": peer.id,
            "role": peer.role,
            "peers": peers,
            "iceServers": self.ice_servers,
        }

    async def leave(self, peer: Peer) -> None:
        if peer.role == "sender":
            # Guard against a superseded sender clearing its replacement.
            if self.sender is not peer:
                return
            self.sender = None
            for viewer in self.viewers.values():
                await viewer.send({"type": "peer-left", "id": peer.id, "role": "sender"})
        else:
            if self.viewers.pop(peer.id, None) is None:
                return
            if self.sender:
                await self.sender.send(
                    {"type": "peer-left", "id": peer.id, "role": "viewer"}
                )

        log.info("%s disconnected (id=%s)", peer.role, peer.id)
        self._notify()

    async def relay(self, sender: Peer, msg: dict[str, Any]) -> None:
        kind = msg.get("type")
        if kind not in RELAYABLE:
            log.debug("dropping non-relayable message %r from %s", kind, sender.id)
            return

        target = self._peer(str(msg.get("to", "")))
        if target is None:
            log.debug("peer %s addressed unknown target %r", sender.id, msg.get("to"))
            return
        # Viewers only ever talk to the sender and vice versa; refuse
        # viewer-to-viewer chatter.
        if target.role == sender.role:
            return

        payload = {k: v for k, v in msg.items() if k != "to"}
        payload["from"] = sender.id
        await target.send(payload)

    def status(self) -> dict[str, Any]:
        return {
            "sender": bool(self.sender),
            "senderLabel": self.sender.label if self.sender else None,
            "viewers": len(self.viewers),
        }
