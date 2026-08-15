"""Unit tests for RemoteCapabilityProxy — lets an isolated plugin process treat
a CoreServicesClient-backed service exactly like the live object it would have
received via PluginContext(services=...) when running in-process.
"""

import pytest

from karcytics_sdk.host.core_services import (
    CoreServicesClient,
    CoreServicesServer,
    RemoteCapabilityProxy,
)
from karcytics_sdk.plugin.context import PluginContext
from karcytics_sdk.plugin.manifest import PluginManifest


@pytest.fixture
def server():
    srv = CoreServicesServer()
    srv.start()
    yield srv
    srv.stop()


def test_proxy_forwards_method_call_with_capability_prefix(server):
    server.register("diagnostics.report_error", lambda kwargs: {"received": kwargs.get("message")})
    client = CoreServicesClient(server.port, token=server.token)
    proxy = RemoteCapabilityProxy(client, "diagnostics")

    result = proxy.report_error(message="oops")

    assert result == {"received": "oops"}


def test_proxy_raises_when_no_handler_registered(server):
    client = CoreServicesClient(server.port, token=server.token)
    proxy = RemoteCapabilityProxy(client, "theme")

    with pytest.raises(RuntimeError, match="No handler registered"):
        proxy.get_colors()


def test_proxy_distinguishes_capability_namespace(server):
    """Two proxies for different capabilities must not be able to reach each
    other's methods — the capability name is a real namespace prefix, not
    just a label.
    """
    server.register("task_scheduler.submit", lambda kwargs: "submitted")  # noqa: ARG005
    client = CoreServicesClient(server.port, token=server.token)
    diagnostics_proxy = RemoteCapabilityProxy(client, "diagnostics")

    with pytest.raises(RuntimeError, match="No handler registered"):
        diagnostics_proxy.submit()


def test_proxy_usable_as_plugin_context_capability(server):
    """An isolated plugin's PluginContext.get(capability) should hand back
    something that works exactly like the in-process live object did —
    the proxy is a drop-in services[...] value, not a special case.
    """
    server.register("diagnostics.report_error", lambda kwargs: {"received": kwargs.get("message")})
    client = CoreServicesClient(server.port, token=server.token)
    proxy = RemoteCapabilityProxy(client, "diagnostics")

    manifest = PluginManifest(
        name="demo",
        entry_point="demo:initialize",
        sdk_version="2.0",
        requires=["diagnostics"],
        process_model="isolated",
    )
    context = PluginContext(services={"diagnostics": proxy}, manifest=manifest)

    result = context.get("diagnostics").report_error(message="boom")

    assert result == {"received": "boom"}
