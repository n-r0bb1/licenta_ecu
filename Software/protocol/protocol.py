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


def _xor_checksum(data: str) -> int:
    cs = 0
    for ch in data:
        cs ^= ord(ch)
    return cs


def parse_line(line: str) -> SensorPacket | None:
    """Parse a framed line: $payload*HH where HH is a 2-char hex XOR checksum."""
    try:
        line = line.strip()

        if not line.startswith("$") or "*" not in line:
            return None

        body = line[1:]
        payload, _, checksum_hex = body.partition("*")

        if len(checksum_hex) != 2:
            return None

        expected = int(checksum_hex, 16)
        actual = _xor_checksum(payload)
        if expected != actual:
            return None

        fields = {}
        for part in payload.split(","):
            key, _, raw = part.partition(":")
            name = _KEYS.get(key.strip())
            if name:
                try:
                    fields[name] = float(raw)
                except ValueError:
                    fields[name] = float("nan")
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
