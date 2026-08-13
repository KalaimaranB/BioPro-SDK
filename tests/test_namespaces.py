import sys


def test_plugin_namespace_isolation():
    """Verify that importing karcytics_sdk.plugin succeeds even when requests is blocked/missing."""
    # Properly back up the pre-existing requests state to prevent other tests from breaking
    original_requests = sys.modules.get("requests")
    sys.modules["requests"] = None
    try:
        import karcytics_sdk.plugin

        # Verify essential developer classes are importable from karcytics_sdk.plugin
        assert hasattr(karcytics_sdk.plugin, "PluginBase")
        assert hasattr(karcytics_sdk.plugin, "PluginState")
        assert hasattr(karcytics_sdk.plugin, "get_logger")
        assert hasattr(karcytics_sdk.plugin, "PrimaryButton")
    finally:
        # Restore the pre-existing requests state perfectly
        if original_requests is None:
            sys.modules.pop("requests", None)
        else:
            sys.modules["requests"] = original_requests


def test_host_namespace_exports():
    """Verify that karcytics_sdk.host exposes host-facing subsystems correctly."""
    import karcytics_sdk.host

    assert hasattr(karcytics_sdk.host, "TrustManager")
    assert hasattr(karcytics_sdk.host, "AIAssistant")
