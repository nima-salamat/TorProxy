from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
)


from PySide6.QtCore import Qt, QTimer, QThreadPool
from stem import Signal as TorSignal
from stem.control import Controller
from stem import SocketClosed, OperationFailed
from stem.connection import AuthenticationFailure

from proxy import get_free_port
from set_proxy import manage_proxy
from tor import TorRunner, Runner

from whatismyip import what_is_my_ip
from ui_.window.log_window import LogWindow
from ui_.btn.pulse_button import PulseButton
from ui_.worker.worker import Worker
from ui_.worker.utils import Data
from config import CONFIG

import logging

logger = logging.getLogger(__name__)



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
        logger.info(f'port(proxy): {self.proxy_port} - port(socks): {self.tor_socks_port} - port(control): {self.tor_control_port}, - port(dns): {self.tor_dns_port}')
        self.tor = TorRunner(self.tor_socks_port, self.tor_control_port, self.tor_dns_port)
        self.tor.bridge = CONFIG["bridge"]
        self.tor.bridges = CONFIG["bridges"]
        self.tor.app_window = self
        self.proxy = Runner(self.proxy_port, self.tor_socks_port,self)
        self.main_layout = QVBoxLayout(self)
        self.setLayout(self.main_layout)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.btn_status = QLabel("Tap to connect 🔌")
        self.set_btn_status_style("disconnected")
        self.main_layout.addWidget(self.btn_status)
        self.connect_btn = PulseButton("Connect")
        self.connect_btn.clicked.connect(self._toggle)
        self.main_layout.addWidget(self.connect_btn)
        self.lbl_percent = QLabel("0%") 
        self.main_layout.addWidget(self.lbl_percent)
        self.data.valueChanged.connect(self.dataValueChanged)
        self.btn_change_identity = QPushButton("Change Identity 🔄")
        self.main_layout.addWidget(self.btn_change_identity)
        self.btn_change_identity.clicked.connect(self.change_identity_)
        self.logs_widget = LogWindow(self)
        self.btn_log = QPushButton("Logs 📄")
        self.btn_log.clicked.connect(self.show_logs)
        self.main_layout.addWidget(self.btn_log)
        self.timer = QTimer()
        self.timer.setInterval(30000)
        self.timer.timeout.connect(self.change_identity_)
        self.timer.start()
        
        layout_ip = QVBoxLayout()
        layout_top_ip = QHBoxLayout()
        layout_ip.addLayout(layout_top_ip)
        self.tor_ip_label = QLabel()
        layout_top_ip.addWidget(self.tor_ip_label)

        self.btn_whatismyip = QPushButton("what.is.my.ip🌐")
        layout_ip.addWidget(self.btn_whatismyip)
        self.btn_whatismyip.clicked.connect(self.whatismyip_clicked)
        self.main_layout.addLayout(layout_ip)
        self.thread_pool = QThreadPool()
    
    def whatismyip_clicked(self):
        self.worker = Worker(lambda: what_is_my_ip()) 
        self.worker.signals.finished.connect(lambda x: self.tor_ip_label.setText("ip: " + x) or self.btn_whatismyip.setEnabled(True))
        self.worker.signals.error.connect(lambda e: self.tor_ip_label.setText("ip: error") or self.btn_whatismyip.setEnabled(True))
        self.thread_pool.start(self.worker)
        self.btn_whatismyip.setDisabled(True)
        
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
        if not self.connected:
            logger.warning("change_tor_identity called but not connected to Tor.")
            return False

        try:
            
                self.controller.authenticate()
                self.controller.signal(TorSignal.NEWNYM)
                logger.info("Tor identity changed successfully (NEWNYM sent).")
                return True

        except SocketClosed:
            logger.error("Tor control socket is closed. Marking connection as disconnected.")
            self.connected = False
            return False

        except AuthenticationFailure:
            logger.critical("Authentication to Tor control port failed. Check password or cookie.")
            return False

        except OperationFailed:
            logger.warning("Tor NEWNYM signal was rejected. Possibly due to rate limit.")
            return False

        except Exception as e:
            logger.exception(f"Unexpected error while sending NEWNYM: {e}")
            return False
        
    def dataValueChanged(self, v):
        if v == "100%":
            if self._parent.isHidden():
                self._parent._notify("T⭕®️🌐🅿️®️⭕❌Y","🌐Connected 💯%")
            self.connected = True
            self.controller =  Controller.from_port(address="127.0.0.1", port=self.tor_control_port)
            manage_proxy("127.0.0.1", self.proxy_port, "set")
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
            self.proxy.stop(); self.tor.stop(); manage_proxy("127.0.0.1", 0, "clear")

            self.running = False
            self.connected = False
            self.btn_status.setText("disconnected")
            self.set_btn_status_style("disconnected")
            
           
            