# 📂 Workflow Context & Attachments API

The **BioPro SDK** provides dedicated types for handling complex workflows that require more than just a JSON state payload. Workflows often need to persist companion binary files (like raw imaging arrays or model weights) alongside the primary state.

The `WorkflowContext` manages these attachments transparently, ensuring that plugins don't have to handle manual path resolution or hashing logic.

---

## `WorkflowAttachment`

Describes a single companion file attached to a workflow.

### Properties

| Property | Type | Description |
| :--- | :--- | :--- |
| `key` | `str` | Logical identifier for the attachment (e.g., `"raw_data"`, `"masks"`). |
| `filename` | `str` | The bare filename on disk (e.g., `"data.bin"`). |
| `relative_path` | `str` | The path relative to the BioPro project root directory. |
| `mime_hint` | `str` | (Optional) Hint about the file content type. Defaults to `application/octet-stream`. |
| `description` | `str` | (Optional) Human-readable explanation of what this file contains. |
| `size_bytes` | `int` | Exact file size in bytes. |
| `sha256` | `str` | Cryptographic hash for integrity verification. |

---

## `WorkflowContext`

A helper passed into your plugin's save/load methods to manage binary attachments in a project-agnostic way.

### Methods

#### `add_attachment(key: str, source_path: Path | str, description: str = "", mime_hint: str = "application/octet-stream") -> None`
Registers a local file to be saved as a companion to the workflow. The BioPro Core engine will automatically hash this file and copy it into the workflow's designated attachment directory during the save phase.

**Parameters:**
- `key`: Logical name you will use to request the file back later.
- `source_path`: Absolute path to the file you want to attach.
- `description`: Optional text describing the payload.

#### `get_path(key: str) -> Path | None`
Resolves the absolute, machine-local path of a previously saved attachment. Returns `None` if the key doesn't exist.

---

## File I/O Helpers

The SDK also exposes basic helper functions to read and write bytes quickly. These are exposed in `biopro_sdk.plugin.io`.

- `read_binary(path: Path | str) -> bytes`: Reads and returns the bytes from a file.
- `write_binary(path: Path | str, data: bytes) -> None`: Safely creates parent directories and writes the bytes to disk.
