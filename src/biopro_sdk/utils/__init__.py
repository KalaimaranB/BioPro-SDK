"""BioPro SDK Utils — Dialogs, I/O, and validation utilities.

Provides:
- Dialog helpers: File dialogs, message boxes, input dialogs
- I/O utilities: JSON loading/saving, config management
- Validation: File path, numeric range, string validation
"""

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
from .io import (
    PluginConfig,
    PluginPreferenceManager,
    get_plugin_logger,
    load_json,
    save_json,
)
from .validation import (
    validate_directory_exists,
    validate_file_exists,
    validate_non_negative,
    validate_not_empty,
    validate_positive,
    validate_value_range,
)

__all__ = [
    # Dialogs
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
    # I/O
    "load_json",
    "save_json",
    "PluginConfig",
    "PluginPreferenceManager",
    "get_plugin_logger",
    # Validation
    "validate_file_exists",
    "validate_directory_exists",
    "validate_value_range",
    "validate_positive",
    "validate_non_negative",
    "validate_not_empty",
]
