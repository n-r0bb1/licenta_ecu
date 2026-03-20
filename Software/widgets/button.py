import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
##
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize, Qt
from widgets import config 

class NavButton(QPushButton):
    def __init__(self, label, icon=None, parent=None):
        super().__init__(label, parent)
        self.setup_style()
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(24, 24))

    def setup_style(self):
        self.setMinimumHeight(config.BUTTON_HEIGHT)
        self.setMinimumWidth(config.BUTTON_WIDTH)
        self.setStyleSheet(f"""
        QPushButton {{
        background-color: {config.BACKGROUND_COLOR};
        color: {config.TEXT_COLOR};
        font-family: {config.FONT_FAMILY};
        font-size: {config.FONT_SIZE}px;
        border-radius: {config.BORDER_RADIUS}px;
        border: none;
        }}
        QPushButton:hover {{
            background-color: {config.BACKGROUND_HOVER};
        }}
        QPushButton:pressed {{
            background-color: {config.BACKGROUND_PRESSED};
        }}
        QPushButton:checked {{
            background-color: {config.BACKGROUND_PRESSED};
        }}
""")
        self.setCheckable(True)  # allows active/selected state