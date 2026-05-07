"""File I/O utilities for BioPro SDK.

Provides convenient wrappers for JSON serialization and configuration
management for plugins.
"""

import json
import logging
from pathlib import Path
from typing import Any

from .preferences import PreferenceManagerProtocol

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# JSON UTILITIES
# ──────────────────────────────────────────────────────────────────────────────


def load_json(path: str) -> dict[str, Any]:
    """Load JSON from file.

    Args:
        path: File path

    Returns:
        Parsed JSON dictionary

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON is invalid
    """
    with open(path) as f:
        return json.load(f)


def save_json(path: str, data: dict[str, Any], pretty: bool = True) -> None:
    """Save JSON to file.

    Args:
        path: File path
        data: Dictionary to save
        pretty: If True, indent for readability (2 spaces)
    """
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2 if pretty else None)


# ──────────────────────────────────────────────────────────────────────────────
# PLUGIN CONFIGURATION
# ──────────────────────────────────────────────────────────────────────────────


class PluginConfig(PreferenceManagerProtocol):
    """Simple configuration management for plugins.

    Stores settings in JSON in ~/.biopro/plugin_configs/{plugin_id}.json

    This is useful for persisting user settings across sessions, like
    the last used parameters or paths.

    Example:
        >>> config = PluginConfig('my_plugin')
        >>> config.set('threshold', 0.5)
        >>> config.set('last_image_dir', '/path/to/images')
        >>> threshold = config.get('threshold', default=0.0)
        >>> config.save()
    """

    def __init__(self, plugin_id: str):
        """Initialize config manager.

        Args:
            plugin_id: Unique plugin identifier (used for filename)
        """
        self.plugin_id = plugin_id
        self.config_dir = Path.home() / ".biopro" / "plugin_configs"
        self.config_file = self.config_dir / f"{plugin_id}.json"
        self.data: dict[str, Any] = {}
        self.load()

    def load(self) -> None:
        """Load config from disk.

        Called automatically in __init__. Call again to reload from disk.
        """
        if self.config_file.exists():
            try:
                self.data = load_json(str(self.config_file))
            except Exception as e:
                logger.warning(f"Failed to load config for {self.plugin_id}: {e}")
                self.data = {}
        else:
            self.data = {}

    def save(self) -> None:
        """Save config to disk.

        Raises:
            IOError: If file cannot be written
        """
        try:
            save_json(str(self.config_file), self.data)
        except Exception as e:
            logger.error(f"Failed to save config for {self.plugin_id}: {e}")

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key
            value: Configuration value (should be JSON-serializable)
        """
        self.data[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key
            default: Value to return if key doesn't exist

        Returns:
            Configuration value or default
        """
        return self.data.get(key, default)

    def has(self, key: str) -> bool:
        """Check if a key exists.

        Args:
            key: Configuration key

        Returns:
            True if key exists
        """
        return key in self.data

    def clear(self) -> None:
        """Clear all config values (does not delete file until save())."""
        self.data.clear()

    def __getitem__(self, key: str):
        """Get value using dictionary syntax."""
        return self.data[key]

    def __setitem__(self, key: str, value: Any):
        """Set value using dictionary syntax."""
        self.data[key] = value


# Alias for unified preference manager terminology
PluginPreferenceManager = PluginConfig

# ──────────────────────────────────────────────────────────────────────────────
# PLUGIN LOGGING
# ──────────────────────────────────────────────────────────────────────────────


def get_plugin_logger(plugin_id: str) -> logging.Logger:
    """Get a logger for a plugin.

    Args:
        plugin_id: Plugin identifier

    Returns:
        Configured logger with plugin name prefixed to 'biopro.plugins'

    Example:
        >>> logger = get_plugin_logger("my_plugin")
        >>> logger.info("Plugin initialized")  # Logs to "biopro.plugins.my_plugin"
    """
    return logging.getLogger(f"biopro.plugins.{plugin_id}")
