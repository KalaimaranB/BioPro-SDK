from karcytics_sdk.plugin.dialogs import SaveWorkflowDialog


def test_save_workflow_dialog(qtbot):
    dialog = SaveWorkflowDialog()
    qtbot.addWidget(dialog)

    dialog.name_input.setText("Test Workflow")
    dialog.desc_input.setPlainText("Test Description")
    dialog.tags_input.setText("tag1, tag2, tag3")

    metadata = dialog.get_metadata()

    assert metadata["name"] == "Test Workflow"
    assert metadata["description"] == "Test Description"
    assert metadata["tags"] == ["tag1", "tag2", "tag3"]
    assert "timestamp" in metadata

    # Try with empty fields
    dialog.name_input.setText("  Trimmed  ")
    dialog.desc_input.setPlainText("")
    dialog.tags_input.setText("tag1,,  ")

    metadata = dialog.get_metadata()
    assert metadata["name"] == "Trimmed"
    assert metadata["description"] == ""
    assert metadata["tags"] == ["tag1"]
