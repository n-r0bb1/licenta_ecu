from dataclasses import dataclass
import serial


@dataclass
class SensorPacket:
    throttle_pct: float
    fuel_pct: float
    eng_temp: float
    air_temp: float
    pressure: float


_KEYS = {
    "THR":  "throttle_pct",
    "FUEL": "fuel_pct",
    "ENGT": "eng_temp",
    "AIRT": "air_temp",
    "PRES": "pressure",
}


def parse_line(line: str) -> SensorPacket | None:
    try:
        fields = {}
        for part in line.strip().split(","):
            key, _, raw = part.partition(":")
            name = _KEYS.get(key.strip())
            if name:
                fields[name] = float(raw)
        if len(fields) != len(_KEYS):
            return None
        return SensorPacket(**fields)
    except (ValueError, TypeError):
        return None


class SerialReader:
    def __init__(self, port: str, baudrate: int = 9600):
        self._ser = serial.Serial(port, baudrate=baudrate, timeout=1)

    def read_packet(self) -> SensorPacket | None:
        raw = self._ser.readline()
        if not raw:
            return None
        return parse_line(raw.decode("ascii", errors="ignore"))

    def close(self):
        self._ser.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()
