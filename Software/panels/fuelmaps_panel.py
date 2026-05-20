import sys, os, csv, math
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from widgets import config

LOG_PATH = "logs/telemetry.csv"
MAX_ROWS = 2000

COLUMNS = [
    ("Timestamp",    "timestamp"),
    ("Throttle %",   "throttle_pct"),
    ("Fuel %",       "fuel_pct"),
    ("Eng Temp °C",  "eng_temp"),
    ("Air Temp °C",  "air_temp"),
    ("Pressure bar", "pressure"),
]

# ── color thresholds (based on fuel_pct) ─────────────────────────────────────
# low consumption = efficient = green; high = red
_GOOD_BG  = QColor("#0d2b14")
_GOOD_FG  = QColor("#4ade80")
_MID_BG   = QColor("#2b2210")
_MID_FG   = QColor("#ffaa00")
_BAD_BG   = QColor("#2b0d10")
_BAD_FG   = QColor("#f87171")
_NULL_BG  = QColor(config.SURFACE_CARD)
_NULL_FG  = QColor(config.TEXT_MUTED)


def _row_colors(fuel_pct: float):
    if fuel_pct <= 33:
        return _GOOD_BG, _GOOD_FG
    elif fuel_pct <= 66:
        return _MID_BG, _MID_FG
    else:
        return _BAD_BG, _BAD_FG


class FuelMapsDock(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)

        panel = QGroupBox("FUEL MAPS")
        panel.setStyleSheet(config.PANEL_STYLE)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 16, 16, 16)
        panel_layout.setSpacing(10)

        # ── toolbar ───────────────────────────────────────────────────────────
        toolbar = QHBoxLayout()

        self._status_lbl = QLabel(LOG_PATH)
        self._status_lbl.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-size: 11px;
            font-family: {config.FONT_FAMILY};
        """)

        legend_green = QLabel("■ Efficient (≤33%)")
        legend_amber = QLabel("■ Moderate (34–66%)")
        legend_red   = QLabel("■ Inefficient (>66%)")
        legend_green.setStyleSheet(f"color: #4ade80; font-size: 11px; font-family: {config.FONT_FAMILY};")
        legend_amber.setStyleSheet(f"color: #ffaa00; font-size: 11px; font-family: {config.FONT_FAMILY};")
        legend_red.setStyleSheet(f"color: #f87171;  font-size: 11px; font-family: {config.FONT_FAMILY};")

        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setFixedHeight(30)
        refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {config.SURFACE_RAISED};
                color: {config.ACCENT};
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 4px;
                padding: 0 16px;
                font-family: {config.FONT_FAMILY};
                font-size: 12px;
            }}
            QPushButton:hover {{ background-color: {config.BORDER_COLOR}; }}
            QPushButton:pressed {{ background-color: {config.SURFACE_RAISED}; }}
        """)
        refresh_btn.clicked.connect(self._load)

        toolbar.addWidget(self._status_lbl)
        toolbar.addSpacing(20)
        toolbar.addWidget(legend_green)
        toolbar.addSpacing(12)
        toolbar.addWidget(legend_amber)
        toolbar.addSpacing(12)
        toolbar.addWidget(legend_red)
        toolbar.addStretch(1)
        toolbar.addWidget(refresh_btn)

        # ── table ─────────────────────────────────────────────────────────────
        self._table = QTableWidget()
        self._table.setColumnCount(len(COLUMNS))
        self._table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.horizontalHeader().setStyleSheet(f"""
            QHeaderView::section {{
                background-color: {config.SURFACE_RAISED};
                color: {config.TEXT_COLOR};
                font-family: {config.FONT_FAMILY};
                font-size: 11px;
                font-weight: bold;
                padding: 6px;
                border: none;
                border-right: 1px solid {config.BORDER_COLOR};
                border-bottom: 2px solid {config.ACCENT};
            }}
        """)
        self._table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {config.SURFACE_CARD};
                gridline-color: {config.BORDER_COLOR};
                color: {config.TEXT_COLOR};
                font-family: {config.FONT_FAMILY};
                font-size: 12px;
                border: 1px solid {config.BORDER_COLOR};
                border-radius: 4px;
            }}
            QTableWidget::item {{
                padding: 4px 8px;
            }}
            QTableWidget::item:selected {{
                background-color: {config.SURFACE_RAISED};
                color: {config.TEXT_COLOR};
            }}
            QScrollBar:vertical {{
                background: {config.SURFACE_CARD};
                width: 6px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical {{
                background: {config.BORDER_COLOR};
                border-radius: 3px;
            }}
        """)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)
        self._table.setSortingEnabled(True)

        panel_layout.addLayout(toolbar)
        panel_layout.addWidget(self._table)
        layout.addWidget(panel)

    def _load(self):
        self._table.setSortingEnabled(False)
        self._table.setRowCount(0)

        if not os.path.exists(LOG_PATH):
            self._status_lbl.setText(f"{LOG_PATH}  —  not found")
            return

        with open(LOG_PATH, newline="") as f:
            rows = list(csv.DictReader(f))

        rows = rows[-MAX_ROWS:]
        self._table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            try:
                fuel = float(row.get("fuel_pct", "nan"))
            except ValueError:
                fuel = float("nan")

            if math.isnan(fuel):
                bg, fg = _NULL_BG, _NULL_FG
            else:
                bg, fg = _row_colors(fuel)

            for c, (_, field) in enumerate(COLUMNS):
                raw = row.get(field, "")

                if field == "timestamp":
                    try:
                        display = datetime.fromtimestamp(float(raw)).strftime("%H:%M:%S.%f")[:-3]
                    except (ValueError, OSError):
                        display = raw
                else:
                    try:
                        display = f"{float(raw):.2f}"
                    except ValueError:
                        display = raw

                item = QTableWidgetItem(display)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                item.setBackground(bg)
                item.setForeground(fg)
                self._table.setItem(r, c, item)

        self._table.setSortingEnabled(True)
        self._table.scrollToBottom()
        self._status_lbl.setText(f"{LOG_PATH}  —  {len(rows)} rows")
