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
    QMessageBox,
    QCheckBox,
    QTextEdit,
    QListWidget,
    QLineEdit,
    QSystemTrayIcon
)

from PySide6.QtGui import QIcon, QImage, QPixmap
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Property, Signal, QObject, QTimer, QRunnable, Slot, QThreadPool
from PySide6.QtGui import QPainter, QColor, QBrush, QAction
import sys
from stem import Signal as TorSignal
from stem.control import Controller
from proxy import get_free_port, load_blocked, set_proxy, remove_blocked, save_blocked, add_to_blocked_hosts, get_blocked

from tor import TorRunner, Runner
import os
import json
import cv2
from pyzbar.pyzbar import decode
import numpy


class Config:
    file_config = "config.json"
    default_data = {"bridges": "", "bridge":False, "mode": "dark"}
    data = {"bridges": "", "bridge":False, "mode": "dark"}
    
    def __getitem__(self, name):
        if name in self.default_data:
            return self.data.get(name, None) or self.default_data[name]
        return None
    
    def __setitem__(self, name, value):
        self.data[name] = value
        self.save()
        
    def __getattr__(self, name):
        if name in ["bridges", "bridge", "mode"]:
            return self[name]
        return super().__getattr__(name)
    
    def __setattr__(self, name, value):
        if name in ["bridges", "bridge", "mode"]:
            self[name] = value
            return
        super().__setattr__(name, value)        
        
    @staticmethod
    def create_if_is_not_exits(fun):
        def inner_function(*args, **kwargs):
            
            dir_ = os.path.dirname(__file__)
            file_path = os.path.join(dir_, Config.file_config)
            
            if not os.path.exists(file_path):
                open(file_path, "w").close()
                
            return fun(*args, **kwargs)
            
        return inner_function    
    
    def save_config(self, data):
        with open(self.file_config, "w") as file:
            file.write(data)

    @create_if_is_not_exits
    def get_config(self):
        with open(self.file_config, "r") as file:
            return file.read()
    
    def json_format(self, data):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return self.default_data

    def json_to_text(self, data):
        return json.dumps(data)
        
    
    def load(self):
        data = self.get_config()
        self.data = self.json_format(data)
        return self.data

    def save(self):
        data = self.json_to_text(self.data)
        self.save_config(data)
        
CONFIG = Config()

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


class Data(QObject):
    valueChanged = Signal(str)

    def __init__(self):
        super().__init__()
        self._value = ""

    def get_value(self):
        return self._value

    def set_value(self, val):
        if self._value != val:
            self._value = val
            self.valueChanged.emit(self._value)

    value = property(get_value, set_value)
    

class QRWorkerSignals(QObject):
    started = Signal()
    finished = Signal()
    error = Signal(str)


    
class Worker(QRunnable):

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = QRWorkerSignals()

    
    @Slot()
    def run(self):
        
        try:
            self.signals.started.emit()
            self.fn(*self.args, **self.kwargs)      
            self.signals.finished.emit()
        except Exception as e:
            self.signals.error.emit(str(e))


class LogWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ = parent
        self.setup_ui()
        self.hide()
        
    def setup_ui(self):
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(300, 400)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        self.setLayout(layout)
        
        content = QWidget()
        content.setStyleSheet("""
            background-color: rgba(40, 40, 40, 220);
            border-radius: 8px;
            border: 1px solid #555;
        """)
        content_layout = QVBoxLayout(content)
        
        self.text_edit = QTextEdit()
        self.text_edit.setStyleSheet("""
            QTextEdit {
                background-color: rgba(20, 20, 20, 200);
                color: #00ff00;
                font-family: 'Courier New';
                border: none;
                border-radius: 5px;
                padding: 5px;
            }
        """)
        self.text_edit.setReadOnly(True)
        content_layout.addWidget(self.text_edit)
        
        button_layout = QHBoxLayout()
        self.btn_clear = QPushButton("Clear")
        self.btn_clear.clicked.connect(self.text_edit.clear)
        self.btn_close = QPushButton("Close")
        self.btn_close.clicked.connect(self.close)
        
        button_layout.addWidget(self.btn_clear)
        button_layout.addStretch()
        button_layout.addWidget(self.btn_close)
        content_layout.addLayout(button_layout)
        
        layout.addWidget(content)
        
    def update_log(self, message):
        self.text_edit.append(message)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.offset = event.pos()
            
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, 'offset'):
            self.move(self.pos() + event.pos() - self.offset)


class ProxyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = Data()
        self.threadpool = QThreadPool()
        self.running = False
        self.connected = False
        self._parent = parent
        self.tor_socks_port = get_free_port()
        self.proxy_port = get_free_port()
        self.tor_control_port = get_free_port()
        self.tor_dns_port = get_free_port()
        print(f'port(proxy): {self.proxy_port} - port(socks): {self.tor_socks_port} - port(control): {self.tor_control_port}, - port(dns): {self.tor_dns_port}')
        self.tor = TorRunner(self.tor_socks_port, self.tor_control_port, self.tor_dns_port)
        self.tor.bridge = CONFIG["bridge"]
        self.tor.bridges = CONFIG["bridges"]
        self.tor.app_window = self
        self.proxy = Runner(self.proxy_port, self.tor_socks_port,self)
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_status = QLabel("tap to connect")
        self.set_btn_status_style("disconnected")
        self.main_layout.addWidget(self.btn_status)
        self.connect_btn = PulseButton("Connect")
        self.connect_btn.clicked.connect(self._toggle)
        self.main_layout.addWidget(self.connect_btn)
        self.lbl_percent = QLabel("0%") 
        self.main_layout.addWidget(self.lbl_percent)
        self.data.valueChanged.connect(self.dataValueChanged)
        self.btn_change_identity = QPushButton("change identity")
        self.main_layout.addWidget(self.btn_change_identity)
        self.btn_change_identity.clicked.connect(self.change_identity_)
        self.logs_widget = LogWindow(self)
        self.btn_log = QPushButton("logs")
        self.btn_log.clicked.connect(self.show_logs)
        self.main_layout.addWidget(self.btn_log)
        self.timer = QTimer()
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.change_identity_)
        self.timer.start()
    
    def show_logs(self):
        if self.logs_widget.isHidden():
            self.logs_widget.setParent(self)
            self.logs_widget.move(10,10)
            self.logs_widget.show() 
        else:
            self.logs_widget.hide() 
            
       
    def change_identity_(self):
        worker = Worker(
            self.change_identity
        )
        self.threadpool.start(worker)

    def change_identity(self):
        if self.connected:
            try:
                print(self.tor_control_port, type(self.tor_control_port))
                with Controller.from_port(address="127.0.0.1", port=self.tor_control_port) as controller:
                    controller.authenticate()
                    controller.signal(TorSignal.NEWNYM)
            except:
                pass      
        
    def dataValueChanged(self, v):
        if v == "100%":
            if self._parent.isHidden():
                self._parent._notify("T⭕®️🌐🅿️®️⭕❌Y","🌐Connected 💯%")
            self.connected = True
            set_proxy(True, f"127.0.0.1:{self.proxy_port}")
            self.btn_status.setText("connected")
            self.set_btn_status_style("connected")
            
        self.lbl_percent.setText(str(v)+"")
        
        
    def set_btn_status_style(self, stmt):
        if stmt == "disconnected":
            color = "#2ecc71"
        else:
            color = "#e74c3c"
        
        self.btn_status.setStyleSheet("""
            QLabel {
                padding: 20px;
                border-radius: 15px;
                font-size: 18px;
                font-weight: bold;
                border: 4px solid %s;
            }
            QLabel:hover {
                border: 4px solid #1B5E20;
            }
        """%(color))
        
        
    def _toggle(self):
        if not self.running:
            try:
                self.proxy.start(); self.tor.start()
                self.btn_status.setText("connecting . . .")
                self.set_btn_status_style("connecting")
                self.running=True

            except Exception as e:
                QMessageBox.critical(self, "Error", f"Start failed: {e}")
                self.proxy.stop(); self.tor.stop()
                self.running = False 
                self.connected = False
                return
        else:
            self.lbl_percent.setText("0%")
            self.proxy.stop(); self.tor.stop(); set_proxy(False)
            self.running = False
            self.connected = False
            self.btn_status.setText("disconnected")
            self.set_btn_status_style("disconnected")
            
           
            
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
    

class QrCodeFloatingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.parent_ = parent
        self.cap = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_frame)
        
        self.data = None
        
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        
        self.camera_label = QLabel() 
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 480)
        self.main_layout.addWidget(self.camera_label)
        
        self.btn_close = QPushButton("close")
        self.btn_close.clicked.connect(self.close)
        self.main_layout.addWidget(self.btn_close)
        
    
    def update_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            QMessageBox.warning(self, "", "Error in reading frame")
            self.close()

        frame  = numpy.flip(frame, (1))
            
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        decoded_objects = decode(rgb_frame)
        
        for obj in decoded_objects:
            try:
                data = obj.data.decode('utf-8')
                self.process_qr_code(data, frame, obj)
            except Exception as e:
                print(f"Error decoding QR: {e}")
                
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        qt_image = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.camera_label.setPixmap(QPixmap.fromImage(qt_image).scaled(
            self.camera_label.width(), 
            self.camera_label.height(),
            Qt.KeepAspectRatio
        ))
    
    def run(self):
        self.cap = cv2.VideoCapture(0)
    
    def process_qr_code(self, data, *args):
        self.data = data
        QMessageBox.information(self, "QR Code Detected!", "Ok")
        self.close()
      
    def close(self):
        self.cap.release()
        self.timer.stop()
        if self.data is not None:
            self.parent_.inp_bridges.setText("\n".join(json.loads(self.data)))
        super().close()

        
class SettingWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent) 
        self._parent = parent    
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)

        top_layout = QHBoxLayout(self)
        main_layout.addLayout(top_layout)  

        mode_layout = QHBoxLayout(self)
        main_layout.addLayout(mode_layout)
        
        btn_group_mode = QButtonGroup(self) 
        
        btn_dark = QRadioButton("dark", self)
        btn_dark.setChecked(CONFIG["mode"]!="light")
        mode_layout.addWidget(btn_dark)
        btn_group_mode.addButton(btn_dark)
        
        btn_light = QRadioButton("light", self)
        btn_light.setChecked(CONFIG["mode"]=="light")
        
        mode_layout.addWidget(btn_light)
        btn_group_mode.addButton(btn_light)
        
        btn_bridge = QCheckBox("bridge", self)
        btn_bridge.setChecked(CONFIG.bridge)
        btn_bridge.stateChanged.connect(self.bridge_state_changed)
        main_layout.addWidget(btn_bridge)
        
        self.inp_bridges = QTextEdit(self,placeholderText="Enter your bridges . . . (obfs4 or webtunnel)")
        self.inp_bridges.setText(CONFIG.bridges)
        self.inp_bridges.setEnabled(CONFIG.bridge)
        self.inp_bridges.textChanged.connect(self.set_bridges)
        main_layout.addWidget(self.inp_bridges)
        btn_group_mode.buttonClicked.connect(self.change_mode)
        self.btn_qrcode = QPushButton("Qr-Code")
        self.btn_qrcode.clicked.connect(self.show_qrcode)
        main_layout.addWidget(self.btn_qrcode)
        
        max_circuit_dirtiness_layout = QHBoxLayout()
        max_circuit_dirtiness_layout.addWidget(QLabel("MaxCircuitDirtiness  "))
        main_layout.addLayout(max_circuit_dirtiness_layout)
        
        self.inp_MaxCircuitDirtiness = QLineEdit(str(self._parent.proxyWidget.tor.MaxCircuitDirtiness))
        
        max_circuit_dirtiness_layout.addWidget(self.inp_MaxCircuitDirtiness)
        self.inp_MaxCircuitDirtiness.textChanged.connect(self.MaxCircuitDirtiness_changed)
        
        self.lbl_MaxCircuitDirtiness = QLabel("✅")
        max_circuit_dirtiness_layout.addWidget(self.lbl_MaxCircuitDirtiness)
        
        
        newnym_layout = QHBoxLayout()
        main_layout.addLayout(newnym_layout)
        newnym_layout.addWidget(QLabel("SIGNAL NEWNYM sends every"))
        self.newnym_inp = QLineEdit(str(self._parent.proxyWidget.timer.interval()))
        newnym_layout.addWidget(self.newnym_inp)
        self.newnym_inp.textChanged.connect(self.newnym_inp_changed)
        newnym_layout.addWidget(QLabel("mili sec"))
        self.newnym_lbl_stat = QLabel(f"({self._parent.proxyWidget.timer.interval()//1000} sec)  ✅")
        newnym_layout.addWidget(self.newnym_lbl_stat)
        self.qrcode_widget = QrCodeFloatingWindow(self)

      
        self.threadpool = QThreadPool()
        
        
    def show_qrcode(self):
     
        worker = Worker(self.qrcode_widget.run)
        worker.signals.finished.connect(self.show_qrcode_widget)
        worker.signals.error.connect(self.show_qrcode_widget)

        self.threadpool.start(worker)

        self.btn_qrcode.setDisabled(True)
        
    def show_qrcode_widget(self, *args):
        if not args: 
            self.qrcode_widget.setParent(self)        
            self.qrcode_widget.move(80, 0)
            self.qrcode_widget.show()
            self.qrcode_widget.timer.start(30)
        self.btn_qrcode.setEnabled(True) 
        
    def newnym_inp_changed(self):
        text = self.newnym_inp.text()
        if text and all([i in "0123456789" for i in text]) and 0 < int(text) < 2_147_483_647: # 2_147_483_647 4 byte signed int
            try:
                self._parent.proxyWidget.timer.setInterval(int(text))
                self.newnym_lbl_stat.setText(f"({self._parent.proxyWidget.timer.interval()//1000} sec)  ✅")
            except OverflowError:
                print(text)
        else:
            self.newnym_lbl_stat.setText("❌")

    def MaxCircuitDirtiness_changed(self):
        text = self.inp_MaxCircuitDirtiness.text()
        if  text and all([i in "0123456789" for i in text]):
            self._parent.proxyWidget.tor.MaxCircuitDirtiness = int(text)
            self.lbl_MaxCircuitDirtiness.setText("✅")
        else:
            self.lbl_MaxCircuitDirtiness.setText("❌")
    
    def set_bridges(self):
        self._parent.proxyWidget.tor.bridges = self.inp_bridges.toPlainText()
        CONFIG.bridges = self.inp_bridges.toPlainText()
         
    def bridge_state_changed(self, state):
        if state==2:
            self._parent.proxyWidget.tor.bridge = True
            self.inp_bridges.setEnabled(True)
            CONFIG.bridge = True
        else: 
            self._parent.proxyWidget.tor.bridge = False
            self.inp_bridges.setEnabled(False)
            CONFIG.bridge = False
            
    def change_mode(self, radiobtn):
        app = QApplication.instance()
        print("hey")
        if radiobtn.text() == "light":
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
            
            CONFIG.mode = "light"
            
        else:
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
            CONFIG.mode= "dark"
            

class BlcokHostsWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent) 
        self._parent = parent    
        main_layout = QVBoxLayout(self)
        self.setLayout(main_layout)
        
        load_blocked()

        self.hosts_list = QListWidget()
        main_layout.addWidget(self.hosts_list)
        self.hosts_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.hosts_list.customContextMenuRequested.connect(self.show_context_menu)

        self._update_hosts_list()
        
        self.inp_host = QLineEdit()
        self.inp_host.setPlaceholderText("Enter a host like 'example.com'")
        main_layout.addWidget(self.inp_host)

        self.btn_add = QPushButton("Add")
        main_layout.addWidget(self.btn_add)
        self.btn_add.clicked.connect(self.add_to_list)
        
        self.threadpool = QThreadPool()
        
    def show_context_menu(self, pos):
        item = self.hosts_list.itemAt(pos)
        if item:
            reply = QMessageBox.question(
                self,
                "Confirm Delete",
                f"Do you want to remove '{item.text()}'?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                remove_blocked(item.text())
                self.hosts_list.takeItem(self.hosts_list.row(item))
                worker = Worker(
                    save_blocked
                )
                self.threadpool.start(worker)
    
    def _update_hosts_list(self):
        self.hosts_list.clear()
        for host in get_blocked():
            self.hosts_list.addItem(host)
        
    def add_to_list(self):
        host = self.inp_host.text()
        print(host)
        if add_to_blocked_hosts(host):
            worker = Worker(
                save_blocked
            )
            self.threadpool.start(worker)
            self.hosts_list.addItem(host)
            self.inp_host.clear()
            self.inp_host.setFocus()
            

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
        
        self.block_host_window = BlcokHostsWindow(self)
        self.stack.addWidget(self.block_host_window)
        
        self.title_bar = CustomTitleBar(self)
        self.main_layout.addWidget(self.title_bar)
        self._createMenuBar()
        self.main_layout.addWidget(self.stack)
        
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("assets/icon.png"))
        
        tray_menu = QMenu()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.show_window)
        self.tray_icon.show()
        
    def show_tray(self):
        self.hide()
    
    def show_window(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self.show()
    
    def close(self):
        self.show()
        super().close()
        
    
    def closeEvent(self, event):
        if self.proxyWidget.running: self.proxyWidget.proxy.stop(); self.proxyWidget.tor.stop(); set_proxy(False)
        event.accept()

    def _createMenuBar(self):
        menuBar = QMenuBar(self)
        self.main_layout.addWidget(menuBar)

        # --- Home ---
        home_action = QAction("    Home🏠    ", self)
        home_action.setShortcut("Ctrl+H")
        home_action.setToolTip("Ctrl+H")
        home_action.triggered.connect(self._show_home)
        menuBar.addAction(home_action)

        # --- Setting ---
        setting_action = QAction("    Setting⚙️    ", self)
        setting_action.setShortcut("Ctrl+S")
        setting_action.setToolTip("Ctrl+S")
        setting_action.triggered.connect(self._show_setting)
        menuBar.addAction(setting_action)

        # --- Block Host ---
        block_action = QAction("    Block Host🚫    ", self)
        block_action.setShortcut("Ctrl+B")
        block_action.setToolTip("Ctrl+B")
        block_action.triggered.connect(self._show_block_host)
        menuBar.addAction(block_action)

        # --- Help ---
        help_action = QAction("    Help❕    ", self)
        help_action.setShortcut("F1")
        help_action.setToolTip("Show shortcuts")
        help_action.triggered.connect(self._show_help)
        menuBar.addAction(help_action)
        
        # --- Quit ---
        exit_action = QAction("    Quit🚪    ", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setToolTip("Ctrl+Q")
        exit_action.triggered.connect(self.ask_close)
        menuBar.addAction(exit_action)

    def ask_close(self):
        reply = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to quit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.close()
    
    def _show_help(self):
        QMessageBox.information(
            self,
            "Keyboard Shortcuts",
            (
                "<b>Keyboard Shortcuts:</b><br><br>"
                "Ctrl + H → Home<br>"
                "Ctrl + S → Setting<br>"
                "Ctrl + B → Block Host<br>"
                "Ctrl + Q → Quit"
            )
        )
    
    def _show_home(self):
        self.stack.setCurrentIndex(0)

    def _show_setting(self):
        self.stack.setCurrentIndex(1)
    
    def _show_block_host(self):
        self.stack.setCurrentIndex(2)
         
    def _notify(self, title, message):
        self.tray_icon.showMessage(title, message, QSystemTrayIcon.Information, 2000)
