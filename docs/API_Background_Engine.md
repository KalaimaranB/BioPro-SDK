# ⚙️ Concurrency Module (`biopro_sdk.plugin.analysis`)

Contains multi-threaded background workers and signals enabling long-running mathematical or file-bound calculations to execute concurrently offscreen, keeping the PyQt6 GUI responsive.

---

## 🏎️ `AnalysisBase`

An abstract base class (`ABC`) hosting the computation logic. Keeping calculations encapsulated here makes them unit-testable and CLI-runnable without importing graphic modules.

### Method Signatures

#### `__init__(self, plugin_id: str) -> None`
*   **Parameters:**
    *   `plugin_id` (`str`): The unique lowercase plugin identifier.

#### `run(self, state: PluginState | None = None) -> dict[str, Any]`
*[Abstract]* The computation entry point. Contains the heavy numeric iterations. Must **NOT** interact with PyQt6 UI widgets or components.
*   **Parameters:**
    *   `state` (`PluginState | None`): Snapshot of the user configurations at execution time.
*   **Returns:**
    *   `dict[str, Any]`: Key-value results dictionary (serialized directly back to UI handlers).

#### `cancel(self) -> None`
Requests the engine to abort computation. Sets internal cancellation boolean flag to `True`.

#### `is_cancelled(self) -> bool`
Returns `True` if a cancellation request has occurred. **CRITICAL:** Subclasses must check this method frequently inside loops (e.g. at the start of every iteration) and return early if true.

---

## 🤖 `AnalysisWorker`

Inherits from `QObject`. Manages thread execution boundaries and wraps signal brokers. Created via `PluginBase.create_worker(analyzer, state)`.

### PyQt6 Custom Signals

*   **`finished` (`pyqtSignal(dict)`):** Emitted with the final results dictionary on successful computation completion.
*   **`error` (`pyqtSignal(str)`):** Emitted with the exception details if an unhandled error occurs during execution.
*   **`progress` (`pyqtSignal(int)`):** Emitted with a value range `0` to `100` reporting current progress percentage.
*   **`cancelled` (`pyqtSignal()`):** Emitted when execution exits early due to user abort actions.

### Method Signatures

#### `cancel(self) -> None`
Triggers the abort sequence on the underlying `AnalysisBase` instance.

#### `run(self) -> None`
Executes the calculation, intercepts exceptions, validates C++ pointer lifecycles, and triggers the appropriate PyQt6 signal.

---

## 💾 I/O & Preferences Managers

These classes and helper functions manage serialization, loading configuration profiles, and syncing user preferences/settings files inside standard JSON paths.

### `PluginConfig`
Handles manifest metadata parsing, validation, and schema checking. Created internally when a plugin is registered.

### `PluginPreferenceManager`
Manages user preferences and settings for the plugin. Saves data automatically to the correct system-appropriate paths.
*   **`get(key: str, default: Any = None) -> Any`:** Retrieves a persistent setting value.
*   **`set(key: str, value: Any) -> None`:** Saves a setting key-value pair persistently.

### Utility I/O Functions
*   **`load_json(file_path: str) -> dict[str, Any]`**: Reads a JSON file from disk and parses it safely.
*   **`save_json(file_path: str, data: dict[str, Any]) -> None`**: Serializes and writes a Python dictionary to disk as JSON.

---

## 📝 Unified Logger: `get_logger`

Retrieves a customized, pre-configured logging adapter mapped to your plugin ID. Every output statement will automatically print with your plugin's name as a prefix, making it easy to identify in log files.

#### Signature
`get_logger(plugin_id: str) -> Logger`
*   **Parameters:**
    *   `plugin_id` (`str`): Lowercase plugin identifier.
*   **Returns:** A fully configured standard python `Logger` adapter.

---

## 🧪 Parameter & Validation Helpers (`biopro_sdk.plugin.validation`)

Use these pre-built, thread-safe validator functions to enforce QA metrics and validate user inputs inside form text fields or wizard pages. If validation fails, they raise a `ValueError` with clear, localization-ready error details.

#### `validate_not_empty(value: str, field_name: str) -> None`
Raises `ValueError` if the given string is empty or contains only whitespace.

#### `validate_file_exists(file_path: str, field_name: str) -> None`
Raises `ValueError` if the specified file path does not exist on disk.

#### `validate_directory_exists(dir_path: str, field_name: str) -> None`
Raises `ValueError` if the specified directory path does not exist.

#### `validate_non_negative(value: float | int, field_name: str) -> None`
Raises `ValueError` if the number is strictly less than 0.

#### `validate_positive(value: float | int, field_name: str) -> None`
Raises `ValueError` if the number is less than or equal to 0.

#### `validate_value_range(value: float | int, min_val: float | int, max_val: float | int, field_name: str) -> None`
Raises `ValueError` if the number does not sit inclusively between the boundaries `[min_val, max_val]`.
