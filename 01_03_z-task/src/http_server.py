from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from .assistant import ProxyAssistant
from .logging_utils import log


def build_handler(assistant: ProxyAssistant):
    class ProxyHandler(BaseHTTPRequestHandler):
        server_version = "ProxyAssistantHTTP/1.0"

        def _send_json(self, status: int, payload: dict[str, Any]) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self) -> None:
            content_length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(content_length) if content_length > 0 else b"{}"

            try:
                body = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid JSON"})
                return

            session_id = body.get("sessionID")
            msg = body.get("msg")

            if not isinstance(session_id, str) or not session_id.strip():
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Field 'sessionID' is required"})
                return

            if not isinstance(msg, str) or not msg.strip():
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Field 'msg' is required"})
                return

            try:
                answer = assistant.respond(session_id=session_id.strip(), user_msg=msg.strip())
                self._send_json(HTTPStatus.OK, {"msg": answer})
            except Exception as error:
                log(f"request error: {error}")
                self._send_json(HTTPStatus.INTERNAL_SERVER_ERROR, {"error": "Internal server error"})

        def log_message(self, format: str, *args: Any) -> None:
            log(f"http: {format % args}")

    return ProxyHandler


def run_http_server(host: str, port: int, assistant: ProxyAssistant) -> None:
    handler = build_handler(assistant)
    server = ThreadingHTTPServer((host, port), handler)
    log(f"HTTP proxy listening on http://{host}:{port}")
    server.serve_forever()
