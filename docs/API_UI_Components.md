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
