import sys


def test_plugin_namespace_isolation():
    """Verify that importing biopro_sdk.plugin succeeds even when requests is blocked/missing."""
    # Properly back up the pre-existing requests state to prevent other tests from breaking
    original_requests = sys.modules.get('requests')
    sys.modules['requests'] = None
    try:
        import biopro_sdk.plugin
        # Verify essential developer classes are importable from biopro_sdk.plugin
        assert hasattr(biopro_sdk.plugin, "PluginBase")
        assert hasattr(biopro_sdk.plugin, "PluginState")
        assert hasattr(biopro_sdk.plugin, "get_logger")
        assert hasattr(biopro_sdk.plugin, "PrimaryButton")
    finally:
        # Restore the pre-existing requests state perfectly
        if original_requests is None:
            sys.modules.pop('requests', None)
        else:
            sys.modules['requests'] = original_requests

def test_host_namespace_exports():
    """Verify that biopro_sdk.host exposes host-facing subsystems correctly."""
    import biopro_sdk.host
    assert hasattr(biopro_sdk.host, "TrustManager")
    assert hasattr(biopro_sdk.host, "AIAssistant")
