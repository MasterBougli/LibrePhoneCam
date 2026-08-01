"""aiohttp application: static pages + the signaling websocket."""

from __future__ import annotations

from typing import cast

from aiohttp import WSMsgType, web

from .paths import web_dir
from .signaling import Hub, Role

WEB_DIR = web_dir()

HUB_KEY = web.AppKey("hub", Hub)


@web.middleware
async def no_store(request: web.Request, handler):
    """Disable caching everywhere, static assets included.

    The Streamlabs browser source caches aggressively and offers no reload
    button, so a stale stylesheet or script means clearing its cache by hand.
    Nothing here is served over the internet, so there is no bandwidth to save.
    """
    response = await handler(request)
    # A websocket's headers went out at the handshake; touching them here is
    # both useless and, for an already-prepared response, wrong.
    if not response.prepared:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return response


def _page(name: str):
    async def handler(_: web.Request) -> web.Response:
        return web.Response(
            body=(WEB_DIR / name).read_bytes(),
            content_type="text/html",
            charset="utf-8",
        )

    return handler


async def health(request: web.Request) -> web.Response:
    return web.json_response(request.app[HUB_KEY].status())


def _short_ua(user_agent: str) -> str:
    """A human-sized device name for the console log."""
    for needle, name in (
        ("iPhone", "iPhone"),
        ("iPad", "iPad"),
        ("Android", "Android"),
        ("Macintosh", "Mac"),
    ):
        if needle in user_agent:
            return name
    return "device"


async def websocket(request: web.Request) -> web.WebSocketResponse:
    role = request.query.get("role")
    if role not in ("sender", "viewer"):
        raise web.HTTPBadRequest(text="role must be 'sender' or 'viewer'")

    ws = web.WebSocketResponse(heartbeat=20.0)
    await ws.prepare(request)

    hub = request.app[HUB_KEY]
    label = _short_ua(request.headers.get("User-Agent", ""))
    peer = await hub.join(cast(Role, role), ws, label)

    try:
        async for msg in ws:
            if msg.type is not WSMsgType.TEXT:
                continue
            try:
                payload = msg.json()
            except ValueError:
                continue
            if isinstance(payload, dict):
                await hub.relay(peer, payload)
    finally:
        await hub.leave(peer)

    return ws


def create_app(hub: Hub) -> web.Application:
    app = web.Application(middlewares=[no_store])
    app[HUB_KEY] = hub
    app.add_routes(
        [
            web.get("/", _page("index.html")),
            web.get("/view", _page("view.html")),
            web.get("/health", health),
            web.get("/ws", websocket),
            web.static("/static", WEB_DIR / "static"),
        ]
    )
    return app
