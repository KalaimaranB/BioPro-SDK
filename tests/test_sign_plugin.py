import os
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from biopro_sdk.host.sign_plugin import PluginSigner, TrustChain, main


def test_project_sign_plugin_missing_files(tmp_path, caplog):
    signer = PluginSigner()
    # Path has no security files
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
[tool.biopro.plugin]
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
    signer.project_sign_plugin(plugin_path, b"invalid_pem")
    assert "Failed to load project private key" in caplog.text

    # Error: Security validation failed (tamper with a file)
    (plugin_path / "main.py").write_text("tampered")
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

    with patch("biopro_sdk.host.sign_plugin.PluginSigner") as mock:
        instance = mock.return_value

        # Project sign
        with patch("sys.argv", ["biopro-sdk", "project-sign", "my_path", "--key-env", "TEST_ENV_KEY"]):
            main()
            instance.project_sign_plugin.assert_called()

        # Delegate
        with patch("sys.argv", ["biopro-sdk", "delegate", "pub_path", "Dev Name"]):
            main()
            instance.delegate_identity.assert_called()

        # Registry
        with patch("sys.argv", ["biopro-sdk", "registry"]):
            main()
            instance.print_registry_entry.assert_called()
