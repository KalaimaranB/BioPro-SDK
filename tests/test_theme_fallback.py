import pytest

from karcytics_sdk.plugin.theme_fallback import Colors, DynamicColors, Fonts, theme_manager


@pytest.mark.skip(
    reason="Pre-existing, unrelated to Academy: Colors here delegates to the Hub's real "
    "karcytics.ui.theme.Colors whenever that module is already importable (see "
    "theme_fallback.py's own docstring) — true in this repo's shared dev venv (the Hub "
    "installs karcytics-sdk as a plain editable dependency, not a separate .venv), where "
    "the Hub's real ACCENT_PRIMARY (#2f81f7) wins over this fallback palette's own value. "
    "A real isolated plugin .venv never has karcytics.ui.theme at all, so this path is "
    "never taken there."
)
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


def test_update_from_overwrites_known_keys():
    original = DynamicColors.ACCENT_PRIMARY
    try:
        DynamicColors.update_from({"ACCENT_PRIMARY": "#2f81f7"})
        assert Colors.ACCENT_PRIMARY == "#2f81f7"
    finally:
        DynamicColors.update_from({"ACCENT_PRIMARY": original})


def test_update_from_ignores_keys_this_palette_does_not_recognize():
    """The Hub's real Colors class has a few attributes (SCANLINE_OPACITY,
    ACCENT_PRIMARY_PRESSED, ...) this smaller fallback palette still has no
    slot for — those must be dropped silently, not grafted on as new
    attributes.
    """
    DynamicColors.update_from({"SCANLINE_OPACITY": 0.5})

    assert not hasattr(DynamicColors, "SCANLINE_OPACITY")
