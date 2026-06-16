import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFrame, QLabel, QLineEdit
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QDoubleValidator
from widgets import config
from widgets.gauge import AnalogGauge


class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "", accent: str = None, parent=None):
        super().__init__(parent)
        self._unit = unit
        color = accent or config.ACCENT
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config.SURFACE_RAISED};
                border: 1px solid {config.BORDER_COLOR};
                border-top: 2px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-size: 10px;
            font-family: {config.FONT_FAMILY};
            border: none;
            background: transparent;
        """)

        self._value_lbl = QLabel("--")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(f"""
            color: {color};
            font-size: 28px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none;
            background: transparent;
        """)

        offset_row = QHBoxLayout()
        offset_row.setSpacing(6)

        offset_lbl = QLabel("Offset")
        offset_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-size: 9px;
            font-family: {config.FONT_FAMILY};
            border: none;
            background: transparent;
        """)

        self._offset_edit = QLineEdit("0.0")
        self._offset_edit.setValidator(QDoubleValidator(-9999.0, 9999.0, 2))
        self._offset_edit.setFixedWidth(60)
        self._offset_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._offset_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {config.SURFACE_CARD};
                color: {config.TEXT_COLOR};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 4px;
                font-size: 11px;
                font-family: {config.FONT_FAMILY};
                padding: 2px 4px;
            }}
            QLineEdit:focus {{
                border: 1px solid {color};
            }}
        """)
        self._offset_edit.textChanged.connect(self._on_offset_changed)

        offset_row.addStretch(1)
        offset_row.addWidget(offset_lbl)
        offset_row.addWidget(self._offset_edit)
        offset_row.addStretch(1)

        layout.addWidget(title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addLayout(offset_row)

        self._raw_value = 0.0
        self._on_change = None  # callback(calibrated_value) invoked when offset changes

    def _on_offset_changed(self, _text):
        calibrated = self.set_raw(self._raw_value)
        if self._on_change is not None:
            self._on_change(calibrated)

    def offset(self) -> float:
        try:
            return float(self._offset_edit.text())
        except ValueError:
            return 0.0

    def set_raw(self, raw_val: float):
        self._raw_value = raw_val
        calibrated = raw_val + self.offset()
        self._value_lbl.setText(f"{calibrated:.1f}{self._unit}")
        return calibrated


class HomeDock(QWidget):
    def __init__(self, worker=None, parent=None):
        super().__init__(parent)
        self._setup_ui()
        if worker is not None:
            worker.packet_received.connect(self._on_packet)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("HOME")
        panel.setStyleSheet(config.PANEL_STYLE)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(16)

        # ── Gauges row ────────────────────────────────────────────────────────
        self.throttle_gauge = AnalogGauge()
        self.throttle_gauge.min_value = 0
        self.throttle_gauge.max_value = 100
        self.throttle_gauge.label = "Throttle %"
        self.throttle_gauge.zones = [
            (0.0, 0.6, "#00aaff"),
            (0.6, 0.8, "#ffaa00"),
            (0.8, 1.0, "#ff3355"),
        ]
        self.throttle_gauge.setFixedSize(360, 360)

        self.fuel_gauge = AnalogGauge()
        self.fuel_gauge.min_value = 0
        self.fuel_gauge.max_value = 100
        self.fuel_gauge.label = "Fuel %"
        self.fuel_gauge.zones = [
            (0.0, 0.3, "#ff3355"),
            (0.3, 0.6, "#ffaa00"),
            (0.6, 1.0, "#00e5a0"),
        ]
        self.fuel_gauge.setFixedSize(360, 360)

        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(48)
        gauges_row.addStretch(1)
        gauges_row.addWidget(self.throttle_gauge)
        gauges_row.addWidget(self.fuel_gauge)
        gauges_row.addStretch(1)

        # ── Metric cards row ──────────────────────────────────────────────────
        self._air_card  = MetricCard("Air Temp",  "°C",  config.ACCENT_GREEN)
        self._eng_card  = MetricCard("Eng Temp",  "°C",  config.ACCENT_RED)
        self._fuel_card = MetricCard("Fuel",       "%",   config.ACCENT_AMBER)
        self._pres_card = MetricCard("Pressure",  " bar", config.ACCENT_PURPLE)

        cards_row = QHBoxLayout()
        cards_row.setSpacing(12)
        for card in (self._air_card, self._eng_card, self._fuel_card, self._pres_card):
            card.setMinimumHeight(100)
            cards_row.addWidget(card)

        # fuel offset must also recalibrate the fuel gauge needle
        self._fuel_card._on_change = self.fuel_gauge.set_value

        panel_layout.addLayout(gauges_row)
        panel_layout.addSpacing(24)
        panel_layout.addLayout(cards_row)
        panel_layout.addStretch(1)

        layout.addWidget(panel)

    def _on_packet(self, pkt):
        self.throttle_gauge.set_value(pkt.throttle_pct)
        self._air_card.set_raw(pkt.air_temp)
        self._eng_card.set_raw(pkt.eng_temp)
        calibrated_fuel = self._fuel_card.set_raw(pkt.fuel_pct)
        self.fuel_gauge.set_value(calibrated_fuel)
        self._pres_card.set_raw(pkt.pressure)
