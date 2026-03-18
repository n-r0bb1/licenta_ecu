# widgets/home_dock.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox

class HomeDock(QWidget):  # Must inherit QWidget
    def __init__(self):
        super().__init__()
        self.setup_widgets()

    def setup_widgets(self):
        layout = QVBoxLayout(self)  # Layout goes on self, not panel directly
        
        panel = QGroupBox("Home")
        panel_layout = QVBoxLayout(panel)  # QGroupBox needs a layout too
        panel_layout.addWidget(QLabel("Hello World"))
        
        layout.addWidget(panel)