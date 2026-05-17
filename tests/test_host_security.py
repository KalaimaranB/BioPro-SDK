import hashlib
import json
import os
from unittest.mock import patch

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from biopro_sdk.host.docs import PluginDocumentation
from biopro_sdk.host.sign_plugin import sign_plugin
from biopro_sdk.host.trust_manager import TrustManager
from biopro_sdk.host.trust_overrides import LocalTrustRegistry
from biopro_sdk.host.trust_path import TrustChain, TrustLink
from biopro_sdk.host.trust_storage import TrustCache


@pytest.fixture
def temp_sec_env(tmp_path):
    """Setup a pristine local security workspace."""
    biopro_dir = tmp_path / ".biopro"
    biopro_dir.mkdir()

    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path, biopro_dir


def test_trust_manager_root_loading_and_developer_trust(temp_sec_env):
    """Test loading anchors and adding new developer trust dynamically."""
    _, biopro_dir = temp_sec_env

    # 1. Initialize empty trust manager
    tm = TrustManager()
    assert len(tm.trusted_roots) >= 1 # Fallback primary key exists

    # 2. Generate a new developer key to trust
    dev_private = ed25519.Ed25519PrivateKey.generate()
    dev_pub = dev_private.public_key()
    dev_pub_bytes = dev_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    dev_pub_hex = dev_pub_bytes.hex()

    # 3. Trust the developer
    success = tm.trust_developer("Dr. Biotech", dev_pub_hex)
    assert success is True

    # Verify the manual public key file got saved
    pub_file = biopro_dir / "trusted_roots" / "manual_dr._biotech.pub"
    assert pub_file.exists()

    # Reloaded roots must now include it
    assert len(tm.trusted_roots) >= 2


def test_trust_chain_de_serialization(tmp_path):
    """Test parsing and serializing multi-link cryptographic trust chains."""
    link1 = TrustLink(subject_name="Dev", subject_pub="aa", issuer_name="Root", signature="bb")
    link2 = TrustLink(subject_name="Root", subject_pub="cc", issuer_name="BioPro Authority", signature="dd")
    chain = TrustChain(links=[link1, link2])

    # Serialize to file
    chain_file = tmp_path / "trust_chain.json"
    with open(chain_file, "w") as f:
        f.write(chain.to_json())
    assert chain_file.exists()

    # Deserialize back
    loaded_chain = TrustChain.from_file(chain_file)
    assert loaded_chain is not None
    assert len(loaded_chain.links) == 2
    assert loaded_chain.links[0].subject_name == "Dev"
    assert loaded_chain.links[1].signature == "dd"


def test_local_trust_registry(temp_sec_env):
    """Test LocalTrustRegistry is_locally_trusted overrides logic."""
    _, biopro_dir = temp_sec_env
    registry = LocalTrustRegistry()

    hashes = {"main.py": "hash_123"}
    assert registry.is_locally_trusted("my_plugin", hashes) is False

    # Trust locally
    registry.trust_current_state("my_plugin", hashes)
    assert registry.is_locally_trusted("my_plugin", hashes) is True

    # Tamper with hashes
    bad_hashes = {"main.py": "tampered_hash"}
    assert registry.is_locally_trusted("my_plugin", bad_hashes) is False

    # Untrust
    registry.remove_trust("my_plugin")
    assert registry.is_locally_trusted("my_plugin", hashes) is False


def test_trust_cache_operations(temp_sec_env, tmp_path):
    """Test Registry storage and TrustCache speed caching operations."""
    _, biopro_dir = temp_sec_env

    # Create mock plugin folder
    plugin_path = tmp_path / "cached_plugin"
    plugin_path.mkdir()
    (plugin_path / "main.py").write_text("code")

    cache = TrustCache()
    assert cache.is_trusted(plugin_path) is False

    # Cache it
    cache.mark_as_trusted(plugin_path, [{"name": "Developer"}])
    assert cache.is_trusted(plugin_path) is True

    # Clear cache
    cache.clear()
    assert cache.is_trusted(plugin_path) is False


def test_trust_manager_verify_plugin_successful_chain(temp_sec_env, tmp_path):
    """Test verify_plugin against a fully signed cryptographically valid chain."""
    _, biopro_dir = temp_sec_env

    # 1. Generate keys
    root_private = ed25519.Ed25519PrivateKey.generate()
    root_pub = root_private.public_key()

    dev_private = ed25519.Ed25519PrivateKey.generate()
    dev_pub = dev_private.public_key()
    dev_pub_raw = dev_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )

    # 2. Self-sign dev cert via Root (simulate local onboarding root)
    sig_by_root = root_private.sign(dev_pub_raw)

    # Register Root key in TrustManager
    tm = TrustManager(root_public_key=root_pub)

    # 3. Create mock plugin directory
    plugin_dir = tmp_path / "my_valid_plugin"
    plugin_dir.mkdir()

    # Write Python file
    py_file = plugin_dir / "main.py"
    py_file.write_text("class MyPlugin: pass")

    # Calculate sha256 of main.py
    hasher = hashlib.sha256()
    hasher.update(b"class MyPlugin: pass")
    py_hash = hasher.hexdigest()

    # Write manifest
    manifest_data = {
        "id": "my_valid_plugin",
        "name": "My Valid Plugin",
        "version": "1.0.0",
        "description": "Valid Plugin desc",
        "manifest_version": 2,
        "integrity": {
            "hashes": {
                "main.py": py_hash
            }
        }
    }

    # Canonicalize manifest and sign it using dev key
    manifest_bytes = json.dumps(manifest_data, sort_keys=True).encode()
    signature_bytes = dev_private.sign(manifest_bytes)

    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump(manifest_data, f)

    with open(plugin_dir / "signature.bin", "wb") as f:
        f.write(signature_bytes)

    # Write trust chain
    link_dev = TrustLink(
        subject_name="Developer",
        subject_pub=dev_pub_raw.hex(),
        issuer_name="Onboarding Root",
        signature=sig_by_root.hex()
    )
    # The top link is root-signed
    root_pub_raw = root_pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw
    )
    link_root = TrustLink(
        subject_name="Onboarding Root",
        subject_pub=root_pub_raw.hex(),
        issuer_name="BioPro Authority",
        signature=root_private.sign(root_pub_raw).hex() # self-signed root link
    )
    chain = TrustChain(links=[link_dev, link_root])
    with open(plugin_dir / "trust_chain.json", "w") as f:
        f.write(chain.to_json())

    # 4. Verify the plugin
    res = tm.verify_plugin(plugin_dir)
    assert res.success is True
    assert res.trust_level == "verified_developer"
    assert res.trust_path[0]["name"] == "BioPro Core"
    assert res.trust_path[1]["name"] == "Onboarding Root"
    assert res.trust_path[2]["name"] == "Developer"

    # Test cached loading performance path
    cached_res = tm.verify_plugin(plugin_dir)
    assert cached_res.success is True
    assert cached_res.trust_level == "verified_cache"

    # Reset Cache
    tm._get_cache().clear()

    # 5. Tamper testing: alter python file content
    py_file.write_text("class MyPlugin: tampered_code()")
    tampered_res = tm.verify_plugin(plugin_dir)
    assert tampered_res.success is False
    assert "Integrity Mismatch" in tampered_res.error_message

    # Restore py file
    py_file.write_text("class MyPlugin: pass")

    # 6. Unauthorized file testing: add unsigned python file
    unsigned_file = plugin_dir / "unauthorized.py"
    unsigned_file.write_text("print('hacked')")
    unauth_res = tm.verify_plugin(plugin_dir)
    assert unauth_res.success is False
    assert "Unauthorized File" in unauth_res.error_message
    unsigned_file.unlink()

    # 7. Missing file testing: delete main.py
    py_file.unlink()
    missing_res = tm.verify_plugin(plugin_dir)
    assert missing_res.success is False
    assert "Missing File" in missing_res.error_message


def test_plugin_documentation():
    """Verify registry for plugin help documentation."""
    doc = PluginDocumentation()
    doc.register_page("my_plugin", "index", "/path/to/help.md")
    assert doc.get_page("my_plugin", "index") == "/path/to/help.md"
    assert doc.get_page("my_plugin", "other") is None
    assert doc.get_all_pages("my_plugin") == {"index": "/path/to/help.md"}


def test_plugin_signer_missing_files(tmp_path):
    """Test sign_plugin error handling on missing target manifest or keys."""
    with pytest.raises(FileNotFoundError):
        sign_plugin(tmp_path, tmp_path / "key.pem", tmp_path / "cert.bin")


def test_sign_plugin_direct(tmp_path):
    """Test sign_plugin with valid mock manifest and credentials."""
    from biopro_sdk.host.sign_plugin import sign_plugin
    plugin_dir = tmp_path / "my_plugin"
    plugin_dir.mkdir()

    with open(plugin_dir / "manifest.json", "w") as f:
        json.dump({"id": "my_plugin", "author": "me"}, f)

    (plugin_dir / "code.py").write_text("print(1)")

    # Generate Ed25519 private key
    private_key = ed25519.Ed25519PrivateKey.generate()
    key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    priv_path = tmp_path / "key.pem"
    priv_path.write_bytes(key_pem)

    cert_path = tmp_path / "cert.bin"
    cert_path.write_text("mock_certificate_data")

    sign_plugin(plugin_dir, priv_path, cert_path)

    assert (plugin_dir / "signature.bin").exists()
    assert (plugin_dir / "dev_cert.bin").exists()


def test_trust_manager_roots_and_developer(tmp_path):
    """Verify PEM key anchoring, key lengths, and cache clears in TrustManager."""
    from biopro_sdk.host.trust_manager import TrustManager

    with patch("pathlib.Path.home", return_value=tmp_path):
        tm = TrustManager()

        # Test loading a PEM key anchor
        roots_dir = tmp_path / ".biopro" / "trusted_roots"
        roots_dir.mkdir(parents=True, exist_ok=True)

        # Write valid PEM public key to glob
        private_key = ed25519.Ed25519PrivateKey.generate()
        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        (roots_dir / "valid_anchor.pub").write_bytes(pub_pem)

        # Write malformed public key to test exception log
        (roots_dir / "bad_anchor.pub").write_text("malformed key")

        # Reload roots
        tm._load_all_roots()
        assert len(tm.trusted_roots) >= 2 # Core root + valid_anchor

        # Test trust_developer invalid public key length
        assert tm.trust_developer("dev_name", "aabbcc") is False # 3 bytes instead of 32

        # Test trust_developer successfully
        pub_hex = ed25519.Ed25519PrivateKey.generate().public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw
        ).hex()

        assert tm.trust_developer("Dev Name", pub_hex) is True


def test_trust_cache_details(tmp_path):
    """Verify custom cache paths, json decode errors, and mtime comparisons."""
    from biopro_sdk.host.trust_storage import TrustCache

    # 1. Custom cache path
    custom_file = tmp_path / "custom_cache.json"
    cache = TrustCache(cache_file=custom_file)
    assert cache.cache_file == custom_file

    # 2. Decoding error
    custom_file.write_text("invalid json data {")
    broken_cache = TrustCache(cache_file=custom_file)
    assert broken_cache.data == {}

    # 3. Path mismatch
    plugin_path = tmp_path / "plugin"
    plugin_path.mkdir()
    (plugin_path / "main.py").write_text("print(1)")

    cache.mark_as_trusted(plugin_path)
    assert cache.is_trusted(plugin_path) is True

    # Simulate move (abs_path mismatch)
    cache.data["plugin"]["abs_path"] = "/other/path"
    assert cache.is_trusted(plugin_path) is False

    # 4. Save exception trigger
    with patch("builtins.open", side_effect=OSError("Permission denied")):
        cache.clear() # Calls _save internally

    # 5. __pycache__ ignore and OSError
    pycache_dir = plugin_path / "__pycache__"
    pycache_dir.mkdir()
    (pycache_dir / "main.pyc").write_bytes(b"c")

    # Trigger OSError selectively by patching getmtime only on file checks
    real_getmtime = os.path.getmtime
    def mock_getmtime_selective(filepath):
        if str(filepath).endswith("main.py"):
            raise OSError("File missing")
        return real_getmtime(filepath)

    with patch("os.path.getmtime", side_effect=mock_getmtime_selective):
        mtime = cache._get_directory_mtime(plugin_path)
        assert mtime > 0


def test_local_trust_registry_tampering_and_save(tmp_path):
    """Verify local machine trust override storage, signatures, tampering, and save failures."""
    from biopro_sdk.host.trust_overrides import LocalTrustRegistry

    with patch("pathlib.Path.home", return_value=tmp_path):
        # 1. First instantiation generates machine key
        reg = LocalTrustRegistry()
        hashes = {"main.py": "hash123"}
        reg.trust_current_state("plugin_a", hashes)

        # Verify files are saved and signed
        assert reg.storage_path.exists()
        assert reg.signature_path.exists()

        # 2. Reloading in a new registry should succeed and verify signature (covers 51-67)
        reg2 = LocalTrustRegistry()
        assert reg2.is_locally_trusted("plugin_a", hashes) is True

        # 3. Tamper with signature to trigger verification exception (covers 68-72)
        reg2.signature_path.write_bytes(b"bad_signature")
        reg3 = LocalTrustRegistry()
        assert reg3.is_locally_trusted("plugin_a", hashes) is False

        # 4. Delete signature file to trigger exception (covers 56-57)
        reg2.signature_path.unlink()
        reg4 = LocalTrustRegistry()
        assert reg4.is_locally_trusted("plugin_a", hashes) is False

        # 5. Trigger exception in save sign (covers 87-88)
        reg5 = LocalTrustRegistry()
        with patch.object(reg5, "_get_or_create_machine_key", side_effect=Exception("Key failure")):
            reg5.save()

        # 6. Remove trust
        reg5.remove_trust("plugin_a")
        assert reg5.is_locally_trusted("plugin_a", hashes) is False




