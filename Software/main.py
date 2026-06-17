# main.py
import sys, os
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QStackedWidget,
    QVBoxLayout, QHBoxLayout, QLabel, QDockWidget, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from widgets.button import NavButton

from panels.home_panel import HomeDock
from panels.config_panel import LogsDock
from panels.telemetry_panel import TelemDock
from panels.fuelmaps_panel import FuelMapsDock
from protocol.worker import SerialWorker

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from widgets import config

ICONS    = os.path.join(os.path.dirname(__file__), "widgets", "icons")
PORT     = "/dev/ttyUSB0"
BAUDRATE = 9600


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.resize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMinimumSize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setMaximumSize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {config.WINDOW_BACKGROUND_COLOR};
            }}
            QDockWidget {{
                background-color: {config.SURFACE_NAV};
            }}
            QLabel {{
                color: {config.TEXT_COLOR};
                font-family: {config.FONT_FAMILY};
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
        self._setup_ui()

    def _setup_ui(self):
        # one shared serial worker for all panels
        self._worker = SerialWorker(PORT, BAUDRATE)

        self.stack = QStackedWidget()
        self.stack.addWidget(HomeDock(worker=self._worker))   # 0
        self.stack.addWidget(LogsDock(worker=self._worker))   # 1
        self.stack.addWidget(TelemDock(worker=self._worker))  # 2
        self.stack.addWidget(FuelMapsDock())                  # 3
        self.setCentralWidget(self.stack)

        self._worker.start()

        # ── Sidebar ───────────────────────────────────────────────────────────
        nav_widget = QWidget()
        nav_widget.setStyleSheet(f"""
            QWidget {{
                background-color: {config.SURFACE_NAV};
                border-right: 1px solid {config.BORDER_COLOR};
            }}
        """)
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setSpacing(0)

        # brand title
        title = QWidget()
        title.setFixedHeight(90)
        title.setStyleSheet(f"""
            QWidget {{
                border-bottom: 1px solid {config.BORDER_COLOR};
                background-color: {config.SURFACE_NAV};
            }}
        """)
        title_layout = QHBoxLayout(title)
        title_layout.setContentsMargins(40, 16, 20, 16)
        title_layout.setSpacing(12)

        logo_lbl = QLabel()
        logo_lbl.setStyleSheet("background: transparent; border: none;")
        pixmap = QPixmap(os.path.join(ICONS, "pegasus.png")).scaled(
            48, 48, Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        logo_lbl.setPixmap(pixmap)
        logo_lbl.setFixedSize(48, 48)

        text_lbl = QLabel("PegaECUs")
        text_lbl.setStyleSheet(f"""
            font-size: 25px;
            font-weight: bold;
            color: {config.TEXT_COLOR};
            font-family: {config.FONT_FAMILY};
            border: none;
            background: transparent;
        """)

        title_layout.addWidget(logo_lbl)
        title_layout.addWidget(text_lbl)
        title_layout.addStretch(1)

        # divider under title
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"background-color: {config.BORDER_COLOR};")
        sep.setFixedHeight(3)

        self._btns = []
        btn_home      = NavButton("Home",icon=os.path.join(ICONS, "home.png"))
        btn_settings  = NavButton("Logs",icon=os.path.join(ICONS, "setting.png"))
        btn_telemetry = NavButton("Telemetry",icon=os.path.join(ICONS, "line-chart.png"))
        btn_fuelmaps  = NavButton("Fuel Maps",icon=os.path.join(ICONS, "setting.png"))
        self._btns = [btn_home, btn_settings, btn_telemetry, btn_fuelmaps]

        def switch(index):
            self.stack.setCurrentIndex(index)
            for i, b in enumerate(self._btns):
                b.setChecked(i == index)

        btn_home.clicked.connect(lambda: switch(0))
        btn_settings.clicked.connect(lambda: switch(1))
        btn_telemetry.clicked.connect(lambda: switch(2))
        btn_fuelmaps.clicked.connect(lambda: switch(3))

        nav_layout.addWidget(title)
        nav_layout.addWidget(sep)
        nav_layout.addSpacing(10)
        for btn in self._btns:
            nav_layout.addWidget(btn)
        nav_layout.addStretch(1)

        nav_widget.setFixedWidth(config.BUTTON_WIDTH + 4)

        nav_dock = QDockWidget()
        nav_dock.setTitleBarWidget(QWidget())
        nav_dock.setWidget(nav_widget)
        nav_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        nav_dock.setFixedWidth(config.BUTTON_WIDTH + 4)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, nav_dock)

        # start on Home, checked
        switch(0)

    def closeEvent(self, event):
        self._worker.stop()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
