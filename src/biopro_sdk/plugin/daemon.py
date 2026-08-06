"""Plugin Worker Daemon — Long-lived background process manager with msgpack IPC.

Provides IPC communication between plugin frontend logic and isolated worker
processes running in plugin virtual environments.
"""

from __future__ import annotations

import os
import select
import struct
import subprocess
import sys
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, ClassVar

import msgpack
from PyQt6.QtCore import QObject

from .logging import get_logger

logger = get_logger(__name__, "biopro_sdk")


class PluginDaemon(QObject):
    """Manages a long-lived worker process for a plugin via length-prefixed msgpack IPC."""

    _instances: ClassVar[dict[str, PluginDaemon]] = {}
    _registry_lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(
        self,
        plugin_id: str,
        daemon_script_path: Path | str | None = None,
        parent: QObject | None = None,
    ):
        super().__init__(parent)
        self.plugin_id = plugin_id
        self.daemon_script_path = Path(daemon_script_path) if daemon_script_path else None
        self._proc: subprocess.Popen | None = None
        self._call_lock = threading.Lock()
        self._retry_count = 0
        self._max_retries = 3
        # In-flight frame read state, resumed across successive
        # _read_frame_with_timeout() polls rather than restarted — see that
        # method and _read_bytes_exact() for why this must persist.
        self._read_header_buf = bytearray()
        self._read_payload_buf = bytearray()
        self._read_payload_len: int | None = None

    @classmethod
    def get_instance(
        self,
        plugin_id: str,
        daemon_script_path: Path | str | None = None,
    ) -> PluginDaemon:
        """Get or create the singleton PluginDaemon for a given plugin ID."""
        with PluginDaemon._registry_lock:
            if plugin_id not in PluginDaemon._instances:
                daemon = PluginDaemon(plugin_id, daemon_script_path)
                PluginDaemon._instances[plugin_id] = daemon
            return PluginDaemon._instances[plugin_id]

    @classmethod
    def start_instance(
        self,
        plugin_id: str,
        daemon_script_path: Path | str | None = None,
    ) -> PluginDaemon:
        """Start and ensure readiness of the daemon for a plugin ID."""
        daemon = PluginDaemon.get_instance(plugin_id, daemon_script_path)
        daemon.ensure_started()
        return daemon

    @classmethod
    def stop_instance(self, plugin_id: str) -> None:
        """Stop and unregister the daemon for a plugin ID."""
        with PluginDaemon._registry_lock:
            daemon = PluginDaemon._instances.pop(plugin_id, None)
            if daemon:
                daemon.shutdown()

    def _resolve_plugin_python_executable(self) -> Path:
        """Resolve python interpreter in plugin directory or fall back to sys.executable."""
        plugin_dir = Path.home() / ".biopro" / "plugins" / self.plugin_id
        venv_dir = plugin_dir / ".venv"

        candidates = []
        if sys.platform == "win32":
            candidates.append(venv_dir / "Scripts" / "python.exe")
        else:
            major, minor = sys.version_info.major, sys.version_info.minor
            candidates.append(venv_dir / "bin" / f"python{major}.{minor}")
            candidates.append(venv_dir / "bin" / "python3")

        for c in candidates:
            if c.exists():
                return c

        return Path(sys.executable)

    def _resolve_daemon_script(self) -> Path:
        """Resolve daemon_worker.py path if not explicitly supplied."""
        if self.daemon_script_path and self.daemon_script_path.exists():
            return self.daemon_script_path

        # Check installed plugin directory
        plugin_dir = Path.home() / ".biopro" / "plugins" / self.plugin_id
        candidate = plugin_dir / "src" / "biopro_plugins" / self.plugin_id / "analysis" / "daemon_worker.py"
        if candidate.exists():
            return candidate

        # Try import spec location
        try:
            import importlib.util

            mod_name = f"biopro_plugins.{self.plugin_id}.analysis.daemon_worker"
            spec = importlib.util.find_spec(mod_name)
            if spec and spec.origin:
                return Path(spec.origin)
        except Exception:
            pass

        raise FileNotFoundError(f"Could not locate daemon worker script for plugin '{self.plugin_id}'.")

    def ensure_started(self, timeout: float = 30.0) -> None:
        """Ensure worker subprocess is running and ready."""
        with self._call_lock:
            if self._proc and self._proc.poll() is None:
                return
            self._start_process(timeout=timeout)

    def _start_process(self, timeout: float = 30.0) -> None:
        """Start worker subprocess and wait for startup ready handshake."""
        self._terminate_process()

        python_exe = self._resolve_plugin_python_executable()
        daemon_script = self._resolve_daemon_script()

        logger.info(
            "Starting PluginDaemon process for '%s' using python=%s script=%s",
            self.plugin_id,
            python_exe,
            daemon_script,
        )

        sp_kwargs: dict[str, Any] = {}
        if sys.platform == "win32":
            sp_kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

        env = os.environ.copy()
        env["PYTHONUNBUFFERED"] = "1"

        self._proc = subprocess.Popen(
            [str(python_exe), str(daemon_script)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            **sp_kwargs,
        )

        # Read ready frame from stdout
        ready_frame = self._read_frame_with_timeout(timeout=timeout)
        if not ready_frame or ready_frame.get("status") != "ready":
            stderr_msg = ""
            if self._proc and self._proc.stderr:
                try:
                    stderr_msg = self._proc.stderr.read().decode("utf-8", errors="replace")
                except Exception:
                    pass
            self._terminate_process()
            error_msg = (
                f"PluginDaemon for '{self.plugin_id}' failed ready handshake. "
                f"Virtual Environment connection failed! Frame: {ready_frame}. Stderr: {stderr_msg}"
            )
            logger.critical(error_msg)
            raise RuntimeError(error_msg)

        logger.info("PluginDaemon for '%s' successfully started and ready.", self.plugin_id)

    def _send_frame(self, data: dict) -> None:
        """Write a length-prefixed msgpack frame to subprocess stdin."""
        if not self._proc or not self._proc.stdin:
            raise RuntimeError("Subprocess is not running.")
        payload = msgpack.packb(data, use_bin_type=True)
        length_header = struct.pack(">I", len(payload))
        self._proc.stdin.write(length_header + payload)
        self._proc.stdin.flush()

    def _read_bytes_exact(self, num_bytes: int, timeout: float, buf: bytearray) -> bool:  # noqa: C901, PLR0911, PLR0912
        """Read exactly num_bytes into buf (appended in place) using non-blocking os.read.

        Bytes already read are kept in `buf` across calls instead of being
        discarded when `timeout` elapses — for a frame too large to arrive
        within a single polling slice, a fresh local buffer here used to
        throw away everything read so far every time the deadline hit, and
        the *next* call would then reinterpret bytes from the middle of the
        still-in-flight payload as a brand new frame header. That permanently
        desynced the stream for any response too big to land in one
        `timeout` window (e.g. a multi-file FCS batch result), so the caller
        would just spin until its own outer timeout gave up — even though
        the daemon had already written a valid, complete response.

        Returns True once buf holds num_bytes, False if `timeout` elapsed
        first (buf keeps its partial progress so the next call can resume).
        """
        if not self._proc or not self._proc.stdout:
            return False

        fd = self._proc.stdout.fileno()
        start_time = time.time()

        while len(buf) < num_bytes:
            if self._proc.poll() is not None:
                # Process exited — try one last read for remaining bytes
                try:
                    rlist, _, _ = select.select([fd], [], [], 0.01)
                    if rlist:
                        chunk = os.read(fd, num_bytes - len(buf))
                        if chunk:
                            buf.extend(chunk)
                except Exception:
                    pass
                return len(buf) == num_bytes

            remaining_timeout = timeout - (time.time() - start_time)
            if remaining_timeout <= 0:
                return False

            if sys.platform != "win32":
                rlist, _, _ = select.select([fd], [], [], min(0.05, remaining_timeout))
                if not rlist:
                    continue
                try:
                    chunk = os.read(fd, num_bytes - len(buf))
                    if not chunk:
                        return False
                    buf.extend(chunk)
                except (OSError, ValueError):
                    return False
            else:
                time.sleep(0.01)
                try:
                    chunk = os.read(fd, num_bytes - len(buf))
                    if not chunk:
                        return False
                    buf.extend(chunk)
                except (OSError, ValueError):
                    return False

        return True

    def _read_frame_with_timeout(self, timeout: float) -> dict | None:
        """Read a single length-prefixed msgpack frame from stdout.

        Resumable across calls: partial header/payload bytes read during a
        previous call that didn't complete within its `timeout` slice are
        kept in self._read_header_buf / self._read_payload_buf and continued
        here rather than restarted — see _read_bytes_exact() for why
        restarting corrupts frame alignment for large responses.
        """
        if self._read_payload_len is None:
            if not self._read_bytes_exact(4, timeout, self._read_header_buf):
                return None
            self._read_payload_len = struct.unpack(">I", bytes(self._read_header_buf))[0]

        if not self._read_bytes_exact(self._read_payload_len, timeout, self._read_payload_buf):
            return None

        payload = bytes(self._read_payload_buf)
        self._read_header_buf = bytearray()
        self._read_payload_buf = bytearray()
        self._read_payload_len = None
        return msgpack.unpackb(payload, raw=False)

    def call(  # noqa: C901
        self,
        method: str,
        kwargs: dict[str, Any],
        cancel_poll: Callable[[], bool] | None = None,
        timeout: float = 120.0,
    ) -> dict[str, Any]:
        """Send a job frame to daemon, poll for completion or cancellation."""
        with self._call_lock:
            for retry in range(self._max_retries):
                try:
                    if not self._proc or self._proc.poll() is not None:
                        self._start_process(timeout=30.0)

                    self._send_frame({"method": method, "kwargs": kwargs})
                    start_time = time.time()

                    while True:
                        if cancel_poll and cancel_poll():
                            logger.info("Call '%s' cancelled by caller.", method)
                            try:
                                self._send_frame({"method": "cancel"})
                            except Exception:
                                pass
                            return {"error": "Task cancelled."}

                        if self._proc.poll() is not None:
                            raise RuntimeError("Daemon process terminated unexpectedly.")

                        elapsed = time.time() - start_time
                        if elapsed > timeout:
                            raise TimeoutError(f"Daemon call '{method}' timed out after {timeout}s.")

                        response = self._read_frame_with_timeout(timeout=0.1)
                        if response is not None:
                            return response

                except Exception as exc:
                    logger.warning(
                        "PluginDaemon call '%s' failed (attempt %d/%d): %s",
                        method,
                        retry + 1,
                        self._max_retries,
                        exc,
                    )
                    self._terminate_process()
                    if retry == self._max_retries - 1:
                        return {"error": f"Daemon call failed after {self._max_retries} attempts: {exc}"}

            return {"error": "Daemon call failed."}

    def _terminate_process(self) -> None:
        """Terminate the worker subprocess safely."""
        if self._proc:
            try:
                if self._proc.poll() is None:
                    self._proc.terminate()
                    self._proc.wait(timeout=2.0)
            except Exception:
                try:
                    self._proc.kill()
                except Exception:
                    pass
            finally:
                self._proc = None
        # Any partially-read frame belonged to this process's now-dead pipe.
        self._read_header_buf = bytearray()
        self._read_payload_buf = bytearray()
        self._read_payload_len = None

    def shutdown(self) -> None:
        """Shutdown the daemon gracefully."""
        with self._call_lock:
            if self._proc and self._proc.poll() is None:
                try:
                    self._send_frame({"method": "exit"})
                except Exception:
                    pass
            self._terminate_process()
            logger.info("PluginDaemon for '%s' shut down.", self.plugin_id)
