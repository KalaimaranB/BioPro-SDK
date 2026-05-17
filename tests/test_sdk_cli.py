import json
import sys
from unittest.mock import MagicMock, patch

import pytest

from biopro_sdk.sdk_cli import SDKCLI, main


@pytest.fixture
def temp_biopro_home(tmp_path):
    """Provide a mock user home directory for .biopro storage."""
    biopro_dir = tmp_path / ".biopro"
    biopro_dir.mkdir()

    # Mocking SDKCLI attributes to use the temp dir
    with patch("pathlib.Path.home", return_value=tmp_path):
        cli = SDKCLI()
        cli.biopro_dir = biopro_dir
        cli.trusted_roots_dir = biopro_dir / "trusted_roots"
        yield cli


def test_cli_init_identity_local(temp_biopro_home):
    """Test bootstrapping local developer identity keypairs and cert stubs."""
    cli = temp_biopro_home

    success = cli.init_identity(is_project=False)
    assert success is True

    # Check generated assets
    assert (cli.trusted_roots_dir / "onboarding_root.pub").exists()
    assert (cli.biopro_dir / "dev_private_key.pem").exists()
    assert (cli.biopro_dir / "dev_cert.bin").exists()


def test_cli_init_identity_project_missing_key(temp_biopro_home):
    """Test project (CI) mode when private key is not present."""
    cli = temp_biopro_home

    # Missing private key PEM
    success = cli.init_identity(is_project=True)
    assert success is False
    assert not (cli.biopro_dir / "dev_cert.bin").exists()


def test_cli_init_identity_project_success(temp_biopro_home):
    """Test project (CI) mode when private key is pre-injected by secrets."""
    cli = temp_biopro_home

    # Generate a key first to act as CI injected PEM
    cli.init_identity(is_project=False)

    # Backup cert bin
    cert_file = cli.biopro_dir / "dev_cert.bin"
    cert_file.unlink()

    # Run in project mode
    success = cli.init_identity(is_project=True)
    assert success is True
    assert cert_file.exists()


def test_cli_sign_plugin_missing_identity(temp_biopro_home, tmp_path):
    """Test plugin signing fails if no developer identity is configured."""
    cli = temp_biopro_home
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()

    success = cli.sign_plugin(str(plugin_dir))
    assert success is False


def test_cli_sign_plugin_missing_manifest(temp_biopro_home, tmp_path):
    """Test plugin signing fails if target plugin lacks manifest.json."""
    cli = temp_biopro_home
    cli.init_identity(is_project=False)  # Setup identity

    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()

    success = cli.sign_plugin(str(plugin_dir))
    assert success is False


def test_cli_sign_plugin_success(temp_biopro_home, tmp_path):
    """Test successful Merkle-integrity calculation and Ed25519 signing."""
    cli = temp_biopro_home
    cli.init_identity(is_project=False)  # Setup identity

    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()

    # Create manifest
    manifest_data = {
        "id": "my_plugin",
        "name": "My Plugin",
        "version": "1.0.0",
        "description": "A scientific tool",
        "author": "Dr. Biotech",  # Legacy V1 field to test migration
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f)

    # Add dummy code files to test Merkle-hashing
    code_file = plugin_dir / "analysis.py"
    code_file.write_text("print('hello')")

    # Ignore list files should not be hashed
    (plugin_dir / ".venv").mkdir()
    (plugin_dir / "signature.bin").write_text("old_sig")

    # Sign
    success = cli.sign_plugin(str(plugin_dir))
    assert success is True

    # Verify signature and certificate are written
    assert (plugin_dir / "signature.bin").exists()
    assert (plugin_dir / "dev_cert.bin").exists()

    # Verify manifest was migrated to V2 schema with integrity hash blocks
    with open(plugin_dir / "manifest.json") as f:
        manifest = json.load(f)

    assert manifest["manifest_version"] == 2
    assert "integrity" in manifest
    assert "hashes" in manifest["integrity"]
    assert "analysis.py" in manifest["integrity"]["hashes"]
    assert "signature.bin" not in manifest["integrity"]["hashes"]  # Ignored
    assert manifest["authors"] == [{"name": "Dr. Biotech"}]  # Migrated


def test_cli_sign_all(temp_biopro_home, tmp_path):
    """Test batch signing inside parent directories."""
    cli = temp_biopro_home

    # Try non-existent directory
    assert cli.sign_all("/non_existent_folder") is False

    # Compliant structure
    cli.init_identity(is_project=False)
    parent_dir = tmp_path / "plugins"
    parent_dir.mkdir()

    p1 = parent_dir / "p1"
    p1.mkdir()
    with open(p1 / "manifest.json", "w") as f:
        json.dump({"id": "p1", "name": "P1", "version": "1.0", "description": "desc"}, f)

    success = cli.sign_all(str(parent_dir))
    assert success is True
    assert (p1 / "signature.bin").exists()


def test_cli_generate_sbom(temp_biopro_home):
    """Test SBOM generation commands."""
    cli = temp_biopro_home

    # Outer non-core environment
    success = cli.generate_sbom("--markdown")
    assert success is False

    # Mocking inner core imports
    mock_generator = MagicMock()
    mock_generator.to_json.return_value = '{"packages": []}'
    mock_generator.to_markdown.return_value = "# SBOM"

    mock_module = MagicMock(SBOMGenerator=MagicMock(return_value=mock_generator))

    with patch.dict(sys.modules, {"biopro.core.sbom": mock_module}):
        assert cli.generate_sbom("--json") is True
        mock_generator.to_json.assert_called_once()

        assert cli.generate_sbom("--markdown") is True
        mock_generator.to_markdown.assert_called_once()


def test_cli_evaluate_plugin_non_existent(temp_biopro_home):
    """Verify evaluation fails gracefully on non-existent paths."""
    cli = temp_biopro_home
    assert cli.evaluate_plugin("/invalid_path_evaluation") is False


def test_cli_evaluate_plugin_failures(temp_biopro_home, tmp_path):
    """Verify evaluation catches missing manifests, invalid JSON, or missing code."""
    cli = temp_biopro_home
    plugin_dir = tmp_path / "bad_plugin"
    plugin_dir.mkdir()

    # Case 1: Missing manifest
    assert cli.evaluate_plugin(str(plugin_dir)) is False

    # Case 2: Invalid JSON manifest
    manifest_file = plugin_dir / "manifest.json"
    manifest_file.write_text("invalid_json{")
    assert cli.evaluate_plugin(str(plugin_dir)) is False

    # Case 3: Valid JSON but missing required fields
    manifest_file.write_text('{"id": "bad"}')
    assert cli.evaluate_plugin(str(plugin_dir)) is False

    # Case 4: Missing python source files
    manifest_file.write_text(
        '{"id": "bad", "name": "Bad", "version": "1.0", "description": "desc", "authors": [{"name": "A"}], "signed_by": {"entity_id": "1"}, "manifest_version": 2}'
    )
    assert cli.evaluate_plugin(str(plugin_dir)) is False


def test_cli_evaluate_plugin_success_and_warns(temp_biopro_home, tmp_path):
    """Verify compliance checks for compliant and semi-compliant plugins."""
    cli = temp_biopro_home
    plugin_dir = tmp_path / "good_plugin"
    plugin_dir.mkdir()

    manifest_data = {
        "id": "good_plugin_id",
        "name": "Good Plugin",
        "version": "1.0.0",
        "description": "A scientific tool",
        "manifest_version": 2,
        "authors": [{"name": "Lead Researcher"}],
        "signed_by": {"entity_type": "developer", "entity_id": "local_dev"},
        "dependencies": {
            "numpy": "1.23.0",  # pinned dependency
            "pandas": ">=1.5.0",  # non-pinned warning trigger
        },
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f)

    code_file = plugin_dir / "main.py"
    code_file.write_text("class MyAnalyzer(AnalysisBase): pass")

    # Unsigned status warnings (still yields True because failed_checks == 0)
    assert cli.evaluate_plugin(str(plugin_dir)) is True

    # Now sign the plugin to assert Green verification status
    cli.init_identity(is_project=False)
    cli.sign_plugin(str(plugin_dir))

    assert cli.evaluate_plugin(str(plugin_dir)) is True


@patch("biopro_sdk.sdk_cli.sys.exit")
def test_main_subparsers_routing(mock_exit, temp_biopro_home):
    """Test argparse CLI routing parameters and exit code handling."""
    mock_cli = MagicMock()
    mock_cli.init_identity.return_value = True

    # Setup commands
    with patch("biopro_sdk.sdk_cli.SDKCLI", return_value=mock_cli):
        with patch.object(sys, "argv", ["biopro-sdk", "init-identity", "--project"]):
            main()
            mock_cli.init_identity.assert_called_once_with(is_project=True)
            mock_exit.assert_called_with(0)


@patch("biopro_sdk.sdk_cli.sys.exit")
def test_main_legacy_shim(mock_exit, temp_biopro_home):
    """Verify that legacy 'sdk' keyword prefix is captured and stripped with a warning."""
    mock_cli = MagicMock()
    mock_cli.init_identity.return_value = True

    with patch("biopro_sdk.sdk_cli.SDKCLI", return_value=mock_cli):
        # Programmatically feed biopro-sdk sdk init-identity
        with patch.object(sys, "argv", ["biopro-sdk", "sdk", "init-identity"]):
            main()
            mock_cli.init_identity.assert_called_once_with(is_project=False)
            mock_exit.assert_called_with(0)


@patch("biopro_sdk.sdk_cli.sys.exit")
def test_main_routing_failure_exit_code(mock_exit, temp_biopro_home):
    """Verify failure exits return non-zero exit codes to environment."""
    mock_cli = MagicMock()
    mock_cli.evaluate_plugin.return_value = False

    with patch("biopro_sdk.sdk_cli.SDKCLI", return_value=mock_cli):
        with patch.object(sys, "argv", ["biopro-sdk", "evaluate", "/bad_path"]):
            main()
            mock_cli.evaluate_plugin.assert_called_once_with("/bad_path")
            mock_exit.assert_called_with(1)


def test_cli_init_identity_exception(temp_biopro_home):
    """Verify init_identity catches file writing exceptions elegantly."""
    cli = temp_biopro_home
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        success = cli.init_identity(is_project=False)
        assert success is False


def test_cli_sign_plugin_json_error(temp_biopro_home, tmp_path):
    """Verify sign_plugin handles corrupted manifest files."""
    cli = temp_biopro_home
    cli.init_identity(is_project=False)

    plugin_dir = tmp_path / "broken_plugin"
    plugin_dir.mkdir()
    (plugin_dir / "manifest.json").write_text("corrupt_json{")

    assert cli.sign_plugin(str(plugin_dir)) is False


def test_cli_sign_all_failures(temp_biopro_home, tmp_path):
    """Verify sign_all returns False if any child plugin signing fails."""
    cli = temp_biopro_home
    cli.init_identity(is_project=False)

    parent_dir = tmp_path / "plugins"
    parent_dir.mkdir()

    # Plugin 1: Valid
    p1 = parent_dir / "p1"
    p1.mkdir()
    with open(p1 / "manifest.json", "w") as f:
        json.dump({"id": "p1", "name": "P1", "version": "1.0", "description": "desc"}, f)

    # Plugin 2: Broken
    p2 = parent_dir / "p2"
    p2.mkdir()
    (p2 / "manifest.json").write_text("bad_json")

    assert cli.sign_all(str(parent_dir)) is True


def test_cli_evaluate_plugin_edge_cases(temp_biopro_home, tmp_path):
    """Test evaluate_plugin's compliance checker edge cases."""
    cli = temp_biopro_home
    plugin_dir = tmp_path / "eval_plugin"
    plugin_dir.mkdir()

    # 1. Manifest has "signed_by" but signature.bin doesn't exist (triggers warning status - Yellow, returns True)
    manifest_data = {
        "id": "eval_plugin",
        "name": "Eval",
        "version": "1.0.0",
        "description": "desc",
        "manifest_version": 2,
        "authors": [{"name": "A"}],
        "signed_by": {"entity_id": "me"},
    }
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f)

    # Add code.py so it passes standard file presence check
    (plugin_dir / "main.py").write_text("print(1)")

    assert cli.evaluate_plugin(str(plugin_dir)) is True

    # 2. Cryptographic signatures present, but manifest integrity block is missing (triggers hard RED status, returns False)
    (plugin_dir / "signature.bin").write_text("dummy_sig")
    (plugin_dir / "dev_cert.bin").write_text("dummy_cert")
    assert cli.evaluate_plugin(str(plugin_dir)) is False

    # Clean up signature files for next tests
    (plugin_dir / "signature.bin").unlink()
    (plugin_dir / "dev_cert.bin").unlink()

    # 3. Missing required V2 manifest keys (triggers hard RED status, returns False)
    manifest_data_no_authors = manifest_data.copy()
    del manifest_data_no_authors["authors"]
    del manifest_data_no_authors["signed_by"]
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data_no_authors, f)
    assert cli.evaluate_plugin(str(plugin_dir)) is False

    # 4. No Python source files (triggers hard RED status, returns False)
    (plugin_dir / "main.py").unlink()
    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f)
    assert cli.evaluate_plugin(str(plugin_dir)) is False


@patch("biopro_sdk.sdk_cli.sys.exit")
def test_main_subparsers_all_routes(mock_exit):
    """Test all argparse subparser commands map correctly to SDKCLI functions."""
    mock_cli = MagicMock()
    mock_cli.init_identity.return_value = True
    mock_cli.sign_plugin.return_value = True
    mock_cli.sign_all.return_value = True
    mock_cli.evaluate_plugin.return_value = True
    mock_cli.generate_sbom.return_value = True

    with patch("biopro_sdk.sdk_cli.SDKCLI", return_value=mock_cli):
        # 1. Sign
        with patch.object(sys, "argv", ["biopro-sdk", "sign", "/path"]):
            main()
            mock_cli.sign_plugin.assert_called_with("/path")

        # 2. Sign All
        with patch.object(sys, "argv", ["biopro-sdk", "sign-all", "/path"]):
            main()
            mock_cli.sign_all.assert_called_with("/path")

        # 3. Evaluate
        with patch.object(sys, "argv", ["biopro-sdk", "evaluate", "/path"]):
            main()
            mock_cli.evaluate_plugin.assert_called_with("/path")

        # 4. SBOM json
        with patch.object(sys, "argv", ["biopro-sdk", "sbom", "--json"]):
            main()
            mock_cli.generate_sbom.assert_called_with("--json")
