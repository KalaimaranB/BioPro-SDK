"""BioPro SDK Core — Base classes for plugin development.

Provides:
- PluginSignals: Standard PyQt6 signals for plugin communication
- PluginState: Base class for serializable plugin state
- AnalysisBase: Abstract base for analysis logic
- AnalysisWorker: Background worker for thread execution
- PluginBase: Main plugin class to inherit from
"""

try:
    from biopro.core.diagnostics import diagnostics
except ImportError:
    class MockDiagnostics:
        def report_error(self, message, exception=None, plugin_id=None, fatal=False):
            import logging
            logging.getLogger("biopro_sdk.diagnostics").error(f"[{plugin_id or 'System'}] {message}: {exception or ''}")
    diagnostics = MockDiagnostics()

from .analysis import AnalysisBase, AnalysisWorker
from .base import PluginBase
from .interfaces import BioProPlugin
from .managed_task import FunctionalTask
from .preferences import PreferenceManagerProtocol
from .signals import PluginSignals
from .state import PluginState

__all__ = [
    "PluginSignals",
    "PluginState",
    "AnalysisBase",
    "AnalysisWorker",
    "PluginBase",
    "FunctionalTask",
    "BioProPlugin",
    "PreferenceManagerProtocol",
    "diagnostics",
]
