# main.py
import sys, os
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from widgets.button import NavButton

from panels.home_panel import HomeDock
from panels.config_panel import ConfigDock
from panels.telemetry_panel import TelemDock
from panels.fuelmaps_panel import FuelMapsDock

from protocol.protocol import SerialReader

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from widgets import config 

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        #self.setWindowTitle("PegaECUs")
        self.resize(1920, 1080)
        self.setMinimumSize(1920, 1080)
        self.setMaximumSize(1920, 1080)
        self.setup_ui()
        self.setStyleSheet(f"""
        QMainWindow {{
        background-color:{config.WINDOW_BACKGROUND_COLOR}
        }}
                           """)


    def setup_ui(self):
        # --- Central area: stacked panels (right side) ---
        self.stack = QStackedWidget()
        self.stack.addWidget(HomeDock())       # index 0
        self.stack.addWidget(ConfigDock())     # index 1
        self.stack.addWidget(TelemDock())      # index 2
        self.stack.addWidget(FuelMapsDock())   # index 3
        self.setCentralWidget(self.stack)

        # --- Left dock: navigation buttons ---
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(10)

        title = QLabel("PegaECU's")
        title.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        title.setStyleSheet(f"""
            font-size: 32px;
            color: {config.TEXT_COLOR};
            font-family: {config.FONT_FAMILY};
            padding-left: 4px;
        """)

        ICONS = os.path.join(os.path.dirname(__file__), "widgets", "icons")
        btn_home = NavButton("Home", icon=os.path.join(ICONS, "home.png"))
        btn_settings = NavButton("Settings")
        btn_telemetry = NavButton("Telemetry")
        btn_fuelmaps = NavButton("Fuel Maps")

        btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))
        btn_telemetry.clicked.connect(lambda: self.stack.setCurrentIndex(2))
        btn_fuelmaps.clicked.connect(lambda: self.stack.setCurrentIndex(3))

        nav_layout.addWidget(title)
        nav_layout.addWidget(btn_home)
        nav_layout.addWidget(btn_settings)
        nav_layout.addWidget(btn_telemetry)
        nav_layout.addWidget(btn_fuelmaps)
        nav_layout.addStretch(1)

        nav_widget.setFixedWidth(config.BUTTON_WIDTH + 16)

        nav_dock = QDockWidget()
        nav_dock.setTitleBarWidget(QWidget())
        nav_dock.setWidget(nav_widget)
        nav_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        nav_dock.setFixedWidth(config.BUTTON_WIDTH + 16)
        self.addDockWidget(Qt.LeftDockWidgetArea, nav_dock)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())