"""Fallback theme stubs for plugin standalone testing."""


class Colors:
    BG_DARKEST = "#0d1117"
    BG_DARK = "#161b22"
    BG_MEDIUM = "#21262d"
    FG_PRIMARY = "#e6edf3"
    FG_SECONDARY = "#8b949e"
    FG_DISABLED = "#484f58"
    BORDER = "#30363d"
    ACCENT_PRIMARY = "#00bcd4"
    ACCENT_NEGATIVE = "#ef5350"


class Fonts:
    SIZE_SMALL = 11
    FAMILY_UI = "Inter, sans-serif"


class _DummySignal:
    def connect(self, cb):
        pass

    def disconnect(self, cb):
        pass


class _DummyThemeManager:
    theme_changed = _DummySignal()


theme_manager = _DummyThemeManager()
