"""Validation utilities for BioPro SDK.

Provides common validation functions for plugin parameters and inputs.
"""

from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# FILE & PATH VALIDATION
# ──────────────────────────────────────────────────────────────────────────────


def validate_file_exists(path: str) -> tuple[bool, str]:
    """Check if file exists.

    Args:
        path: File path to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not path:
        return False, "File path is empty"
    if not Path(path).exists():
        return False, f"File not found: {path}"
    return True, ""


def validate_directory_exists(path: str) -> tuple[bool, str]:
    """Check if directory exists.

    Args:
        path: Directory path to validate

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not path:
        return False, "Directory path is empty"
    if not Path(path).is_dir():
        return False, f"Directory not found: {path}"
    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
# NUMERIC VALIDATION
# ──────────────────────────────────────────────────────────────────────────────


def validate_value_range(value: float, min_val: float, max_val: float, name: str = "value") -> tuple[bool, str]:
    """Check if value is within range.

    Args:
        value: Value to validate
        min_val: Minimum allowed value (inclusive)
        max_val: Maximum allowed value (inclusive)
        name: Name of value for error message

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if value < min_val or value > max_val:
        return False, f"{name} must be between {min_val} and {max_val}"
    return True, ""


def validate_positive(value: float, name: str = "value") -> tuple[bool, str]:
    """Check if value is positive (> 0).

    Args:
        value: Value to validate
        name: Name of value for error message

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if value <= 0:
        return False, f"{name} must be positive (> 0)"
    return True, ""


def validate_non_negative(value: float, name: str = "value") -> tuple[bool, str]:
    """Check if value is non-negative (>= 0).

    Args:
        value: Value to validate
        name: Name of value for error message

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if value < 0:
        return False, f"{name} must be non-negative (>= 0)"
    return True, ""


# ──────────────────────────────────────────────────────────────────────────────
# STRING VALIDATION
# ──────────────────────────────────────────────────────────────────────────────


def validate_not_empty(value: str, name: str = "value") -> tuple[bool, str]:
    """Check if string is not empty.

    Args:
        value: String to validate
        name: Name of value for error message

    Returns:
        Tuple of (is_valid, error_message). If valid, error_message is empty.
    """
    if not value or not value.strip():
        return False, f"{name} cannot be empty"
    return True, ""
