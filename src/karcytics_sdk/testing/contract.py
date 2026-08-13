from pathlib import Path

import pytest

from karcytics_sdk.plugin.context import PluginContext
from karcytics_sdk.plugin.manifest import PluginManifest


class ContractTestBase:
    """Base pytest class for plugin contract testing.

    Plugin authors should subclass this in their test suite and set `PLUGIN_DIR`
    to the path of their plugin root.

    Example:
        class TestMyPluginContract(ContractTestBase):
            PLUGIN_DIR = Path(__file__).parent.parent
    """

    PLUGIN_DIR: Path | None = None

    @pytest.fixture
    def manifest(self) -> PluginManifest:
        if self.PLUGIN_DIR is None:
            pytest.fail("PLUGIN_DIR must be set on the test class.")

        manifest_path = self.PLUGIN_DIR / "plugin.toml"
        if not manifest_path.exists():
            pytest.fail(f"plugin.toml not found at {manifest_path}")

        with open(manifest_path, encoding="utf-8") as f:
            return PluginManifest.from_toml(f.read())

    def test_manifest_is_valid(self, manifest: PluginManifest):
        """Test that the manifest is parsable and contains required fields."""
        assert manifest.name, "Plugin name is missing or empty"
        assert manifest.entry_point, "Entry point is missing or empty"
        assert manifest.sdk_version, "SDK version is missing or empty"

    def test_headless_initialization(self, manifest: PluginManifest):
        """Test that the plugin can initialize in a headless environment without Core."""
        import importlib

        # 1. Create a mocked dictionary of all possible services the plugin could ask for
        # In a real test, you might want to use actual Mock objects for these.
        class MockService:
            pass

        mocked_services = {cap: MockService() for cap in manifest.requires}

        # 2. Build the capability-scoped context
        context = PluginContext(services=mocked_services, manifest=manifest)

        # 3. Resolve entry point
        try:
            module_name, func_name = manifest.entry_point.split(":")
        except ValueError:
            pytest.fail(f"Invalid entry_point format '{manifest.entry_point}'. Expected 'module:function'")

        try:
            module = importlib.import_module(module_name)
            init_func = getattr(module, func_name)
        except Exception as e:
            pytest.fail(f"Failed to load entry point {manifest.entry_point}: {e}")

        # 4. Attempt initialization
        try:
            plugin_instance = init_func(context)
        except Exception as e:
            pytest.fail(f"Plugin failed to initialize headlessly. Ensure it does not rely on global UI/Core state: {e}")

        assert plugin_instance is not None, "Initialization function returned None"
