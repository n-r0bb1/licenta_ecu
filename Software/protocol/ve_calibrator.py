"""
Online VE self-calibration using SGD (stochastic gradient descent).

Each packet pair gives us:
  - predicted fuel flow  (from FuelMapEngine, before VE scaling)
  - observed fuel drop   (fuel_pct[t-1] - fuel_pct[t], converted to mL/s)

The ratio  observed / predicted  is the "true" VE multiplier at that
(load, RPM) operating point.  We nudge the relevant VE cell toward it
with a small learning rate so the map converges gradually over a drive.

Signal quality rules:
  - Ignore packets where throttle changed more than THROTTLE_STABILITY_THRESH
    between steps (transients are noisy).
  - Ignore packets where the observed fuel drop is negative (sensor noise /
    refuel event) or implausibly large.
  - Require a minimum fuel drop to avoid amplifying noise near zero.
"""

import csv, os, re

# ── tuneable constants ────────────────────────────────────────────────────────
LEARNING_RATE             = 0.05   # how aggressively each packet nudges a cell
THROTTLE_STABILITY_THRESH = 5.0   # % — skip update if throttle jumped more than this
MIN_FUEL_DROP_ML_S        = 0.001  # mL/s — ignore drops below this (sensor noise floor)
MAX_FUEL_DROP_ML_S        = 8.0   # mL/s — ignore implausibly large drops (WOT ~4.5 mL/s)
VE_MIN                    = 40.0  # hard floor to prevent runaway
VE_MAX                    = 110.0 # hard ceiling (allow slight overboost room)

# how many cell updates before we save to disk (avoid thrashing the filesystem)
SAVE_EVERY_N_UPDATES = 10


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


class VECalibrator:
    """
    Attach one instance per session to a FuelMapEngine.
    Call update() on every packet — it maintains its own previous-state
    memory and applies corrections to engine._ve_map in place.
    """

    def __init__(self, engine, ve_dir: str, save_callback=None):
        """
        engine        : FuelMapEngine instance (mutated in place)
        ve_dir        : absolute path to data/ve_maps/
        save_callback : optional callable(car_name, ve_map) — called after
                        every SAVE_EVERY_N_UPDATES corrections so the UI
                        table can refresh.  Signature: (str, list[list[float]])
        """
        self._engine        = engine
        self._ve_dir        = ve_dir
        self._save_cb       = save_callback

        # previous-packet state
        self._prev_fuel_pct   : float | None = None
        self._prev_throttle   : float | None = None
        self._prev_tank_l     : float | None = None

        # counters
        self._updates_since_save = 0
        self.total_corrections   = 0   # visible to UI if needed

    def reset(self):
        """Call when the car profile changes."""
        self._prev_fuel_pct  = None
        self._prev_throttle  = None
        self._prev_tank_l    = None
        self._updates_since_save = 0

    def update(self, throttle_pct: float, fuel_pct: float,
               tank_liters: float, dt: float = 1.0) -> bool:
        """
        throttle_pct : current throttle (0–100)
        fuel_pct     : current fuel level (0–100, calibrated)
        tank_liters  : current tank capacity in litres
        dt           : seconds since last call (default 1 — matches 1 Hz serial)

        Returns True if a VE cell was updated this call.
        """
        engine = self._engine

        # ── guard: need a previous sample ────────────────────────────────────
        if self._prev_fuel_pct is None:
            self._prev_fuel_pct  = fuel_pct
            self._prev_throttle  = throttle_pct
            self._prev_tank_l    = tank_liters
            return False

        # ── guard: throttle stability ─────────────────────────────────────────
        throttle_delta = abs(throttle_pct - self._prev_throttle)
        if throttle_delta > THROTTLE_STABILITY_THRESH:
            self._prev_fuel_pct  = fuel_pct
            self._prev_throttle  = throttle_pct
            self._prev_tank_l    = tank_liters
            return False

        # ── observed fuel consumption ─────────────────────────────────────────
        fuel_drop_pct = self._prev_fuel_pct - fuel_pct          # % of tank
        fuel_drop_l   = (fuel_drop_pct / 100.0) * tank_liters   # litres
        obs_ml_s      = (fuel_drop_l * 1000.0) / dt             # mL/s

        # ── guard: signal quality ─────────────────────────────────────────────
        if not (MIN_FUEL_DROP_ML_S <= obs_ml_s <= MAX_FUEL_DROP_ML_S):
            self._prev_fuel_pct  = fuel_pct
            self._prev_throttle  = throttle_pct
            self._prev_tank_l    = tank_liters
            return False

        # ── predicted flow (without VE, so we can compute the true VE) ───────
        # engine.flow_ml_s is proportional to VE; divide out to get the base
        load = throttle_pct
        rpm  = engine.rpm
        current_ve_frac = engine._lookup_ve(load, rpm) / 100.0
        if current_ve_frac <= 0:
            return False

        predicted_base_ml_s = engine.flow_ml_s / current_ve_frac

        if predicted_base_ml_s <= 0:
            return False

        # ── true VE ratio ─────────────────────────────────────────────────────
        # true_ve_frac = observed / predicted_base
        true_ve_frac = obs_ml_s / predicted_base_ml_s
        true_ve_pct  = true_ve_frac * 100.0

        # ── locate the cell (MAP kPa × RPM grid) ─────────────────────────────
        from protocol.fuel_engine import (
            _nearest_ve_row, _nearest_ve_col, _throttle_to_map_kpa,
            MAP_STEPS, VE_RPM_STEPS,
        )
        map_kpa = _throttle_to_map_kpa(load)
        row = _nearest_ve_row(map_kpa)
        col = _nearest_ve_col(rpm)

        # ── ensure VE map exists in engine ────────────────────────────────────
        if engine._ve_map is None:
            engine._ve_map = [
                [engine._lookup_ve(
                    (MAP_STEPS[r] - 20.0) / 81.0 * 100.0,
                    VE_RPM_STEPS[c],
                ) for c in range(len(VE_RPM_STEPS))]
                for r in range(len(MAP_STEPS))
            ]

        # ── SGD nudge ─────────────────────────────────────────────────────────
        old_ve = engine._ve_map[row][col]
        new_ve = old_ve + LEARNING_RATE * (true_ve_pct - old_ve)
        new_ve = round(max(VE_MIN, min(VE_MAX, new_ve)), 1)
        engine._ve_map[row][col] = new_ve

        self.total_corrections  += 1
        self._updates_since_save += 1

        # ── persist ───────────────────────────────────────────────────────────
        if self._updates_since_save >= SAVE_EVERY_N_UPDATES:
            self._flush(engine._car_name, engine._ve_map)
            self._updates_since_save = 0
            if self._save_cb:
                self._save_cb(engine._car_name, engine._ve_map)

        # update previous state
        self._prev_fuel_pct  = fuel_pct
        self._prev_throttle  = throttle_pct
        self._prev_tank_l    = tank_liters
        return True

    def flush_now(self):
        """Force an immediate save + UI refresh (call on shutdown or car switch)."""
        engine = self._engine
        if engine._ve_map and engine._car_name:
            self._flush(engine._car_name, engine._ve_map)
            if self._save_cb:
                self._save_cb(engine._car_name, engine._ve_map)
            self._updates_since_save = 0

    def _flush(self, car_name: str, ve_map: list[list[float]]):
        from protocol.fuel_engine import MAP_STEPS, VE_RPM_STEPS
        os.makedirs(self._ve_dir, exist_ok=True)
        path = os.path.join(self._ve_dir, f"{_slug(car_name)}.csv")
        with open(path, "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["map_kpa"] + [str(r) for r in VE_RPM_STEPS])
            for r, kpa in enumerate(MAP_STEPS):
                w.writerow([str(kpa)] + [f"{v:.1f}" for v in ve_map[r]])
