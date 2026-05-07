"""Preference Manager Interface for BioPro SDK."""

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class PreferenceManagerProtocol(Protocol):
    """Standardized interface for preference management.

    This interface ensures that both the Core application and SDK plugins
    have a unified way to interact with preferences, adhering to the
    Dependency Inversion Principle (DIP).
    """

    def load(self) -> None:
        """Load preferences from storage."""
        ...

    def save(self) -> None:
        """Save preferences to storage."""
        ...

    def set(self, key: str, value: Any) -> None:
        """Set a configuration value."""
        ...

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value."""
        ...

    def has(self, key: str) -> bool:
        """Check if a key exists."""
        ...

    def clear(self) -> None:
        """Clear all preference values."""
        ...
