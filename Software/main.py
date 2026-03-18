# main.py
import sys
from PySide6.QtWidgets import *
from PySide6.QtCore import Qt
from panels.home import HomeDock
# from panels.home import SettingsDock  # add more as needed

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PegaECUs")
        self.resize(1920, 1080)
        self.setMinimumSize(1920, 1080)
        self.setMaximumSize(1920, 1080)
        self.setup_ui()


    def setup_ui(self):
        # --- Central area: stacked panels (right side) ---
        self.stack = QStackedWidget()
        self.stack.addWidget(HomeDock())       # index 0
        #self.stack.addWidget(SettingsDock())   # index 1
        self.setCentralWidget(self.stack)

        # --- Left dock: navigation buttons ---
        nav_widget = QWidget()
        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setAlignment(Qt.AlignTop)

        btn_home = QPushButton("Home")
        btn_settings = QPushButton("Settings")

        btn_home.clicked.connect(lambda: self.stack.setCurrentIndex(0))
        btn_settings.clicked.connect(lambda: self.stack.setCurrentIndex(1))

        nav_layout.addWidget(btn_home)
        nav_layout.addWidget(btn_settings)

        nav_dock = QDockWidget("Menu")
        nav_dock.setWidget(nav_widget)
        nav_dock.setFeatures(QDockWidget.NoDockWidgetFeatures)  # lock it in place
        self.addDockWidget(Qt.LeftDockWidgetArea, nav_dock)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())