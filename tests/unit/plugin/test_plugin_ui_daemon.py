"""Unit tests for biopro_sdk.plugin.daemon.PluginUIDaemon."""

import time
from pathlib import Path
from unittest.mock import patch

import pytest

from biopro_sdk.plugin.daemon import PluginUIDaemon


@pytest.fixture
def mock_ui_daemon_script(tmp_path):
    """Create a temporary Python script that acts as a mock UI daemon worker.

    Speaks the kind-tagged frame protocol (request/response/event) rather than
    the plain PluginDaemon protocol — this is what distinguishes PluginUIDaemon.
    """
    script_path = tmp_path / "mock_ui_worker.py"
    code = """
import sys
import struct
import threading
import time
import msgpack

def write_frame(data):
    payload = msgpack.packb(data, use_bin_type=True)
    header = struct.pack('>I', len(payload))
    sys.stdout.buffer.write(header + payload)
    sys.stdout.buffer.flush()

def read_frame():
    header = sys.stdin.buffer.read(4)
    if not header or len(header) < 4:
        return None
    length = struct.unpack('>I', header)[0]
    payload = sys.stdin.buffer.read(length)
    return msgpack.unpackb(payload, raw=False)

def emit_spontaneous_events():
    # Simulate the plugin's own UI firing tutorial/state events with no
    # request behind them at all, at any time — the thing PluginDaemon's
    # synchronous call() protocol can't represent.
    time.sleep(0.15)
    write_frame({"kind": "event", "topic": "state_changed", "payload": {"n": 1}})

def main():
    write_frame({"kind": "event", "topic": "ready", "payload": {"geometry": [0, 0, 800, 600]}})
    threading.Thread(target=emit_spontaneous_events, daemon=True).start()

    while True:
        frame = read_frame()
        if not frame:
            break
        method = frame.get("method")
        request_id = frame.get("request_id")
        kwargs = frame.get("kwargs", {})

        if method == "exit":
            break
        elif method == "ping":
            write_frame({"kind": "response", "request_id": request_id, "payload": {"status": "pong"}})
        elif method == "echo":
            write_frame({
                "kind": "response",
                "request_id": request_id,
                "payload": {"echo": kwargs.get("msg")},
            })
        elif method == "slow_echo":
            time.sleep(kwargs.get("delay", 0.3))
            write_frame({
                "kind": "response",
                "request_id": request_id,
                "payload": {"echo": kwargs.get("msg")},
            })
        else:
            write_frame({
                "kind": "response",
                "request_id": request_id,
                "payload": {"error": f"Unknown method {method}"},
            })

if __name__ == "__main__":
    main()
"""
    script_path.write_text(code, encoding="utf-8")
    return script_path


def test_ui_daemon_singleton_and_ready_handshake(mock_ui_daemon_script):
    plugin_id = "test_ui_plugin_singleton"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)
    assert daemon is PluginUIDaemon.get_instance(plugin_id)

    res = daemon.call("ping", {})
    assert res == {"status": "pong"}

    PluginUIDaemon.stop_instance(plugin_id)
    assert daemon._proc is None


def test_ui_daemon_call_request_response(mock_ui_daemon_script):
    plugin_id = "test_ui_plugin_echo"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)

    res = daemon.call("echo", {"msg": "hello"})
    assert res == {"echo": "hello"}

    PluginUIDaemon.stop_instance(plugin_id)


def test_ui_daemon_dispatches_unsolicited_event(mock_ui_daemon_script):
    """The worker fires a state_changed event with no request behind it at all —
    event_received must still deliver it, proving the reader thread dispatches
    events independent of whether anything is blocked in call().
    """
    plugin_id = "test_ui_plugin_events"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)

    received = []
    daemon.event_received.connect(lambda topic, payload: received.append((topic, payload)))

    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not received:
        from PyQt6.QtWidgets import QApplication

        QApplication.processEvents()
        time.sleep(0.02)

    assert received == [("state_changed", {"n": 1})]

    PluginUIDaemon.stop_instance(plugin_id)


def test_ui_daemon_concurrent_calls_do_not_block_each_other(mock_ui_daemon_script):
    """Unlike PluginDaemon (single _call_lock serializes every call), PluginUIDaemon
    must let a fast call return while a slow one is still in flight — each call
    gets its own request_id and its own response queue off the shared reader.
    """
    plugin_id = "test_ui_plugin_concurrent"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)

    results: dict[str, dict] = {}

    def call_slow():
        results["slow"] = daemon.call("slow_echo", {"msg": "slow", "delay": 0.4}, timeout=5.0)

    import threading

    t = threading.Thread(target=call_slow)
    t.start()

    time.sleep(0.05)  # let the slow call's request land first
    fast_result = daemon.call("ping", {}, timeout=5.0)
    t.join(timeout=5.0)

    assert fast_result == {"status": "pong"}
    assert results["slow"] == {"echo": "slow"}

    PluginUIDaemon.stop_instance(plugin_id)


def test_ui_daemon_call_timeout_raises(mock_ui_daemon_script):
    plugin_id = "test_ui_plugin_timeout"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)

    with pytest.raises(TimeoutError):
        daemon.call("slow_echo", {"msg": "x", "delay": 2.0}, timeout=0.2)

    PluginUIDaemon.stop_instance(plugin_id)


def test_ui_daemon_send_event_is_fire_and_forget(mock_ui_daemon_script):
    """send_event() (e.g. theme_changed) must not block waiting for a reply —
    the worker script here never answers events, only requests.
    """
    plugin_id = "test_ui_plugin_send_event"
    daemon = PluginUIDaemon.start_instance(plugin_id, daemon_script_path=mock_ui_daemon_script)

    daemon.send_event("theme_changed", {"theme": "dark"})

    # The connection must still be healthy afterward.
    assert daemon.call("ping", {}) == {"status": "pong"}

    PluginUIDaemon.stop_instance(plugin_id)


def test_resolve_daemon_script_finds_plugin_root_layout(tmp_path):
    """Older plugins (manifest_version 2, no src/biopro_plugins/<id>/ tree —
    e.g. Synthetic Biology) keep everything at the plugin's own root next to
    manifest.json/__init__.py. ui_daemon.py must be discoverable there too,
    not just under the newer src/ layout Flow Cytometry uses.
    """
    plugin_id = "test_root_layout_plugin"
    plugin_dir = tmp_path / ".biopro" / "plugins" / plugin_id
    plugin_dir.mkdir(parents=True)
    root_script = plugin_dir / "ui_daemon.py"
    root_script.write_text("# not executed by this test")

    daemon = PluginUIDaemon(plugin_id)
    with patch.object(Path, "home", return_value=tmp_path):
        resolved = daemon._resolve_daemon_script()

    assert resolved == root_script


def test_resolve_daemon_script_prefers_src_layout_when_both_exist(tmp_path):
    plugin_id = "test_both_layouts_plugin"
    plugin_dir = tmp_path / ".biopro" / "plugins" / plugin_id
    src_dir = plugin_dir / "src" / "biopro_plugins" / plugin_id
    src_dir.mkdir(parents=True)
    src_script = src_dir / "ui_daemon.py"
    src_script.write_text("# not executed by this test")
    (plugin_dir / "ui_daemon.py").write_text("# not executed by this test")

    daemon = PluginUIDaemon(plugin_id)
    with patch.object(Path, "home", return_value=tmp_path):
        resolved = daemon._resolve_daemon_script()

    assert resolved == src_script
