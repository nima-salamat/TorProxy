from PySide6.QtWidgets import (
    QPushButton,

)

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Property
from PySide6.QtGui import QPainter, QColor, QBrush

import logging

logger = logging.getLogger(__name__)


class PulseButton(QPushButton):
    def __init__(self, text):
        super().__init__(text)
        self.setFixedSize(250, 250)
        self.connected = False
        self._pulse_radius = 0
        self._pulse_color = "#2ecc71"  

        self.anim = QPropertyAnimation(self, b"pulseRadius")
        self.anim.setStartValue(0)
        self.anim.setEndValue(100)
        self.anim.setDuration(1000)
        self.anim.setLoopCount(-1)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)

        self.updateStyle()
        self.clicked.connect(self.toggle_state)

    def updateStyle(self):
        if self.connected:
            self.setText("DISCONNECT")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #e74c3c;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 125px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #c0392b;
                }}
            """)
            self._pulse_color = "#e74c3c"
            self.anim.start()
        else:
            self.setText("CONNECT")
            self.setStyleSheet(f"""
                QPushButton {{
                    background-color: #2ecc71;
                    color: white;
                    font-size: 20px;
                    font-weight: bold;
                    border-radius: 125px;
                    border: none;
                }}
                QPushButton:hover {{
                    background-color: #27ae60;
                }}
            """)
            self._pulse_color = "#540809"
            self.anim.stop()
            self._pulse_radius = 0
            self.update()

    def toggle_state(self):
        self.connected = not self.connected
        self.updateStyle()

    def paintEvent(self, event):
        super().paintEvent(event)

        if self.connected:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            center = self.rect().center()

            opacity = max(0.0, 1.0 - self._pulse_radius / 100)
            color = QColor(self._pulse_color)
            color.setAlphaF(opacity * 0.7)

            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, self._pulse_radius, self._pulse_radius)

    def getPulseRadius(self):
        return self._pulse_radius

    def setPulseRadius(self, value):
        self._pulse_radius = value
        self.update()

    pulseRadius = Property(int, getPulseRadius, setPulseRadius)  
