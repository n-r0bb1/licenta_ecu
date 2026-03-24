# widgets/home_dock.py
import sys, os

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
##
from PySide6.QtWidgets import QPushButton
from PySide6.QtCore import QSize, Qt
from widgets import config 

class HomeDock(QWidget): 
    def __init__(self):
        super().__init__()
        self.setup_widgets()

    def setup_widgets(self):
        layout = QVBoxLayout(self) 
        panel = QGroupBox("Home")
        
        panel.setStyleSheet("""
            QGroupBox {
                font-size: 24px;
                color: #000000;
                font-weight: normal;
                font-family: {config.FONT_FAMILY}
            }
        """)
        
        panel_layout = QVBoxLayout(panel)  
        panel_layout.addWidget(QLabel("Hello World"))
        layout.addWidget(panel)