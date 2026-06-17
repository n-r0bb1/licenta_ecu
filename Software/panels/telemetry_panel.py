import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QCheckBox
from PySide6.QtCore import Qt
import pyqtgraph as pg

from protocol.worker import SerialWorker
from protocol.datastore import DataStore
from widgets import config

PORT     = "/dev/ttyUSB0"
BAUDRATE = 9600
LOG_PATH = "data/logs/telemetry.csv"

SERIES = {
    "throttle_pct": ("#00aaff", "Throttle %"),
    "fuel_pct":     ("#ffaa00", "Fuel %"),
    "eng_temp":     ("#ff3333", "Eng Temp °C"),
    "air_temp":     ("#00cc88", "Air Temp °C"),
    "pressure":     ("#cc88ff", "Pressure bar"),
}


class TelemDock(QWidget):
    def __init__(self, worker=None, port: str = PORT, baudrate: int = BAUDRATE, parent=None):
        super().__init__(parent)
        os.makedirs("data/logs", exist_ok=True)
        self._store       = DataStore(LOG_PATH)
        self._t0          = None
        self._curves      = {}
        self._owns_worker = worker is None
        self._setup_ui()
        if self._owns_worker:
            self._start_worker(port, baudrate)
        else:
            self._worker = worker
            worker.packet_received.connect(self._on_packet)
            worker.connected.connect(lambda: self._set_status(f"Connected — {port}", "#00cc88"))
            worker.error.connect(lambda msg: self._set_status(f"Error: {msg}", "#ff3333"))

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        panel  = QGroupBox("TELEMETRY")
        panel.setStyleSheet(config.PANEL_STYLE)

        self._status = QLabel(f"Connecting to {PORT}...")
        self._status.setStyleSheet("color: #ffaa00; font-size: 12px; padding: 2px 6px;")

        self._graph = pg.PlotWidget()
        self._graph.setBackground(config.SURFACE_RAISED)
        self._graph.showGrid(x=True, y=True, alpha=0.15)
        self._graph.setLabel("bottom", "Time", units="s",
                             color=config.TEXT_MUTED, size="10pt")
        legend = self._graph.addLegend(offset=(12, 12))
        legend.setLabelTextColor(config.TEXT_COLOR)

        self._checkboxes = {}
        checkbox_row = QHBoxLayout()
        checkbox_row.setSpacing(16)

        for field, (color, label) in SERIES.items():
            self._curves[field] = self._graph.plot(
                [], [], pen=pg.mkPen(color, width=2), name=label
            )

            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.setStyleSheet(f"""
                QCheckBox {{
                    color: {color};
                    font-family: {config.FONT_FAMILY};
                    font-size: 11px;
                    spacing: 6px;
                }}
                QCheckBox::indicator {{
                    width: 14px;
                    height: 14px;
                    border: 1px solid {color};
                    border-radius: 3px;
                    background: transparent;
                }}
                QCheckBox::indicator:checked {{
                    background: {color};
                }}
            """)
            cb.stateChanged.connect(lambda state, f=field: self._toggle_curve(f, state))
            self._checkboxes[field] = cb
            checkbox_row.addWidget(cb)

        checkbox_row.addStretch()

        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(self._status)
        panel_layout.addLayout(checkbox_row)
        panel_layout.addWidget(self._graph)
        layout.addWidget(panel)

    def _toggle_curve(self, field: str, state: int):
        self._curves[field].setVisible(state == Qt.CheckState.Checked.value)

    def _start_worker(self, port: str, baudrate: int):
        self._worker = SerialWorker(port, baudrate)
        self._worker.packet_received.connect(self._on_packet)
        self._worker.connected.connect(lambda: self._set_status(f"Connected — {port}", "#00cc88"))
        self._worker.error.connect(lambda msg: self._set_status(f"Error: {msg}", "#ff3333"))
        self._worker.start()

    def _set_status(self, text: str, color: str):
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {color}; font-size: 12px; padding: 2px 6px;")

    def _on_packet(self, pkt):
        self._store.add(pkt)
        times, _ = self._store.get_series("throttle_pct")
        if not times:
            return
        if self._t0 is None:
            self._t0 = times[0]
        rel = [t - self._t0 for t in times]
        for field, curve in self._curves.items():
            _, values = self._store.get_series(field)
            curve.setData(rel, values)

    def closeEvent(self, event):
        if self._owns_worker:
            self._worker.stop()
        self._store.close()
        super().closeEvent(event)
