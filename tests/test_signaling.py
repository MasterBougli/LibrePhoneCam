"""End-to-end exercise of the signaling hub.

Drives two real websocket clients through the handshake the phone and the
browser source perform, without needing either. Run it with `pytest`, or
directly with `python tests/test_signaling.py`.
"""

from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path

import aiohttp
from aiohttp import web

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from librephonecam.app import create_app  # noqa: E402
from librephonecam.signaling import Hub  # noqa: E402

TIMEOUT = 5


async def recv(ws: aiohttp.ClientWebSocketResponse) -> dict:
    msg = await asyncio.wait_for(ws.receive(), timeout=TIMEOUT)
    assert msg.type is aiohttp.WSMsgType.TEXT, f"expected TEXT, got {msg.type}"
    return msg.json()


@contextlib.asynccontextmanager
async def running_server():
    hub = Hub(ice_servers=[{"urls": ["stun:example.test:3478"]}])
    runner = web.AppRunner(create_app(hub), access_log=None)
    await runner.setup()
    site = web.TCPSite(runner, "127.0.0.1", 0)
    await site.start()
    port = runner.addresses[0][1]
    try:
        yield f"http://127.0.0.1:{port}", hub
    finally:
        await runner.cleanup()


async def scenario() -> None:
    async with running_server() as (base, hub):
        async with aiohttp.ClientSession() as session:
            # --- viewer arrives first, as it does when Streamlabs is already open
            viewer = await session.ws_connect(f"{base}/ws?role=viewer")
            hello = await recv(viewer)
            assert hello["type"] == "welcome", hello
            assert hello["peers"] == [], "no sender yet"
            assert hello["iceServers"] == [{"urls": ["stun:example.test:3478"]}]
            viewer_id = hello["id"]

            # --- then the phone connects and should learn about the viewer
            sender = await session.ws_connect(f"{base}/ws?role=sender")
            hello = await recv(sender)
            assert hello["type"] == "welcome", hello
            assert hello["peers"] == [viewer_id], hello
            sender_id = hello["id"]

            notice = await recv(viewer)
            assert notice == {"type": "peer-joined", "id": sender_id, "role": "sender"}

            # --- offer / answer / ICE all relay with `to` rewritten to `from`
            await sender.send_json({"type": "offer", "to": viewer_id, "sdp": "v=0-fake"})
            got = await recv(viewer)
            assert got == {"type": "offer", "from": sender_id, "sdp": "v=0-fake"}, got

            await viewer.send_json({"type": "answer", "to": sender_id, "sdp": "v=0-reply"})
            got = await recv(sender)
            assert got == {"type": "answer", "from": viewer_id, "sdp": "v=0-reply"}, got

            await viewer.send_json(
                {"type": "ice", "to": sender_id, "candidate": {"candidate": "host"}}
            )
            got = await recv(sender)
            assert got["type"] == "ice" and got["from"] == viewer_id, got

            # --- messages that are not part of the WebRTC dance are dropped
            await sender.send_json({"type": "evil", "to": viewer_id, "payload": "x"})
            await sender.send_json({"type": "ice", "to": viewer_id, "candidate": {"c": 1}})
            got = await recv(viewer)
            assert got["type"] == "ice", f"'evil' should have been dropped, got {got}"

            # --- a second phone takes over instead of being refused
            sender2 = await session.ws_connect(f"{base}/ws?role=sender")
            assert (await recv(sender2))["type"] == "welcome"
            assert (await recv(sender))["type"] == "superseded"
            assert hub.sender is not None and hub.sender.id != sender_id

            # The displaced sender must not unregister its replacement.
            await sender.close()
            await asyncio.sleep(0.1)
            assert hub.sender is not None, "superseded sender wrongly cleared the slot"

            # --- viewer leaving is announced to the phone
            await viewer.close()
            notice = await recv(sender2)
            assert notice["type"] == "peer-left" and notice["id"] == viewer_id, notice
            assert hub.status()["viewers"] == 0

            await sender2.close()
            await asyncio.sleep(0.1)
            assert hub.status() == {"sender": False, "senderLabel": None, "viewers": 0}


def test_signaling_roundtrip() -> None:
    asyncio.run(scenario())


if __name__ == "__main__":
    try:
        test_signaling_roundtrip()
    except AssertionError as exc:
        print(f"FAIL: {exc}")
        raise SystemExit(1)
    print("signaling roundtrip: OK")
