import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import QWidget, QVBoxLayout, QGroupBox, QLabel
from PySide6.QtCore import QThread, Signal
import pyqtgraph as pg

from protocol.protocol import SerialReader, SensorPacket
from protocol.datastore import DataStore
from widgets import config

PORT     = "/dev/ttyUSB0"
BAUDRATE = 9600
LOG_PATH = "logs/telemetry.csv"

SERIES = {
    "throttle_pct": ("#00aaff", "Throttle %"),
    "fuel_pct":     ("#ffaa00", "Fuel %"),
    "eng_temp":     ("#ff3333", "Eng Temp °C"),
    "air_temp":     ("#00cc88", "Air Temp °C"),
    "pressure":     ("#cc88ff", "Pressure bar"),
}


class SerialWorker(QThread):
    packet_received = Signal(object)
    error           = Signal(str)
    connected       = Signal()

    def __init__(self, port: str, baudrate: int):
        super().__init__()
        self._port     = port
        self._baudrate = baudrate
        self._running  = False

    def run(self):
        self._running = True
        try:
            with SerialReader(self._port, self._baudrate) as reader:
                self.connected.emit()
                while self._running:
                    pkt = reader.read_packet()
                    if pkt:
                        self.packet_received.emit(pkt)
        except Exception as e:
            self.error.emit(str(e))

    def stop(self):
        self._running = False
        self.wait()


class TelemDock(QWidget):
    def __init__(self, port: str = PORT, baudrate: int = BAUDRATE, parent=None):
        super().__init__(parent)
        os.makedirs("logs", exist_ok=True)
        self._store  = DataStore(LOG_PATH)
        self._t0     = None
        self._curves = {}
        self._setup_ui()
        self._start_worker(port, baudrate)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        panel  = QGroupBox("Telemetry")
        panel.setStyleSheet(f"""
            QGroupBox {{
                font-size: 24px;
                color: #ffffff;
                font-weight: normal;
                font-family: {config.FONT_FAMILY};
            }}
        """)

        self._status = QLabel(f"Connecting to {PORT}...")
        self._status.setStyleSheet("color: #ffaa00; font-size: 12px; padding: 2px 6px;")

        self._graph = pg.PlotWidget()
        self._graph.setBackground("#0f0f1a")
        self._graph.showGrid(x=True, y=True, alpha=0.3)
        self._graph.setLabel("bottom", "Time", units="s")
        self._graph.addLegend()

        for field, (color, label) in SERIES.items():
            self._curves[field] = self._graph.plot(
                [], [], pen=pg.mkPen(color, width=2), name=label
            )

        panel_layout = QVBoxLayout(panel)
        panel_layout.addWidget(self._status)
        panel_layout.addWidget(self._graph)
        layout.addWidget(panel)

    def _start_worker(self, port: str, baudrate: int):
        self._worker = SerialWorker(port, baudrate)
        self._worker.packet_received.connect(self._on_packet)
        self._worker.connected.connect(lambda: self._set_status(f"Connected — {port}", "#00cc88"))
        self._worker.error.connect(lambda msg: self._set_status(f"Error: {msg}", "#ff3333"))
        self._worker.start()

    def _set_status(self, text: str, color: str):
        self._status.setText(text)
        self._status.setStyleSheet(f"color: {color}; font-size: 12px; padding: 2px 6px;")

    def _on_packet(self, pkt: SensorPacket):
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
        self._worker.stop()
        self._store.close()
        super().closeEvent(event)
