"""Core Services local server — how an out-of-process module reaches core.

`PluginUIDaemon`'s stdio pipe is 1:1 with whoever spawned it: right for
Hub->module control and module->Hub events, wrong for "any module process
needs to call a shared core service" (task scheduling, project I/O,
diagnostics reporting, theme queries, ...) — today handed to in-process
plugins as live object references via ``PluginContext(services=...)``, which
stops working once a plugin is a separate process.

This follows the same shape already used for the AI/Gemma service
(`karcytics_sdk.host.ai.AIServerManager`): one local server the Hub starts once,
reachable over loopback by any process regardless of how it was spawned —
not routed through a spawn-time pipe. Keep this channel for small, infrequent
control-plane calls; bulk data (arrays, images, dataframes) should cross via
the filesystem instead, the same way project state already persists there.
"""

from __future__ import annotations

import hmac
import json
import logging
import secrets
import threading
import time
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger("karcytics.host.core_services")

RPCHandler = Callable[[dict[str, Any]], Any]


class CoreServicesServer:
    """Loopback-only JSON-RPC-style server exposing core services to module processes.

    Handlers are registered by name and receive the call's ``kwargs`` dict,
    returning any JSON-serializable value. Registration is left to the Hub
    (e.g. ``register("task_scheduler.submit", ...)``,
    ``register("diagnostics.report_error", ...)``) so this class stays
    agnostic of what "core" actually is.

    Binding to loopback only keeps this off the network, but any local
    process (or, on a shared machine, another local user) can still reach a
    loopback port — so every request must additionally present a bearer
    token, generated once per server instance and handed to callers out of
    band (today: via `PluginUIDaemon`'s worker environment, see
    `daemon.py`). There is no way to disable this check: a Hub-only, no-auth
    mode would be one flag away from silently reintroducing the hole.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 0, token: str | None = None):
        self._host = host
        self._requested_port = port
        self._token = token if token is not None else secrets.token_urlsafe(32)
        self._handlers: dict[str, RPCHandler] = {}
        self._handlers_lock = threading.Lock()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    @property
    def token(self) -> str:
        """The bearer token every request to this server must present."""
        return self._token

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

            def _is_authorized(self) -> bool:
                header = self.headers.get("Authorization", "")
                scheme, _, presented = header.partition(" ")
                if scheme != "Bearer" or not presented:
                    return False
                # Constant-time comparison: this is a bearer-token check, not a
                # content match, and an early-exit comparison would let a
                # timing attack narrow the token character by character.
                return hmac.compare_digest(presented, server._token)

            def do_POST(self) -> None:  # noqa: N802
                if self.path != "/rpc":
                    self.send_response(404)
                    self.end_headers()
                    return

                if not self._is_authorized():
                    logger.warning(
                        "CoreServicesServer rejected unauthorized request",
                        extra={"client_addr": self.client_address[0], "path": self.path},
                    )
                    response = {"error": "Unauthorized"}
                    payload = json.dumps(response).encode("utf-8")
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json")
                    self.send_header("Content-Length", str(len(payload)))
                    self.end_headers()
                    self.wfile.write(payload)
                    return

                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(length) if length else b"{}"
                start = time.monotonic()
                method = None
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
                    logger.warning("CoreServicesServer handler error: %s", exc, extra={"method": method})
                    response = {"error": str(exc)}
                    status = 500

                logger.info(
                    "CoreServicesServer handled RPC call",
                    extra={
                        "method": method,
                        "status": status,
                        "duration_ms": round((time.monotonic() - start) * 1000, 2),
                        "client_addr": self.client_address[0],
                    },
                )

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

    `token` is required, not optional-with-a-silent-unauthenticated-fallback:
    `CoreServicesServer` rejects every request without a valid one, so a
    client built without a token would only discover that at its first call.
    """

    def __init__(self, port: int, token: str, host: str = "127.0.0.1", timeout: float = 10.0):
        self._url = f"http://{host}:{port}/rpc"
        self._token = token
        self._timeout = timeout

    def call(self, method: str, **kwargs: Any) -> Any:
        """Invoke a registered core service method and return its result.

        Raises:
            RuntimeError: If the server reports an error (unknown method,
                bad/missing token, or a handler-side exception) or the HTTP
                call itself fails.
        """
        try:
            resp = requests.post(
                self._url,
                json={"method": method, "kwargs": kwargs},
                headers={"Authorization": f"Bearer {self._token}"},
                timeout=self._timeout,
            )
        except requests.RequestException as exc:
            raise RuntimeError(f"Core services call '{method}' failed: {exc}") from exc

        body = resp.json()
        if "error" in body:
            raise RuntimeError(f"Core services call '{method}' failed: {body['error']}")
        return body.get("result")


class RemoteCapabilityProxy:
    """Makes a `CoreServicesClient` look like the live service object a plugin
    would have received in-process via `PluginContext(services={...})`.

    An isolated plugin has no live `task_scheduler`/`diagnostics`/... instance
    to hand into its `PluginContext` — only a connection to the Hub's
    `CoreServicesServer`. This wraps that connection so `context.get(name)`
    still returns something callable the same way regardless of process
    model: `proxy.report_error(message=...)` becomes
    `client.call("diagnostics.report_error", message=...)`. Method calls only
    — this is not a general RPC stub (no attribute access, no properties),
    since every core service so far is used as a set of methods.
    """

    def __init__(self, client: CoreServicesClient, capability: str):
        self._client = client
        self._capability = capability

    def __getattr__(self, method_name: str) -> Callable[..., Any]:
        def _call(**kwargs: Any) -> Any:
            return self._client.call(f"{self._capability}.{method_name}", **kwargs)

        return _call


class RemoteWorkflowManager:
    """Worker-side stand-in for `ProjectManager.workflows` (a `WorkflowManager`).

    Only the two read operations an isolated panel's call sites actually use
    are covered — `list_all()` and `load_attachments()` — not a general
    proxy for the rest of that class.
    """

    def __init__(self, client: CoreServicesClient) -> None:
        self._client = client

    def list_all(self) -> list[dict[str, Any]]:
        return self._client.call("project.list_workflows")

    def load_attachments(self, filename: str) -> list[dict[str, Any]]:
        return self._client.call("project.load_attachments", filename=filename)


class RemoteProjectManager:
    """Worker-side stand-in for the Hub's live `ProjectManager`.

    An isolated plugin runs in its own process with no shared memory, so it
    can never hold the Hub's real `ProjectManager` the way an in-process
    plugin does via `self.window().project_manager` — this forwards every
    call a plugin actually makes to the Hub's real copy over
    `CoreServicesServer`, so call sites written for the in-process case
    (`pm.project_dir`, `pm.add_image(...)`, `pm.workflows.list_all()`, ...)
    keep working unchanged. `ui_daemon_runtime.run()` sets
    `window.project_manager` to one of these (or `None`, if no project is
    open) the same way `WorkspaceWindow` sets that attribute in-process —
    see `fetch_remote_project_manager()` below.
    """

    def __init__(self, client: CoreServicesClient, info: dict[str, Any]) -> None:
        self._client = client
        self.project_dir = Path(info["project_dir"])
        self.assets_dir = Path(info["assets_dir"])
        self.project_name = info["project_name"]
        self.workflows = RemoteWorkflowManager(client)

    def add_image(self, filepath: Path | str, copy_to_workspace: bool, subfolder: str | None = None) -> str:
        return self._client.call(
            "project.add_image",
            filepath=str(filepath),
            copy_to_workspace=copy_to_workspace,
            subfolder=subfolder,
        )

    def get_asset_path(self, file_hash: str) -> Path | None:
        result = self._client.call("project.get_asset_path", file_hash=file_hash)
        return Path(result) if result else None

    def save_workflow(
        self,
        module_id: str,
        payload: dict[str, Any],
        metadata: dict[str, Any],
        filename: str | None = None,
        attachments: list[dict[str, Any]] | None = None,
    ) -> str:
        return self._client.call(
            "project.save_workflow",
            module_id=module_id,
            payload=payload,
            metadata=metadata,
            filename=filename,
            attachments=attachments or [],
        )

    def load_workflow_payload(self, filename: str) -> dict[str, Any]:
        return self._client.call("project.load_workflow_payload", filename=filename)

    def attach_workflow_file(
        self,
        wf_filename: str,
        source_path: Path | str,
        key: str,
        description: str = "",
        mime_hint: str = "application/octet-stream",
    ) -> dict[str, Any]:
        return self._client.call(
            "project.attach_workflow_file",
            wf_filename=wf_filename,
            source_path=str(source_path),
            key=key,
            description=description,
            mime_hint=mime_hint,
        )


def fetch_remote_project_manager(client: CoreServicesClient) -> RemoteProjectManager | None:
    """Ask the Hub for its currently active project and wrap it, or return
    `None` if no project is open.

    Mirrors `_confirm_hub_theme_or_exit`'s one-shot startup fetch, but is
    non-fatal on a miss: every flow_cytometry call site that reads
    `window().project_manager` already treats `None` as a normal, handled
    state (its own "standalone" fallback), so this only needs to reproduce
    that state, not gate startup on it.
    """
    info = client.call("project.get_info")
    if not info:
        return None
    return RemoteProjectManager(client, info)
