from pathlib import Path

from biopro_sdk.plugin.workflow import WorkflowAttachment, WorkflowContext


def test_attachment_roundtrip_dict():
    """Test serialization of WorkflowAttachment."""
    att = WorkflowAttachment(
        key="raw",
        filename="data.bin",
        relative_path="wf_attachments/data.bin",
        mime_hint="application/octet-stream",
        description="Raw data floats",
        size_bytes=1024,
        sha256="abcdef",
    )
    d = att.to_dict()
    assert d["key"] == "raw"
    assert d["filename"] == "data.bin"

    att2 = WorkflowAttachment.from_dict(d)
    assert att2.key == att.key
    assert att2.relative_path == att.relative_path
    assert att2.sha256 == att.sha256


def test_context_add_attachment():
    """Test adding pending attachments to context."""
    ctx = WorkflowContext()
    ctx.add_attachment("raw", "/path/to/my_data.bin", description="desc")

    assert "raw" in ctx.pending_attachments
    assert ctx.pending_attachments["raw"]["source_path"] == Path("/path/to/my_data.bin")
    assert ctx.pending_attachments["raw"]["description"] == "desc"


def test_context_get_path(tmp_path):
    """Test resolving an attachment's absolute path."""
    att = WorkflowAttachment(key="raw", filename="data.bin", relative_path="my_wf_attachments/data.bin")
    ctx = WorkflowContext(attachments=[att], resolve_base=tmp_path)

    resolved = ctx.get_path("raw")
    assert resolved == tmp_path / "my_wf_attachments/data.bin"


def test_context_missing_key_returns_none(tmp_path):
    """Test getting path of non-existent key."""
    ctx = WorkflowContext(resolve_base=tmp_path)
    assert ctx.get_path("missing") is None


def test_context_from_dicts_resolves_base_path(tmp_path):
    """Test instantiation from serialized dicts."""
    dicts = [
        {
            "key": "raw",
            "filename": "data.bin",
            "relative_path": "atts/data.bin",
            "mime_hint": "test",
            "description": "test",
            "size_bytes": 0,
            "sha256": "",
        }
    ]
    ctx = WorkflowContext.from_attachment_dicts(dicts, resolve_base=tmp_path)
    assert "raw" in ctx._attachments
    assert ctx.get_path("raw") == tmp_path / "atts/data.bin"
