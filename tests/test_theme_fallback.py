from karcytics_sdk.plugin.theme_fallback import Colors, Fonts, theme_manager


def test_theme_fallback_colors():
    assert Colors.BG_DARKEST == "#0d1117"
    assert Colors.ACCENT_PRIMARY == "#00bcd4"


def test_theme_fallback_fonts():
    assert Fonts.SIZE_SMALL == 11
    assert Fonts.FAMILY_UI == "Inter, sans-serif"


def test_theme_manager_dummy_signal():
    def dummy_cb():
        pass

    # Just to reach 100% coverage on the connect/disconnect methods
    theme_manager.theme_changed.connect(dummy_cb)
    theme_manager.theme_changed.disconnect(dummy_cb)
