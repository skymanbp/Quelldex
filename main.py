#!/usr/bin/env python3
"""
Quelldex — Source & Data Organization Engine
PySide6 Desktop Application
"""

import sys
import os

# Support both normal run and PyInstaller bundle
if getattr(sys, 'frozen', False):
    HERE = sys._MEIPASS
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QSettings

from src.ui.theme import QSS, set_theme


def main():
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Quelldex")
    app.setOrganizationName("Quelldex")

    # Restore saved theme before building UI
    saved = QSettings("Quelldex", "Quelldex").value("theme", "dark")
    if saved in ("dark", "light", "midnight"):
        set_theme(saved)

    from src.ui.theme import QSS as CURRENT_QSS
    app.setStyleSheet(CURRENT_QSS)

    from src.ui.app import QuelldexWindow
    window = QuelldexWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
