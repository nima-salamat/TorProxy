from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QMenuBar,
    QMenu,
    QStackedWidget,
    QWidget,
    QButtonGroup,
    QRadioButton,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox
)

import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Property
from PySide6.QtGui import QPainter, QColor, QBrush, QAction
import sys

from proxy import get_free_port, load_blocked, set_proxy, blocked_hosts, save_blocked

from tor import TorRunner, Runner


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




class ProxyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.running = False
        
        self.tor_socks_port = get_free_port()
        self.proxy_port = get_free_port()
        print(f'port(proxy): {self.proxy_port} - port(socks): {self.tor_socks_port}')
        
        self.tor = TorRunner(self.tor_socks_port)
        self.tor.app_window = self
        self.proxy = Runner(self.proxy_port, self.tor_socks_port, self)
        
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.connect_btn = PulseButton("Connect")
        self.connect_btn.clicked.connect(self._toggle)
        self.main_layout.addWidget(self.connect_btn)
        

    def _toggle(self):
        if not self.running:
            try:
                self.proxy.start(); self.tor.start()
                set_proxy(True, f"127.0.0.1:{self.proxy_port}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Start failed: {e}"); return
            self.running=True
        else:
            self.proxy.stop(); self.tor.stop(); set_proxy(False)
            self.running=False;
class CustomTitleBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)

        self.title = QLabel("T⭕®️🌐🅿️®️⭕❌Y")
        self.title.setStyleSheet("margin-left: 10px;")
        
        self.btn_min = QPushButton("➖")
        self.btn_close = QPushButton("✖️")

        for btn in (self.btn_min, self.btn_close):
            btn.setFixedSize(30, 30)

        self.btn_min.clicked.connect(lambda: parent.showMinimized())
        self.btn_close.clicked.connect(parent.close)

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
        

        
class SettingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent) 
        self._parent = parent    
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        top_layout = QHBoxLayout(self)
        main_layout.addLayout(top_layout)

        btn_back = QPushButton("back", self)
        top_layout.addWidget(btn_back)

        btn_back.clicked.connect(self.back_to_proxy)
        

        mode_layout = QHBoxLayout(self)
        main_layout.addLayout(mode_layout)
        
        btn_group_mode = QButtonGroup(self) 
        
        btn_dark = QRadioButton("dark", self)
        btn_dark.setChecked(True) # default mode 
        mode_layout.addWidget(btn_dark)
        btn_group_mode.addButton(btn_dark)
        
        btn_light = QRadioButton("light", self)
        mode_layout.addWidget(btn_light)
        btn_group_mode.addButton(btn_light)
        
        btn_group_mode.buttonClicked.connect(self.change_mode)
    
    def change_mode(self, radiobtn):
        if radiobtn.text() == "light":
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
        else:
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
            
    def back_to_proxy(self):
        self._parent.stack.setCurrentIndex(0)
        

class Window(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowFlag(Qt.FramelessWindowHint)
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.stack = QStackedWidget(self)
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0,0,0,0)
        self.main_widget.setLayout(self.main_layout)

        self.setWindowTitle("app")
        self.resize(800, 600)
        
        
        self.proxyWidget = ProxyWindow(self)
        self.stack.addWidget(self.proxyWidget)
        self.settingWidget = SettingWindow(self)
        self.stack.addWidget(self.settingWidget)
        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        self._createMenuBar()
        
        self.main_layout.addWidget(self.stack)
    
    def closeEvent(self, event):
        if self.running: self.proxy.stop(); self.tor.stop(); set_proxy(False)
        event.accept()
    def _createMenuBar(self):
        
        menuBar = QMenuBar(self)
        self.main_layout.addWidget(menuBar)

        
        fileMenu = QMenu("&File", self)
        menuBar.addMenu(fileMenu)
    
        editMenu = QMenu("&Edit", self)
        menuBar.addMenu(editMenu)
        
        viewMenu = QMenu("&View", self)
        menuBar.addMenu(viewMenu)
        appearance_action = QAction("&Appearance", self)
        appearance_action.setShortcut("Ctrl+E")
        appearance_action.triggered.connect(self._show_appearance)
        viewMenu.addAction(appearance_action)
        helpMenu = QMenu("&Help", self)
        menuBar.addMenu(helpMenu)
        
    def _show_appearance(self):
        self.stack.setCurrentIndex(1)
        
        
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette())) 
    win = Window()
    win.show()
    app.exec()
