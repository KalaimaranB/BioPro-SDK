"""Marketplace Sandbox Caching & Asset Verification module for BioPro.

Enforces SOLID Interface Segregation (ISP) by dividing concerns between
remote querying, sandboxed local caching, and cryptographic verification of remote assets.
"""

import abc
import hashlib
import logging
import os
import shutil
import urllib.request
from pathlib import Path


logger = logging.getLogger(__name__)


class IMarketplaceQueryService(abc.ABC):
    """Interface for querying remote plugin metadata and asset stubs."""

    @abc.abstractmethod
    def fetch_plugin_details(self, plugin_id: str) -> dict:
        """Fetch remote plugin metadata (manifest.json)."""
        pass

    @abc.abstractmethod
    def download_asset(self, url: str, target_path: Path) -> Path:
        """Download remote asset securely to target path."""
        pass


class ISandboxCacheService(abc.ABC):
    """Interface for managing the sandbox caching directory structure and lifecycles."""

    @abc.abstractmethod
    def get_cache_path(self, plugin_id: str, asset_type: str, filename: str) -> Path:
        """Get a securely sandboxed path inside ~/.biopro/cache/marketplace/."""
        pass

    @abc.abstractmethod
    def purge_cache(self, plugin_id: str | None = None) -> None:
        """Purge sandbox cache contents for security/cleanup."""
        pass


class IAssetVerifier(abc.ABC):
    """Interface for inspecting and validating downloaded assets against signed hashes."""

    @abc.abstractmethod
    def verify_asset(self, file_path: Path, expected_hash: str) -> bool:
        """Inspect and compare SHA-256 file hash to expected hash.

        Raises AssetVerificationError if hash mismatches.
        """
        pass


class AssetVerificationError(Exception):
    """Raised when a downloaded asset fails cryptographic integrity hash matching."""
    pass


class MarketplaceQueryService(IMarketplaceQueryService):
    """Concrete service for querying marketplace stubs and downloading assets securely."""

    def __init__(self, downloader=None):
        self.downloader = downloader or urllib.request.urlretrieve

    def fetch_plugin_details(self, plugin_id: str) -> dict:
        """Query remote manifest metadata. (Mocked stub for extension)."""
        logger.info(f"Fetching remote details for plugin: {plugin_id}")
        return {"id": plugin_id, "status": "online"}

    def download_asset(self, url: str, target_path: Path) -> Path:
        """Securely fetch a remote image and write it to target sandboxed path."""
        target_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            self.downloader(url, str(target_path))
            return target_path
        except Exception as e:
            logger.error(f"Failed to securely fetch remote asset from {url}: {e}")
            raise IOError(f"Remote Fetch Failed: {str(e)}")


class SandboxCacheService(ISandboxCacheService):
    """Concrete cache manager maintaining safe sandboxed local folder boundaries."""

    def __init__(self, base_dir: Path | None = None):
        if base_dir is None:
            self.base_dir = Path.home() / ".biopro" / "cache" / "marketplace"
        else:
            self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def get_cache_path(self, plugin_id: str, asset_type: str, filename: str) -> Path:
        """Calculates path and asserts that it does not exit the sandbox directory."""
        # Pre-emptively reject relative path traversal tokens
        if ".." in plugin_id or ".." in asset_type or ".." in filename:
            raise ValueError(
                "Directory Traversal Attempt Blocked: Attempting to write outside of the sandboxed cache boundary."
            )

        # Strip path parts to prevent simple relative injections
        safe_plugin_id = Path(plugin_id).name
        safe_asset_type = Path(asset_type).name
        safe_filename = Path(filename).name

        # Resolve path to clean all relative parts
        target_path = (self.base_dir / safe_plugin_id / safe_asset_type / safe_filename).resolve()

        # Enforce Sandbox Directory Boundary Constraint (Block Directory Traversal)
        resolved_base = self.base_dir.resolve()
        if not str(target_path).startswith(str(resolved_base)):
            raise ValueError(
                "Directory Traversal Attempt Blocked: Attempting to write outside of the sandboxed cache boundary."
            )

        return target_path

    def purge_cache(self, plugin_id: str | None = None) -> None:
        """Clears part or all of the marketplace cache to prevent build stale states."""
        if plugin_id:
            safe_plugin_id = Path(plugin_id).name
            target = self.base_dir / safe_plugin_id
            if target.exists():
                shutil.rmtree(target)
        else:
            if self.base_dir.exists():
                shutil.rmtree(self.base_dir)
                self.base_dir.mkdir(parents=True, exist_ok=True)


class AssetVerifier(IAssetVerifier):
    """Concrete validator confirming cryptographic integrity of fetched assets."""

    def __init__(self, on_tampered_callback=None):
        self.on_tampered_callback = on_tampered_callback

    def verify_asset(self, file_path: Path, expected_hash: str) -> bool:
        """Calculates file SHA-256 and asserts match. Fires warning on error."""
        if not file_path.exists():
            return False

        hasher = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        calc_hash = hasher.hexdigest()

        if calc_hash != expected_hash:
            if self.on_tampered_callback:
                self.on_tampered_callback(file_path, calc_hash, expected_hash)
            raise AssetVerificationError(
                f"Asset Cryptographic Tampering Detected: File '{file_path.name}' hash '{calc_hash}' "
                f"does not match expected signed hash '{expected_hash}'."
            )

        return True
