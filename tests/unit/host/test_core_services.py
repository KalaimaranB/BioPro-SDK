"""Unit tests for biopro_sdk.host.core_services."""

import pytest

from biopro_sdk.host.core_services import CoreServicesClient, CoreServicesServer


@pytest.fixture
def server():
    srv = CoreServicesServer()
    srv.start()
    yield srv
    srv.stop()


def test_registered_method_round_trips(server):
    server.register("echo", lambda kwargs: {"you_said": kwargs.get("msg")})
    client = CoreServicesClient(server.port)

    result = client.call("echo", msg="hello")

    assert result == {"you_said": "hello"}


def test_unregistered_method_raises_on_client(server):
    client = CoreServicesClient(server.port)

    with pytest.raises(RuntimeError, match="No handler registered"):
        client.call("nonexistent_method")


def test_handler_exception_surfaces_as_client_error(server):
    def _boom(kwargs):  # noqa: ARG001
        raise ValueError("core-side failure")

    server.register("boom", _boom)
    client = CoreServicesClient(server.port)

    with pytest.raises(RuntimeError, match="core-side failure"):
        client.call("boom")


def test_unregister_removes_method(server):
    server.register("temp", lambda kwargs: "ok")  # noqa: ARG005
    client = CoreServicesClient(server.port)
    assert client.call("temp") == "ok"

    server.unregister("temp")

    with pytest.raises(RuntimeError, match="No handler registered"):
        client.call("temp")


def test_multiple_methods_dispatch_independently(server):
    server.register("task_scheduler.submit", lambda kwargs: {"task_id": "abc123"})
    server.register("diagnostics.report_error", lambda kwargs: {"received": kwargs.get("message")})
    client = CoreServicesClient(server.port)

    assert client.call("task_scheduler.submit", analyzer="dummy") == {"task_id": "abc123"}
    assert client.call("diagnostics.report_error", message="oops") == {"received": "oops"}


def test_start_is_idempotent():
    srv = CoreServicesServer()
    srv.start()
    port_before = srv.port
    srv.start()  # must not rebind or raise
    assert srv.port == port_before
    srv.stop()


def test_port_raises_before_start():
    srv = CoreServicesServer()
    with pytest.raises(RuntimeError, match="not running"):
        _ = srv.port
