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


def test_plugin_manifest_parsing_from_pyproject():
    """Current plugins ship pyproject.toml's [tool.karcytics.plugin], not plugin.toml."""
    toml_str = """
    [project]
    name = "synthetic-biology-module"

    [tool.karcytics.plugin]
    id = "synthetic_biology"
    name = "Synthetic Biology Module"
    entry_point = "karcytics_plugins.synthetic_biology:initialize"
    min_core_version = "2.0.0"
    process_model = "isolated"
    requires = ["task_scheduler", "logger", "event_bus"]
    """

    manifest = PluginManifest.from_pyproject_toml(toml_str)
    assert manifest.name == "Synthetic Biology Module"
    assert manifest.entry_point == "karcytics_plugins.synthetic_biology:initialize"
    assert manifest.sdk_version == "2.0.0"
    assert manifest.process_model == "isolated"
    assert "task_scheduler" in manifest.requires
    assert "event_bus" in manifest.requires


def test_plugin_manifest_pyproject_missing_section():
    with pytest.raises(ValueError):
        PluginManifest.from_pyproject_toml('[project]\nname = "x"\n')


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
