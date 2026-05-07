"""Trust Cache Persistent Storage.

Implements a local database (currently JSON-based for simplicity, but
designed for SQLite) to store the verified state of plugins. Enables
sub-millisecond 'verified' status checks using file modification times.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class TrustCache:
    """High-performance cache for cryptographically verified plugins."""

    def __init__(self, cache_file: Path | None = None):
        """Initialize the cache and load existing trust data."""
        if cache_file:
            self.cache_file = cache_file
        else:
            # Standard secure location (app data directory)
            self.cache_file = Path.home() / ".biopro" / "trust_cache.json"

        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.data: dict[str, dict[str, Any]] = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        """Load cache from disk."""
        if not self.cache_file.exists():
            return {}
        try:
            with open(self.cache_file) as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load trust cache: {e}. Starting fresh.")
            return {}

    def _save(self):
        """Save cache to disk."""
        try:
            with open(self.cache_file, "w") as f:
                json.dump(self.data, f)
        except Exception as e:
            logger.error(f"Failed to save trust cache: {e}")

    def is_trusted(self, plugin_path: Path) -> bool:
        """Check if a plugin folder remains trusted based on its metadata.

        A plugin is trusted if it exists in the cache and its modification
        time (mtime) and folder name match the cached record.
        """
        plugin_id = plugin_path.name
        if plugin_id not in self.data:
            return False

        cached_info = self.data[plugin_id]

        # Security: Also check that the path hasn't moved (optional, but good)
        if cached_info.get("abs_path") != str(plugin_path.absolute()):
            return False

        # Optimization: Check mtime
        current_mtime = self._get_directory_mtime(plugin_path)
        return current_mtime == cached_info.get("last_mtime")

    def mark_as_trusted(self, plugin_path: Path, trust_path: list | None = None):
        """Updates the cache with a newly verified plugin state."""
        plugin_id = plugin_path.name
        self.data[plugin_id] = {
            "abs_path": str(plugin_path.absolute()),
            "last_mtime": self._get_directory_mtime(plugin_path),
            "verified_at": os.path.getmtime(plugin_path),
            "trust_path": trust_path,
        }
        self._save()

    def _get_directory_mtime(self, path: Path) -> float:
        """Calculates the latest modification time for the entire directory recursively.

        This ensures that content changes in files are detected even if the
        directory mtime doesn't update.
        """
        max_mtime = os.path.getmtime(path)
        for root, _, files in os.walk(path):
            if "__pycache__" in root:
                continue
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    max_mtime = max(max_mtime, os.path.getmtime(file_path))
                except OSError:
                    continue
        return max_mtime

    def clear(self):
        """Evict all trust records."""
        self.data = {}
        self._save()
