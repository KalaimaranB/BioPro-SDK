import os
import sys

import pytest

# Force Qt to render offscreen (requires no visible monitor display)
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Global QApplication instance to prevent GC cleanup mid-session
_qapp = None

@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Ensure a global QApplication instance is initialized before executing PyQt6 tests."""
    global _qapp
    from PyQt6.QtWidgets import QApplication

    _qapp = QApplication.instance()
    if _qapp is None:
        _qapp = QApplication(sys.argv)

    yield _qapp
