import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QFont, QFontMetricsF


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

        # tick_step: value interval between major ticks (None = auto 10 majors)
        # minor_ticks: how many minor divisions between each major pair
        # label_step: only label major ticks whose value is a multiple of this
        #             (None = label every major tick)
        # red_ticks: set/list of values whose tick line is drawn red
        # red_above: if set, all ticks at or above this value are drawn red
        self.tick_step   = None
        self.minor_ticks = 5
        self.label_step  = None
        self.red_ticks   = set()
        self.red_above   = None

        self.setMinimumSize(160, 160)

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
        span = self.max_value - self.min_value
        if span <= 0:
            return

        if self.tick_step is not None:
            step      = self.tick_step
            num_major = round(span / step)
        else:
            num_major = 10
            step      = span / num_major

        n_minor   = max(1, self.minor_ticks)
        total_sub = num_major * n_minor

        for i in range(total_sub + 1):
            ratio    = i / total_sub
            val      = self.min_value + ratio * span
            val_r    = int(round(val))
            is_major = (i % n_minor == 0)

            # determine tick colour
            is_red = (
                val_r in self.red_ticks
                or (self.red_above is not None and val >= self.red_above)
            )

            angle_deg = self._angle_for_ratio(ratio) - 90
            angle_rad = math.radians(angle_deg)

            if is_major:
                r_inner, r_outer = 68, 80
                tick_color = "#ff3355" if is_red else "#aaaacc"
                pen = QPen(QColor(tick_color))
                pen.setWidth(2)
            else:
                r_inner, r_outer = 73, 80
                tick_color = "#ff3355" if is_red else "#555566"
                pen = QPen(QColor(tick_color))
                pen.setWidth(1)

            painter.setPen(pen)
            x1 = r_inner * math.cos(angle_rad)
            y1 = r_inner * math.sin(angle_rad)
            x2 = r_outer * math.cos(angle_rad)
            y2 = r_outer * math.sin(angle_rad)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            if is_major:
                # show label only when label_step is None, or val is a multiple of it
                show_label = (
                    self.label_step is None
                    or val_r % self.label_step == 0
                )
                if show_label:
                    lx = 58 * math.cos(angle_rad)
                    ly = 58 * math.sin(angle_rad)
                    font = QFont()
                    font.setPointSize(6)
                    painter.setFont(font)
                    label_color = "#ff3355" if is_red else "#8888aa"
                    painter.setPen(QColor(label_color))
                    painter.drawText(
                        QRectF(lx - 14, ly - 7, 28, 14),
                        Qt.AlignmentFlag.AlignCenter,
                        str(val_r),
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


class FuelGauge(AnalogGauge):
    """
    Half-circle fuel gauge.
    Arc runs 180° from left (E) to right (F), opening downward.
    4 quarter divisions with labels: E  1/4  1/2  3/4  F
    """

    # Arc geometry constants (degrees, Qt convention: 0=3-o'clock, CCW positive)
    _START_DEG = 180   # left  = "E"
    _SPAN_DEG  = -180  # sweep CW to right = "F"  (negative = clockwise)
    _ARC_RECT  = QRectF(-75, -55, 150, 150)   # shifted up so arc is in upper half

    def _ratio_to_angle_rad(self, ratio: float) -> float:
        """Convert 0..1 ratio to angle in radians for trig (0=right, CCW positive)."""
        deg = self._START_DEG + ratio * abs(self._SPAN_DEG) * (-1 if self._SPAN_DEG < 0 else 1)
        # Qt angles: _START_DEG=180 means left; we go CW so subtract ratio*180
        deg = 180 - ratio * 180
        return math.radians(deg)

    def _draw_track(self, painter):
        pen = QPen(QColor("#2a2a3e"))
        pen.setWidth(10)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        painter.drawArc(self._ARC_RECT, self._START_DEG * 16, self._SPAN_DEG * 16)

    def _draw_value_arc(self, painter):
        ratio = self._ratio()
        for zone_start, zone_end, color in self.zones:
            if zone_start >= ratio:
                break
            seg_end = min(zone_end, ratio)
            pen = QPen(QColor(color))
            pen.setWidth(10)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            painter.setPen(pen)
            arc_start = self._START_DEG + zone_start * self._SPAN_DEG
            arc_span  = (seg_end - zone_start) * self._SPAN_DEG
            painter.drawArc(self._ARC_RECT, int(arc_start * 16), int(arc_span * 16))

    def _draw_ticks(self, painter):
        labels = ["E", "1/4", "1/2", "3/4", "F"]
        for i, lbl in enumerate(labels):
            ratio = i / (len(labels) - 1)
            angle_rad = self._ratio_to_angle_rad(ratio)
            cx = self._ARC_RECT.center().x()
            cy = self._ARC_RECT.center().y()
            r_arc = self._ARC_RECT.width() / 2

            # tick endpoints (pointing inward from arc)
            x_out = cx + r_arc * math.cos(angle_rad)
            y_out = cy - r_arc * math.sin(angle_rad)
            x_in  = cx + (r_arc - 12) * math.cos(angle_rad)
            y_in  = cy - (r_arc - 12) * math.sin(angle_rad)

            pen = QPen(QColor("#aaaacc"))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawLine(int(x_in), int(y_in), int(x_out), int(y_out))

            # label
            lx = cx + (r_arc - 26) * math.cos(angle_rad)
            ly = cy - (r_arc - 26) * math.sin(angle_rad)
            font = QFont()
            font.setPointSize(7)
            font.setBold(lbl in ("E", "F"))
            painter.setFont(font)
            color = "#ff3355" if lbl == "E" else "#00e5a0" if lbl == "F" else "#8888aa"
            painter.setPen(QColor(color))
            painter.drawText(QRectF(lx - 16, ly - 8, 32, 16),
                             Qt.AlignmentFlag.AlignCenter, lbl)

    def _draw_needle(self, painter):
        ratio = self._ratio()
        angle_rad = self._ratio_to_angle_rad(ratio)
        cx = self._ARC_RECT.center().x()
        cy = self._ARC_RECT.center().y()
        r_needle = self._ARC_RECT.width() / 2 - 8

        nx = cx + r_needle * math.cos(angle_rad)
        ny = cy - r_needle * math.sin(angle_rad)

        # shadow
        pen = QPen(QColor(0, 0, 0, 80))
        pen.setWidth(5)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(cx) + 2, int(cy) + 2, int(nx) + 2, int(ny) + 2)

        # body
        pen = QPen(QColor("#ffffff"))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(int(cx), int(cy), int(nx), int(ny))

        # colored tip
        tip_color = self.zones[0][2] if self.zones else "#00aaff"
        for zs, ze, zc in self.zones:
            if zs <= ratio <= ze:
                tip_color = zc
                break
        pen = QPen(QColor(tip_color))
        pen.setWidth(3)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        mx = cx + (r_needle * 0.55) * math.cos(angle_rad)
        my = cy - (r_needle * 0.55) * math.sin(angle_rad)
        painter.drawLine(int(mx), int(my), int(nx), int(ny))

        # center cap
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawEllipse(int(cx) - 7, int(cy) - 7, 14, 14)
        painter.setBrush(QColor("#0f0f1a"))
        painter.drawEllipse(int(cx) - 4, int(cy) - 4, 8, 8)

    def _draw_center_text(self, painter):
        font = QFont()
        font.setPointSize(18)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#ffffff"))
        painter.drawText(QRectF(-45, 20, 90, 28),
                         Qt.AlignmentFlag.AlignCenter,
                         f"{int(self._value)}%")
        font.setPointSize(8)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#6666aa"))
        painter.drawText(QRectF(-40, 48, 80, 16),
                         Qt.AlignmentFlag.AlignCenter,
                         self.label)
