import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtCore import QThread, Signal
from protocol.protocol import SerialReader

PORT     = "/dev/ttyUSB0"
BAUDRATE = 9600


class SerialWorker(QThread):
    packet_received = Signal(object)
    error           = Signal(str)
    connected       = Signal()

    def __init__(self, port: str = PORT, baudrate: int = BAUDRATE):
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
