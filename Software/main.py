import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QDockWidget
from widgets.gauge import AnalogGauge

class MainWindow(QMainWindow):
    def __init__(self):
        self.setWindowTitle("PegaECUs")
        self.setup_ui()

    def setup_ui(self):
        sidemenu = QDockWdget("SideMenu")
        self.addDockWidget(sidemenu)

        