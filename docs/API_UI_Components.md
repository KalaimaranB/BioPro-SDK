# 🎨 UI Module (`biopro_sdk.plugin.components` & `wizard`)

Provides standard, theme-aware user interface components, unified styling classes, and an interactive, multi-step guided setup framework.

---

## 🔘 Semantic Buttons

Inherit from `QPushButton`. These elements dynamically apply the correct font weights, border curvatures, and color schemes based on whether light or dark mode is active.

### Available Classes

*   **`PrimaryButton`:** Used for final actions or positive progressions (e.g. "Save Configuration", "Next Step"). Applies active primary brand colors.
*   **`SecondaryButton`:** Used for neutral actions, navigation backtracking, or cancel flows (e.g. "Back", "Close"). Applies muted secondary gray outlines.
*   **`DangerButton`:** Used exclusively for destructive or irreversible actions (e.g. "Delete Session", "Reset Factory"). Applies brand-compliant crimson colors.

---

## 🧙‍♂️ Guided Setup: `WizardPanel` & `WizardStep`

A robust, multi-step guided workflow panel. Instead of rendering a single massive form, it partitions complex onboarding pathways into modular steps.

### 1. `WizardStep`

An abstract base class (`ABC`) representing a single page inside the guided wizard.

#### Lifecycle Hooks & Attributes

*   **`label` (`str`):** Class-level attribute specifying the human-readable title of this step (displayed in the Step Indicator).
*   **`build_page(self, panel: WizardPanel) -> QWidget`:** *[Abstract]* Returns the `QWidget` container hosting your widgets for this step page.
*   **`on_enter(self) -> None`:** *[Optional]* Hook executed automatically when the wizard transitions onto this step page. Override to refresh form values or load data from disk.
*   **`on_next(self, panel: WizardPanel) -> bool`:** *[Abstract]* Hook executed when the user requests to advance forward. Validate form inputs here; return `True` to allow navigation, or `False` to block progression.

---

### 2. `WizardPanel`

Inherits from `QWidget`. Manages and animates a collection of `WizardStep` subclass instances.

#### Method Signatures

*   **`add_step(self, step: WizardStep) -> None`:** appends a step page to the wizard layout.
*   **`next_step(self) -> None`:** Transitions forward to the next step (after calling `on_next()`).
*   **`prev_step(self) -> None`:** Transitions backward to the previous step.
*   **`current_index(self) -> int`:** Returns the zero-indexed integer of the active step.
*   **`step_count(self) -> int`:** Returns the total number of registered steps.
*   **`set_index(self, index: int) -> None`:** Direct navigation jumping to a specific step.
*   **`validate_current_step(self) -> bool`:** Manually triggers `on_next()` validation check on the active step page.

---

## 💬 Unified Dialog Helpers

These functions enable plugins to display interactive modal prompt windows, retrieve text/numeric inputs, choose files/directories, or present visual error/warning dialogs using theme-compliant, unified styles.

### Message Boxes

#### `show_info(parent: QWidget | None, title: str, message: str) -> None`
Displays a modal information dialog with an OK button.
*   **Parameters:**
    *   `parent` (`QWidget | None`): Optional parent graphic container.
    *   `title` (`str`): Title of the dialog window.
    *   `message` (`str`): Primary text message inside the dialog.

#### `show_warning(parent: QWidget | None, title: str, message: str) -> None`
Displays a modal warning dialog alerting the user to non-fatal issues.

#### `show_error(parent: QWidget | None, title: str, message: str) -> None`
Displays a modal error dialog alerting the user to critical system or validation failures.

#### `ask_yes_no(parent: QWidget | None, title: str, question: str) -> bool`
Prompts the user with a question.
*   **Returns:** `True` if "Yes" was clicked, or `False` if "No" was clicked.

#### `ask_ok_cancel(parent: QWidget | None, title: str, question: str) -> bool`
Prompts the user with a confirmation request.
*   **Returns:** `True` if "OK" was clicked, or `False` if "Cancel" was clicked.

### Value Inputs

#### `get_text(parent: QWidget | None, title: str, label: str, default: str = "") -> str | None`
Retrieves a text string input from the user. Returns `None` if the input dialog was cancelled.

#### `get_number(parent: QWidget | None, title: str, label: str, min_val: int = -2147483648, max_val: int = 2147483647, step: int = 1, default: int = 0) -> int | None`
Retrieves a bounded integer input value. Returns `None` if cancelled.

#### `get_double(parent: QWidget | None, title: str, label: str, min_val: float = -1.79e+308, max_val: float = 1.79e+308, decimals: int = 2, step: float = 0.1, default: float = 0.0) -> float | None`
Retrieves a floating-point number input. Returns `None` if cancelled.

### File & Directory Selectors

#### `get_directory(parent: QWidget | None, title: str, start_dir: str = "") -> str | None`
Prompts the user to select an existing system directory.

#### `get_image_path(parent: QWidget | None, title: str, start_dir: str = "") -> str | None`
Prompts the user to choose an image file (supports PNG, JPG, JPEG, TIF, TIFF).

#### `get_save_path(parent: QWidget | None, title: str, start_dir: str = "", filter_str: str = "All Files (*)") -> str | None`
Prompts the user to select a path on disk for saving an output file.
