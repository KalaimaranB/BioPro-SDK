import pytest

from biopro_sdk.host.marketplace_cache import (
    AssetVerificationError,
    AssetVerifier,
    MarketplaceQueryService,
    SandboxCacheService,
)


def test_marketplace_query_service(tmp_path):
    def mock_downloader(url, path):
        with open(path, "w") as f:
            f.write("downloaded_data")

    service = MarketplaceQueryService(downloader=mock_downloader)
    details = service.fetch_plugin_details("test_plugin")
    assert details["id"] == "test_plugin"

    target = tmp_path / "test.txt"
    service.download_asset("http://example.com/asset", target)
    assert target.exists()
    assert target.read_text() == "downloaded_data"

    # Test download error
    def failing_downloader(url, path):
        raise ValueError("Failed")

    service_fail = MarketplaceQueryService(downloader=failing_downloader)
    with pytest.raises(OSError, match="Remote Fetch Failed: Failed"):
        service_fail.download_asset("http://example.com/asset", tmp_path / "fail.txt")


def test_sandbox_cache_service(tmp_path):
    service = SandboxCacheService(base_dir=tmp_path)

    # Normal path
    path = service.get_cache_path("plugin1", "images", "icon.png")
    assert str(path).startswith(str(tmp_path.resolve()))

    # Traversal attempt in arguments
    with pytest.raises(ValueError, match="Directory Traversal Attempt Blocked"):
        service.get_cache_path("../plugin1", "images", "icon.png")

    # Purge specific plugin
    path.parent.mkdir(parents=True)
    path.write_text("data")
    assert path.exists()
    service.purge_cache("plugin1")
    assert not path.exists()

    # Purge all
    path2 = service.get_cache_path("plugin2", "images", "icon.png")
    path2.parent.mkdir(parents=True)
    path2.write_text("data")
    service.purge_cache()
    assert not path2.exists()


def test_asset_verifier(tmp_path):
    # Create dummy file
    test_file = tmp_path / "test.bin"
    test_file.write_text("dummy content")

    import hashlib

    hasher = hashlib.sha256()
    hasher.update(b"dummy content")
    expected_hash = hasher.hexdigest()

    cb_called = False

    def tampered_cb(path, calc, expected):
        nonlocal cb_called
        cb_called = True

    verifier = AssetVerifier(on_tampered_callback=tampered_cb)

    # Missing file
    assert verifier.verify_asset(tmp_path / "missing.bin", expected_hash) is False

    # Good file
    assert verifier.verify_asset(test_file, expected_hash) is True
    assert not cb_called

    # Tampered file
    with pytest.raises(AssetVerificationError):
        verifier.verify_asset(test_file, "wrong_hash")

    assert cb_called
