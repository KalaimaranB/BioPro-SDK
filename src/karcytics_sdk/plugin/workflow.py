"""Workflow execution context for Karcytics plugins.

Provides helpers to manage binary attachments and workflow-associated data.
"""

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class WorkflowAttachment:
    """Describes a non-JSON companion file associated with a workflow."""

    key: str
    filename: str
    relative_path: str
    mime_hint: str = "application/octet-stream"
    description: str = ""
    size_bytes: int = 0
    sha256: str = ""

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "WorkflowAttachment":
        return cls(**d)


class WorkflowContext:
    """Context helper for workflows to attach and resolve non-JSON files."""

    def __init__(
        self,
        attachments: list[WorkflowAttachment] | None = None,
        resolve_base: Path | None = None,
    ):
        self._attachments: dict[str, WorkflowAttachment] = {a.key: a for a in (attachments or [])}
        self.resolve_base = Path(resolve_base) if resolve_base else None

        # Temporary storage for attachments being created during save
        self.pending_attachments: dict[str, dict] = {}

    def add_attachment(
        self,
        key: str,
        source_path: Path | str,
        description: str = "",
        mime_hint: str = "application/octet-stream",
    ) -> None:
        """Register a new attachment to be saved with the workflow."""
        self.pending_attachments[key] = {
            "source_path": Path(source_path),
            "description": description,
            "mime_hint": mime_hint,
        }

    def get_path(self, key: str) -> Path | None:
        """Resolve the absolute path of an existing attachment by its key."""
        if key not in self._attachments or not self.resolve_base:
            return None

        att = self._attachments[key]
        return self.resolve_base / att.relative_path

    def to_attachment_dicts(self) -> list[dict]:
        """Serialize current persistent attachments to dictionaries."""
        return [att.to_dict() for att in self._attachments.values()]

    @classmethod
    def from_attachment_dicts(cls, data: list[dict], resolve_base: Path | str) -> "WorkflowContext":
        """Deserialize attachments from a workflow JSON payload."""
        attachments = [WorkflowAttachment.from_dict(d) for d in data]
        return cls(attachments=attachments, resolve_base=Path(resolve_base))
