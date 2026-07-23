from collections.abc import Callable
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class IEventBus(Protocol):
    """Abstract interface for the global event bus."""

    def subscribe(self, event_type: str, callback: Callable[..., Any]) -> None:
        """Subscribe a callback to a specific event type."""
        ...

    def publish(self, event_type: str, *args: Any, **kwargs: Any) -> None:
        """Publish an event to all subscribers."""
        ...
