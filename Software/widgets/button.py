import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon
from widgets import config


class NavButton(QPushButton):
    def __init__(self, label, icon=None, parent=None):
        super().__init__(label, parent)
        self._setup_style()
        if icon:
            self.setIcon(QIcon(icon) if isinstance(icon, str) else icon)
            self.setIconSize(QSize(20, 20))

    def _setup_style(self):
        self.setMinimumHeight(config.BUTTON_HEIGHT)
        self.setMinimumWidth(config.BUTTON_WIDTH)
        self.setCheckable(True)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.BACKGROUND_COLOR};
                color: {config.TEXT_MUTED};
                font-family: {config.FONT_FAMILY};
                font-size: {config.FONT_SIZE}px;
                border: none;
                border-left: 3px solid transparent;
                text-align: left;
                padding-left: 18px;
            }}
            QPushButton:hover {{
                background-color: {config.BACKGROUND_HOVER};
                color: {config.TEXT_COLOR};
                border-left: 3px solid {config.ACCENT};
            }}
            QPushButton:checked {{
                background-color: {config.BACKGROUND_ACTIVE};
                color: {config.ACCENT};
                border-left: 3px solid {config.ACCENT};
            }}
            QPushButton:pressed {{
                background-color: {config.BACKGROUND_PRESSED};
            }}
        """)
