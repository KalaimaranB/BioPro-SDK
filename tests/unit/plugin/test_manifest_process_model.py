"""Unit tests for PluginManifest.process_model — declares whether a plugin
runs in the Hub's own interpreter ("in_process") or in its own subprocess
("isolated"). See karcytics_sdk.plugin.manifest.PluginManifest.
"""

import pytest

from karcytics_sdk.plugin.manifest import PluginManifest


def test_process_model_defaults_to_in_process():
    manifest = PluginManifest(name="demo", entry_point="demo:initialize", sdk_version="2.0")

    assert manifest.process_model == "in_process"


def test_process_model_accepts_isolated():
    manifest = PluginManifest(
        name="demo",
        entry_point="demo:initialize",
        sdk_version="2.0",
        process_model="isolated",
    )

    assert manifest.process_model == "isolated"


def test_process_model_rejects_invalid_value():
    with pytest.raises(ValueError, match="process_model"):
        PluginManifest(
            name="demo",
            entry_point="demo:initialize",
            sdk_version="2.0",
            process_model="some_other_thing",
        )


def test_from_toml_defaults_process_model_when_absent():
    toml_str = """
    [plugin]
    name = "demo"
    entry_point = "demo:initialize"
    sdk_version = "2.0"
    """

    manifest = PluginManifest.from_toml(toml_str)

    assert manifest.process_model == "in_process"


def test_from_toml_reads_declared_process_model():
    toml_str = """
    [plugin]
    name = "demo"
    entry_point = "demo:initialize"
    sdk_version = "2.0"
    process_model = "isolated"
    """

    manifest = PluginManifest.from_toml(toml_str)

    assert manifest.process_model == "isolated"


def test_from_toml_rejects_invalid_process_model():
    toml_str = """
    [plugin]
    name = "demo"
    entry_point = "demo:initialize"
    sdk_version = "2.0"
    process_model = "bogus"
    """

    with pytest.raises(ValueError, match="process_model"):
        PluginManifest.from_toml(toml_str)
