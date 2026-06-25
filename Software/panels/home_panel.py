import sys, os, json
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QFrame, QLabel, QLineEdit, QSizePolicy, QComboBox,
    QCheckBox
)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QDoubleValidator
from widgets import config
from widgets.gauge import AnalogGauge, FuelGauge
from protocol.fuel_engine import FuelMapEngine, _IDLE_RPM
from protocol.ve_calibrator import VECalibrator

_VE_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "ve_maps")


_CARS_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "cars.json")


def _load_profiles() -> dict:
    with open(_CARS_JSON, encoding="utf-8") as f:
        entries = json.load(f)
    return {
        e["name"]: {
            "Engine CC":   e["engine_cc"],
            "Engine Vol":  e["engine_vol"],
            "Cylinders":   str(e.get("cylinders", "—")),
            "Horsepower":  e["horsepower"],
            "Traction":    e["traction"],
            "Weight":      e["weight"],
            "Fuel Type":   e["fuel_type"],
            # numeric fields used by gauges
            "tank_liters": e["tank_liters"],
            "max_speed":   e["max_speed_kmh"],
            "rpm_max":     e["rpm_max"],
            "rpm_redline": e["rpm_redline"],
        }
        for e in entries
    }


CAR_PROFILES = _load_profiles()


# ── shared helpers ────────────────────────────────────────────────────────────

def _line_edit(value: str, width: int, color: str) -> QLineEdit:
    e = QLineEdit(value)
    e.setFixedWidth(width)
    e.setAlignment(Qt.AlignmentFlag.AlignCenter)
    e.setValidator(QDoubleValidator(0.0, 99999.0, 2))
    e.setStyleSheet(f"""
        QLineEdit {{
            background-color: {config.SURFACE_CARD};
            color: {config.TEXT_COLOR};
            border: 1px solid {config.BORDER_COLOR};
            border-radius: 4px;
            font-size: 12px;
            font-family: {config.FONT_FAMILY};
            padding: 3px 6px;
        }}
        QLineEdit:focus {{ border: 1px solid {color}; }}
    """)
    return e


def _field_label(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setStyleSheet(f"""
        color: {config.TEXT_MUTED};
        font-size: 10px;
        font-family: {config.FONT_FAMILY};
        border: none; background: transparent;
    """)
    return lbl


# ── MetricCard ────────────────────────────────────────────────────────────────

class MetricCard(QFrame):
    def __init__(self, title: str, unit: str = "", accent: str = None, parent=None):
        super().__init__(parent)
        self._unit  = unit
        self._color = accent or config.ACCENT
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config.SURFACE_RAISED};
                border: 1px solid {config.BORDER_COLOR};
                border-top: 2px solid {self._color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        self._value_lbl = QLabel("--")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 36px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        offset_row = QHBoxLayout()
        offset_row.setSpacing(8)
        self._offset_edit = _line_edit("0.0", 72, self._color)
        self._offset_edit.textChanged.connect(self._on_offset_changed)
        offset_row.addStretch(1)
        offset_row.addWidget(_field_label("Offset"))
        offset_row.addWidget(self._offset_edit)
        offset_row.addStretch(1)

        layout.addWidget(title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addLayout(offset_row)

        self._raw_value = 0.0
        self._on_change = None

    def _on_offset_changed(self, _):
        calibrated = self.set_raw(self._raw_value)
        if self._on_change is not None:
            self._on_change(calibrated)

    def offset(self) -> float:
        try:
            return float(self._offset_edit.text())
        except ValueError:
            return 0.0

    def set_raw(self, raw_val: float) -> float:
        self._raw_value = raw_val
        calibrated = raw_val + self.offset()
        self._value_lbl.setText(f"{calibrated:.1f}{self._unit}")
        return calibrated


# ── FuelCard ──────────────────────────────────────────────────────────────────

class FuelCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        color = config.ACCENT_AMBER
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config.SURFACE_RAISED};
                border: 1px solid {config.BORDER_COLOR};
                border-top: 2px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(6)

        title_lbl = QLabel("FUEL")
        title_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        self._value_lbl = QLabel("--")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 36px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        offset_row = QHBoxLayout()
        offset_row.setSpacing(8)
        self._offset_edit = _line_edit("0.0", 72, color)
        self._offset_edit.textChanged.connect(self._on_offset_changed)
        offset_row.addStretch(1)
        offset_row.addWidget(_field_label("Offset %"))
        offset_row.addWidget(self._offset_edit)
        offset_row.addStretch(1)

        # manual override checkbox
        self._manual_cb = QCheckBox("Manual")
        self._manual_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {color};
                font-family: {config.FONT_FAMILY};
                font-size: 11px;
                font-weight: bold;
                spacing: 4px;
            }}
            QCheckBox::indicator {{
                width: 14px; height: 14px;
                border: 1px solid {color};
                border-radius: 3px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {color};
            }}
        """)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background: {config.BORDER_COLOR}; border: none;")
        div.setFixedHeight(1)

        vol_row = QHBoxLayout()
        vol_row.setSpacing(12)

        cur_col = QVBoxLayout()
        cur_col.setSpacing(3)
        self._cur_vol_edit = _line_edit("40.0", 72, color)
        cur_col.addWidget(_field_label("Current (L)"))
        cur_col.addWidget(self._cur_vol_edit)

        max_col = QVBoxLayout()
        max_col.setSpacing(3)
        self._max_vol_edit = _line_edit("50.0", 72, color)
        max_col.addWidget(_field_label("Tank cap. (L)"))
        max_col.addWidget(self._max_vol_edit)

        vol_row.addStretch(1)
        vol_row.addLayout(cur_col)
        vol_row.addLayout(max_col)
        vol_row.addStretch(1)

        layout.addWidget(title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addLayout(offset_row)
        layout.addWidget(self._manual_cb)
        layout.addWidget(div)
        layout.addLayout(vol_row)

        self._raw_value = 0.0
        self._on_change = None

        for edit in (self._cur_vol_edit, self._max_vol_edit):
            edit.textChanged.connect(self._on_offset_changed)

    def is_manual(self) -> bool:
        return self._manual_cb.isChecked()

    def _on_offset_changed(self, _):
        if self.is_manual():
            calibrated = self._calc_manual_pct()
        else:
            calibrated = self.set_raw(self._raw_value)
        if self._on_change is not None:
            self._on_change(calibrated)

    def _calc_manual_pct(self) -> float:
        """Compute fuel % from the manual Current (L) / Tank cap. (L) fields."""
        cur = self.current_liters()
        cap = self.tank_liters()
        pct = (cur / cap * 100.0) if cap > 0 else 0.0
        pct = max(0.0, min(pct, 100.0))
        return self.set_raw(pct)

    def offset(self) -> float:
        try:
            return float(self._offset_edit.text())
        except ValueError:
            return 0.0

    def current_liters(self) -> float:
        try:
            return float(self._cur_vol_edit.text())
        except ValueError:
            return 0.0

    def tank_liters(self) -> float:
        try:
            v = float(self._max_vol_edit.text())
            return v if v > 0 else 50.0
        except ValueError:
            return 50.0

    def set_tank(self, liters: float):
        self._max_vol_edit.setText(str(int(liters)))

    def set_raw(self, raw_val: float) -> float:
        self._raw_value = raw_val
        calibrated = max(0.0, min(raw_val + self.offset(), 100.0))
        self._value_lbl.setText(f"{calibrated:.1f}%")
        return calibrated


# ── EfficCard ─────────────────────────────────────────────────────────────────

class EfficCard(QFrame):
    def __init__(self, title: str, unit: str, accent: str, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config.SURFACE_RAISED};
                border: 1px solid {config.BORDER_COLOR};
                border-top: 2px solid {accent};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(2)

        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        self._value_lbl = QLabel("--")
        self._value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._value_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 30px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        unit_lbl = QLabel(unit)
        unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        unit_lbl.setStyleSheet(f"""
            color: #ffffff;
            font-size: 11px;
            font-weight: bold;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        layout.addWidget(title_lbl)
        layout.addWidget(self._value_lbl)
        layout.addWidget(unit_lbl)

    def set_value(self, value: float, decimals: int = 1):
        self._value_lbl.setText(f"{value:.{decimals}f}")


# ── CarProfileCard ────────────────────────────────────────────────────────────

class CarProfileCard(QFrame):
    # emits the full profile dict whenever the dropdown changes
    profile_changed = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        color = config.ACCENT_PURPLE
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {config.SURFACE_RAISED};
                border: 1px solid {config.BORDER_COLOR};
                border-top: 2px solid {color};
                border-radius: 6px;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 14, 18, 14)
        layout.setSpacing(10)

        title_lbl = QLabel("CAR PROFILE")
        title_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-size: 11px;
            font-family: {config.FONT_FAMILY};
            border: none; background: transparent;
        """)

        self._combo = QComboBox()
        self._combo.addItems(CAR_PROFILES.keys())
        self._combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {config.SURFACE_CARD};
                color: {config.TEXT_COLOR};
                border: 1px solid {color};
                border-radius: 4px;
                font-family: {config.FONT_FAMILY};
                font-size: 12px;
                padding: 5px 10px;
            }}
            QComboBox:hover {{ border: 1px solid {config.ACCENT}; }}
            QComboBox::drop-down {{ border: none; width: 24px; }}
            QComboBox::down-arrow {{
                width: 10px; height: 10px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid {color};
            }}
            QComboBox QAbstractItemView {{
                background-color: {config.SURFACE_CARD};
                color: {config.TEXT_COLOR};
                border: 1px solid {config.BORDER_COLOR};
                selection-background-color: {config.SURFACE_RAISED};
                selection-color: {color};
                font-family: {config.FONT_FAMILY};
                font-size: 12px;
                padding: 4px;
            }}
        """)

        div = QFrame()
        div.setFrameShape(QFrame.Shape.HLine)
        div.setStyleSheet(f"background: {config.BORDER_COLOR}; border: none;")
        div.setFixedHeight(1)

        SPEC_KEYS = [
            ("Engine CC",  "Engine CC"),
            ("Engine Vol", "Engine Vol"),
            ("Cylinders",  "Cylinders"),
            ("Horsepower", "Horsepower"),
            ("Traction",   "Traction"),
            ("Weight",     "Weight"),
            ("Fuel Type",  "Fuel Type"),
        ]
        self._spec_rows: dict[str, QLabel] = {}
        specs_layout = QVBoxLayout()
        specs_layout.setSpacing(6)

        for key, label in SPEC_KEYS:
            row = QHBoxLayout()
            row.setSpacing(8)

            key_lbl = QLabel(label)
            key_lbl.setFixedWidth(90)
            key_lbl.setStyleSheet(f"""
                color: {config.TEXT_MUTED};
                font-size: 11px;
                font-family: {config.FONT_FAMILY};
                border: none; background: transparent;
            """)

            val_lbl = QLabel("--")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val_lbl.setStyleSheet(f"""
                color: {config.TEXT_COLOR};
                font-size: 12px;
                font-weight: bold;
                font-family: {config.FONT_FAMILY};
                border: none; background: transparent;
            """)
            self._spec_rows[key] = val_lbl

            row.addWidget(key_lbl)
            row.addWidget(val_lbl, stretch=1)
            specs_layout.addLayout(row)

        layout.addWidget(title_lbl)
        layout.addWidget(self._combo)
        layout.addWidget(div)
        layout.addLayout(specs_layout)

        self._combo.currentTextChanged.connect(self._on_profile_changed)
        self._on_profile_changed(self._combo.currentText())

    def _on_profile_changed(self, name: str):
        profile = CAR_PROFILES.get(name, {})
        for key, lbl in self._spec_rows.items():
            value = profile.get(key, "--")
            if key == "Fuel Type":
                c = config.ACCENT_AMBER if value == "Gasoline" else config.ACCENT_PURPLE
                lbl.setStyleSheet(f"""
                    color: {c}; font-size: 12px; font-weight: bold;
                    font-family: {config.FONT_FAMILY};
                    border: none; background: transparent;
                """)
            lbl.setText(value)
        self.profile_changed.emit(profile)


# ── HomeDock ──────────────────────────────────────────────────────────────────

class HomeDock(QWidget):
    # emitted on every packet with (rpm, map_kpa) for live VE map highlight
    operating_point = Signal(float, float)

    def __init__(self, worker=None, parent=None):
        super().__init__(parent)
        self._engine     = FuelMapEngine()
        self._calibrator = VECalibrator(
            engine=self._engine,
            ve_dir=_VE_DIR,
            save_callback=self._on_ve_calibrated,
        )
        self._setup_ui()
        if worker is not None:
            worker.packet_received.connect(self._on_packet)
        # throttle operating point emissions to ~5 Hz
        self._op_timer = QTimer(self)
        self._op_timer.setInterval(200)
        self._op_timer.timeout.connect(self._emit_operating_point)
        self._op_timer.start()
        self._pending_rpm = 0.0
        self._pending_map = 0.0

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("HOME")
        panel.setStyleSheet(config.PANEL_STYLE)
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(24)

        # ── Left column: gauges + efficiency cards ────────────────────────────
        left_col = QVBoxLayout()
        left_col.setSpacing(16)

        # Speed gauge (top-left)
        self.speed_gauge = AnalogGauge()
        self.speed_gauge.min_value   = 0
        self.speed_gauge.max_value   = 240
        self.speed_gauge.label       = "km/h"
        self.speed_gauge.tick_step   = 10
        self.speed_gauge.minor_ticks = 2
        self.speed_gauge.label_step  = 20
        self.speed_gauge.red_ticks   = {30, 50, 130}
        self.speed_gauge.zones = [
            (0.0, 0.6, "#00aaff"),
            (0.6, 0.8, "#ffaa00"),
            (0.8, 1.0, "#ff3355"),
        ]
        self.speed_gauge.setFixedSize(320, 320)

        # RPM gauge (top-center)
        self.rpm_gauge = AnalogGauge()
        self.rpm_gauge.min_value = 0
        self.rpm_gauge.max_value = 8000
        self.rpm_gauge.label = "RPM"
        self.rpm_gauge.tick_step   = 1000
        self.rpm_gauge.minor_ticks = 5
        self.rpm_gauge.zones = [
            (0.0, 0.60, "#00aaff"),
            (0.60, 0.85, "#ffaa00"),
            (0.85, 1.0,  "#ff3355"),
        ]
        self.rpm_gauge.setFixedSize(320, 320)

        # Fuel gauge (top-right, half-circle)
        self.fuel_gauge = FuelGauge()
        self.fuel_gauge.min_value = 0
        self.fuel_gauge.max_value = 100
        self.fuel_gauge.label = "Fuel %"
        self.fuel_gauge.zones = [
            (0.0, 0.3, "#ff3355"),
            (0.3, 0.6, "#ffaa00"),
            (0.6, 1.0, "#00e5a0"),
        ]
        self.fuel_gauge.setFixedSize(320, 320)

        gauges_row = QHBoxLayout()
        gauges_row.setSpacing(20)
        gauges_row.addWidget(self.speed_gauge)
        gauges_row.addWidget(self.rpm_gauge)
        gauges_row.addWidget(self.fuel_gauge)

        # Efficiency cards row
        self._l100_card  = EfficCard("Consumption",  "L / 100 km", config.ACCENT)
        self._mpg_card   = EfficCard("Fuel Economy",  "MPG",        config.ACCENT_GREEN)
        self._range_card = EfficCard("Range Left",    "km",         config.ACCENT_AMBER)
        self._gear_card  = EfficCard("Gear",          "auto",       config.ACCENT_PURPLE)

        effic_row = QHBoxLayout()
        effic_row.setSpacing(12)
        for card in (self._l100_card, self._mpg_card, self._range_card, self._gear_card):
            card.setMinimumHeight(110)
            effic_row.addWidget(card)

        left_col.addLayout(gauges_row)
        left_col.addLayout(effic_row)

        # ── Right column: sensor metric cards + profile ───────────────────────
        right_col = QVBoxLayout()
        right_col.setSpacing(12)

        self._air_card     = MetricCard("Air Temp",  "°C",   config.ACCENT_GREEN)
        self._eng_card     = MetricCard("Eng Temp",  "°C",   config.ACCENT_RED)
        self._pres_card    = MetricCard("Pressure",  " bar", config.ACCENT_PURPLE)
        self._fuel_card    = FuelCard()
        self._profile_card = CarProfileCard()

        # Neutral checkbox — create before adding to layout
        self._neutral_cb = QCheckBox("Neutral")
        self._neutral_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {config.ACCENT_AMBER};
                font-family: {config.FONT_FAMILY};
                font-size: 12px;
                font-weight: bold;
                spacing: 6px;
            }}
            QCheckBox::indicator {{
                width: 16px; height: 16px;
                border: 2px solid {config.ACCENT_AMBER};
                border-radius: 4px;
                background: transparent;
            }}
            QCheckBox::indicator:checked {{
                background: {config.ACCENT_AMBER};
            }}
        """)
        self._neutral_cb.toggled.connect(self._on_neutral_toggled)

        for card in (self._air_card, self._eng_card, self._pres_card, self._fuel_card):
            card.setMinimumHeight(140)
            card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            right_col.addWidget(card)

        right_col.addSpacing(6)
        right_col.addWidget(self._neutral_cb)
        right_col.addSpacing(6)

        self._profile_card.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        right_col.addWidget(self._profile_card)

        # wire fuel card → fuel gauge needle
        self._fuel_card._on_change = self.fuel_gauge.set_value

        # wire profile dropdown → update gauges + fuel tank
        self._profile_card.profile_changed.connect(self._on_profile_changed)

        panel_layout.addLayout(left_col, stretch=3)
        panel_layout.addLayout(right_col, stretch=1)

        root.addWidget(panel)

        # apply the initially selected profile
        first = next(iter(CAR_PROFILES.values()), {})
        self._on_profile_changed(first)

    def _on_profile_changed(self, profile: dict):
        
        rpm_max     = profile.get("rpm_max", 8000)
        rpm_redline = profile.get("rpm_redline", 7000)
        max_speed   = profile.get("max_speed", 240)
        tank        = profile.get("tank_liters", 50)
        car_name    = self._profile_card._combo.currentText()
        print("Home car:", car_name)
        # flush calibration data for the previous car before switching
        self._calibrator.flush_now()
        self._calibrator.reset()

        # update engine model
        self._engine.set_car(car_name, tank_liters=tank)

        # RPM gauge
        redline_ratio = rpm_redline / rpm_max
        warn_ratio    = max(0.0, redline_ratio - 0.15)
        self.rpm_gauge.max_value = rpm_max
        self.rpm_gauge.tick_step = 1000
        self.rpm_gauge.red_above = rpm_redline
        self.rpm_gauge.zones = [
            (0.0,           warn_ratio,    "#00aaff"),
            (warn_ratio,    redline_ratio, "#ffaa00"),
            (redline_ratio, 1.0,           "#ff3355"),
        ]
        self.rpm_gauge.update()

        # Speed gauge
        self.speed_gauge.max_value = max_speed
        self.speed_gauge.tick_step = 10
        self.speed_gauge.update()

        # Fuel card
        self._fuel_card.set_tank(tank)

    def _on_packet(self, pkt):
        self._air_card.set_raw(pkt.air_temp)
        self._eng_card.set_raw(pkt.eng_temp)
        self._pres_card.set_raw(pkt.pressure)

        # use manual fuel % when checkbox is checked
        if self._fuel_card.is_manual():
            calibrated_fuel = self._fuel_card._calc_manual_pct()
        else:
            calibrated_fuel = self._fuel_card.set_raw(pkt.fuel_pct)
        self.fuel_gauge.set_value(calibrated_fuel)

        # run fuel-map engine
        tank_l     = self._fuel_card.tank_liters()
        cur_liters = self._fuel_card.current_liters()
        self._engine.set_tank(tank_l)
        self._engine.update(
            throttle_pct=pkt.throttle_pct,
            fuel_pct=calibrated_fuel,
            fuel_liters_override=cur_liters,
        )

        # run VE calibration (uses fuel drop between packets as ground truth)
        self._calibrator.update(
            throttle_pct=pkt.throttle_pct,
            fuel_pct=calibrated_fuel,
            tank_liters=tank_l,
        )

        # update gauges from engine output
        self.rpm_gauge.set_value(self._engine.rpm)
        self.speed_gauge.set_value(
            self._engine.rpm / self.rpm_gauge.max_value * self.speed_gauge.max_value
        )

        # efficiency cards
        self._l100_card.set_value(self._engine.l100)
        self._mpg_card.set_value(self._engine.mpg)
        self._range_card.set_value(self._engine.range_km, decimals=0)
        self._gear_card.set_value(float(self._engine.gear), decimals=0)

        # save last packet for VE map reload re-apply
        self._last_pkt = pkt

        # store operating point for the throttled signal
        from protocol.fuel_engine import _throttle_to_map_kpa
        self._pending_rpm = self._engine.rpm
        self._pending_map = _throttle_to_map_kpa(pkt.throttle_pct)

    def _emit_operating_point(self):
        self.operating_point.emit(self._pending_rpm, self._pending_map)

    def _on_neutral_toggled(self, checked: bool):
        self._engine.set_neutral(checked)
        # force a gauge update immediately so RPM shows idle / speed shows 0
        if checked:
            self.rpm_gauge.set_value(_IDLE_RPM)
            self.speed_gauge.set_value(0.0)
            self._gear_card.set_value(0.0, decimals=0)
            self._pending_rpm = _IDLE_RPM
            self._pending_map = 20.0  # idle vacuum

    def reload_ve_map(self):
        """Reload the VE map from disk and immediately recompute (called when user edits VE Map panel)."""
        self._engine.reload_ve_map()
        # re-run the engine update with the last known data to reflect changes immediately
        if hasattr(self, '_last_pkt'):
            self._reapply_engine()

    def _reapply_engine(self):
        """Re-run engine model with the last packet data (used after VE map edits)."""
        pkt = self._last_pkt
        tank_l = self._fuel_card.tank_liters()
        cur_liters = self._fuel_card.current_liters()
        self._engine.set_tank(tank_l)
        if self._fuel_card.is_manual():
            calibrated_fuel = self._fuel_card._calc_manual_pct()
        else:
            calibrated_fuel = self._fuel_card.set_raw(pkt.fuel_pct)
        self._engine.update(
            throttle_pct=pkt.throttle_pct,
            fuel_pct=calibrated_fuel,
            fuel_liters_override=cur_liters,
        )
        self.rpm_gauge.set_value(self._engine.rpm)
        self.speed_gauge.set_value(
            self._engine.rpm / self.rpm_gauge.max_value * self.speed_gauge.max_value
        )
        self._l100_card.set_value(self._engine.l100)
        self._mpg_card.set_value(self._engine.mpg)
        self._range_card.set_value(self._engine.range_km, decimals=0)
        self._gear_card.set_value(float(self._engine.gear), decimals=0)
        from protocol.fuel_engine import _throttle_to_map_kpa
        self._pending_rpm = self._engine.rpm
        self._pending_map = _throttle_to_map_kpa(pkt.throttle_pct)

    def _on_ve_calibrated(self, car_name: str, ve_map: list[list[float]]):
        """Called by VECalibrator after every SAVE_EVERY_N_UPDATES corrections."""
        # reload into the engine so the next update() uses the corrected map
        self._engine.reload_ve_map()
