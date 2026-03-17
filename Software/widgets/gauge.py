import sys
import math
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QSlider, QLabel
)
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QBrush


class AnalogGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._value = 0
        self.min_value = 0
        self.max_value = 8000
        self.label = "RPM"
        self.unit = ""

        # color zones: list of (start, end, color) as % of range
        self.zones = [
            (0.0,  0.6,  "#00aaff"),
            (0.6,  0.8,  "#ffaa00"),
            (0.8,  1.0,  "#ff3333"),
        ]

        self.setMinimumSize(220, 220)

    def set_value(self, value):
        self._value = max(self.min_value, min(self.max_value, value))
        self.update()

    def get_value(self):
        return self._value

    # ── helpers ──────────────────────────────────────────────────────────────

    def _ratio(self):
        span = self.max_value - self.min_value
        if span == 0:
            return 0.0
        return (self._value - self.min_value) / span

    def _angle_for_ratio(self, ratio):
        """Returns angle in degrees; 0° = 3 o'clock, grows clockwise."""
        return -135 + ratio * 270

    # ── paint ─────────────────────────────────────────────────────────────────

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        side = min(self.width(), self.height())
        painter.setViewport(
            (self.width() - side) // 2,
            (self.height() - side) // 2,
            side, side,
        )
        # logical coords: -100..+100 with (0,0) at centre
        painter.setWindow(-100, -100, 200, 200)

        self._draw_background(painter)
        self._draw_track(painter)
        self._draw_value_arc(painter)
        self._draw_ticks(painter)
        self._draw_needle(painter)
        self._draw_center_text(painter)

    def _draw_background(self, painter):
        # outer ring
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#16213e"))
        painter.drawEllipse(-98, -98, 196, 196)

        # inner face
        painter.setBrush(QColor("#0f0f1a"))
        painter.drawEllipse(-88, -88, 176, 176)

    def _draw_track(self, painter):
        pen = QPen(QColor("#2a2a3e"))
        pen.setWidth(10)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        rect = QRectF(-75, -75, 150, 150)
        painter.drawArc(rect, int(225 * 16), int(-270 * 16))

    def _draw_value_arc(self, painter):
        ratio = self._ratio()
        rect = QRectF(-75, -75, 150, 150)

        # find which zone we are in and draw segments up to value
        for zone_start, zone_end, color in self.zones:
            if zone_start >= ratio:
                break
            seg_end = min(zone_end, ratio)

            pen = QPen(QColor(color))
            pen.setWidth(10)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)

            arc_start = 225 - zone_start * 270        # in degrees
            arc_span  = -(seg_end - zone_start) * 270

            painter.drawArc(rect, int(arc_start * 16), int(arc_span * 16))

    def _draw_ticks(self, painter):
        num_major = 10
        num_minor = 5   # minor ticks between each major pair

        total_ticks = num_major * num_minor + num_major

        for i in range(total_ticks + 1):
            ratio = i / total_ticks
            angle_deg = self._angle_for_ratio(ratio) - 90   # -90 to start at top
            angle_rad = math.radians(angle_deg)

            is_major = (i % num_minor == 0)

            if is_major:
                r_inner, r_outer = 68, 80
                pen = QPen(QColor("#aaaacc"))
                pen.setWidth(2)
            else:
                r_inner, r_outer = 73, 80
                pen = QPen(QColor("#555566"))
                pen.setWidth(1)

            painter.setPen(pen)
            x1 = r_inner * math.cos(angle_rad)
            y1 = r_inner * math.sin(angle_rad)
            x2 = r_outer * math.cos(angle_rad)
            y2 = r_outer * math.sin(angle_rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            # label on major ticks
            if is_major:
                lx = 58 * math.cos(angle_rad)
                ly = 58 * math.sin(angle_rad)
                label_val = int(self.min_value + ratio * (self.max_value - self.min_value))

                font = QFont()
                font.setPointSize(6)
                painter.setFont(font)
                painter.setPen(QColor("#8888aa"))
                painter.drawText(
                    QRectF(lx - 14, ly - 7, 28, 14),
                    Qt.AlignmentFlag.AlignCenter,
                    str(label_val),
                )

    def _draw_needle(self, painter):
        ratio = self._ratio()
        angle_deg = self._angle_for_ratio(ratio) - 90
        angle_rad = math.radians(angle_deg)

        nx = 65 * math.cos(angle_rad)
        ny = 65 * math.sin(angle_rad)

        # needle shadow
        pen = QPen(QColor(0, 0, 0, 80))
        pen.setWidth(5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(2, 2, int(nx) + 2, int(ny) + 2)

        # needle body
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(0, 0, int(nx), int(ny))

        # needle tip accent (colored by zone)
        tip_color = "#00aaff"
        for zone_start, zone_end, color in self.zones:
            if zone_start <= ratio <= zone_end:
                tip_color = color
                break
        pen = QPen(QColor(tip_color))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        tx = 65 * math.cos(angle_rad)
        ty = 65 * math.sin(angle_rad)
        mx = 40 * math.cos(angle_rad)
        my = 40 * math.sin(angle_rad)
        painter.drawLine(int(mx), int(my), int(tx), int(ty))

        # center cap
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(-7, -7, 14, 14)
        painter.setBrush(QColor("#0f0f1a"))
        painter.drawEllipse(-4, -4, 8, 8)

    def _draw_center_text(self, painter):
        # value
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(
            QRectF(-45, 15, 90, 28),
            Qt.AlignmentFlag.AlignCenter,
            str(int(self._value)),
        )

        # label below value
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#6666aa"))
        painter.drawText(
            QRectF(-40, 44, 80, 16),
            Qt.AlignmentFlag.AlignCenter,
            self.label,
        )


# ── Test window ───────────────────────────────────────────────────────────────

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Analog Gauge Test")
        self.setStyleSheet("background-color: #0a0a14; color: white;")
        self.resize(700, 400)

        # --- three gauges ---
        rpm_gauge = AnalogGauge()
        rpm_gauge.min_value = 0
        rpm_gauge.max_value = 8000
        rpm_gauge.label = "RPM"
        rpm_gauge.zones = [
            (0.0, 0.6, "#00aaff"),
            (0.6, 0.8, "#ffaa00"),
            (0.8, 1.0, "#ff3333"),
        ]

        temp_gauge = AnalogGauge()
        temp_gauge.min_value = 0
        temp_gauge.max_value = 120
        temp_gauge.label = "°C  COOLANT"
        temp_gauge.zones = [
            (0.0, 0.5, "#00aaff"),
            (0.5, 0.75, "#00cc88"),
            (0.75, 1.0, "#ff3333"),
        ]

        boost_gauge = AnalogGauge()
        boost_gauge.min_value = -1
        boost_gauge.max_value = 3
        boost_gauge.label = "BAR  BOOST"
        boost_gauge.zones = [
            (0.0,  0.25, "#555577"),
            (0.25, 0.75, "#00aaff"),
            (0.75, 1.0,  "#ff3333"),
        ]

        # --- sliders ---
        def make_slider(gauge, min_val, max_val):
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_val, max_val)
            slider.setValue(min_val)
            slider.valueChanged.connect(gauge.set_value)
            slider.setStyleSheet("""
                QSlider::groove:horizontal {
                    height: 4px; background: #2a2a3e; border-radius: 2px;
                }
                QSlider::handle:horizontal {
                    width: 14px; height: 14px; margin: -5px 0;
                    background: #00aaff; border-radius: 7px;
                }
                QSlider::sub-page:horizontal {
                    background: #00aaff; border-radius: 2px;
                }
            """)
            return slider

        rpm_slider   = make_slider(rpm_gauge,   0, 8000)
        temp_slider  = make_slider(temp_gauge,  0, 120)
        boost_slider = make_slider(boost_gauge, -1, 3)

        def make_col(gauge, slider, title):
            lbl = QLabel(title)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setStyleSheet("color: #6666aa; font-size: 11px; margin-bottom: 4px;")
            col = QVBoxLayout()
            col.addWidget(gauge)
            col.addWidget(lbl)
            col.addWidget(slider)
            w = QWidget()
            w.setLayout(col)
            return w

        row = QHBoxLayout()
        row.setSpacing(20)
        row.addWidget(make_col(rpm_gauge,   rpm_slider,   "drag to set RPM"))
        row.addWidget(make_col(temp_gauge,  temp_slider,  "drag to set temp"))
        row.addWidget(make_col(boost_gauge, boost_slider, "drag to set boost"))

        container = QWidget()
        container.setLayout(row)
        self.setCentralWidget(container)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())