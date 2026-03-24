# widgets/home_dock.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox

class ConfigDock(QWidget):  # Must inherit QWidget
    def __init__(self):
        super().__init__()
        self.setup_widgets()

    def setup_widgets(self):
        layout = QVBoxLayout(self)  # Layout goes on self, not panel directly
        
        panel = QGroupBox("Config")
        panel_layout = QVBoxLayout(panel)  
        panel_layout.addWidget(QLabel("Hello World"))
        
        layout.addWidget(panel)