"""Unit tests for the request dispatcher inside ui_daemon_runtime — the piece
that turns an incoming {"method": ..., "kwargs": ...} frame into a response
payload, independent of the stdio transport or Qt event loop around it.
"""

from karcytics_sdk.plugin.ui_daemon_runtime import RequestDispatcher


def test_dispatch_calls_registered_handler_with_kwargs():
    dispatcher = RequestDispatcher()
    dispatcher.register("greet", lambda kwargs: {"message": f"hello {kwargs['name']}"})

    result = dispatcher.dispatch({"method": "greet", "kwargs": {"name": "world"}})

    assert result == {"message": "hello world"}


def test_dispatch_unknown_method_returns_error_payload():
    dispatcher = RequestDispatcher()

    result = dispatcher.dispatch({"method": "nope", "kwargs": {}})

    assert "error" in result
    assert "nope" in result["error"]


def test_dispatch_handler_exception_is_contained_as_error_payload():
    def _boom(kwargs):  # noqa: ARG001
        raise ValueError("kaboom")

    dispatcher = RequestDispatcher()
    dispatcher.register("boom", _boom)

    result = dispatcher.dispatch({"method": "boom", "kwargs": {}})

    assert "error" in result
    assert "kaboom" in result["error"]


def test_later_registration_overrides_earlier_handler():
    dispatcher = RequestDispatcher()
    dispatcher.register("greet", lambda kwargs: {"v": 1})  # noqa: ARG005
    dispatcher.register("greet", lambda kwargs: {"v": 2})  # noqa: ARG005

    result = dispatcher.dispatch({"method": "greet", "kwargs": {}})

    assert result == {"v": 2}
