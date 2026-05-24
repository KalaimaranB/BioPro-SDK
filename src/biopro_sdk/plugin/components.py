"""Semantic UI components for BioPro SDK.

Provides pre-styled button and component classes that respect the active theme
and maintain visual consistency across all plugins.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QFrame, QLabel, QPushButton

try:
    from biopro.ui.theme import Colors, Fonts, theme_manager
except ImportError:

    class FallbackColors:
        ACCENT_PRIMARY = "#007ACC"
        BG_DARKEST = "#121212"
        ACCENT_PRIMARY_HOVER = "#005999"
        BG_MEDIUM = "#1E1E1E"
        FG_SECONDARY = "#888888"
        GLOW_COLOR = "transparent"
        BG_DARK = "#1A1A1A"
        BORDER = "#333333"
        BG_LIGHT = "#252525"
        FG_PRIMARY = "#FFFFFF"

    class FallbackFonts:
        FAMILY_UI = "Segoe UI, Arial"
        FAMILY_HEADINGS = "Segoe UI, Arial"
        SIZE_LARGE = 18
        SIZE_NORMAL = 13

    Colors = FallbackColors
    Fonts = FallbackFonts

    class MockThemeManager:
        class MockSignal:
            def connect(self, callback):
                pass

        theme_changed = MockSignal()

    theme_manager = MockThemeManager()


def _connect_theme_signal(callback):
    theme_manager.theme_changed.connect(callback)
    callback()


class PrimaryButton(QPushButton):
    """Primary action button using accent color.

    Use this for the main action in your UI (e.g., "Run Analysis", "Apply Changes").
    Automatically respects the active theme and handles hover/disabled states.
    """

    def __init__(self, text: str, parent=None):
        """Create a primary button.

        Args:
            text: Button text
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._glow_effect = None
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-weight: bold;
                font-family: {Fonts.FAMILY_UI};
            }}
            QPushButton:hover {{ background-color: {Colors.ACCENT_PRIMARY_HOVER}; }}
            QPushButton:disabled {{ background-color: {Colors.BG_MEDIUM}; color: {Colors.FG_SECONDARY}; }}
        """)

        # Add "Lightsaber" glow if enabled in theme
        if Colors.GLOW_COLOR != "transparent":
            from PyQt6.QtGui import QColor
            from PyQt6.QtWidgets import QGraphicsDropShadowEffect

            if self._glow_effect is None:
                self._glow_effect = QGraphicsDropShadowEffect(self)
                self.setGraphicsEffect(self._glow_effect)

            if self._glow_effect is not None:
                self._glow_effect.setBlurRadius(15)
                self._glow_effect.setOffset(0, 0)
                self._glow_effect.setColor(QColor(Colors.GLOW_COLOR))
        else:
            if self._glow_effect:
                self.setGraphicsEffect(None)
                self._glow_effect = None


class SecondaryButton(QPushButton):
    """Secondary/outline button for non-critical actions.

    Use this for secondary actions like "Cancel", "Reset", or "Back".
    Provides visual distinction while maintaining hierarchy.
    """

    def __init__(self, text: str, parent=None):
        """Create a secondary button.

        Args:
            text: Button text
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 10px 20px;
                font-size: 13px;
                font-family: {Fonts.FAMILY_UI};
            }}
            QPushButton:hover {{ background-color: {Colors.BG_LIGHT}; border-color: {Colors.FG_SECONDARY}; }}
        """)


class DangerButton(QPushButton):
    """Destructive action button for delete/remove operations.

    Use this for dangerous actions that cannot be undone (even though BioPro
    has undo, make clear that this action is destructive).
    """

    def __init__(self, text: str, parent=None):
        """Create a danger button.

        Args:
            text: Button text
            parent: Parent widget
        """
        super().__init__(text, parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 13px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #c82333; }
        """)


class ModuleCard(QFrame):
    """Standardized, interactive card for lists and grids.

    Use this to display modules, plugins, or workflow steps in a grid layout.
    Automatically handles hover state and theme colors.
    """

    def __init__(self, parent=None):
        """Create a card.

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setObjectName("BioCard")
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        glow_css = ""
        if Colors.GLOW_COLOR != "transparent":
            glow_css = f"border: 1px solid {Colors.ACCENT_PRIMARY};"

        self.setStyleSheet(f"""
            QFrame#BioCard {{
                background-color: {Colors.BG_DARK};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                font-family: {Fonts.FAMILY_UI};
            }}
            QFrame#BioCard:hover {{
                border: 1px solid {Colors.ACCENT_PRIMARY};
                background-color: {Colors.BG_MEDIUM};
                {glow_css}
            }}
        """)


class HeaderLabel(QLabel):
    """Standardized H1 header label.

    Use this for section headers and major titles.
    """

    def __init__(self, text: str, parent=None):
        """Create a header label.

        Args:
            text: Label text
            parent: Parent widget
        """
        super().__init__(text, parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; "
            f"font-weight: bold; "
            f"font-family: {Fonts.FAMILY_HEADINGS}; "
            f"color: {Colors.FG_PRIMARY};"
        )


class SubtitleLabel(QLabel):
    """Standardized subtitle/secondary header label.

    Use this for subsection headers and secondary titles.
    """

    def __init__(self, text: str, parent=None):
        """Create a subtitle label.

        Args:
            text: Label text
            parent: Parent widget
        """
        super().__init__(text, parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600; color: {Colors.FG_PRIMARY};")
