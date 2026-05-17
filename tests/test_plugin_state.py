import sys
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest
from biopro_sdk.plugin.base import PluginBase
from biopro_sdk.plugin.state import PluginState


@dataclass
class MockState(PluginState):
    threshold: float = 0.5
    filter_type: str = "Gaussian"
    heavy_data: list = None


class MockPlugin(PluginBase):
    def __init__(self, plugin_id: str, parent=None):
        super().__init__(plugin_id, parent)
        self.state = MockState()
        self.heavy_asset = [9] * 1000

    def get_state(self) -> MockState:
        return self.state

    def set_state(self, state: PluginState) -> None:
        assert isinstance(state, MockState)
        self.state = state


def test_plugin_state_serialization():
    """Test PluginState to_dict and from_dict serialization methods."""
    state = MockState(threshold=0.8, filter_type="Median")
    state_dict = state.to_dict()

    assert state_dict == {"threshold": 0.8, "filter_type": "Median", "heavy_data": None}

    new_state = MockState.from_dict(state_dict)
    assert isinstance(new_state, MockState)
    assert new_state.threshold == 0.8
    assert new_state.filter_type == "Median"


def test_plugin_base_properties():
    """Test basic properties and protocols of PluginBase."""
    plugin = MockPlugin(plugin_id="my_test_plugin")

    assert plugin.plugin_id == "my_test_plugin"
    assert plugin.__plugin_id__ == "my_test_plugin"
    assert plugin.__version__ == "1.0.0"
    assert plugin.get_panel_class() == MockPlugin


def test_plugin_signal_proxying():
    """Verify that PluginBase proxies missing attributes to self.signals."""
    plugin = MockPlugin(plugin_id="test_proxy")

    # Exists on PluginSignals
    assert plugin.state_changed == plugin.signals.state_changed
    assert plugin.status_message == plugin.signals.status_message

    # Missing attribute entirely
    with pytest.raises(AttributeError):
        _ = plugin.non_existent_attribute


def test_plugin_event_bus():
    """Verify that PluginBase can publish and subscribe to the CentralEventBus."""
    plugin = MockPlugin(plugin_id="test_bus")
    called_data = []

    def callback(data):
        called_data.append(data)

    plugin.subscribe_event("test.topic", callback)
    plugin.publish_event("test.topic", "hello_world")

    assert called_data == ["hello_world"]


def test_plugin_undo_redo_history():
    """Verify the history mechanisms (push, undo, redo, can_undo, can_redo)."""
    plugin = MockPlugin(plugin_id="test_history")

    # Mocking standard HistoryManager structures
    mock_history = MagicMock()
    mock_module_history = MagicMock()
    mock_history.get_module_history.return_value = mock_module_history
    plugin.history = mock_history

    # Mock stack behaviors
    mock_module_history.undo_stack = [1, 2]
    mock_module_history.redo_stack = []

    assert plugin.can_undo() is True
    assert plugin.can_redo() is False

    # Trigger state change
    plugin.state.threshold = 0.95

    # Set up signal spy
    spy = MagicMock()
    plugin.state_changed.connect(spy)

    # Test Push State
    plugin.push_state()
    mock_history.get_module_history.assert_called_with("test_history")
    mock_module_history.push.assert_called_once_with({"threshold": 0.95, "filter_type": "Gaussian", "heavy_data": None})
    assert spy.call_count == 1

    # Test Undo
    mock_module_history.undo.return_value = {"threshold": 0.5, "filter_type": "Gaussian", "heavy_data": None}
    plugin.undo()
    assert plugin.state.threshold == 0.5
    assert spy.call_count == 2

    # Test Redo
    mock_module_history.redo.return_value = {"threshold": 0.95, "filter_type": "Gaussian", "heavy_data": None}
    plugin.redo()
    assert plugin.state.threshold == 0.95
    assert spy.call_count == 3


@patch("biopro_sdk.plugin.base.theme_manager")
def test_theme_propagation(mock_theme_manager):
    """Verify applying base stylesheets propagates styles correctly."""
    plugin = MockPlugin(plugin_id="test_theme")
    plugin._apply_theme_styles()

    # Style sheet must contain color tags from Colors mock
    assert "background:" in plugin.styleSheet()


def test_cleanup_and_destructor_raii():
    """Verify cleanup breaks references to heavy assets for prompt GC collection."""
    plugin = MockPlugin(plugin_id="test_cleanup")

    # Set up heavy resources in state and instance
    plugin.state.heavy_data = [99] * 500

    mock_inspector = MagicMock()
    mock_inspector.get_heavy_resources.side_effect = [
        [("heavy_data", plugin.state.heavy_data)],  # attributes of State
        [("heavy_asset", plugin.heavy_asset)],  # attributes of Instance
    ]

    with patch.dict(sys.modules, {"biopro.core.resource_inspector": MagicMock(ResourceInspector=mock_inspector)}):
        # Trigger cleanup
        plugin.cleanup()

        # Assets must be pruned to None
        assert plugin.state.heavy_data is None
        assert plugin.heavy_asset is None
        assert plugin.state.threshold == 0.5  # Non-heavy values are preserved


def test_widget_close_event():
    """Verify close widget event triggers automated RAII cleanup."""
    plugin = MockPlugin(plugin_id="test_close")

    # Spy on cleanup
    plugin.cleanup = MagicMock()

    # Create real QCloseEvent
    from PyQt6.QtGui import QCloseEvent

    event = QCloseEvent()

    plugin.closeEvent(event)

    plugin.cleanup.assert_called_once()
