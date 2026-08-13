from typing import Any, Protocol, runtime_checkable

from karcytics_sdk.plugin.managed_task import AnalysisBase
from karcytics_sdk.plugin.state import PluginState


@runtime_checkable
class ITaskScheduler(Protocol):
    """Abstract interface for background task scheduling."""

    def submit(self, analyzer: AnalysisBase, state: PluginState | None = None) -> Any:
        """Submit a background analysis task for execution."""
        ...

    def cancel_all(self) -> None:
        """Cancel all pending tasks."""
        ...
