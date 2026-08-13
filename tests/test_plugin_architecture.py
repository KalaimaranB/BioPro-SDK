import pytest

from karcytics_sdk.plugin.context import PluginContext, UndeclaredCapabilityAccess
from karcytics_sdk.plugin.manifest import PluginManifest


def test_plugin_manifest_parsing():
    toml_str = """
    [plugin]
    name = "test-plugin"
    entry_point = "my_module:init"
    sdk_version = ">=2.0"
    requires = ["task_scheduler", "logger"]
    """

    manifest = PluginManifest.from_toml(toml_str)
    assert manifest.name == "test-plugin"
    assert manifest.entry_point == "my_module:init"
    assert manifest.sdk_version == ">=2.0"
    assert "task_scheduler" in manifest.requires
    assert "logger" in manifest.requires
    assert "event_bus" not in manifest.requires


def test_plugin_manifest_missing_section():
    with pytest.raises(ValueError):
        PluginManifest.from_toml("invalid = true")


def test_plugin_context_capability_access():
    manifest = PluginManifest(name="test", entry_point="test:test", sdk_version="1.0", requires=["logger"])

    services = {"logger": object(), "task_scheduler": object()}

    context = PluginContext(services=services, manifest=manifest)

    # Allowed access
    assert context.get("logger") is not None

    # Denied access
    with pytest.raises(UndeclaredCapabilityAccess):
        context.get("task_scheduler")


def test_plugin_context_missing_host_service():
    manifest = PluginManifest(
        name="test", entry_point="test:test", sdk_version="1.0", requires=["logger", "task_scheduler"]
    )

    # Host forgot to provide task_scheduler
    services = {"logger": object()}

    context = PluginContext(services=services, manifest=manifest)

    with pytest.raises(RuntimeError):
        context.get("task_scheduler")
