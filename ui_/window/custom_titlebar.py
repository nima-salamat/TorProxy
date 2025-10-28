from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QHBoxLayout,
    QPushButton,
)
from PySide6.QtCore import Qt

class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.parent_ = parent
        self.title = QLabel("T⭕®️🌐🅿️®️⭕❌Y")
        self.title.setStyleSheet("margin-left: 10px;")
        
        self.btn_min = QPushButton("➖")
        self.btn_close = QPushButton("✖️")

        for btn in (self.btn_min, self.btn_close):
            btn.setFixedSize(30, 30)

        self.btn_min.clicked.connect(lambda: parent.showMinimized())
        self.btn_close.clicked.connect(self.parent_.show_tray)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.btn_min)
        layout.addWidget(self.btn_close)

        self._start_pos = None

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event): 
        if self._start_pos:
            delta = event.globalPosition().toPoint() - self._start_pos
            self.window().move(self.window().pos() + delta)
            self._start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._start_pos = None
    