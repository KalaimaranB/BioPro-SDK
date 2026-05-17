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
