from unittest.mock import MagicMock, patch

import pytest
import requests

from biopro_sdk.host.ai import AIAssistant, AIServerManager


@pytest.fixture
def temp_ai_env(tmp_path):
    """Setup temp workspace for model files and logs."""
    biopro_dir = tmp_path / ".biopro"
    biopro_dir.mkdir()

    with patch("pathlib.Path.home", return_value=tmp_path):
        yield tmp_path, biopro_dir


@patch("socket.socket")
def test_ai_server_manager_initialization(mock_socket, temp_ai_env):
    """Test default values and signals for AIServerManager."""
    _, biopro_dir = temp_ai_env

    mock_s = MagicMock()
    mock_s.connect_ex.return_value = 1 # closed
    mock_socket.return_value.__enter__.return_value = mock_s

    manager = AIServerManager()
    assert manager.model_path == str(biopro_dir / "models" / "gemma4.gguf")
    assert manager.is_running() is False


@patch("os.path.exists")
def test_ai_server_start_missing_model(mock_exists, temp_ai_env):
    """Verify that start_server fails if the model file is not downloaded."""
    mock_exists.return_value = False

    manager = AIServerManager()
    spy = MagicMock()
    manager.signals.prompt_download.connect(spy)

    manager.start_server()
    spy.assert_called_once()


@patch("os.path.exists")
@patch("requests.get")
@patch("socket.socket")
def test_ai_server_reuses_existing_healthy_server(mock_socket, mock_get, mock_exists, temp_ai_env):
    """Verify that manager connects to and reuses an active background llama-cpp server."""
    mock_exists.return_value = True

    # Simulate port 8080 is open and healthy
    mock_s = MagicMock()
    mock_s.connect_ex.return_value = 0
    mock_socket.return_value.__enter__.return_value = mock_s

    mock_res = MagicMock(status_code=200)
    mock_get.return_value = mock_res

    manager = AIServerManager()

    spy = MagicMock()
    manager.signals.server_started.connect(spy)

    # Run the internal startup logic synchronously to avoid threading races
    manager._start_server_internal()

    assert manager._is_running is True
    spy.assert_called_once()


@patch("os.path.exists")
@patch("requests.get")
@patch("socket.socket")
@patch("subprocess.Popen")
@patch("subprocess.run")
def test_ai_server_launches_new_subprocess(mock_run, mock_popen, mock_socket, mock_get, mock_exists, temp_ai_env):
    """Verify subprocess creation parameters on a fresh startup."""
    mock_exists.return_value = True

    # Simulate port 8080 is closed (returns 1 on connect_ex)
    mock_s = MagicMock()
    mock_s.connect_ex.side_effect = [1, 0, 0] # closed initially, then opens during polling
    mock_socket.return_value.__enter__.return_value = mock_s

    # Mock requests to succeed on launch verification loop
    mock_res = MagicMock(status_code=200)
    mock_get.return_value = mock_res

    # Mock subprocess creation
    mock_proc = MagicMock()
    mock_proc.poll.return_value = None
    mock_popen.return_value = mock_proc

    manager = AIServerManager()

    spy = MagicMock()
    manager.signals.server_started.connect(spy)

    manager._start_server_internal()

    assert manager._is_running is True
    mock_popen.assert_called_once()
    spy.assert_called_once()

    # Test stop_server stops the process
    manager.stop_server()
    assert manager._is_running is False
    mock_proc.terminate.assert_called_once()


@patch("requests.post")
def test_ai_assistant_ask_question_non_stream(mock_post, temp_ai_env, tmp_path):
    """Test AIAssistant non-streaming responses and context gatherers."""
    _, biopro_dir = temp_sec_env = temp_ai_env

    # Create mock user guides to test document contextualizer
    docs_dir = tmp_path / "docs"
    docs_dir.mkdir()
    (docs_dir / "01_User_Guide.md").write_text("BioPro uses desktop components.")
    (docs_dir / "02_Getting_Started.md").write_text("Follow starting procedures.")

    # Create local soul Persona file
    (biopro_dir / "soul.md").write_text("- Be polite.\n- Talk like an expert.")

    # Mock successful response
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": "I am the BioPro assistant. Here is your advice."
                }
            }
        ]
    }
    mock_post.return_value = mock_res

    assistant = AIAssistant(host_docs_dir=docs_dir)
    res = assistant.ask_question(prompt="desktop", include_core=True)

    assert "advice" in res["result"]
    assert "01_User_Guide.md" in res["sources"]
    assert len(assistant.history) == 2


@patch("requests.post")
def test_ai_assistant_ask_question_stream(mock_post):
    """Test AIAssistant streaming chunk parsing and callbacks."""
    # Yield dynamic byte chunks simulating server SSE stream
    chunks = [
        b'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        b'data: {"choices": [{"delta": {"content": " world"}}]}',
        b"data: [DONE]"
    ]

    mock_res = MagicMock(status_code=200)
    mock_res.iter_lines.return_value = chunks
    mock_post.return_value = mock_res

    assistant = AIAssistant()
    called_chunks = []

    def callback(text):
        called_chunks.append(text)

    res = assistant.ask_question(prompt="hi", stream=True, callback=callback)

    assert res["result"] == "Hello world"
    assert called_chunks == ["Hello", " world"]


@patch("requests.post")
def test_ai_assistant_connection_error(mock_post):
    """Verify elegant fallback results if the background server is offline."""
    mock_post.side_effect = requests.exceptions.ConnectionError("Offline")

    assistant = AIAssistant()
    res = assistant.ask_question("test question")
    assert "Could not connect" in res["result"]
    assert res["sources"] == []


def test_ai_assistant_query_docs():
    """Verify documentation queries register help indices."""
    from biopro_sdk.host.docs import docs_registry
    docs_registry.register_page("my_plugin", "index", "/path/to/help.md")

    assistant = AIAssistant()

    # Mock ask_question inside query_docs
    assistant.ask_question = MagicMock(return_value={"result": "Docs content"})

    res = assistant.query_docs("my_plugin", "how to align?")
    assert res == "Docs content"

    # Try plugin with empty docs
    res_empty = assistant.query_docs("unknown_plugin", "help")
    assert "No documentation" in res_empty
