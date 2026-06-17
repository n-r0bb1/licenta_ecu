import sys, os, csv, json, re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QSizePolicy, QComboBox,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QBrush, QFont, QPainter
from widgets import config

# ── paths ─────────────────────────────────────────────────────────────────────
_CARS_JSON    = os.path.join(os.path.dirname(__file__), "..", "data", "cars.json")
_MAPS_DIR     = os.path.join(os.path.dirname(__file__), "..", "data", "fuel_maps")

# ── fuel map constants ────────────────────────────────────────────────────────
RPM_STEPS  = list(range(1000, 9000, 1000))   # 1000 … 8000
LOAD_STEPS = list(range(0, 110, 10))          # 0 … 100
RPM_MAX    = 8000

BASE        = 2.0
LOAD_FACTOR = 9.0
RPM_FACTOR  = 4.0


# ── helpers ───────────────────────────────────────────────────────────────────

def _car_names() -> list[str]:
    with open(_CARS_JSON, encoding="utf-8") as f:
        return [e["name"] for e in json.load(f)]


def _slug(name: str) -> str:
    """Convert a car name to a safe filename stem."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _csv_path(car_name: str) -> str:
    return os.path.join(_MAPS_DIR, f"{_slug(car_name)}.csv")


def _formula(load_pct: float, rpm: int) -> float:
    return round(BASE + (load_pct / 100) * LOAD_FACTOR + (rpm / RPM_MAX) * RPM_FACTOR, 1)


def _build_default_table() -> list[list[float]]:
    return [[_formula(load, rpm) for rpm in RPM_STEPS] for load in LOAD_STEPS]


def _save_csv(car_name: str, data: list[list[float]]):
    os.makedirs(_MAPS_DIR, exist_ok=True)
    with open(_csv_path(car_name), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["load_pct"] + [str(r) for r in RPM_STEPS])
        for r, load in enumerate(LOAD_STEPS):
            w.writerow([str(load)] + [f"{v:.1f}" for v in data[r]])


def _load_csv(car_name: str) -> list[list[float]] | None:
    path = _csv_path(car_name)
    if not os.path.exists(path):
        return None
    try:
        with open(path, newline="") as f:
            rows = list(csv.reader(f))
        # skip header, parse values (skip first column = load label)
        return [[float(v) for v in row[1:]] for row in rows[1:]]
    except Exception:
        return None


def _hsl_cell_color(value: float, v_min: float, v_max: float) -> tuple[QColor, QColor]:
    span = v_max - v_min
    t    = (value - v_min) / span if span > 0 else 0.0
    t    = max(0.0, min(1.0, t))
    hue  = int(120 * (1.0 - t))
    bg   = QColor.fromHsl(hue, 180, 80)
    fg   = QColor("#f0f0f0") if bg.lightness() < 128 else QColor("#111111")
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


# ── FuelMapTable ──────────────────────────────────────────────────────────────

class FuelMapTable(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._car_name: str = ""
        self._data: list[list[float]] = _build_default_table()
        self._ignore_change = False
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(8)

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        # car selector
        car_lbl = QLabel("Car:")
        car_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
        """)
        self._combo = QComboBox()
        self._combo.addItems(_car_names())
        self._combo.setStyleSheet(_combo_style(config.ACCENT_PURPLE))
        self._combo.currentTextChanged.connect(self._on_car_changed)

        # status label (shows save path / last saved)
        self._status_lbl = QLabel("")
        self._status_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 10px;
            padding: 0 6px;
        """)

        self._hover_lbl = QLabel("")
        self._hover_lbl.setStyleSheet(f"""
            color: {config.ACCENT};
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
            padding: 2px 8px;
            border: 1px solid {config.BORDER_COLOR};
            border-radius: 4px;
        """)
        self._hover_lbl.setFixedHeight(26)
        self._hover_lbl.setMinimumWidth(260)

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
        self._table = QTableWidget(len(LOAD_STEPS), len(RPM_STEPS))
        self._table.setHorizontalHeaderLabels([str(r) for r in RPM_STEPS])
        self._table.setVerticalHeaderLabels([f"{l}%" for l in LOAD_STEPS])

        hdr_style = f"""
            QHeaderView::section {{
                background-color: {config.SURFACE_RAISED};
                color: {config.TEXT_COLOR};
                font-family: {config.FONT_FAMILY};
                font-size: 11px;
                font-weight: bold;
                padding: 4px;
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
        self._table.verticalHeader().setFixedWidth(48)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {config.SURFACE_CARD};
                gridline-color: {config.BORDER_COLOR};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 2px;
                font-family: {config.FONT_FAMILY};
                font-size: 11px;
                font-weight: bold;
            }}
            QTableWidget::item:selected {{ border: 2px solid {config.ACCENT}; }}
        """)
        self._table.cellChanged.connect(self._on_cell_changed)
        self._table.cellEntered.connect(self._on_cell_hover)
        self._table.setMouseTracking(True)

        table_row = QHBoxLayout()
        table_row.setSpacing(4)
        table_row.addWidget(_RotatedLabel("Engine Load %  ↓", parent=self))
        table_row.addWidget(self._table)

        root.addLayout(toolbar)
        root.addLayout(axis_row)
        root.addLayout(table_row)

        # load the first car
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
            t   = i / (steps - 1)
            hue = int(120 * (1.0 - t))
            c   = QColor.fromHsl(hue, 180, 80)
            f   = QFrame()
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

    # ── data ──────────────────────────────────────────────────────────────────

    def _on_car_changed(self, car_name: str):
        self._car_name = car_name
        loaded = _load_csv(car_name)
        if loaded and len(loaded) == len(LOAD_STEPS) and all(
            len(row) == len(RPM_STEPS) for row in loaded
        ):
            self._data = loaded
        else:
            # first time: generate defaults and save immediately
            self._data = _build_default_table()
            _save_csv(car_name, self._data)

        self._populate(recolor=True)
        self._update_status()

    def _populate(self, recolor: bool = False):
        self._ignore_change = True
        if recolor:
            flat  = [v for row in self._data for v in row]
            v_min, v_max = min(flat), max(flat)

        font = QFont(config.FONT_FAMILY, 10)
        font.setBold(True)

        for r in range(len(LOAD_STEPS)):
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
                    bg, fg = _hsl_cell_color(val, v_min, v_max)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))

        self._ignore_change = False

    def _recolor_all(self):
        flat  = [v for row in self._data for v in row]
        v_min, v_max = min(flat), max(flat)
        for r in range(len(LOAD_STEPS)):
            for c in range(len(RPM_STEPS)):
                item = self._table.item(r, c)
                if item:
                    bg, fg = _hsl_cell_color(self._data[r][c], v_min, v_max)
                    item.setBackground(QBrush(bg))
                    item.setForeground(QBrush(fg))

    def _update_status(self):
        path = _csv_path(self._car_name)
        self._status_lbl.setText(f"→ {os.path.relpath(path)}")

    def _save(self):
        if not self._car_name:
            return
        _save_csv(self._car_name, self._data)
        self._status_lbl.setText(f"Saved  →  {os.path.relpath(_csv_path(self._car_name))}")

    def _reset(self):
        self._data = _build_default_table()
        self._populate(recolor=True)
        # auto-save after reset so the file reflects the reset state
        if self._car_name:
            _save_csv(self._car_name, self._data)
            self._update_status()

    # ── cell interaction ──────────────────────────────────────────────────────

    def _on_cell_changed(self, row: int, col: int):
        if self._ignore_change:
            return
        item = self._table.item(row, col)
        if item is None:
            return
        try:
            val = max(0.0, min(99.9, float(item.text().replace(",", "."))))
            self._data[row][col] = round(val, 1)
        except ValueError:
            self._ignore_change = True
            item.setText(f"{self._data[row][col]:.1f}")
            self._ignore_change = False
            return
        self._recolor_all()
        # auto-save on every edit
        if self._car_name:
            _save_csv(self._car_name, self._data)

    def _on_cell_hover(self, row: int, col: int):
        if 0 <= row < len(LOAD_STEPS) and 0 <= col < len(RPM_STEPS):
            self._hover_lbl.setText(
                f"RPM: {RPM_STEPS[col]}   "
                f"Load: {LOAD_STEPS[row]}%   "
                f"Pulse width: {self._data[row][col]:.1f} ms"
            )


# ── FuelMapsDock ──────────────────────────────────────────────────────────────

class FuelMapsDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("FUEL MAPS")
        panel.setStyleSheet(config.PANEL_STYLE)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.addWidget(FuelMapTable())

        root.addWidget(panel)
