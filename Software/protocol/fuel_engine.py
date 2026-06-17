"""
Fuel-map-based efficiency engine.

Given:
  - throttle position (0–100 %) as engine load proxy
  - the active car profile (from cars.json)
  - the injector pulse-width table for that car (from data/fuel_maps/)

Computes per packet:
  - current gear (automatic shift logic)
  - engine RPM
  - injector pulse width (ms) from the map
  - instantaneous fuel flow (mL/s)
  - L / 100 km
  - MPG (imperial)
  - range remaining (km)

All public state is available as plain attributes after calling update().
"""

import os, csv, json, re

# ── paths ─────────────────────────────────────────────────────────────────────
_CARS_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "cars.json")
_MAPS_DIR  = os.path.join(os.path.dirname(__file__), "..", "data", "fuel_maps")
_VE_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "ve_maps")

# ── fuel map grid ─────────────────────────────────────────────────────────────
RPM_STEPS  = list(range(1000, 9000, 1000))
LOAD_STEPS = list(range(0, 110, 10))

# ── automatic gearbox constants ───────────────────────────────────────────────
# Each gear is defined as (upshift_rpm, downshift_rpm, ratio).
# ratio is relative wheel torque multiplier — not used directly but kept for
# future speed calculation.
_GEAR_RATIOS = [3.31, 1.95, 1.41, 1.00, 0.74, 0.64]   # typical 6-speed auto

# RPM bands: shift up when RPM exceeds threshold, down when below.
# Expressed as fraction of rpm_max so they scale with any engine.
_UPSHIFT_FRAC   = 0.78   # shift up  when RPM > 78 % of rpm_max
_DOWNSHIFT_FRAC = 0.38   # shift down when RPM < 38 % of rpm_max

# Injector constant: mL of fuel per ms of open time per cylinder.
# Calibrated so that mid-throttle cruise gives realistic L/100 values (~7–12).
_ML_PER_MS = 0.0028

# 4-stroke: each cylinder fires every 2 crankshaft revolutions
_STROKES = 2

# Cylinders assumed from displacement (rough rule of thumb used for estimation)
def _cylinders_from_cc(cc: int) -> int:
    if cc <= 1000:
        return 3
    elif cc <= 2000:
        return 4
    else:
        return 6


# ── helpers ───────────────────────────────────────────────────────────────────

def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _load_map(car_name: str) -> list[list[float]] | None:
    path = os.path.join(_MAPS_DIR, f"{_slug(car_name)}.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        return [[float(v) for v in row[1:]] for row in rows[1:]]
    except Exception:
        return None


def _load_ve_map(car_name: str) -> list[list[float]] | None:
    path = os.path.join(_VE_DIR, f"{_slug(car_name)}.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        return [[float(v) for v in row[1:]] for row in rows[1:]]
    except Exception:
        return None


def _load_car(car_name: str) -> dict | None:
    with open(_CARS_JSON, encoding="utf-8") as f:
        for e in json.load(f):
            if e["name"] == car_name:
                return e
    return None


def _nearest_row(load_pct: float) -> int:
    """Return the closest LOAD_STEPS index."""
    load_pct = max(0.0, min(100.0, load_pct))
    return min(range(len(LOAD_STEPS)),
               key=lambda i: abs(LOAD_STEPS[i] - load_pct))


def _nearest_col(rpm: float) -> int:
    """Return the closest RPM_STEPS index."""
    rpm = max(RPM_STEPS[0], min(RPM_STEPS[-1], rpm))
    return min(range(len(RPM_STEPS)),
               key=lambda i: abs(RPM_STEPS[i] - rpm))


# ── FuelMapEngine ─────────────────────────────────────────────────────────────

class FuelMapEngine:
    """
    Stateful per-session engine.  Call set_car() when the profile changes,
    then update() on every sensor packet.
    """

    def __init__(self):
        # public outputs (updated by update())
        self.gear        = 1
        self.rpm         = 0.0
        self.pulse_ms    = 0.0
        self.flow_ml_s   = 0.0
        self.l100        = 8.0
        self.mpg         = 29.4
        self.range_km    = 0.0

        # car parameters
        self._rpm_max    = 8000
        self._max_speed  = 200.0   # km/h at rpm_max in top gear
        self._cylinders  = 4
        self._tank_l     = 50.0
        self._map: list[list[float]] | None = None
        self._ve_map: list[list[float]] | None = None
        self._car_name   = ""

        # internal shift state
        self._gear       = 1

    def set_car(self, car_name: str, tank_liters: float | None = None):
        """Load profile + fuel map for the given car."""
        self._car_name = car_name
        car = _load_car(car_name)
        if car:
            self._rpm_max   = car.get("rpm_max", 8000)
            self._max_speed = float(car.get("max_speed_kmh", 200))
            cc_str          = car.get("engine_cc", "1600 cc")
            cc              = int(re.sub(r"[^0-9]", "", cc_str) or 1600)
            self._cylinders = _cylinders_from_cc(cc)
            self._tank_l    = float(tank_liters or car.get("tank_liters", 50))

        self._map    = _load_map(car_name)
        self._ve_map = _load_ve_map(car_name)
        self._gear   = 1

    def set_tank(self, liters: float):
        self._tank_l = liters

    def reload_map(self):
        """Re-read both CSVs from disk (called after the map editor saves)."""
        if self._car_name:
            self._map    = _load_map(self._car_name)
            self._ve_map = _load_ve_map(self._car_name)

    def reload_ve_map(self):
        """Re-read only the VE map from disk."""
        if self._car_name:
            self._ve_map = _load_ve_map(self._car_name)

    # ── core update ───────────────────────────────────────────────────────────

    def update(self, throttle_pct: float, fuel_pct: float,
               fuel_liters_override: float = 0.0) -> None:
        """
        throttle_pct     : 0–100  (engine load proxy)
        fuel_pct         : 0–100  (current tank level)
        fuel_liters_override : if > 0, use this instead of fuel_pct × tank
        """
        load  = max(0.0, min(100.0, throttle_pct))
        rpm   = self._auto_rpm(load)
        pw    = self._lookup_pulse(load, rpm)
        ve    = self._lookup_ve(load, rpm) / 100.0   # 0.0–1.0

        # instantaneous fuel flow scaled by volumetric efficiency
        # fires = rpm / (2 * 60) firings per second per cylinder (4-stroke)
        firings_per_sec = rpm / (_STROKES * 60.0)
        flow_ml_s       = pw * _ML_PER_MS * self._cylinders * firings_per_sec * ve

        # speed: rpm expressed as fraction of rpm_max → fraction of max_speed
        # (linear approximation: at rpm_max in top gear = max_speed)
        speed_kmh = max(1.0, (rpm / self._rpm_max) * self._max_speed)

        # L/100km: flow (mL/s) → L/h (/1000 *3600) → L/100km (/speed *100)
        l100 = (flow_ml_s / 1000.0 * 3600.0) / speed_kmh * 100.0
        l100 = max(0.1, l100)

        mpg = 235.214573 / l100

        fuel_l = fuel_liters_override if fuel_liters_override > 0 \
                 else (max(0.0, fuel_pct) / 100.0) * self._tank_l
        range_km = (fuel_l / l100) * 100.0

        # persist
        self.gear     = self._gear
        self.rpm      = rpm
        self.pulse_ms = pw
        self.flow_ml_s = flow_ml_s
        self.l100     = l100
        self.mpg      = mpg
        self.range_km = range_km

    # ── automatic gearbox ─────────────────────────────────────────────────────

    def _auto_rpm(self, load_pct: float) -> float:
        """
        Simple automatic shift model.
        - Effective RPM = load% mapped to 20–100% of current gear's RPM band.
        - Shift up when RPM > upshift threshold, down when < downshift threshold.
        """
        rpm_max = self._rpm_max

        for _ in range(len(_GEAR_RATIOS)):          # iterate until stable
            ratio       = _GEAR_RATIOS[self._gear - 1]
            # within this gear, RPM scales from idle (20%) to max-in-gear
            max_in_gear = rpm_max * (ratio / _GEAR_RATIOS[0])
            max_in_gear = min(max_in_gear, rpm_max)
            idle_rpm    = max_in_gear * 0.20

            rpm = idle_rpm + (load_pct / 100.0) * (max_in_gear - idle_rpm)

            if rpm > rpm_max * _UPSHIFT_FRAC and self._gear < len(_GEAR_RATIOS):
                self._gear += 1
            elif rpm < rpm_max * _DOWNSHIFT_FRAC and self._gear > 1:
                self._gear -= 1
            else:
                break

        return round(rpm, 0)

    # ── map lookup ────────────────────────────────────────────────────────────

    def _lookup_pulse(self, load_pct: float, rpm: float) -> float:
        if self._map is None:
            return round(2.0 + (load_pct / 100) * 9.0 + (rpm / 8000) * 4.0, 1)
        row = _nearest_row(load_pct)
        col = _nearest_col(rpm)
        return self._map[row][col]

    def _lookup_ve(self, load_pct: float, rpm: float) -> float:
        """Return volumetric efficiency % (0–100). Falls back to default curve."""
        if self._ve_map is None:
            # default VE curve: peaks ~85% at mid-RPM/high-load, drops at extremes
            rpm_norm  = min(rpm, RPM_STEPS[-1]) / RPM_STEPS[-1]
            load_norm = load_pct / 100.0
            ve = 60.0 + load_norm * 20.0 + rpm_norm * (1.0 - rpm_norm) * 40.0
            return round(min(ve, 100.0), 1)
        row = _nearest_row(load_pct)
        col = _nearest_col(rpm)
        return self._ve_map[row][col]
