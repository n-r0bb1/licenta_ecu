# test_button.py
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtCore import Qt
from widgets.button import NavButton

if __name__ == "__main__":
    app = QApplication(sys.argv)

    window = QWidget()
    window.setWindowTitle("Button Test")
    window.setStyleSheet("background-color: #1a1a1a;")  # dark bg to see the button clearly

    layout = QVBoxLayout(window)
    layout.setAlignment(Qt.AlignCenter)

    btn = NavButton("Home")
    btn2 = NavButton("Settings")

    layout.addWidget(btn)
    layout.addWidget(btn2)

    window.resize(300, 200)
    window.show()

    sys.exit(app.exec())