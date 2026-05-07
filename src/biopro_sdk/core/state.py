"""Plugin state management for BioPro SDK.

Provides base class for plugin state that integrates with BioPro's
undo/redo history system. Enables serialization and deserialization
of plugin states for workflow persistence.
"""

from __future__ import annotations

from abc import ABC
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class PluginState(ABC):
    """Base state class for plugin analysis state.

    Subclass this in your plugin and use @dataclass for automatic serialization.
    Enables undo/redo integration via BioPro's HistoryManager.

    All fields in your state should be simple types (str, int, float, list, dict)
    to ensure proper serialization. Complex objects should be stored as paths
    or serializable representations.

    Example:
        >>> @dataclass
        ... class MyAnalysisState(PluginState):
        ...     image_path: str = ""
        ...     threshold: float = 0.5
        ...     results: list = None
        ...
        ...     def to_dict(self) -> dict:
        ...         return asdict(self)
        ...
        ...     @classmethod
        ...     def from_dict(cls, data: dict):
        ...         return cls(**data)
    """

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization.

        Returns:
            Dictionary representation of the state
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> PluginState:
        """Reconstruct state from dictionary.

        Args:
            data: Dictionary previously produced by to_dict()

        Returns:
            New instance of this state class
        """
        return cls(**data)
