"""Plugin Tier — Core classes, UI components, and utilities for BioPro plugins."""

from .base import PluginBase
from .signals import PluginSignals
from .state import PluginState
from .analysis import AnalysisBase, AnalysisRunnable, AnalysisWorker
from .events import CentralEventBus
from .preferences import PreferenceManagerProtocol
from .logging import get_logger
from .interfaces import BioProPlugin

from .components import (
    DangerButton,
    HeaderLabel,
    ModuleCard,
    PrimaryButton,
    SecondaryButton,
    SubtitleLabel,
)
from .wizard import StepIndicator, WizardPanel, WizardStep

from .dialogs import (
    ask_ok_cancel,
    ask_yes_no,
    get_directory,
    get_double,
    get_image_path,
    get_number,
    get_save_path,
    get_text,
    show_error,
    show_info,
    show_warning,
)
from .io import PluginConfig, PluginPreferenceManager, load_json, save_json
from .validation import (
    validate_directory_exists,
    validate_file_exists,
    validate_non_negative,
    validate_not_empty,
    validate_positive,
    validate_value_range,
)

__all__ = [
    # Base and Core
    "PluginBase",
    "PluginSignals",
    "PluginState",
    "AnalysisBase",
    "AnalysisRunnable",
    "AnalysisWorker",
    "CentralEventBus",
    "PreferenceManagerProtocol",
    "get_logger",
    "BioProPlugin",
    # UI Components
    "DangerButton",
    "HeaderLabel",
    "ModuleCard",
    "PrimaryButton",
    "SecondaryButton",
    "StepIndicator",
    "SubtitleLabel",
    "WizardPanel",
    "WizardStep",
    # Dialogs
    "ask_ok_cancel",
    "ask_yes_no",
    "get_directory",
    "get_double",
    "get_image_path",
    "get_number",
    "get_save_path",
    "get_text",
    "show_error",
    "show_info",
    "show_warning",
    # I/O & Configuration
    "PluginConfig",
    "PluginPreferenceManager",
    "load_json",
    "save_json",
    # Validation Helpers
    "validate_directory_exists",
    "validate_file_exists",
    "validate_non_negative",
    "validate_not_empty",
    "validate_positive",
    "validate_value_range",
]
