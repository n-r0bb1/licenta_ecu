import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QGroupBox
from PySide6.QtCore import Qt
from widgets import config


class ConfigDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("CONFIGURATION")
        panel.setStyleSheet(config.PANEL_STYLE)

        placeholder = QLabel("Configuration coming soon")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 14px;
        """)

        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(placeholder)

        layout.addWidget(panel)
