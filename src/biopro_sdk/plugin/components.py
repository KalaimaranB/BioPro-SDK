"""Semantic UI components for BioPro SDK.

Provides pre-styled button and component classes that respect the active theme
and maintain visual consistency across all plugins.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStyledItemDelegate,
    QTableWidget,
    QWidget,
)

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
        SIZE_SMALL = 11

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


def apply_component_style(widget: QWidget, component_type: str) -> None:
    """Helper function to dynamically apply theme CSS without requiring a subclass."""
    # Useful for injecting basic styles into standard Qt widgets directly
    pass


class BioButton(QPushButton):
    """Base unified button class.

    Variants: 'primary', 'secondary', 'danger'.
    """

    def __init__(self, text: str, variant: str = "primary", parent=None):
        super().__init__(text, parent)
        self.variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._glow_effect = None
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        if self.variant == "primary":
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

        elif self.variant == "secondary":
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
        elif self.variant == "danger":
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


class PrimaryButton(BioButton):
    """Primary action button using accent color (backwards compatible)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, variant="primary", parent=parent)


class SecondaryButton(BioButton):
    """Secondary/outline button for non-critical actions (backwards compatible)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, variant="secondary", parent=parent)


class DangerButton(BioButton):
    """Destructive action button for delete/remove operations (backwards compatible)."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, variant="danger", parent=parent)


class BioToggleButton(QPushButton):
    """A button that handles active/inactive state natively."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
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
            QPushButton:checked {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
                border: none;
                font-weight: bold;
            }}
        """)


class BioRunButton(PrimaryButton):
    """Pre-configured action button for starting tasks."""

    def __init__(self, text: str = "🧬 Run", parent=None):
        super().__init__(text, parent)


class BioCancelButton(SecondaryButton):
    """Pre-configured action button for cancelling tasks."""

    def __init__(self, text: str = "⏹ Cancel", parent=None):
        super().__init__(text, parent)


class BioHelpButton(QPushButton):
    """Small help (?) button for tooltips and dialogs."""

    def __init__(self, parent=None):
        super().__init__("?", parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(20, 20)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.FG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
                font-family: {Fonts.FAMILY_UI};
            }}
            QPushButton:hover {{
                background-color: {Colors.BG_LIGHT};
                color: {Colors.FG_PRIMARY};
                border-color: {Colors.FG_PRIMARY};
            }}
        """)


class ModuleCard(QFrame):
    """Standardized, interactive card for lists and grids."""

    def __init__(self, parent=None):
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
    """Standardized H1 header label."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(
            f"font-size: {Fonts.SIZE_LARGE}px; "
            f"font-weight: bold; "
            f"font-family: {Fonts.FAMILY_HEADINGS}; "
            f"color: {Colors.FG_PRIMARY};"
        )


BioHeaderLabel = HeaderLabel


class SubtitleLabel(QLabel):
    """Standardized subtitle/secondary header label."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"font-size: {Fonts.SIZE_NORMAL}px; font-weight: 600; color: {Colors.FG_PRIMARY};")


class BioCaptionLabel(QLabel):
    """For educational text or hints."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        try:
            size = getattr(Fonts, "SIZE_SMALL", 11)
        except AttributeError:
            size = 11
        self.setStyleSheet(f"font-size: {size}px; color: {Colors.FG_SECONDARY};")


class BioStatusLabel(QLabel):
    """Standardized italicized status text."""

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setWordWrap(True)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"font-size: {Fonts.SIZE_NORMAL}px; font-style: italic; color: {Colors.FG_SECONDARY};")


class BioComboBox(QComboBox):
    """Standardized combo box."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setItemDelegate(QStyledItemDelegate(self))
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QComboBox {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border-left: 1px solid {Colors.BORDER};
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                selection-background-color: {Colors.ACCENT_PRIMARY};
                selection-color: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
                outline: none;
            }}
        """)


class BioSpinBox(QSpinBox):
    """Standardized numeric input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QSpinBox {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)


class BioDoubleSpinBox(QDoubleSpinBox):
    """Standardized floating point input."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QDoubleSpinBox {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)


class BioLineEdit(QLineEdit):
    """Standardized text input."""

    def __init__(self, text: str = "", parent=None):
        super().__init__(text, parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QLineEdit {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
        """)


class BioListWidget(QListWidget):
    """Standardized list widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: transparent;
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
            }}
            QListWidget::item:selected {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
            }}
        """)


class BioTableWidget(QTableWidget):
    """Standardized table widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
                gridline-color: {Colors.BORDER};
            }}
            QHeaderView::section {{
                background-color: {Colors.BG_MEDIUM};
                color: {Colors.FG_PRIMARY};
                border: 1px solid {Colors.BORDER};
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
            }}
        """)


class BioSplitter(QSplitter):
    """Standardized splitter."""

    def __init__(self, orientation=Qt.Orientation.Horizontal, parent=None):
        super().__init__(orientation, parent)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QSplitter::handle {{
                background-color: {Colors.BORDER};
            }}
        """)


class BioScrollArea(QScrollArea):
    """Standardized scroll area with transparent background."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWidgetResizable(True)
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
        """)
