from unittest.mock import patch

import pytest

from biopro_sdk.testing.contract import ContractTestBase


# Dummy module for importlib mock
class DummyModule:
    @staticmethod
    def initialize(context):
        return "dummy_plugin_instance"


@pytest.fixture(autouse=True)
def mock_importlib():
    with patch("importlib.import_module", return_value=DummyModule) as mock:
        yield mock


# Test a subclass that defines a valid plugin dir
def test_contract_subclass_execution(tmp_path):
    # 1. Create a dummy manifest
    plugin_dir = tmp_path / "valid_plugin"
    plugin_dir.mkdir()
    manifest_toml = """
[project]
name = "MyPlugin"
version = "1.0.0"

[plugin]
id = "my_plugin"
entry_point = "dummy_module:initialize"
min_core_version = "1.0.0"
"""
    (plugin_dir / "plugin.toml").write_text(manifest_toml)

    # 2. Subclass the base
    class TestMyPluginContract(ContractTestBase):
        PLUGIN_DIR = plugin_dir

    # 3. Pytest will execute these automatically if we run it as a normal test file,
    # but to test it here explicitly:
    tester = TestMyPluginContract()

    # We must use pytest mechanics or just call the fixture manually by passing the mock
    class DummyRequest:
        pass

    from biopro_sdk.plugin.manifest import PluginManifest

    manifest = PluginManifest.from_toml(manifest_toml)

    # Run the tests
    tester.test_manifest_is_valid(manifest)
    tester.test_headless_initialization(manifest)


def test_contract_missing_dir():
    class TestBadPluginContract(ContractTestBase):
        pass

    tester = TestBadPluginContract()
    with pytest.raises(pytest.fail.Exception):
        tester.manifest()


def test_contract_missing_file(tmp_path):
    class TestBadPluginContract(ContractTestBase):
        PLUGIN_DIR = tmp_path

    tester = TestBadPluginContract()
    with pytest.raises(pytest.fail.Exception):
        tester.manifest()
