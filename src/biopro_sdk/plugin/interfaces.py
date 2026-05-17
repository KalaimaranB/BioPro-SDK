"""BioPro Plugin Interfaces.

Defines the formal structural requirements for BioPro analysis modules
using PEP 544 Protocols.
"""

from typing import Protocol, runtime_checkable

from PyQt6.QtWidgets import QWidget


@runtime_checkable
class BioProPlugin(Protocol):
    """Structural protocol for a valid BioPro Plugin module.

    Any Python module or class that implements this protocol can be
    loaded as a BioPro plugin.
    """

    def get_panel_class(self) -> type[QWidget]:
        """Returns the main QWidget class for the plugin's UI."""
        ...

    @property
    def __version__(self) -> str:
        """The version string of the plugin (e.g. '1.2.3')."""
        ...

    @property
    def __plugin_id__(self) -> str:
        """The unique identifier for the plugin (matches manifest.json id)."""
        ...

    def cleanup(self) -> None:
        """Release instance-specific resources (e.g. caches, local memory).

        Called when a specific instance of the plugin panel is closed.
        """
        ...

    def shutdown(self) -> None:
        """Release global/module resources (e.g. GPU models, open files).

        Called when the application exists or the module is unloaded.
        """
        ...
