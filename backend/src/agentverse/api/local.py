"""Trusted local operator boundary for HTTP and WebSocket requests."""
from urllib.parse import urlsplit
from ipaddress import ip_address

from starlette.responses import JSONResponse


class LocalBoundary:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] not in {"http", "websocket"}:
            return await self.app(scope, receive, send)
        headers = dict(scope["headers"])
        host = headers.get(b"host", b"").decode("latin-1").lower()
        origin = headers.get(b"origin", b"").decode("latin-1").lower()
        try:
            peer = scope.get("client")
            trusted_peer = bool(peer and ip_address(peer[0]).is_loopback)
            parsed = urlsplit("//" + host)
            allowed = trusted_peer and parsed.hostname in {"localhost", "127.0.0.1", "::1"} and parsed.netloc == host and parsed.username is None
        except ValueError:
            allowed = False
        if not allowed or (origin and origin not in {"http://" + host, "https://" + host}):
            if scope["type"] == "websocket":
                return await send({"type": "websocket.close", "code": 1008})
            return await JSONResponse({"detail": "local origin required"}, 403)(scope, receive, send)
        if scope["type"] == "http" and scope["method"] in {"POST", "PUT", "PATCH"}:
            data = bytearray()
            while True:
                message = await receive()
                if message["type"] == "http.disconnect":
                    return
                data.extend(message.get("body", b""))
                if len(data) > 16384:
                    return await JSONResponse({"detail": "request exceeds 16 KiB"}, 413)(scope, receive, send)
                if not message.get("more_body"):
                    break
            async def body():
                return {"type": "http.request", "body": bytes(data), "more_body": False}
            return await self.app(scope, body, send)
        return await self.app(scope, receive, send)
