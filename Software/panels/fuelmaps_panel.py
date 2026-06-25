import sys, os, csv, json, re, math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QBrush, QFont, QPainter
from widgets import config

# ── paths ─────────────────────────────────────────────────────────────────────
_CARS_JSON = os.path.join(os.path.dirname(__file__), "..", "data", "cars.json")
_VE_DIR    = os.path.join(os.path.dirname(__file__), "..", "data", "ve_maps")

# ── VE map grid ──────────────────────────────────────────────────────────────
RPM_STEPS  = list(range(500, 8500, 500))           # 500 … 8000  (16 columns)
MAP_STEPS  = list(range(20, 105, 5))               # 20 … 100 kPa (17 rows)


# ── helpers ──────────────────────────────────────────────────────────────────

def _car_names() -> list[str]:
    with open(_CARS_JSON, encoding="utf-8") as f:
        return [e["name"] for e in json.load(f)]


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _ve_csv_path(car_name: str) -> str:
    return os.path.join(_VE_DIR, f"{_slug(car_name)}.csv")


def _ve_default(map_kpa: int, rpm: int) -> float:
    """Realistic NA VE curve — bell-shaped over RPM, rising with MAP."""
    rpm_norm = rpm / 8000.0
    map_norm = (map_kpa - 20.0) / 80.0                          # 0..1

    # bell curve peaks at ~55% of RPM range (sweet spot for NA intake tuning)
    rpm_bell = math.exp(-((rpm_norm - 0.55) ** 2) / (2 * 0.18 ** 2))

    # base VE: 30% at vacuum idle, up to ~95% at WOT + peak RPM
    ve = 30.0 + map_norm * 50.0 + rpm_bell * 20.0 * (0.5 + 0.5 * map_norm)

    # high-RPM breathing penalty (valve float, flow restriction)
    if rpm_norm > 0.75:
        ve -= (rpm_norm - 0.75) * 40.0

    return round(max(25.0, min(100.0, ve)), 1)


def _build_default_ve_table() -> list[list[float]]:
    return [[_ve_default(kpa, rpm) for rpm in RPM_STEPS] for kpa in MAP_STEPS]


def _save_ve_csv(car_name: str, data: list[list[float]]):
    os.makedirs(_VE_DIR, exist_ok=True)
    with open(_ve_csv_path(car_name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["map_kpa"] + [str(r) for r in RPM_STEPS])
        for r, kpa in enumerate(MAP_STEPS):
            w.writerow([str(kpa)] + [f"{v:.1f}" for v in data[r]])


def _load_ve_csv(car_name: str) -> list[list[float]] | None:
    path = _ve_csv_path(car_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        data = [[float(v) for v in row[1:]] for row in rows[1:]]
        if len(data) == len(MAP_STEPS) and all(len(r) == len(RPM_STEPS) for r in data):
            return data
    except Exception:
        pass
    return None


def _ve_cell_color(value: float, v_min: float, v_max: float) -> tuple[QColor, QColor]:
    """Low VE → red (lean), mid VE → green (stoich sweet spot), high VE → blue (rich)."""
    span = v_max - v_min
    t    = (value - v_min) / span if span > 0 else 0.0
    t    = max(0.0, min(1.0, t))
    # 0 (red) → 120 (green) → 220 (blue) via two-segment interpolation
    if t < 0.5:
        hue = int(t * 2 * 120)         # 0→120
    else:
        hue = int(120 + (t - 0.5) * 2 * 100)  # 120→220
    bg = QColor.fromHsl(hue, 200, 70)
    fg = QColor("#f0f0f0") if bg.lightness() < 128 else QColor("#111111")
    return bg, fg


def _btn_style(color: str) -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {color};
            border: 1px solid {color};
            border-radius: 4px;
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
            padding: 5px 18px;
        }}
        QPushButton:hover {{ background-color: {config.SURFACE_RAISED}; }}
        QPushButton:pressed {{ background-color: {config.BACKGROUND_PRESSED}; }}
    """


def _combo_style(color: str) -> str:
    return f"""
        QComboBox {{
            background-color: {config.SURFACE_CARD};
            color: {config.TEXT_COLOR};
            border: 1px solid {color};
            border-radius: 4px;
            font-family: {config.FONT_FAMILY};
            font-size: 12px;
            padding: 4px 10px;
            min-width: 180px;
        }}
        QComboBox:hover {{ border: 1px solid {config.ACCENT}; }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {color};
            width: 0; height: 0;
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
    """


# ── rotated axis label ────────────────────────────────────────────────────────

class _RotatedLabel(QWidget):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self._text = text
        self.setFixedWidth(16)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QColor(config.TEXT_MUTED))
        painter.setFont(QFont(config.FONT_FAMILY, 9))
        painter.translate(self.width(), self.height())
        painter.rotate(-90)
        painter.drawText(0, 0, self.height(), self.width(),
                         Qt.AlignmentFlag.AlignCenter, self._text)


# ── nearest cell helpers ──────────────────────────────────────────────────────

def _nearest_row(map_kpa: float) -> int:
    map_kpa = max(MAP_STEPS[0], min(MAP_STEPS[-1], map_kpa))
    return min(range(len(MAP_STEPS)),
               key=lambda i: abs(MAP_STEPS[i] - map_kpa))


def _nearest_col(rpm: float) -> int:
    rpm = max(RPM_STEPS[0], min(RPM_STEPS[-1], rpm))
    return min(range(len(RPM_STEPS)),
               key=lambda i: abs(RPM_STEPS[i] - rpm))


def _throttle_to_map_kpa(throttle_pct: float) -> float:
    """Closed throttle ≈ 20 kPa (high vacuum), WOT ≈ 101 kPa (atmospheric)."""
    return 20.0 + (throttle_pct / 100.0) * 81.0


# ── VEMapTable ────────────────────────────────────────────────────────────────

class VEMapTable(QWidget):
    """
    Volumetric Efficiency map — RPM (x) vs Manifold Pressure kPa (y).
    Mimics a real AFR/VE table layout with pressure on the Y-axis.
    """

    # emitted whenever the VE map is saved (cell edit, Save button, or Reset)
    map_saved = Signal(str)  # car_name

    def __init__(self, parent=None):
        super().__init__(parent)
        self._car_name: str = ""
        self._data: list[list[float]] = _build_default_ve_table()
        self._ignore_change = False
        self._hl_row: int | None = None   # highlighted row (engine operating point)
        self._hl_col: int | None = None
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        car_lbl = QLabel("Car:")
        car_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
        """)
        self._combo = QComboBox()
        self._combo.addItems(_car_names())
        self._combo.setStyleSheet(_combo_style(config.ACCENT_GREEN))
        self._combo.currentTextChanged.connect(self._on_car_changed)

        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 10px;
            padding: 0 6px;
        """)

        self._hover_lbl = QLabel("")
        self._hover_lbl.setStyleSheet(f"""
            color: {config.ACCENT_GREEN};
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
            padding: 2px 8px;
            border: 1px solid {config.BORDER_COLOR};
            border-radius: 4px;
        """)
        self._hover_lbl.setFixedHeight(26)
        self._hover_lbl.setMinimumWidth(320)

        save_btn = QPushButton("💾  Save map")
        save_btn.setFixedHeight(28)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.setStyleSheet(_btn_style(config.ACCENT_GREEN))
        save_btn.clicked.connect(self._save)

        reset_btn = QPushButton("↺  Reset")
        reset_btn.setFixedHeight(28)
        reset_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        reset_btn.setStyleSheet(_btn_style(config.ACCENT_AMBER))
        reset_btn.clicked.connect(self._reset)

        toolbar.addWidget(car_lbl)
        toolbar.addWidget(self._combo)
        toolbar.addWidget(self._status_lbl)
        toolbar.addSpacing(8)
        toolbar.addWidget(self._hover_lbl)
        toolbar.addStretch(1)
        toolbar.addWidget(self._build_legend())
        toolbar.addSpacing(12)
        toolbar.addWidget(save_btn)
        toolbar.addWidget(reset_btn)

        # ── x-axis label ──────────────────────────────────────────────────────
        axis_row = QHBoxLayout()
        axis_row.setSpacing(0)
        corner = QLabel("")
        corner.setFixedWidth(52)
        x_lbl = QLabel("Engine RPM →")
        x_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        x_lbl.setStyleSheet(
            f"color: {config.TEXT_MUTED}; font-family: {config.FONT_FAMILY}; font-size: 10px;"
        )
        axis_row.addWidget(corner)
        axis_row.addWidget(x_lbl)

        # ── table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget(len(MAP_STEPS), len(RPM_STEPS))
        self._table.setHorizontalHeaderLabels([str(r) for r in RPM_STEPS])
        self._table.setVerticalHeaderLabels([f"{kpa}" for kpa in MAP_STEPS])

        hdr_style = f"""
            QHeaderView::section {{
                background-color: {config.SURFACE_RAISED};
                color: {config.TEXT_COLOR};
                font-family: {config.FONT_FAMILY};
                font-size: 10px;
                font-weight: bold;
                padding: 3px;
                border: none;
                border-right: 1px solid {config.BORDER_COLOR};
                border-bottom: 1px solid {config.BORDER_COLOR};
            }}
        """
        self._table.horizontalHeader().setStyleSheet(hdr_style)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.verticalHeader().setStyleSheet(hdr_style)
        self._table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.verticalHeader().setDefaultAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        self._table.verticalHeader().setFixedWidth(40)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {config.SURFACE_CARD};
                gridline-color: {config.BORDER_COLOR};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 1px;
                font-family: {config.FONT_FAMILY};
                font-size: 10px;
                font-weight: bold;
            }}
            QTableWidget::item:selected {{ border: 2px solid {config.ACCENT_GREEN}; }}
        """)
        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellEntered.connect(self._on_cell_hover)
        self._table.setMouseTracking(True)

        table_row = QHBoxLayout()
        table_row.setSpacing(4)
        table_row.addWidget(_RotatedLabel("MAP (kPa)  ↓", parent=self))
        table_row.addWidget(self._table)

        root.addLayout(toolbar)
        root.addLayout(axis_row)
        root.addLayout(table_row)

        if self._combo.count():
            self._on_car_changed(self._combo.currentText())

    @staticmethod
    def _build_legend() -> QWidget:
        steps    = 40
        swatches = QWidget()
        h = QHBoxLayout(swatches)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        for i in range(steps):
            t = i / (steps - 1)
            if t < 0.5:
                hue = int(t * 2 * 120)
            else:
                hue = int(120 + (t - 0.5) * 2 * 100)
            c = QColor.fromHsl(hue, 200, 70)
            f = QFrame()
            f.setFixedSize(8, 16)
            f.setStyleSheet(f"background: {c.name()}; border: none;")
            h.addWidget(f)

        s = f"color: {config.TEXT_MUTED}; font-size: 9px; font-family: {config.FONT_FAMILY};"
        lo = QLabel("  lean"); lo.setStyleSheet(s)
        hi = QLabel("rich  "); hi.setStyleSheet(s)

        outer = QWidget()
        row   = QHBoxLayout(outer)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(4)
        row.addWidget(lo)
        row.addWidget(swatches)
        row.addWidget(hi)
        return outer

    def sync_car(self, car_name: str):
        idx = self._combo.findText(car_name)
        if idx >= 0 and idx != self._combo.currentIndex():
            self._combo.setCurrentIndex(idx)

    # ── live operating point highlight ────────────────────────────────────────

    def set_operating_point(self, rpm: float, map_kpa: float):
        """Highlight the cell matching the engine's current (RPM, MAP kPa)."""
        row = _nearest_row(map_kpa)
        col = _nearest_col(rpm)
        # restore previous highlight cell to normal color
        if self._hl_row is not None and self._hl_col is not None:
            old_item = self._table.item(self._hl_row, self._hl_col)
            if old_item:
                val = self._data[self._hl_row][self._hl_col]
                flat = [v for row in self._data for v in row]
                bg, fg = _ve_cell_color(val, min(flat), max(flat))
                old_item.setBackground(QBrush(bg))
                old_item.setForeground(QBrush(fg))
                old_font = old_item.font()
                old_font.setBold(False)
                old_font.setPointSize(10)   # use your table's normal font size
                old_item.setFont(old_font)       
        # highlight new cell
        new_item = self._table.item(row, col)
        if new_item is None:
            new_item = QTableWidgetItem()
            self._table.setItem(row, col, new_item)
        new_item.setBackground(QBrush(QColor("#00E5FF")))   # bright cyan
        new_item.setForeground(QBrush(QColor("#000000")))   # black text
        font = new_item.font()
        font.setBold(True)
        font.setPointSize(18)   # 2 points larger than normal
        new_item.setFont(font)

        self._hl_row, self._hl_col = row, col

    def clear_operating_point(self):
        """Remove highlight when no valid operating point (e.g. neutral)."""
        if self._hl_row is not None and self._hl_col is not None:
            old_item = self._table.item(self._hl_row, self._hl_col)
            if old_item:
                val = self._data[self._hl_row][self._hl_col]
                flat = [v for row in self._data for v in row]
                bg, fg = _ve_cell_color(val, min(flat), max(flat))
                old_item.setBackground(QBrush(bg))
                old_item.setForeground(QBrush(fg))
        self._hl_row, self._hl_col = None, None

    # ── data ──────────────────────────────────────────────────────────────────

    def _on_car_changed(self, car_name: str):
        print("VE editor car:", car_name)
        self._car_name = car_name
        loaded = _load_ve_csv(car_name)
        if loaded:
            self._data = loaded
        else:
            self._data = _build_default_ve_table()
            _save_ve_csv(car_name, self._data)

        self._populate(recolor=True)
        self._update_status()

    def _populate(self, recolor: bool = False):
        self._ignore_change = True
        if recolor:
            flat  = [v for row in self._data for v in row]
            v_min, v_max = min(flat), max(flat)

        font = QFont(config.FONT_FAMILY, 9)
        font.setBold(True)

        for r in range(len(MAP_STEPS)):
            for c in range(len(RPM_STEPS)):
                val  = self._data[r][c]
                item = self._table.item(r, c)
                if item is None:
                    item = QTableWidgetItem()
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFont(font)
                    self._table.setItem(r, c, item)
                item.setText(f"{val:.1f}")
                if recolor:
                    bg, fg = _ve_cell_color(val, v_min, v_max)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))

        self._ignore_change = False

    def _recolor_all(self):
        flat  = [v for row in self._data for v in row]
        v_min, v_max = min(flat), max(flat)
        for r in range(len(MAP_STEPS)):
            for c in range(len(RPM_STEPS)):
                item = self._table.item(r, c)
                if item:
                    bg, fg = _ve_cell_color(self._data[r][c], v_min, v_max)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))

    def _update_status(self):
        self._status_lbl.setText(f"→ {os.path.relpath(_ve_csv_path(self._car_name))}")

    def _save(self):
        if not self._car_name:
            return
        _save_ve_csv(self._car_name, self._data)
        self._status_lbl.setText(f"Saved  →  {os.path.relpath(_ve_csv_path(self._car_name))}")
        self.map_saved.emit(self._car_name)

    def _reset(self):
        self._data = _build_default_ve_table()
        self._populate(recolor=True)
        if self._car_name:
            _save_ve_csv(self._car_name, self._data)
            self._update_status()
            self.map_saved.emit(self._car_name)

    # ── cell interaction ──────────────────────────────────────────────────────

    def _on_cell_changed(self, row: int, col: int):
        if self._ignore_change:
            return
        item = self._table.item(row, col)
        if item is None:
            return
        try:
            val = max(0.0, min(110.0, float(item.text().replace(",", "."))))
            self._data[row][col] = round(val, 1)
        except ValueError:
            self._ignore_change = True
            item.setText(f"{self._data[row][col]:.1f}")
            self._ignore_change = False
            return
        self._recolor_all()
        if self._car_name:
            _save_ve_csv(self._car_name, self._data)
            self.map_saved.emit(self._car_name)

    def _on_cell_hover(self, row: int, col: int):
        if 0 <= row < len(MAP_STEPS) and 0 <= col < len(RPM_STEPS):
            self._hover_lbl.setText(
                f"RPM: {RPM_STEPS[col]}   "
                f"MAP: {MAP_STEPS[row]} kPa   "
                f"VE: {self._data[row][col]:.1f}%"
            )


# ── FuelMapsDock ──────────────────────────────────────────────────────────────

class FuelMapsDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._ve_table = VEMapTable()
        self._setup_ui()

    @property
    def ve_table(self) -> VEMapTable:
        """Expose the embedded VEMapTable so MainWindow can wire live highlights."""
        return self._ve_table

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("VOLUMETRIC EFFICIENCY MAP")
        panel.setStyleSheet(config.PANEL_STYLE)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.addWidget(self._ve_table)

        root.addWidget(panel)
