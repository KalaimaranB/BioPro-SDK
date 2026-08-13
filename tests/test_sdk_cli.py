from pathlib import Path
from unittest.mock import patch

from karcytics_sdk.cli.commands import migrate, scaffold, security


class DummyArgs:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


@patch("karcytics_sdk.cli.commands.security.PluginSigner")
def test_security_init(mock_signer_class):
    mock_signer = mock_signer_class.return_value
    args = DummyArgs()
    assert security.init_identity(args) is True
    mock_signer.init_identity.assert_called_once()


@patch("karcytics_sdk.cli.commands.security.PluginSigner")
def test_security_sign(mock_signer_class):
    mock_signer = mock_signer_class.return_value
    args = DummyArgs(plugin_dir="/test")
    assert security.sign_plugin(args) is True
    mock_signer.sign_plugin.assert_called_once_with(Path("/test"))


def test_scaffold_create_manifest(tmp_path):
    plugin_dir = tmp_path / "my_plugin"
    args = DummyArgs(plugin_dir=str(plugin_dir), id=None, name=None, version=None, desc=None)
    assert scaffold.create_manifest(args) is True
    assert (plugin_dir / "pyproject.toml").exists()


def test_scaffold_bootstrap(tmp_path):
    plugin_dir = tmp_path / "my_plugin"
    args = DummyArgs(plugin_dir=str(plugin_dir))
    assert scaffold.bootstrap_plugin(args) is True
    assert (plugin_dir / "pyproject.toml").exists()
    assert (plugin_dir / "src" / "__init__.py").exists()


def test_migrate_missing(tmp_path):
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()
    args = DummyArgs(plugin_dir=str(plugin_dir))
    assert migrate.migrate_plugin(args) is False


@patch("karcytics_sdk.cli.main.sys.exit")
def test_main_cli(mock_exit):
    from karcytics_sdk.cli.main import main

    with patch("sys.argv", ["karcytics-sdk", "doctor", "/path"]):
        main()
        mock_exit.assert_called_with(0)
