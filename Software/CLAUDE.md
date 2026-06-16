# CLAUDE.md (Software)

Guidance for Claude Code when working specifically inside `/Software` — the PySide6 desktop GUI for PegaECUs. See the repo-root `CLAUDE.md` for the Hardware side and overall project context.

## Run

```bash
cd Software
python -m venv venv
source venv/bin/activate
pip install PySide6 pyserial pyqtgraph numpy   # no requirements.txt checked in
python main.py
```

Serial port/baud are hardcoded in two places that must stay in sync: `main.py:21-22` (`PORT`, `BAUDRATE`) and `protocol/worker.py:7-8` (module-level defaults used when `TelemDock` creates its own worker).

## Structure

- `main.py` — `MainWindow`: builds one `SerialWorker`, passes it into every panel, lays out the left `NavButton` sidebar + `QStackedWidget` of panels.
- `protocol/protocol.py` — `SensorPacket` dataclass + `parse_line()`. Expects exactly the 5 keys in `_KEYS` (`THR, FUEL, ENGT, AIRT, PRES`); a line missing any key returns `None` from `parse_line`.
- `protocol/worker.py` — `SerialWorker(QThread)`. Emits `packet_received(SensorPacket)`, `connected`, `error(str)`. Owns the blocking `serial.readline()` loop.
- `protocol/datastore.py` — `DataStore`: ring buffer (`deque(maxlen=500)`) of `TimedPacket` plus append-only CSV writer to `logs/telemetry.csv`.
- `panels/home_panel.py` — `HomeDock`: two `AnalogGauge`s (throttle, fuel) + 4 `MetricCard`s (air temp, eng temp, fuel, pressure), all driven by `worker.packet_received`.
- `panels/telemetry_panel.py` — `TelemDock`: pyqtgraph time-series of all 5 fields, writes to its own `DataStore`. Can either share a passed-in worker or spin up its own (`_owns_worker` flag controls whether it stops the worker on close).
- `panels/fuelmaps_panel.py` — `FuelMapsDock`: re-reads `logs/telemetry.csv` on demand (`_load`), color-codes rows by `fuel_pct` thresholds (≤33 green, ≤66 amber, else red). Not live — refresh is manual via the toolbar button.
- `panels/config_panel.py` — placeholder only, no actual settings UI yet.
- `widgets/config.py` — single source of truth for colors/sizing; every panel reads from it instead of hardcoding style values.
- `widgets/gauge.py`, `widgets/button.py` — custom-painted `AnalogGauge` (QPainter, color zones, needle) and checkable `NavButton`.

## Known issue: protocol mismatch

Hardware (`/Hardware/src/serial/PacketBuilder.cpp`) sends `HUM` (humidity from DHT11). Software's `_KEYS` in `protocol.py:14-20` expects `PRES` (pressure). Since `parse_line` requires `len(fields) == len(_KEYS)`, every real packet from current hardware firmware fails to parse and `read_packet()` silently returns `None`. When touching either side, decide which field is authoritative rather than patching around the mismatch — see repo-root CLAUDE.md "Key Design Decisions" for the two resolution options.

## Patterns to follow

- New panels that need live data take a `worker` kwarg and connect to `worker.packet_received`; don't create a second `SerialWorker`/serial connection unless intentionally decoupled (as `TelemDock` does when no worker is passed).
- Styling stays inline via `setStyleSheet(...)` pulling from `widgets/config.py` constants — no separate `.qss` files.
- `sys.path.insert(0, ...)` shims at the top of `panels/*.py` and `protocol/worker.py` are there to allow running files standalone; keep the pattern if adding new top-level modules under `Software/`.
- CSV log schema is defined by `TimedPacket` field order in `datastore.py`; both `TelemDock` and `FuelMapsDock` assume that schema when reading `logs/telemetry.csv` — changing `TimedPacket` fields requires updating `COLUMNS` in `fuelmaps_panel.py` too.

## Testing

No automated tests. Manually verify by running `python main.py` and checking gauges/cards/graph update as packets arrive (or feeding a fake serial source if hardware isn't attached).
