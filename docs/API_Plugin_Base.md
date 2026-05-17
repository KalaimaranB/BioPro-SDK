# 🧬 Core Plugin Module (`biopro_sdk.plugin`)

The foundational module for all BioPro plugins. It contains the central UI controllers, serializable state models, and a thread-safe publish/subscribe event broker.

---

## 🏛️ `PluginBase`

Inherits from `QWidget`. Every custom plugin panel must extend this class to gain automated theme synchronization, state undo/redo capabilities, and thread disposal hooks.

### Method Signatures

#### `__init__(self, plugin_id: str, parent: QWidget | None = None) -> None`
Initializes the plugin workspace under the specified identifier.
*   **Parameters:**
    *   `plugin_id` (`str`): The unique lowercase identifier corresponding to the `id` key in `manifest.json`.
    *   `parent` (`QWidget | None`): Optional parent graphical container.

#### `push_state(self) -> None`
Captures a deep-copy serialization of `self.state` and commits it to the internal Undo stack. Call this whenever the user performs an active modification (e.g. toggles checkboxes, changes thresholds).

#### `undo(self) -> None`
Pops the previous state checkpoint from the undo stack and restores it to `self.state`. Automatically triggers widget repaints.

#### `redo(self) -> None`
Re-applies the next forward checkpoint from the redo stack.

#### `create_worker(self, analyzer: AnalysisBase, state: PluginState | None = None) -> AnalysisWorker`
Instantiates a thread-safe background execution controller for heavy calculations.
*   **Parameters:**
    *   `analyzer` (`AnalysisBase`): Subclass handling scientific calculation logic.
    *   `state` (`PluginState | None`): State variables snapshot for this run.

#### `start_worker(self, worker: AnalysisWorker) -> None`
Submits the background worker to the global `QThreadPool` for immediate asynchronous offscreen execution.

---

## 💾 `PluginState`

A serializable dataclass representing the model variables of the plugin panel.

### Example Schema
```python
from dataclasses import dataclass
from biopro_sdk.plugin import PluginState

@dataclass
class NormalizationState(PluginState):
    scale_factor: float = 1.0
    enable_denoise: bool = True
```

---

## 📡 `CentralEventBus`

A thread-safe, global pub/sub event dispatcher enabling decoupled, real-time message exchange between multiple distinct plugins.

### Method Signatures

#### `publish(self, event_name: str, payload: dict[str, Any]) -> None`
Broadcasts an event message along with a key-value dictionary payload to all registered listening handlers.
*   **Parameters:**
    *   `event_name` (`str`): Unique dot-separated event path (e.g. `"biopro.gel_imager.scan_completed"`).
    *   `payload` (`dict[str, Any]`): Arbitrary scientific data or metadata dictionary.

#### `subscribe(self, event_name: str, handler: Callable[[dict[str, Any]], None]) -> None`
Registers a callback handler to listen for a specific event channel.
*   **Parameters:**
    *   `event_name` (`str`): Dot-separated event path matching publishers.
    *   `handler` (`Callable`): Target function receiving the payload dict.
