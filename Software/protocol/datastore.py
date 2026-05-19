from collections import deque
from dataclasses import dataclass, fields, astuple
import csv
import time

from protocol.protocol import SensorPacket


HISTORY = 500


@dataclass
class TimedPacket:
    timestamp: float
    throttle_pct: float
    fuel_pct: float
    eng_temp: float
    air_temp: float
    pressure: float


class DataStore:
    def __init__(self, log_path: str, maxlen: int = HISTORY):
        self.buffer: deque[TimedPacket] = deque(maxlen=maxlen)
        self._log = open(log_path, "a", newline="")
        self._writer = csv.writer(self._log)
        if self._log.tell() == 0:
            self._writer.writerow([f.name for f in fields(TimedPacket)])

    def add(self, pkt: SensorPacket) -> None:
        tp = TimedPacket(
            time.time(),
            pkt.throttle_pct,
            pkt.fuel_pct,
            pkt.eng_temp,
            pkt.air_temp,
            pkt.pressure,
        )
        self.buffer.append(tp)
        self._writer.writerow(astuple(tp))
        self._log.flush()

    def get_series(self, field: str) -> tuple[list[float], list[float]]:
        return (
            [p.timestamp for p in self.buffer],
            [getattr(p, field) for p in self.buffer],
        )

    def close(self) -> None:
        self._log.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
