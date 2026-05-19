import sys, os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox
from widgets import config
from widgets.gauge import AnalogGauge


class HomeDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        panel = QGroupBox("Home")
        panel.setStyleSheet(f"""
            QGroupBox {{
                font-size: 24px;
                color: #ffffff;
                font-weight: normal;
                font-family: {config.FONT_FAMILY};
            }}
        """)

        self.speed_gauge = AnalogGauge()
        self.speed_gauge.min_value = 0
        self.speed_gauge.max_value = 260
        self.speed_gauge.label = "km/h"
        self.speed_gauge.zones = [
            (0.0, 0.6, "#00aaff"),
            (0.6, 0.8, "#ffaa00"),
            (0.8, 1.0, "#ff3333"),
        ]

        self.rpm_gauge = AnalogGauge()
        self.rpm_gauge.min_value = 0
        self.rpm_gauge.max_value = 8000
        self.rpm_gauge.label = "RPM"
        self.rpm_gauge.zones = [
            (0.0, 0.6, "#00aaff"),
            (0.6, 0.8, "#ffaa00"),
            (0.8, 1.0, "#ff3333"),
        ]

        gauges_layout = QHBoxLayout()
        gauges_layout.addWidget(self.speed_gauge)
        gauges_layout.addWidget(self.rpm_gauge)

        panel_layout = QVBoxLayout(panel)
        panel_layout.addLayout(gauges_layout)

        layout.addWidget(panel)
