import json
import os
import subprocess
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from karcytics_sdk.host.sign_plugin import PluginSigner, SecurityValidationError, TrustChain, main
def test_sign_plugin_ignores_gitignored_files(tmp_path):
    """A gitignored file sitting on disk must never end up in the signed
    security ledger just because sign_plugin happened to walk past it.

    This is exactly what happened with a local .claude/settings.json: it got
    hashed and signed on a dev machine, then CI (a clean checkout that never
    had a .claude/ directory at all, since it's gitignored) rejected the
    release as tampered because the file it expected didn't exist.
    """
    signer = PluginSigner()
    signer.dev_dir = tmp_path / "dev"
    signer.private_key_path = signer.dev_dir / "private.key"
    signer.public_key_path = signer.dev_dir / "public.pub"
    signer.delegation_path = signer.dev_dir / "delegation.json"
    signer.init_identity()

    plugin_path = tmp_path / "my_plugin"
    plugin_path.mkdir()
    subprocess.run(["git", "init"], cwd=plugin_path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=plugin_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=plugin_path, check=True)

    (plugin_path / "pyproject.toml").write_text(
        '[project]\nname = "MyPlugin"\nversion = "1.0.0"\n'
        '[tool.karcytics.plugin]\nid = "my_plugin"\nentry_point = "m:f"\n'
        'authors = [{name = "Test", role = "Developer"}]\n'
    )
    (plugin_path / "main.py").write_text("print(1)")
    (plugin_path / ".gitignore").write_text(".claude/\n")

    claude_dir = plugin_path / ".claude"
    claude_dir.mkdir()
    (claude_dir / "settings.json").write_text('{"local": "only"}')

    subprocess.run(["git", "add", "pyproject.toml", "main.py", ".gitignore"], cwd=plugin_path, check=True)

    signer.sign_plugin(plugin_path)

    security_data = json.loads((plugin_path / "security.json").read_text())
    assert not any(".claude" in rel_path for rel_path in security_data["hashes"]), (
        f"gitignored .claude/settings.json leaked into the signed ledger: {security_data['hashes']}"
    )
    assert "main.py" in security_data["hashes"]


def test_project_sign_plugin_missing_files(tmp_path, caplog):
    signer = PluginSigner()
    # Path has no security files — must raise, not fail silently, so a broken
    # or missing developer signature can never let a CI release ship anyway.
    with pytest.raises(SecurityValidationError):
        signer.project_sign_plugin(tmp_path, b"dummy")
    assert "Developer signature (signature.bin) or security ledger is missing. Rejecting pipeline." in caplog.text


def test_project_sign_plugin_success_and_errors(tmp_path, caplog):
    signer = PluginSigner()
    signer.dev_dir = tmp_path / "dev"
    signer.private_key_path = signer.dev_dir / "private.key"
    signer.public_key_path = signer.dev_dir / "public.pub"
    signer.delegation_path = signer.dev_dir / "delegation.json"

    # 1. Init identity
    signer.init_identity()

    # 2. Setup a valid plugin
    plugin_path = tmp_path / "my_plugin"
    plugin_path.mkdir()

    # Manifest
    toml_content = """[project]
name = "MyPlugin"
version = "1.0.0"
[tool.karcytics.plugin]
id = "my_plugin"
entry_point = "m:f"
authors = [{name = "Test", role = "Developer"}]
"""
    (plugin_path / "pyproject.toml").write_text(toml_content)
    (plugin_path / "main.py").write_text("print(1)")

    signer.sign_plugin(plugin_path)

    # 3. Create a Project key
    project_key = ed25519.Ed25519PrivateKey.generate()
    project_pem = project_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )

    # Sign it successfully
    signer.project_sign_plugin(plugin_path, project_pem)
    assert (plugin_path / "project_signature.bin").exists()

    chain = TrustChain.from_file(plugin_path / "trust_chain.json")
    assert len(chain.links) == 1
    # Without delegation, it does not append the runner link.

    # Error: Invalid Project PEM
    with pytest.raises(Exception, match="Unable to load PEM file"):
        signer.project_sign_plugin(plugin_path, b"invalid_pem")
    assert "Failed to load project private key" in caplog.text

    # Error: Security validation failed (tamper with a file) — must raise so
    # the CI step actually fails instead of silently exiting 0 on a plugin
    # whose shipped files no longer match what was signed.
    (plugin_path / "main.py").write_text("tampered")
    with pytest.raises(SecurityValidationError):
        signer.project_sign_plugin(plugin_path, project_pem)
    assert "Security validation failed before project-signing." in caplog.text


def test_delegate_identity(tmp_path, caplog):
    signer = PluginSigner()
    signer.dev_dir = tmp_path / "dev"
    signer.private_key_path = signer.dev_dir / "private.key"
    signer.public_key_path = signer.dev_dir / "public.pub"
    signer.delegation_path = signer.dev_dir / "delegation.json"

    signer.init_identity()

    # Target pub key to sign
    target_key = ed25519.Ed25519PrivateKey.generate()
    target_pub = target_key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    target_file = tmp_path / "target.pub"
    target_file.write_bytes(target_pub)

    # Run delegation (self-signed)
    cwd = os.getcwd()
    os.chdir(tmp_path)  # To write delegation in tmp_path
    try:
        signer.delegate_identity(target_file, "Target Dev")
    finally:
        os.chdir(cwd)

    out_file = tmp_path / "delegation_target_dev.json"
    assert out_file.exists()

    # Delegate with authority key
    auth_key = ed25519.Ed25519PrivateKey.generate()
    auth_pem = auth_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    auth_file = tmp_path / "auth.pem"
    auth_file.write_bytes(auth_pem)

    os.chdir(tmp_path)
    try:
        signer.delegate_identity(target_file, "Target Dev 2", authority_key_path=auth_file)
    finally:
        os.chdir(cwd)

    out_file2 = tmp_path / "delegation_target_dev_2.json"
    assert out_file2.exists()


def test_print_registry_entry(tmp_path, caplog, capsys):
    signer = PluginSigner()
    signer.dev_dir = tmp_path / "dev"
    signer.private_key_path = signer.dev_dir / "private.key"
    signer.public_key_path = signer.dev_dir / "public.pub"

    signer.print_registry_entry()
    assert "No identity found." in caplog.text

    signer.init_identity()
    signer.print_registry_entry()

    captured = capsys.readouterr()
    assert "COPY THIS TO YOUR registry.json" in captured.out


def test_main_cli_routing(tmp_path):
    project_key = ed25519.Ed25519PrivateKey.generate()
    project_pem = project_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    os.environ["TEST_ENV_KEY"] = project_pem

    with patch("karcytics_sdk.host.sign_plugin.PluginSigner") as mock:
        instance = mock.return_value

        # Project sign
        with patch("sys.argv", ["karcytics-sdk", "project-sign", "my_path", "--key-env", "TEST_ENV_KEY"]):
            main()
            instance.project_sign_plugin.assert_called()

        # Delegate
        with patch("sys.argv", ["karcytics-sdk", "delegate", "pub_path", "Dev Name"]):
            main()
            instance.delegate_identity.assert_called()

        # Registry
        with patch("sys.argv", ["karcytics-sdk", "registry"]):
            main()
            instance.print_registry_entry.assert_called()
