# widgets/nav_button.py
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize
import PySide6 as Qt 
class NavButton(QPushButton):
    def __init__(self, label, icon=None, parent=None):
        super().__init__(label, parent)
        self.setup_style()
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(24, 24))

    def setup_style(self):
        self.setMinimumHeight(45)
        self.setMinimumWidth(150)
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #2c2c2c;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-size: 14px;
                text-align: left;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QPushButton:pressed {
                background-color: #1a1a1a;
            }
            QPushButton:checked {
                background-color: #0078d4;
            }
        """)
        self.setCheckable(True)  # allows active/selected state