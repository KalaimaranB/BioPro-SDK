"""Dialog utilities for BioPro SDK.

Provides convenient wrappers for common PyQt6 file dialogs and message boxes
that work with the current theme.
"""

from PyQt6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

# ──────────────────────────────────────────────────────────────────────────────
# FILE DIALOGS
# ──────────────────────────────────────────────────────────────────────────────


def get_image_path(parent=None, title: str = "Select Image", start_dir: str = "") -> str | None:
    """Show file dialog to select an image.

    Args:
        parent: Parent widget
        title: Dialog title
        start_dir: Initial directory

    Returns:
        Selected file path or None if cancelled
    """
    file_path, _ = QFileDialog.getOpenFileName(
        parent, title, start_dir, "Images (*.png *.jpg *.jpeg *.tiff *.tif);;All Files (*)"
    )
    return file_path if file_path else None


def get_image_paths(parent=None, title: str = "Select Images", start_dir: str = "") -> list[str]:
    """Show file dialog to select multiple images.

    Args:
        parent: Parent widget
        title: Dialog title
        start_dir: Initial directory

    Returns:
        List of selected file paths
    """
    file_paths, _ = QFileDialog.getOpenFileNames(
        parent, title, start_dir, "Images (*.png *.jpg *.jpeg *.tiff *.tif);;All Files (*)"
    )
    return file_paths if file_paths else []


def import_assets_workflow(parent, project_manager, file_paths: list[str]) -> list[str]:
    """Orchestrates the multi-file import workflow as requested by the user.

    1. If multiple files, asks if they should be grouped in a subdirectory.
    2. Asks once for 'Copy to Workspace' for the entire batch.
    3. Executes the batch import via ProjectManager.

    Returns:
        List of file hashes for the imported assets.
    """
    if not file_paths:
        return []

    subfolder = None
    if len(file_paths) > 1 and ask_yes_no(
        parent,
        "Group Files?",
        "Would you like to create a subdirectory in 'assets' for this collected set of files?",
    ):
        subfolder = get_text(parent, "Subdirectory Name", "Enter folder name:", default="experiment_data")
        if not subfolder or not subfolder.strip():
            subfolder = None

    copy_to_workspace = ask_yes_no(
        parent,
        "Copy to Workspace?",
        f"Copy these {len(file_paths)} files into the project assets folder?\n\n"
        "This ensures the project remains portable if moved to another computer.",
    )

    from pathlib import Path

    path_objs = [Path(p) for p in file_paths]

    return project_manager.batch_add_images(path_objs, copy_to_workspace, subfolder)


def get_save_path(parent=None, title: str = "Save As", start_dir: str = "", file_filter: str = "") -> str | None:
    """Show save file dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        start_dir: Initial directory
        file_filter: Qt file filter string (e.g. "CSV Files (*.csv);;All Files (*)")

    Returns:
        Selected file path or None if cancelled
    """
    if not file_filter:
        file_filter = "All Files (*)"

    file_path, _ = QFileDialog.getSaveFileName(parent, title, start_dir, file_filter)
    return file_path if file_path else None


def get_directory(parent=None, title: str = "Select Directory", start_dir: str = "") -> str | None:
    """Show directory selection dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        start_dir: Initial directory

    Returns:
        Selected directory path or None if cancelled
    """
    dir_path = QFileDialog.getExistingDirectory(parent, title, start_dir)
    return dir_path if dir_path else None


# ──────────────────────────────────────────────────────────────────────────────
# MESSAGE BOXES
# ──────────────────────────────────────────────────────────────────────────────


def show_info(parent=None, title: str = "Information", message: str = "") -> None:
    """Show information dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
    """
    QMessageBox.information(parent, title, message)


def show_warning(parent=None, title: str = "Warning", message: str = "") -> None:
    """Show warning dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
    """
    QMessageBox.warning(parent, title, message)


def show_error(parent=None, title: str = "Error", message: str = "") -> None:
    """Show error dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message
    """
    QMessageBox.critical(parent, title, message)


def ask_yes_no(parent=None, title: str = "", message: str = "") -> bool:
    """Show yes/no question dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message

    Returns:
        True if user clicks Yes, False otherwise
    """
    reply = QMessageBox.question(parent, title, message, QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    return reply == QMessageBox.StandardButton.Yes


def ask_ok_cancel(parent=None, title: str = "", message: str = "") -> bool:
    """Show OK/Cancel dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        message: Dialog message

    Returns:
        True if user clicks OK, False otherwise
    """
    reply = QMessageBox.question(
        parent, title, message, QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel
    )
    return reply == QMessageBox.StandardButton.Ok


# ──────────────────────────────────────────────────────────────────────────────
# INPUT DIALOGS
# ──────────────────────────────────────────────────────────────────────────────


def get_text(parent=None, title: str = "", label: str = "", default: str = "") -> str | None:
    """Show text input dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        label: Label text
        default: Default value in text field

    Returns:
        User input or None if cancelled
    """
    text, ok = QInputDialog.getText(parent, title, label, text=default)
    return text if ok else None


def get_number(
    parent=None,
    title: str = "",
    label: str = "",
    value: int = 0,
    min_val: int = -999999,
    max_val: int = 999999,
) -> int | None:
    """Show integer input dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        label: Label text
        value: Default value
        min_val: Minimum allowed value
        max_val: Maximum allowed value

    Returns:
        User input or None if cancelled
    """
    num, ok = QInputDialog.getInt(parent, title, label, value, min_val, max_val)
    return num if ok else None


def get_double(
    parent=None,
    title: str = "",
    label: str = "",
    value: float = 0.0,
    min_val: float = -999.99,
    max_val: float = 999.99,
    decimals: int = 2,
) -> float | None:
    """Show float input dialog.

    Args:
        parent: Parent widget
        title: Dialog title
        label: Label text
        value: Default value
        min_val: Minimum allowed value
        max_val: Maximum allowed value
        decimals: Number of decimal places

    Returns:
        User input or None if cancelled
    """
    num, ok = QInputDialog.getDouble(parent, title, label, value, min_val, max_val, decimals)
    return num if ok else None
