"""Functional Task Utilities for BioPro SDK.

Enables developers to run arbitrary functions (downloads, I/O, networking)
on the global TaskScheduler without needing to subclass AnalysisBase manually.
"""

from collections.abc import Callable
from typing import Any

from .analysis import AnalysisBase
from .state import PluginState


class FunctionalTask(AnalysisBase):
    """A proxy that converts a callable into a BioPro Analysis task.

    Example:
        >>> def my_download():
        ...     return {"file": "data.fcs"}
        >>> task = FunctionalTask(my_download, "my_plugin")
        >>> task_scheduler.submit(task, None)
    """

    def __init__(
        self, func: Callable[[], Any], plugin_id: str = "unknown", name: str = "Utility Task"
    ):
        """Initialize the task.

        Args:
            func: The function to execute. Should return a dict or None.
            plugin_id: The ID of the plugin owning this task (optional).
            name: Human-readable name for logging/UI.
        """
        super().__init__(plugin_id)
        self.func = func
        self.name = name

    def run(self, state: PluginState | None = None) -> dict:
        """Executes the wrapped function and returns standardized results."""
        try:
            result = self.func()
            if isinstance(result, dict):
                return result
            return {"result": result, "status": "success"}
        except Exception as e:
            # The AnalysisWorker will catch this and emit the error signal
            raise e

    def __repr__(self):
        return f"<FunctionalTask: {self.name} ({self.plugin_id})>"
