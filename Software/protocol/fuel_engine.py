"""
VE-based fuel efficiency engine.

Given throttle position, the active car profile, and the volumetric
efficiency table (MAP kPa × RPM), computes per packet:
  - current gear (automatic 6-speed shift logic)
  - engine RPM
  - VE % at current operating point
  - instantaneous fuel flow (mL/s)
  - L / 100 km, MPG, range remaining

Fuel flow model:
  air_per_rev  = (displacement / 2) × (VE / 100) × air_density
  fuel_per_rev = air_per_rev / AFR
  flow_mL_s    = fuel_per_rev × (RPM / 60) / fuel_density

All public state is available as plain attributes after calling update().
"""

import os, csv, json, re, math

# ── paths ─────────────────────────────────────────────────────────────────────
_CARS_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "cars.json")
_VE_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "ve_maps")

# ── VE map grid (MAP kPa × RPM) ──────────────────────────────────────────────
VE_RPM_STEPS = list(range(500, 8500, 500))    # 500 … 8000  (16 cols)
MAP_STEPS    = list(range(20, 105, 5))         # 20 … 100 kPa (17 rows)

# ── automatic gearbox constants ───────────────────────────────────────────────
_GEAR_RATIOS    = [3.31, 1.95, 1.41, 1.00, 0.74, 0.64]
_UPSHIFT_FRAC   = 0.78
_DOWNSHIFT_FRAC = 0.38
_IDLE_RPM       = 750.0

# ── thermodynamic constants ───────────────────────────────────────────────────
_AIR_DENSITY_KG_ML = 0.001225 / 1000.0   # kg per mL at sea level / 15 °C
_FUEL_DENSITY_KG_ML = 0.75 / 1000.0      # gasoline ≈ 0.75 kg/L → kg/mL
_AFR_GASOLINE      = 14.7      # stoichiometric air/fuel ratio
_AFR_DIESEL        = 14.5
_STROKES           = 2         # 4-stroke: 1 combustion event per 2 revolutions


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


def _load_ve_map(car_name: str) -> list[list[float]] | None:
    path = os.path.join(_VE_DIR, f"{_slug(car_name)}.csv")
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        data = [[float(v) for v in row[1:]] for row in rows[1:]]
        if len(data) == len(MAP_STEPS) and all(len(r) == len(VE_RPM_STEPS) for r in data):
            return data
    except Exception:
        pass
    return None


def _load_car(car_name: str) -> dict | None:
    with open(_CARS_JSON, encoding="utf-8") as f:
        for e in json.load(f):
            if e["name"] == car_name:
                return e
    return None


def _nearest_ve_row(map_kpa: float) -> int:
    map_kpa = max(MAP_STEPS[0], min(MAP_STEPS[-1], map_kpa))
    return min(range(len(MAP_STEPS)),
               key=lambda i: abs(MAP_STEPS[i] - map_kpa))


def _nearest_ve_col(rpm: float) -> int:
    rpm = max(VE_RPM_STEPS[0], min(VE_RPM_STEPS[-1], rpm))
    return min(range(len(VE_RPM_STEPS)),
               key=lambda i: abs(VE_RPM_STEPS[i] - rpm))


def _throttle_to_map_kpa(throttle_pct: float) -> float:
    """Closed throttle ≈ 20 kPa (high vacuum), WOT ≈ 101 kPa (atmospheric)."""
    return 20.0 + (throttle_pct / 100.0) * 81.0


# ── FuelMapEngine ─────────────────────────────────────────────────────────────

class FuelMapEngine:
    """
    Stateful per-session engine.  Call set_car() when the profile changes,
    then update() on every sensor packet.
    """

    def __init__(self):
        # public outputs
        self.gear        = 1
        self.rpm         = 0.0
        self.ve_pct      = 0.0
        self.flow_ml_s   = 0.0
        self.l100        = 8.0
        self.mpg         = 29.4
        self.range_km    = 0.0

        # car parameters
        self._rpm_max       = 8000
        self._max_speed     = 200.0
        self._cylinders     = 4
        self._displacement_ml = 1600.0   # total engine displacement in mL
        self._tank_l        = 50.0
        self._afr           = _AFR_GASOLINE
        self._ve_map: list[list[float]] | None = None
        self._car_name      = ""

        # internal shift state
        self._gear = 1
        self._neutral = False

    def set_car(self, car_name: str, tank_liters: float | None = None):
        self._car_name = car_name
        car = _load_car(car_name)
        if car:
            self._rpm_max   = car.get("rpm_max", 8000)
            self._max_speed = float(car.get("max_speed_kmh", 200))
            cc_str          = car.get("engine_cc", "1600 cc")
            cc              = int(re.sub(r"[^0-9]", "", cc_str) or 1600)
            self._displacement_ml = float(cc)
            self._cylinders = car.get("cylinders", _cylinders_from_cc(cc))
            self._tank_l    = float(tank_liters or car.get("tank_liters", 50))
            fuel_type       = car.get("fuel_type", "Gasoline")
            self._afr       = _AFR_DIESEL if fuel_type == "Diesel" else _AFR_GASOLINE

        self._ve_map = _load_ve_map(car_name)
        self._gear   = 1
        self._neutral = False

    def set_tank(self, liters: float):
        self._tank_l = liters

    def reload_ve_map(self):
        if self._car_name:
            self._ve_map = _load_ve_map(self._car_name)
            print("Reloaded VE map for", self._car_name)

    def set_neutral(self, enabled: bool):
        self._neutral = enabled

    def is_neutral(self) -> bool:
        return self._neutral

    # ── core update ───────────────────────────────────────────────────────────

    def update(self, throttle_pct: float, fuel_pct: float,
               fuel_liters_override: float = 0.0) -> None:
        load = max(0.0, min(100.0, throttle_pct))
        if self._neutral:
            rpm = _IDLE_RPM
        else:
            rpm = self._auto_rpm(load)
        ve   = self._lookup_ve(load, rpm) / 100.0   # 0.0–1.0

        # displacement per combustion event (4-stroke: fires every 2 revs)
        # each cylinder sweeps displacement_ml / cylinders per stroke
        disp_per_fire_ml = self._displacement_ml / self._cylinders

        # air mass drawn per firing (mL of air × density → kg)
        air_ml_per_fire  = disp_per_fire_ml * ve
        air_kg_per_fire  = air_ml_per_fire * _AIR_DENSITY_KG_ML

        # fuel mass per firing (stoichiometric)
        fuel_kg_per_fire = air_kg_per_fire / self._afr

        # fuel volume per firing (kg → mL)
        fuel_ml_per_fire = fuel_kg_per_fire / _FUEL_DENSITY_KG_ML

        # firings per second across all cylinders
        firings_per_sec = (rpm / (_STROKES * 60.0)) * self._cylinders

        flow_ml_s = fuel_ml_per_fire * firings_per_sec

        # speed directly from throttle (same mapping used in _auto_rpm)
        speed_kmh = (load / 100.0) * self._max_speed

        if speed_kmh < 1.0 or self._neutral:
            l100 = 0.0
        else:
            l100 = (flow_ml_s / 1000.0 * 3600.0) / speed_kmh * 100.0
        l100 = max(0.0, l100)

        mpg = 235.214573 / l100 if l100 > 0 else 0.0

        fuel_l = fuel_liters_override if fuel_liters_override > 0 \
                 else (max(0.0, fuel_pct) / 100.0) * self._tank_l
        range_km = (fuel_l / l100) * 100.0 if l100 > 0 else 0.0

        self.gear     = 0 if self._neutral else self._gear
        self.rpm      = rpm
        self.ve_pct   = round(ve * 100.0, 1)
        self.flow_ml_s = flow_ml_s
        self.l100     = l100
        self.mpg      = mpg
        self.range_km = range_km

    # ── automatic gearbox ─────────────────────────────────────────────────────

    def _auto_rpm(self, load_pct: float) -> float:
        """
        Throttle sets target speed proportionally.  Gear is chosen to keep
        RPM in a comfortable band, then RPM is derived from speed + gear.
        """
        rpm_max   = self._rpm_max
        top_ratio = _GEAR_RATIOS[-1]
        speed_kmh = (load_pct / 100.0) * self._max_speed

        # find the highest gear that keeps RPM above a comfortable minimum
        min_cruise_rpm = _IDLE_RPM * 1.5
        best_gear = 1
        for g in range(1, len(_GEAR_RATIOS) + 1):
            ratio = _GEAR_RATIOS[g - 1]
            rpm   = (speed_kmh / self._max_speed) * rpm_max * (ratio / top_ratio)
            if rpm >= min_cruise_rpm:
                best_gear = g

        self._gear = best_gear
        cur_ratio  = _GEAR_RATIOS[self._gear - 1]
        rpm = (speed_kmh / self._max_speed) * rpm_max * (cur_ratio / top_ratio)
        # only apply idle floor when the car is moving (load > 0)
        if load_pct > 0:
            rpm = max(rpm, _IDLE_RPM)
        else:
            rpm = 0.0

        return round(rpm, 0)

    # ── VE lookup ─────────────────────────────────────────────────────────────

    def _lookup_ve(self, load_pct: float, rpm: float) -> float:
        map_kpa = _throttle_to_map_kpa(load_pct)
        if self._ve_map is None:
            rpm_norm = min(rpm, VE_RPM_STEPS[-1]) / VE_RPM_STEPS[-1]
            map_norm = (map_kpa - 20.0) / 80.0
            rpm_bell = math.exp(-((rpm_norm - 0.55) ** 2) / (2 * 0.18 ** 2))
            ve = 30.0 + map_norm * 50.0 + rpm_bell * 20.0 * (0.5 + 0.5 * map_norm)
            if rpm_norm > 0.75:
                ve -= (rpm_norm - 0.75) * 40.0
            return round(max(25.0, min(100.0, ve)), 1)
        row = _nearest_ve_row(map_kpa)
        col = _nearest_ve_col(rpm)
        print(
        f"Lookup -> MAP={MAP_STEPS[row]} "
        f"RPM={VE_RPM_STEPS[col]} "
        f"VE={self._ve_map[row][col]}"
)
        return self._ve_map[row][col]
