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
    QVBoxLayout,
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
        BORDER_FOCUS = "#007ACC"

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


def _apply_global_sdk_styles() -> None:
    """Inject QToolTip styling globally and configure the QApplication palette for dark mode."""
    import re

    from PyQt6.QtGui import QColor, QPalette
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if not isinstance(app, QApplication):
        return

    # --- 0. Enforce Fusion Style Engine ---
    # macOS native style engine heavily ignores custom background colors for native containers (tooltips, dropdowns).
    # Forcing Fusion ensures our theme correctly styles everything cross-platform.
    app.setStyle("Fusion")

    # --- 1. Enforce Dark Palette Globally ---
    # This ensures native OS wrappers (like macOS dropdown menus) use dark backgrounds instead of white.
    palette = app.palette()
    palette.setColor(QPalette.ColorRole.Window, QColor(Colors.BG_DARK))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(Colors.BG_MEDIUM))
    palette.setColor(QPalette.ColorRole.Text, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(Colors.BG_LIGHT))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(Colors.FG_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(Colors.ACCENT_PRIMARY))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(Colors.BG_DARKEST))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(Colors.BG_DARKEST))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(Colors.FG_PRIMARY))
    app.setPalette(palette)

    # --- 2. Global Stylesheet Overrides ---
    qss = app.styleSheet() or ""
    # Remove any existing QToolTip block
    qss = re.sub(r"QToolTip\s*\{[^}]*\}", "", qss)

    try:
        family = getattr(Fonts, "FAMILY_UI", "Arial")
    except NameError:
        family = "Arial"

    tooltip_qss = f"""
        QToolTip {{
            color: #ffffff;
            background-color: {Colors.BG_DARKEST};
            border: 1px solid {Colors.BORDER_FOCUS};
            padding: 5px 8px;
            font-family: {family};
            font-size: 11px;
        }}
    """

    app.setStyleSheet(qss + tooltip_qss)


try:
    _connect_theme_signal(_apply_global_sdk_styles)
except Exception:
    pass


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
        self.setObjectName(f"BioButton_{variant}")
        self.variant = variant
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._glow_effect = None
        self.custom_css_overrides = ""
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setProperty("variant", self.variant)
        self.style().unpolish(self)
        self.style().polish(self)

        if self.custom_css_overrides:
            self.setStyleSheet(f"QPushButton {{ {self.custom_css_overrides} }}")
        else:
            self.setStyleSheet("")

        if self.variant == "primary" and Colors.GLOW_COLOR != "transparent":
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
        self.setObjectName("BioToggleButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        # Extensible defaults that subclasses or instances can configure
        self.custom_css_overrides = ""

        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.style().unpolish(self)
        self.style().polish(self)

        if self.custom_css_overrides:
            self.setStyleSheet(f"QPushButton#BioToggleButton {{ {self.custom_css_overrides} }}")
        else:
            self.setStyleSheet("")


class BioRunButton(PrimaryButton):
    """Pre-configured action button for starting tasks."""

    def __init__(self, text: str = "🧬 Run", parent=None):
        super().__init__(text, parent)


class BioCancelButton(SecondaryButton):
    """Pre-configured action button for cancelling tasks."""

    def __init__(self, text: str = "⏹ Cancel", parent=None):
        super().__init__(text, parent)


class _HelpPopup(QWidget):
    """Rich popup for help buttons."""

    def __init__(self, text: str, title: str = "", parent=None):
        super().__init__(parent, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)

        container = QFrame()
        container.setObjectName("PopupContainer")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 12, 12, 12)
        container_layout.setSpacing(6)

        if title:
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet(
                f"font-weight: bold; color: {Colors.ACCENT_PRIMARY}; font-family: {Fonts.FAMILY_UI}; font-size: 13px;"
            )
            container_layout.addWidget(title_lbl)

        text_lbl = QLabel(text)
        text_lbl.setWordWrap(True)
        text_lbl.setMinimumWidth(200)
        text_lbl.setMaximumWidth(400)
        text_lbl.setStyleSheet(
            f"color: {Colors.FG_PRIMARY}; font-family: {Fonts.FAMILY_UI}; font-size: 12px; line-height: 1.4;"
        )
        container_layout.addWidget(text_lbl)

        layout.addWidget(container)

        self.setStyleSheet(f"""
            QFrame#PopupContainer {{
                background-color: {Colors.BG_DARKEST};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
            }}
        """)


class BioHelpButton(QPushButton):
    """Small help (?) button that shows a rich popup dialog on click."""

    def __init__(self, parent=None):
        super().__init__("?", parent)
        self.setObjectName("BioHelpButton")
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(20, 20)
        self._help_text = ""
        self._help_title = ""
        self.clicked.connect(self._show_popup)
        _connect_theme_signal(self._apply_theme_styles)

    def setHelpText(self, text: str, title: str = "") -> None:
        """Set the detailed help text and optional title for the popup."""
        self._help_text = text
        self._help_title = title

    def setToolTip(self, text: str | None) -> None:
        """Override to use the click popup instead of the native hover tooltip for backwards compatibility."""
        super().setToolTip("")
        self.setHelpText(text or "")

    def _show_popup(self) -> None:
        if not self._help_text:
            return

        self._popup = _HelpPopup(self._help_text, self._help_title, self.window())
        self._popup.adjustSize()

        # Position the popup below the button
        pos = self.mapToGlobal(self.rect().bottomLeft())
        # Offset slightly for aesthetics
        pos.setY(pos.y() + 5)
        pos.setX(pos.x() - 10)
        self._popup.move(pos)
        self._popup.show()

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QPushButton#BioHelpButton {{
                background-color: transparent;
                color: {Colors.FG_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 10px;
                font-size: 11px;
                font-weight: bold;
                font-family: {Fonts.FAMILY_UI};
                padding: 0px;
                margin: 0px;
            }}
            QPushButton#BioHelpButton:hover {{
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
        from PyQt6.QtWidgets import QListView

        # Override native macOS popup view to allow proper styling
        view = QListView()
        self.setView(view)
        self.setItemDelegate(QStyledItemDelegate(self))
        _connect_theme_signal(self._apply_theme_styles)

    def _apply_theme_styles(self) -> None:
        self.setStyleSheet(f"""
            QComboBox {{
                combobox-popup: 0;
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
                border-radius: 4px;
                outline: none;
                padding: 2px;
            }}
            QComboBox QAbstractItemView::item {{
                min-height: 24px;
                padding: 2px 4px;
                border-radius: 2px;
            }}
            QComboBox QAbstractItemView::item:hover {{
                background-color: {Colors.BG_LIGHT};
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: {Colors.ACCENT_PRIMARY};
                color: {Colors.BG_DARKEST};
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
