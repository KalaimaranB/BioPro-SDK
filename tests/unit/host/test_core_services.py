"""Unit tests for karcytics_sdk.host.core_services."""

import pytest
import requests

from karcytics_sdk.host.core_services import (
    CoreServicesClient,
    CoreServicesServer,
    RemoteProjectManager,
    fetch_remote_project_manager,
)


@pytest.fixture
def server():
    srv = CoreServicesServer()
    srv.start()
    yield srv
    srv.stop()


@pytest.fixture
def client(server):
    return CoreServicesClient(server.port, token=server.token)


def test_registered_method_round_trips(server, client):
    server.register("echo", lambda kwargs: {"you_said": kwargs.get("msg")})

    result = client.call("echo", msg="hello")

    assert result == {"you_said": "hello"}


def test_unregistered_method_raises_on_client(client):
    with pytest.raises(RuntimeError, match="No handler registered"):
        client.call("nonexistent_method")


def test_handler_exception_surfaces_as_client_error(server, client):
    def _boom(kwargs):  # noqa: ARG001
        raise ValueError("core-side failure")

    server.register("boom", _boom)

    with pytest.raises(RuntimeError, match="core-side failure"):
        client.call("boom")


def test_unregister_removes_method(server, client):
    server.register("temp", lambda kwargs: "ok")  # noqa: ARG005
    assert client.call("temp") == "ok"

    server.unregister("temp")

    with pytest.raises(RuntimeError, match="No handler registered"):
        client.call("temp")


def test_multiple_methods_dispatch_independently(server, client):
    server.register("task_scheduler.submit", lambda kwargs: {"task_id": "abc123"})
    server.register("diagnostics.report_error", lambda kwargs: {"received": kwargs.get("message")})

    assert client.call("task_scheduler.submit", analyzer="dummy") == {"task_id": "abc123"}
    assert client.call("diagnostics.report_error", message="oops") == {"received": "oops"}


def test_start_is_idempotent():
    srv = CoreServicesServer()
    srv.start()
    port_before = srv.port
    srv.start()  # must not rebind or raise
    assert srv.port == port_before
    srv.stop()


def test_port_raises_before_start():
    srv = CoreServicesServer()
    with pytest.raises(RuntimeError, match="not running"):
        _ = srv.port


def test_token_is_auto_generated_and_nonempty():
    srv = CoreServicesServer()
    assert isinstance(srv.token, str)
    assert len(srv.token) >= 16


def test_explicit_token_is_honored():
    srv = CoreServicesServer(token="my-fixed-token")  # noqa: S106
    assert srv.token == "my-fixed-token"


def test_request_without_auth_header_is_rejected(server):
    server.register("echo", lambda kwargs: kwargs)

    resp = requests.post(f"http://127.0.0.1:{server.port}/rpc", json={"method": "echo", "kwargs": {}})

    assert resp.status_code == 401


def test_request_with_wrong_token_is_rejected(server):
    server.register("echo", lambda kwargs: kwargs)
    client = CoreServicesClient(server.port, token="wrong-token")  # noqa: S106

    with pytest.raises(RuntimeError, match="Unauthorized"):
        client.call("echo")


def test_request_with_malformed_auth_header_is_rejected(server):
    server.register("echo", lambda kwargs: kwargs)

    resp = requests.post(
        f"http://127.0.0.1:{server.port}/rpc",
        json={"method": "echo", "kwargs": {}},
        headers={"Authorization": server.token},  # missing "Bearer " prefix
    )

    assert resp.status_code == 401


def test_fetch_remote_project_manager_returns_none_with_no_active_project(server, client):
    server.register("project.get_info", lambda _kwargs: None)

    assert fetch_remote_project_manager(client) is None


def test_fetch_remote_project_manager_wraps_the_info_reply(server, client, tmp_path):
    project_dir = tmp_path / "proj"
    server.register(
        "project.get_info",
        lambda _kwargs: {
            "project_dir": str(project_dir),
            "assets_dir": str(project_dir / "assets"),
            "project_name": "My Project",
        },
    )

    pm = fetch_remote_project_manager(client)

    assert isinstance(pm, RemoteProjectManager)
    assert pm.project_dir == project_dir
    assert pm.assets_dir == project_dir / "assets"
    assert pm.project_name == "My Project"


def test_remote_project_manager_add_image_forwards_kwargs(server, client, tmp_path):
    calls = []
    server.register(
        "project.get_info",
        lambda _kwargs: {"project_dir": str(tmp_path), "assets_dir": str(tmp_path / "assets"), "project_name": "P"},
    )
    server.register(
        "project.add_image",
        lambda kwargs: (calls.append(kwargs), "deadbeef")[1],
    )

    pm = fetch_remote_project_manager(client)
    file_hash = pm.add_image("/some/file.fcs", copy_to_workspace=True, subfolder="raw")

    assert file_hash == "deadbeef"
    assert calls == [{"filepath": "/some/file.fcs", "copy_to_workspace": True, "subfolder": "raw"}]


def test_remote_project_manager_get_asset_path_round_trips(server, client, tmp_path):
    resolved = tmp_path / "assets" / "sample.fcs"
    server.register(
        "project.get_info",
        lambda _kwargs: {"project_dir": str(tmp_path), "assets_dir": str(tmp_path / "assets"), "project_name": "P"},
    )
    server.register("project.get_asset_path", lambda kwargs: str(resolved) if kwargs["file_hash"] == "abc" else None)

    pm = fetch_remote_project_manager(client)

    assert pm.get_asset_path("abc") == resolved
    assert pm.get_asset_path("missing") is None


def test_remote_project_manager_save_and_load_workflow_round_trip(server, client, tmp_path):
    server.register(
        "project.get_info",
        lambda _kwargs: {"project_dir": str(tmp_path), "assets_dir": str(tmp_path / "assets"), "project_name": "P"},
    )
    server.register("project.save_workflow", lambda kwargs: f"{kwargs['module_id']}_{kwargs['filename']}.json")
    server.register("project.load_workflow_payload", lambda kwargs: {"filename": kwargs["filename"], "steps": []})

    pm = fetch_remote_project_manager(client)
    new_filename = pm.save_workflow("flow_cytometry", {"a": 1}, {"note": "x"}, filename="wf")
    payload = pm.load_workflow_payload(new_filename)

    assert new_filename == "flow_cytometry_wf.json"
    assert payload == {"filename": new_filename, "steps": []}


def test_remote_project_manager_attach_workflow_file_forwards_kwargs(server, client, tmp_path):
    calls = []
    server.register(
        "project.get_info",
        lambda _kwargs: {"project_dir": str(tmp_path), "assets_dir": str(tmp_path / "assets"), "project_name": "P"},
    )
    server.register("project.attach_workflow_file", lambda kwargs: (calls.append(kwargs), {"key": kwargs["key"]})[1])

    pm = fetch_remote_project_manager(client)
    record = pm.attach_workflow_file("wf.json", "/tmp/att.fcs", key="raw_fcs")

    assert record == {"key": "raw_fcs"}
    assert calls == [
        {
            "wf_filename": "wf.json",
            "source_path": "/tmp/att.fcs",
            "key": "raw_fcs",
            "description": "",
            "mime_hint": "application/octet-stream",
        }
    ]


def test_remote_workflow_manager_list_all_and_load_attachments(server, client, tmp_path):
    server.register(
        "project.get_info",
        lambda _kwargs: {"project_dir": str(tmp_path), "assets_dir": str(tmp_path / "assets"), "project_name": "P"},
    )
    server.register("project.list_workflows", lambda _kwargs: [{"filename": "wf.json"}])
    server.register("project.load_attachments", lambda kwargs: [{"filename": kwargs["filename"], "key": "raw_fcs"}])

    pm = fetch_remote_project_manager(client)

    assert pm.workflows.list_all() == [{"filename": "wf.json"}]
    assert pm.workflows.load_attachments("wf.json") == [{"filename": "wf.json", "key": "raw_fcs"}]
