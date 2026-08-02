"""Fallback theme stubs for plugin standalone testing."""

import sys

from PyQt6.QtCore import QObject, pyqtSignal


class DynamicColors:
    DARK = {
        "BG_DARKEST": "#0d1117",
        "BG_DARK": "#161b22",
        "BG_MEDIUM": "#21262d",
        "BG_LIGHT": "#30363d",
        "FG_PRIMARY": "#e6edf3",
        "FG_SECONDARY": "#8b949e",
        "FG_DISABLED": "#484f58",
        "BORDER": "#30363d",
        "BORDER_FOCUS": "#58a6ff",
        "ACCENT_PRIMARY": "#00bcd4",
        "ACCENT_PRIMARY_HOVER": "#0097a7",
        "ACCENT_NEGATIVE": "#ef5350",
        "GLOW_COLOR": "rgba(0, 188, 212, 0.4)",
        "DNA_PRIMARY": "#00bcd4",
    }
    LIGHT = {
        "BG_DARKEST": "#f6f8fa",
        "BG_DARK": "#ffffff",
        "BG_MEDIUM": "#f0f6fc",
        "BG_LIGHT": "#e1e4e8",
        "FG_PRIMARY": "#24292e",
        "FG_SECONDARY": "#57606a",
        "FG_DISABLED": "#959da5",
        "BORDER": "#d0d7de",
        "BORDER_FOCUS": "#0969da",
        "ACCENT_PRIMARY": "#00bcd4",
        "ACCENT_PRIMARY_HOVER": "#0097a7",
        "ACCENT_NEGATIVE": "#cf222e",
        "GLOW_COLOR": "rgba(0, 188, 212, 0.2)",
        "DNA_PRIMARY": "#00bcd4",
    }

    _mode = "dark"

    @classmethod
    def set_theme(cls, theme_name: str):
        cls._mode = "light" if "light" in theme_name.lower() else "dark"
        palette = cls.LIGHT if cls._mode == "light" else cls.DARK
        for k, v in palette.items():
            setattr(cls, k, v)


class _ColorsProxy:
    def __getattr__(self, name):
        if "biopro.ui.theme" in sys.modules:
            return getattr(sys.modules["biopro.ui.theme"].Colors, name)
        return getattr(DynamicColors, name, "#0d1117")

    def __setattr__(self, name, value):
        if name.startswith("_"):
            super().__setattr__(name, value)
        elif "biopro.ui.theme" in sys.modules:
            setattr(sys.modules["biopro.ui.theme"].Colors, name, value)
        else:
            setattr(DynamicColors, name, value)


Colors = _ColorsProxy()
DynamicColors.set_theme("dark")


class Fonts:
    SIZE_SMALL = 11
    SIZE_NORMAL = 13
    SIZE_LARGE = 18
    FAMILY_UI = "Inter, sans-serif"
    FAMILY_HEADINGS = "Inter, sans-serif"


class _ThemeManagerProxy(QObject):
    theme_changed = pyqtSignal()

    def __init__(self):
        super().__init__()

    def connect(self, slot):
        if "biopro.ui.theme" in sys.modules:
            sys.modules["biopro.ui.theme"].theme_manager.theme_changed.connect(slot)
        self.theme_changed.connect(slot)

    def set_theme(self, theme_name: str):
        DynamicColors.set_theme(theme_name)
        self.theme_changed.emit()


theme_manager = _ThemeManagerProxy()
