"""Unit tests for ui_daemon_runtime's isolated-window menu bar.

An isolated plugin's window has no menu bar unless run() builds one — see
_build_menu_bar's docstring. File > Close Window is always present and
purely local; Theme is only added when the Hub registered a
CoreServicesServer (KARCYTICS_CORE_SERVICES_PORT/TOKEN env vars), and is
populated lazily so a window that never opens that menu never pays for the
Hub round-trip.
"""

from unittest.mock import MagicMock, patch

from PyQt6.QtWidgets import QMainWindow, QMenu

from karcytics_sdk.plugin.ui_daemon_runtime import (
    _build_menu_bar,
    _build_theme_menu,
    _format_about_developer,
    _format_about_karcytics,
    _show_fetched_about,
)


def _menu_named(window: QMainWindow, title: str) -> QMenu:
    return next(a.menu() for a in window.menuBar().actions() if a.text() == title)


def test_build_menu_bar_always_adds_file_close_action(qapp, monkeypatch):  # noqa: ARG001
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_PORT", raising=False)
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_TOKEN", raising=False)
    window = QMainWindow()

    _build_menu_bar(window, MagicMock())

    menus = {action.text(): action for action in window.menuBar().actions()}
    assert "&File" in menus
    file_actions = [a.text() for a in menus["&File"].menu().actions()]
    assert "&Close Window" in file_actions


def test_build_menu_bar_skips_theme_menu_without_core_services_env(qapp, monkeypatch):  # noqa: ARG001
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_PORT", raising=False)
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_TOKEN", raising=False)
    window = QMainWindow()

    _build_menu_bar(window, MagicMock())

    menus = {action.text() for action in window.menuBar().actions()}
    assert "&Theme" not in menus


def test_build_menu_bar_adds_theme_menu_when_core_services_configured(qapp, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_PORT", "12345")
    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_TOKEN", "secret-token")  # noqa: S105
    window = QMainWindow()

    with patch("karcytics_sdk.host.core_services.CoreServicesClient") as mock_client_cls:
        _build_menu_bar(window, MagicMock())

    mock_client_cls.assert_called_once_with(12345, token="secret-token")
    menus = {action.text() for action in window.menuBar().actions()}
    assert "&Theme" in menus


def test_theme_menu_has_a_disabled_placeholder_before_first_show(qapp):  # noqa: ARG001
    """Not cosmetic: a top-level QMenu left genuinely empty until aboutToShow
    never syncs into the real native macOS menu bar at all — confirmed live
    via Accessibility introspection of a real spawned window. The
    placeholder exists purely so the menu has content the moment Qt's
    Cocoa bridge first builds it; the network round-trip itself still only
    happens lazily, on the user's first click (checked next).
    """
    menu = QMenu()
    client = MagicMock()
    logger = MagicMock()

    _build_theme_menu(menu, client, logger)

    assert len(menu.actions()) == 1
    assert menu.actions()[0].isEnabled() is False
    client.call.assert_not_called()


def test_theme_menu_populates_lazily_on_first_show(qapp):  # noqa: ARG001
    menu = QMenu()
    client = MagicMock()
    client.call.return_value = {"Dark Themes": [["Default Dark", "/path/dark.json"]]}
    logger = MagicMock()

    _build_theme_menu(menu, client, logger)
    client.call.assert_not_called()

    menu.aboutToShow.emit()

    client.call.assert_called_once_with("theme.list_categorized_themes")
    category_actions = [a.text() for a in menu.actions()]
    assert "Dark Themes" in category_actions
    assert "Loading…" not in category_actions  # placeholder removed, not just hidden


def test_theme_menu_action_switches_theme_via_core_services(qapp):  # noqa: ARG001
    menu = QMenu()
    client = MagicMock()
    client.call.return_value = {"Dark Themes": [["Default Dark", "/path/dark.json"]]}
    logger = MagicMock()

    _build_theme_menu(menu, client, logger)
    menu.aboutToShow.emit()

    submenu = menu.actions()[0].menu()
    submenu.actions()[0].trigger()

    client.call.assert_any_call("theme.switch_theme", path="/path/dark.json")


def test_theme_menu_populate_runs_only_once(qapp):  # noqa: ARG001
    menu = QMenu()
    client = MagicMock()
    client.call.return_value = {}
    logger = MagicMock()

    _build_theme_menu(menu, client, logger)
    menu.aboutToShow.emit()
    menu.aboutToShow.emit()

    assert client.call.call_count == 1


def test_theme_menu_shows_unavailable_placeholder_when_hub_call_fails(qapp):  # noqa: ARG001
    menu = QMenu()
    client = MagicMock()
    client.call.side_effect = RuntimeError("no route to Hub")
    logger = MagicMock()

    _build_theme_menu(menu, client, logger)
    menu.aboutToShow.emit()

    action_texts = [a.text() for a in menu.actions()]
    assert "(Hub unavailable)" in action_texts
    assert menu.actions()[0].isEnabled() is False
    logger.warning.assert_called_once()


def test_build_menu_bar_skips_help_menu_without_core_services_env(qapp, monkeypatch):  # noqa: ARG001
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_PORT", raising=False)
    monkeypatch.delenv("KARCYTICS_CORE_SERVICES_TOKEN", raising=False)
    window = QMainWindow()

    _build_menu_bar(window, MagicMock())

    menus = {action.text() for action in window.menuBar().actions()}
    assert "&Help" not in menus


def test_build_menu_bar_adds_help_menu_with_about_actions(qapp, monkeypatch):  # noqa: ARG001
    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_PORT", "12345")
    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_TOKEN", "secret-token")  # noqa: S105
    window = QMainWindow()

    with patch("karcytics_sdk.host.core_services.CoreServicesClient"):
        _build_menu_bar(window, MagicMock())

    menus = {action.text() for action in window.menuBar().actions()}
    assert "&Help" in menus
    help_actions = [a.text() for a in _menu_named(window, "&Help").actions()]
    assert help_actions == ["About Karcytics", "About the Developer", "🎓 Academy"]


def test_show_fetched_about_shows_formatted_info(qapp):  # noqa: ARG001
    window = QMainWindow()
    client = MagicMock()
    client.call.return_value = {
        "name": "Karcytics™",
        "version": "1.2.3",
        "tagline": "Bio Analysis Made Simple",
        "description": "d",
        "copyright": "c",
    }
    logger = MagicMock()

    with patch("karcytics_sdk.plugin.ui_daemon_runtime.QMessageBox") as mock_box:
        _show_fetched_about(
            window, client, logger, "menu.get_about_karcytics", "About Karcytics", _format_about_karcytics
        )

    client.call.assert_called_once_with("menu.get_about_karcytics")
    mock_box.about.assert_called_once()
    shown_window, shown_title, shown_html = mock_box.about.call_args[0]
    assert shown_window is window
    assert shown_title == "About Karcytics"
    assert "1.2.3" in shown_html
    assert "Bio Analysis Made Simple" in shown_html


def test_show_fetched_about_warns_when_hub_is_unreachable(qapp):  # noqa: ARG001
    window = QMainWindow()
    client = MagicMock()
    client.call.side_effect = RuntimeError("no route to Hub")
    logger = MagicMock()

    with patch("karcytics_sdk.plugin.ui_daemon_runtime.QMessageBox") as mock_box:
        _show_fetched_about(
            window,
            client,
            logger,
            "menu.get_about_developer",
            "About the Developer",
            _format_about_developer,
        )

    mock_box.warning.assert_called_once()
    mock_box.about.assert_not_called()
    logger.warning.assert_called_once()


def test_format_about_karcytics_includes_every_field():
    html = _format_about_karcytics(
        {"name": "N", "version": "1.0", "tagline": "T", "description": "D", "copyright": "C"}
    )
    for field in ("N", "1.0", "T", "D", "C"):
        assert field in html


def test_help_menu_about_actions_use_no_menu_role(qapp, monkeypatch):  # noqa: ARG001
    r"""Not cosmetic: Qt auto-classifies an action whose text matches
    /^about\b/i as AboutRole unless told otherwise, and macOS allows only
    one About-role item per app menu — a slot the OS-injected "About
    Python" already occupies for this bare, unbundled interpreter process.
    Confirmed live: with the default auto-detected role, both actions
    vanished from the native bar entirely (not merged into the app menu,
    just gone), and the now-empty Help menu didn't sync either. NoRole
    keeps them as plain items in this window's own Help menu.
    """
    from PyQt6.QtGui import QAction

    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_PORT", "12345")
    monkeypatch.setenv("KARCYTICS_CORE_SERVICES_TOKEN", "secret-token")  # noqa: S105
    window = QMainWindow()

    with patch("karcytics_sdk.host.core_services.CoreServicesClient"):
        _build_menu_bar(window, MagicMock())

    for action in _menu_named(window, "&Help").actions():
        assert action.menuRole() == QAction.MenuRole.NoRole


def test_format_about_developer_renders_each_bio_paragraph():
    html = _format_about_developer({"name": "N", "role": "R", "bio": "para one\n\npara two"})
    assert "N" in html
    assert "R" in html
    assert "para one" in html
    assert "para two" in html
    assert html.count("<p>") == 3  # role + two bio paragraphs


class TestWireAcademyMenu:
    """`_wire_academy_menu` connects the Help menu's "🎓 Academy" action
    (built earlier by `_build_help_menu`, before `panel` exists) once the
    real panel is available — see `run()`'s own docstring for why that
    can't happen in one pass.
    """

    def test_clicking_with_no_registered_courses_shows_info_not_a_crash(self, qapp, monkeypatch):  # noqa: ARG002
        from PyQt6.QtWidgets import QWidget

        from karcytics_sdk.plugin.ui_daemon_runtime import _build_help_menu, _wire_academy_menu

        monkeypatch.setenv("KARCYTICS_PLUGIN_ID", "__test_plugin_with_no_courses__")
        window = QMainWindow()
        _build_help_menu(window, MagicMock(), MagicMock())
        panel = QWidget()

        shown = []
        with patch("karcytics_sdk.plugin.dialogs.show_info", side_effect=lambda *a, **k: shown.append(a)):
            _wire_academy_menu(window, panel, MagicMock())
            window._academy_menu_action.trigger()

        assert shown, "show_info should be called when no courses are registered"
        assert not hasattr(window, "_academy_overlay")

    def test_clicking_with_a_registered_course_starts_it_and_shows_the_overlay(
        self,
        qapp,
        monkeypatch,  # noqa: ARG002
    ):
        from PyQt6.QtWidgets import QWidget

        from karcytics_sdk.plugin.runtime_services import tutorial_manager
        from karcytics_sdk.plugin.tutorial_models import Course, InfoStep
        from karcytics_sdk.plugin.ui_daemon_runtime import _build_help_menu, _wire_academy_menu

        plugin_id = "__test_plugin_with_a_course__"
        monkeypatch.setenv("KARCYTICS_PLUGIN_ID", plugin_id)
        course = Course(id="__test_course_for_menu_wiring__", title="Test", steps=[InfoStep(id="s1", text="hi")])
        tutorial_manager.register_storyboard(plugin_id, course)

        window = QMainWindow()
        _build_help_menu(window, MagicMock(), MagicMock())
        panel = QWidget()
        window.setCentralWidget(panel)
        window.show()

        _wire_academy_menu(window, panel, MagicMock())
        window._academy_menu_action.trigger()

        assert tutorial_manager.active_course is course
        assert tutorial_manager.current_step.id == "s1"
        assert window._academy_overlay.isVisible()
        window.close()
