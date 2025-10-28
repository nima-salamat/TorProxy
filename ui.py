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
from qtpy.QtCore import QThread
from stem import Signal as TorSignal
from stem.control import Controller
from stem import SocketClosed, OperationFailed
from stem.connection import AuthenticationFailure

from proxy import get_free_port, load_blocked, remove_blocked, save_blocked, add_to_blocked_hosts, get_blocked
from set_proxy import manage_proxy
from tor import TorRunner, Runner, resource_path
import os
import json
import cv2
from pyzbar.pyzbar import decode
import numpy
import keyboard
import threading
import time
from whatismyip import what_is_my_ip, check_connectivity

import logging

logger = logging.getLogger(__name__)


from config import CONFIG
from ui_.worker.worker import Worker
from ui_.window.proxy_window import ProxyWindow


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
                logger.error(f"Error decoding QR: {e}")
                
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
        
        self.btn_dark = QRadioButton("dark", self)
        self.btn_dark.setChecked(CONFIG["mode"]!="light")
        mode_layout.addWidget(self.btn_dark)
        btn_group_mode.addButton(self.btn_dark)
        
        self.btn_light = QRadioButton("light", self)
        self.btn_light.setChecked(CONFIG["mode"]=="light")
        
        mode_layout.addWidget(self.btn_light)
        btn_group_mode.addButton(self.btn_light)
        
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
        worker.signals.finished.connect(lambda x: self.show_qrcode_widget())
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
                logger.error(text)
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
        if radiobtn.text() == "light":
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
            
            CONFIG.mode = "light"
            self._parent.toggle_btn.setText("🌞")
            
        else:
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
            CONFIG.mode= "dark"
            self._parent.toggle_btn.setText("🌛")
            

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
        if add_to_blocked_hosts(host):
            worker = Worker(
                save_blocked
            )
            self.threadpool.start(worker)
            self.hosts_list.addItem(host)
            self.inp_host.clear()
            self.inp_host.setFocus()
            

class Window(QMainWindow):
    toggle_visibility_signal = Signal()
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
        self.tray_icon.setIcon(QIcon(resource_path("assets/icon.png")))
        
        tray_menu = QMenu()
        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.close)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self.show_window)
        self.tray_icon.show()
        
        self.listener_running = True
        self.listener_thread = threading.Thread(target=self._start_key_listener, daemon=True)
        self.listener_thread.start()
        
        self.toggle_visibility_signal.connect(self._toggle_visibility)

    def _toggle_visibility(self):
        self.setHidden(not self.isHidden())

    def _start_key_listener(self):
        keyboard.add_hotkey('ctrl+alt+p', lambda: self.toggle_visibility_signal.emit())
        while self.listener_running:
            time.sleep(0.5)
        keyboard.unhook_all_hotkeys()
        
        
    def show_tray(self):
        self.hide()
        # # shold use show becuase tray will delete after system locked in this case windows
        # self.tray_icon.show()
        
    
    def show_window(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            if self.isHidden():
                self.show()
            else:
                self.hide()
        # self.tray_icon.show()
        
    
    def close(self):
        self.listener_running = False
        self.listener_thread.join()
        self.show()
        super().close()
        
    def closeEvent(self, event):
        self.listener_running = False
        self.listener_thread.join()
        if self.proxyWidget.running: self.proxyWidget.proxy.stop(); self.proxyWidget.tor.stop(); manage_proxy("127.0.0.1", 0, "clear")
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
        
        self.toggle_btn = QPushButton("🌞" if CONFIG["mode"] == "light" else "🌛", self)
        self.toggle_btn.setToolTip("Toggle Light/Dark Mode")
        self.toggle_btn.setCheckable(True)
        self.toggle_btn.clicked.connect(self._toggle_theme)
        menuBar.setCornerWidget(self.toggle_btn, Qt.TopRightCorner)
    
    def _toggle_theme(self):
        app = QApplication.instance()
        if self.toggle_btn.text() == "🌞":
            self.toggle_btn.setText("🌛")
            self.settingWidget.btn_dark.setChecked(True)
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
            
            CONFIG.mode= "dark"
                
        else:
            self.toggle_btn.setText("🌞")
            self.settingWidget.btn_light.setChecked(True)
            app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette())) 
            CONFIG.mode = "light"
     
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
                "Alt + Ctrl + P → Hide/Show Hotkey<br>"
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
