"""BioPro SDK — Complete plugin development framework.

Provides everything needed to build plugins:

Core Components:
    - PluginBase: Main plugin class to inherit from
    - PluginState: State management with undo/redo
    - PluginSignals: Standard signals for communication
    - AnalysisBase: Abstract analysis logic class
    - AnalysisWorker: Background worker for threads

UI Components:
    - PrimaryButton, SecondaryButton, DangerButton: Semantic buttons
    - ModuleCard, HeaderLabel: Styled components
    - WizardStep, WizardPanel: Multi-step interface framework

Utilities:
    - Dialogs: File, message, and input dialogs
    - I/O: JSON and configuration management
    - Validation: Input validation helpers

Contrib (Optional):
    - Image utilities: Common image processing functions

Example:
    >>> from biopro_sdk.core import PluginBase, PluginState
    >>> from biopro_sdk.ui import PrimaryButton, WizardPanel
    >>> from biopro_sdk.utils import show_error
    >>>
    >>> class MyState(PluginState):
    ...     image_path: str = ""
    ...
    >>> class MyPlugin(PluginBase):
    ...     def __init__(self, plugin_id: str):
    ...         super().__init__(plugin_id)
    ...         self.state = MyState()
    ...
    ...     def get_state(self) -> PluginState:
    ...         return self.state
    ...
    ...     def set_state(self, state: PluginState) -> None:
    ...         self.state = state
"""

from . import contrib, core, ui, utils
from .core import (
    AnalysisBase,
    AnalysisWorker,
    PluginBase,
    PluginSignals,
    PluginState,
    PreferenceManagerProtocol,
    diagnostics,
)
from .core.ai import AIAssistant, AIServerManager, ai_manager
from .core.docs import PluginDocumentation, docs_registry
from .core.events import CentralEventBus
from .ui import (
    DangerButton,
    HeaderLabel,
    ModuleCard,
    PrimaryButton,
    SecondaryButton,
    StepIndicator,
    SubtitleLabel,
    WizardPanel,
    WizardStep,
)
from .utils import (
    PluginConfig,
    PluginPreferenceManager,
    ask_ok_cancel,
    ask_yes_no,
    get_directory,
    get_double,
    get_image_path,
    get_number,
    get_save_path,
    get_text,
    load_json,
    save_json,
    show_error,
    show_info,
    show_warning,
    validate_directory_exists,
    validate_file_exists,
    validate_non_negative,
    validate_not_empty,
    validate_positive,
    validate_value_range,
)

__all__ = [
    # Submodules
    "core",
    "ui",
    "utils",
    "contrib",
    # Core
    "PluginBase",
    "PluginState",
    "PluginSignals",
    "AnalysisBase",
    "AnalysisWorker",
    "PreferenceManagerProtocol",
    "CentralEventBus",
    "PluginDocumentation",
    "docs_registry",
    "AIAssistant",
    "AIServerManager",
    "ai_manager",
    # UI
    "PrimaryButton",
    "SecondaryButton",
    "DangerButton",
    "ModuleCard",
    "HeaderLabel",
    "SubtitleLabel",
    "StepIndicator",
    "WizardStep",
    "WizardPanel",
    # Utils
    "get_image_path",
    "get_save_path",
    "get_directory",
    "show_info",
    "show_warning",
    "show_error",
    "ask_yes_no",
    "ask_ok_cancel",
    "get_text",
    "get_number",
    "get_double",
    "load_json",
    "save_json",
    "PluginConfig",
    "PluginPreferenceManager",
    "validate_file_exists",
    "validate_directory_exists",
    "validate_value_range",
    "validate_positive",
    "validate_non_negative",
    "validate_not_empty",
    "diagnostics",
]
