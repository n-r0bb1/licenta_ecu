import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from widgets import config


class ConfigDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        panel = QGroupBox("Config")
        panel.setStyleSheet(f"""
            QGroupBox {{
                font-size: 24px;
                color: #ffffff;
                font-weight: normal;
                font-family: {config.FONT_FAMILY};
            }}
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(QLabel("Hello World"))

        layout.addWidget(panel)
