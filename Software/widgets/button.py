import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
##
from PySide6.QtWidgets import QPushButton, QStylePainter, QStyleOptionButton, QStyle
from PySide6.QtCore import QSize, Qt, QRect
from PySide6.QtGui import QIcon
from widgets import config

class NavButton(QPushButton):
    def __init__(self, label, icon=None, parent=None):
        super().__init__(label, parent)
        self.setup_style()

        if icon:
            self._icon = QIcon(icon) if isinstance(icon, str) else icon
            self._icon_size = QSize(24, 24)
        else:
            self._icon = None

    def setup_style(self):
        self.setMinimumHeight(config.BUTTON_HEIGHT)
        self.setMinimumWidth(config.BUTTON_WIDTH)
        self.setStyleSheet(f"""
        QPushButton {{
        background-color: {config.BACKGROUND_COLOR};
        color: {config.TEXT_COLOR};
        font-family: {config.FONT_FAMILY};
        font-size: {config.FONT_SIZE}px;
        border-radius: 0;
        border: none;
        border-top: 3px solid {config.TEXT_COLOR};
        text-align: center;
        padding-left: 12px;
       
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
        self.setCheckable(True)

    def paintEvent(self, _event):
        painter = QStylePainter(self)
        option = QStyleOptionButton()
        self.initStyleOption(option)
        option.icon = QIcon()       # strip icon so Qt draws only the text centered
        painter.drawControl(QStyle.ControlElement.CE_PushButton, option)

        if self._icon:
            icon_x = 12
            icon_y = (self.height() - self._icon_size.height()) // 2
            self._icon.paint(painter, QRect(icon_x, icon_y, self._icon_size.width(), self._icon_size.height()))