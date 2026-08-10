"""Core Services local server — how an out-of-process module reaches core.

`PluginUIDaemon`'s stdio pipe is 1:1 with whoever spawned it: right for
Hub->module control and module->Hub events, wrong for "any module process
needs to call a shared core service" (task scheduling, project I/O,
diagnostics reporting, theme queries, ...) — today handed to in-process
plugins as live object references via ``PluginContext(services=...)``, which
stops working once a plugin is a separate process.

This follows the same shape already used for the AI/Gemma service
(`biopro_sdk.host.ai.AIServerManager`): one local server the Hub starts once,
reachable over loopback by any process regardless of how it was spawned —
not routed through a spawn-time pipe. Keep this channel for small, infrequent
control-plane calls; bulk data (arrays, images, dataframes) should cross via
the filesystem instead, the same way project state already persists there.
"""

from __future__ import annotations

import json
import logging
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

import requests

logger = logging.getLogger("biopro.host.core_services")

RPCHandler = Callable[[dict[str, Any]], Any]


class CoreServicesServer:
    """Loopback-only JSON-RPC-style server exposing core services to module processes.

    Handlers are registered by name and receive the call's ``kwargs`` dict,
    returning any JSON-serializable value. Registration is left to the Hub
    (e.g. ``register("task_scheduler.submit", ...)``,
    ``register("diagnostics.report_error", ...)``) so this class stays
    agnostic of what "core" actually is.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0):
        self._host = host
        self._requested_port = port
        self._handlers: dict[str, RPCHandler] = {}
        self._handlers_lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def port(self) -> int:
        """The bound port — only valid after `start()`."""
        if self._httpd is None:
            raise RuntimeError("CoreServicesServer is not running.")
        return self._httpd.server_address[1]

    def register(self, method: str, handler: RPCHandler) -> None:
        """Register a handler for an RPC method name (e.g. "theme.get_colors")."""
        with self._handlers_lock:
            self._handlers[method] = handler

    def unregister(self, method: str) -> None:
        with self._handlers_lock:
            self._handlers.pop(method, None)

    def _dispatch(self, method: str, kwargs: dict[str, Any]) -> Any:
        with self._handlers_lock:
            handler = self._handlers.get(method)
        if handler is None:
            raise KeyError(f"No handler registered for method '{method}'.")
        return handler(kwargs)

    def start(self) -> None:
        """Start the server on a background thread. Idempotent."""
        if self._httpd is not None:
            return

        server = self  # captured by the request handler below

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A002
                logger.debug("CoreServicesServer: " + fmt, *args)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/rpc":
                    self.send_response(404)
                    self.end_headers()
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                try:
                    body = json.loads(raw.decode("utf-8"))
                    method = body["method"]
                    kwargs = body.get("kwargs", {})
                    result = server._dispatch(method, kwargs)
                    response = {"result": result}
                    status = 200
                except KeyError as exc:
                    response = {"error": f"No handler registered: {exc}"}
                    status = 404
                except Exception as exc:  # noqa: BLE001
                    logger.warning("CoreServicesServer handler error: %s", exc)
                    response = {"error": str(exc)}
                    status = 500

                payload = json.dumps(response).encode("utf-8")
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

        self._httpd = ThreadingHTTPServer((self._host, self._requested_port), _Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, name="core-services-server", daemon=True)
        self._thread.start()
        logger.info("CoreServicesServer listening on %s:%d", self._host, self.port)

    def stop(self) -> None:
        """Stop the server and wait for its thread to exit."""
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None
        if self._thread is not None:
            self._thread.join(timeout=2.0)
            self._thread = None


class CoreServicesClient:
    """Thin client used by an out-of-process module to reach `CoreServicesServer`.

    Replaces the live object references a plugin gets via
    ``PluginContext(services=...)`` when running in-process — e.g. what was
    ``context.services["task_scheduler"].submit(...)`` becomes
    ``client.call("task_scheduler.submit", ...)``.
    """

    def __init__(self, port: int, host: str = "127.0.0.1", timeout: float = 10.0):
        self._url = f"http://{host}:{port}/rpc"
        self._timeout = timeout

    def call(self, method: str, **kwargs: Any) -> Any:
        """Invoke a registered core service method and return its result.

        Raises:
            RuntimeError: If the server reports an error (unknown method or a
                handler-side exception) or the HTTP call itself fails.
        """
        try:
            resp = requests.post(self._url, json={"method": method, "kwargs": kwargs}, timeout=self._timeout)
        except requests.RequestException as exc:
            raise RuntimeError(f"Core services call '{method}' failed: {exc}") from exc

        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"Core services call '{method}' failed: {body['error']}")
        return body.get("result")
