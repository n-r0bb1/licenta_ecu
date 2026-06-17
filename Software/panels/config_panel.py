import sys, os, shutil
from datetime import datetime

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QPushButton, QFileDialog, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QBrush

from widgets import config

LOG_PATH = "data/logs/telemetry.csv"
MAX_LIVE  = 200   # max rows kept in the live table

COLUMNS = [
    ("Timestamp",    "timestamp"),
    ("Throttle %",   "throttle_pct"),
    ("Fuel %",       "fuel_pct"),
    ("Eng Temp °C",  "eng_temp"),
    ("Air Temp °C",  "air_temp"),
    ("Pressure bar", "pressure"),
]

_GOOD_BG = QColor("#0d2b14");  _GOOD_FG = QColor("#4ade80")
_MID_BG  = QColor("#2b2210");  _MID_FG  = QColor("#ffaa00")
_BAD_BG  = QColor("#2b0d10");  _BAD_FG  = QColor("#f87171")
_NULL_BG = QColor(config.SURFACE_CARD)
_NULL_FG = QColor(config.TEXT_MUTED)


def _row_colors(fuel_pct: float):
    if fuel_pct <= 33:
        return _GOOD_BG, _GOOD_FG
    elif fuel_pct <= 66:
        return _MID_BG, _MID_FG
    else:
        return _BAD_BG, _BAD_FG


def _btn_style(color: str) -> str:
    return f"""
        QPushButton {{
            background-color: transparent;
            color: {color};
            border: 1px solid {color};
            border-radius: 4px;
            font-family: {config.FONT_FAMILY};
            font-size: 11px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{ background-color: {config.SURFACE_RAISED}; }}
        QPushButton:pressed {{ background-color: {config.BACKGROUND_PRESSED}; }}
    """


def _table_style() -> str:
    return f"""
        QTableWidget {{
            background-color: {config.SURFACE_CARD};
            gridline-color: {config.BORDER_COLOR};
            color: {config.TEXT_COLOR};
            font-family: {config.FONT_FAMILY};
            font-size: 12px;
            border: 1px solid {config.BORDER_COLOR};
            border-radius: 4px;
        }}
        QTableWidget::item {{ padding: 4px 8px; }}
        QTableWidget::item:selected {{
            background-color: {config.SURFACE_RAISED};
            color: {config.TEXT_COLOR};
        }}
        QScrollBar:vertical {{
            background: {config.SURFACE_CARD};
            width: 6px; border-radius: 3px;
        }}
        QScrollBar::handle:vertical {{
            background: {config.BORDER_COLOR}; border-radius: 3px;
        }}
    """


def _header_style() -> str:
    return f"""
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
    """


class LogsDock(QWidget):
    def __init__(self, worker=None, parent=None):
        super().__init__(parent)
        self._worker     = worker
        self._live_rows  = 0
        self._setup_ui()
        if worker is not None:
            worker.packet_received.connect(self._on_packet)

        self._info_timer = QTimer(self)
        self._info_timer.setInterval(5000)
        self._info_timer.timeout.connect(self._refresh_log_info)
        self._info_timer.start()

    def _setup_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # ── Live feed ─────────────────────────────────────────────────────────
        live_group = QGroupBox("LIVE FEED")
        live_group.setStyleSheet(config.PANEL_STYLE)
        live_layout = QVBoxLayout(live_group)
        live_layout.setContentsMargins(12, 12, 12, 12)
        live_layout.setSpacing(8)

        # toolbar row
        live_toolbar = QHBoxLayout()

        for text, color in [("■ Efficient (≤33%)", "#4ade80"),
                             ("■ Moderate (34–66%)", "#ffaa00"),
                             ("■ Inefficient (>66%)", "#f87171")]:
            lbl = QLabel(text)
            lbl.setStyleSheet(
                f"color: {color}; font-size: 11px; font-family: {config.FONT_FAMILY};"
            )
            live_toolbar.addWidget(lbl)
            live_toolbar.addSpacing(10)

        live_toolbar.addStretch(1)

        btn_clear = QPushButton("Clear")
        btn_clear.setFixedHeight(28)
        btn_clear.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_clear.setStyleSheet(_btn_style(config.TEXT_MUTED))
        btn_clear.clicked.connect(self._clear_live)
        live_toolbar.addWidget(btn_clear)

        # live table
        self._live_table = QTableWidget(0, len(COLUMNS))
        self._live_table.setHorizontalHeaderLabels([c[0] for c in COLUMNS])
        self._live_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._live_table.horizontalHeader().setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        self._live_table.horizontalHeader().setStyleSheet(_header_style())
        self._live_table.setStyleSheet(_table_style())
        self._live_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._live_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._live_table.verticalHeader().setVisible(False)
        self._live_table.setVerticalScrollMode(QTableWidget.ScrollMode.ScrollPerPixel)

        live_layout.addLayout(live_toolbar)
        live_layout.addWidget(self._live_table)
        root.addWidget(live_group, stretch=3)

        # ── Log file actions ──────────────────────────────────────────────────
        file_group = QGroupBox("LOG FILE")
        file_group.setStyleSheet(config.PANEL_STYLE)
        file_layout = QVBoxLayout(file_group)
        file_layout.setContentsMargins(12, 12, 12, 12)
        file_layout.setSpacing(8)

        self._log_info = QLabel(self._log_summary())
        self._log_info.setStyleSheet(f"""
            color: {config.TEXT_MUTED};
            font-family: {config.FONT_FAMILY};
            font-size: 12px;
            padding: 4px 0;
        """)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(10)

        btn_save = QPushButton("Save snapshot")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.setStyleSheet(_btn_style(config.ACCENT))
        btn_save.clicked.connect(self._save_snapshot)

        btn_download = QPushButton("Download CSV")
        btn_download.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_download.setStyleSheet(_btn_style(config.ACCENT_GREEN))
        btn_download.clicked.connect(self._download_csv)

        btn_row.addWidget(btn_save)
        btn_row.addWidget(btn_download)
        btn_row.addStretch()

        file_layout.addWidget(self._log_info)
        file_layout.addLayout(btn_row)
        root.addWidget(file_group, stretch=1)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _log_summary(self) -> str:
        if not os.path.exists(LOG_PATH):
            return "No log file found."
        size_kb = os.path.getsize(LOG_PATH) / 1024
        try:
            with open(LOG_PATH, newline="") as f:
                rows = sum(1 for _ in f) - 1
        except OSError:
            rows = 0
        return f"Path: {LOG_PATH}   |   Rows: {max(rows, 0)}   |   Size: {size_kb:.1f} KB"

    def _refresh_log_info(self):
        self._log_info.setText(self._log_summary())

    def _clear_live(self):
        self._live_table.setRowCount(0)
        self._live_rows = 0

    def _append_row(self, ts: str, thr: float, fuel: float,
                    eng: float, air: float, pres: float):
        # drop oldest row if at capacity
        if self._live_rows >= MAX_LIVE:
            self._live_table.removeRow(0)
            self._live_rows -= 1

        row = self._live_table.rowCount()
        self._live_table.insertRow(row)

        try:
            bg, fg = _row_colors(fuel)
        except Exception:
            bg, fg = _NULL_BG, _NULL_FG

        values = [ts, f"{thr:.1f}", f"{fuel:.1f}",
                  f"{eng:.1f}", f"{air:.1f}", f"{pres:.2f}"]

        for c, text in enumerate(values):
            item = QTableWidgetItem(text)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setBackground(QBrush(bg))
            item.setForeground(QBrush(fg))
            self._live_table.setItem(row, c, item)

        self._live_table.scrollToBottom()
        self._live_rows += 1

    # ── slots ─────────────────────────────────────────────────────────────────

    def _on_packet(self, pkt):
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._append_row(ts, pkt.throttle_pct, pkt.fuel_pct,
                         pkt.eng_temp, pkt.air_temp, pkt.pressure)

    def _save_snapshot(self):
        if not os.path.exists(LOG_PATH):
            self._log_info.setText("No log file to snapshot.")
            return
        os.makedirs("data/logs", exist_ok=True)
        ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join("data/logs", f"snapshot_{ts}.csv")
        shutil.copy2(LOG_PATH, dest)
        self._log_info.setText(f"Snapshot saved: {dest}")

    def _download_csv(self):
        if not os.path.exists(LOG_PATH):
            self._log_info.setText("No log file to download.")
            return
        ts           = datetime.now().strftime("%Y%m%d_%H%M%S")
        default_name = os.path.expanduser(f"~/telemetry_{ts}.csv")
        path, _      = QFileDialog.getSaveFileName(
            self, "Save telemetry log", default_name, "CSV files (*.csv)"
        )
        if path:
            shutil.copy2(LOG_PATH, path)
            self._log_info.setText(f"Saved to: {path}")
