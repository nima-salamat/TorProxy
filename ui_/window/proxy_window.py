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

from proxy import get_free_port, is_port_free
from set_proxy import manage_proxy
from tor import TorRunner, Runner

from whatismyip import what_is_my_ip
from ui_.window.log_window import LogWindow
from ui_.btn.pulse_button import PulseButton
from ui_.worker.worker import Worker
from ui_.worker.utils import Data
from config import CONFIG
import json
import logging

logger = logging.getLogger(__name__)



class ProxyWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data = Data()
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
        self.thread_pool.start(worker)

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
            manage_proxy("127.0.0.1", self.proxy.port, "set")
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
        if self.running:
            self._stop_services()
            return

        self.connect_btn.setEnabled(False)
        self.btn_status.setText("checking ports ...")
        self.set_btn_status_style("connecting")

        worker = Worker(self._check_ports_worker)
        worker.signals.finished.connect(self._on_ports_checked)
        self.thread_pool.start(worker)

    # ===== slot that runs on main thread with the result =====
    def _on_ports_checked(self, result):
        """
        result == (ok, ports, messages)
        This runs in the GUI thread so it's safe to touch UI and self.proxy/self.tor.
        """

        try:
            ok, ports, messages = json.loads(result)
        except Exception:
            ok = False
            ports = {}
            messages = [f"Invalid result from port checker: {result!r}"]

        # log messages to widget (safe in main thread)
        for m in messages:
            try:
                self.logs_widget.update_log(m)
            except Exception:
                logger.info("log: %s", m)

        if not ok:
            # failed -> re-enable button and set disconnected style
            self.set_btn_status_style("disconnected")
            self.btn_status.setText("port check failed")
            self.connect_btn.setEnabled(True)
            self.connect_btn.toggle_state()
            return

        # ok==True -> attempt to set ports and start services (on main thread)
        try:
            # set ports from the ports dict (only keys that passed checks)
            if "proxy_port" in ports:
                self.proxy.port = ports["proxy_port"]
            if "tor_port" in ports:
                self.tor.socks_port = ports["tor_port"]
                self.proxy.tor_socks_port = ports["tor_port"]
            if "control_port" in ports:
                self.tor.control_port = ports["control_port"]
            if "dns_port" in ports:
                self.tor.dns_port = ports["dns_port"]

            # start services (wrap try/except)
            self.btn_status.setText("connecting . . .")
            self.set_btn_status_style("connecting")

            try:
                self.proxy.start()
            except Exception as e:
                logger.exception("proxy.start() failed: %s", e)
                raise

            try:
                self.tor.start()
            except Exception as e:
                logger.exception("tor.start() failed: %s", e)
                # if tor fails, try to stop proxy to avoid half-start
                try:
                    self.proxy.stop()
                except Exception:
                    logger.exception("Stopping proxy after tor.start failure also failed.")
                raise

            self.running = True
            # Don't mark connected True until your Data signals 100% (existing logic)
            self.logs_widget.update_log("Started proxy and tor successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Start failed: {e}")
            self.running = False
            self.connected = False
            self.btn_status.setText("disconnected")
            self.set_btn_status_style("disconnected")
        finally:
            # always re-enable the button
            self.connect_btn.setEnabled(True)

   # ===== helper worker (runs in background) =====
    def _check_ports_worker(self):
        """
        Pure worker: no GUI ops here.
        Returns (ok: bool, ports: dict, messages: list[str])
        Clear and explicit failures list is used so we know دقیقاً چرا fail شده.
        """
        messages = []
        failures = []
        ports = {}

        checks = [
            ("proxy_port", "proxy_port_checked", "proxy port"),
            ("tor_port", "tor_port_checked", "tor socks port"),
            ("control_port", "control_port_checked", "tor control port"),
            ("dns_port", "dns_port_checked", "dns port"),
        ]

        for cfg_key, checked_key, human in checks:
            # read checked flag (use try/except because CONFIG may not have key)
            try:
                raw_checked = CONFIG[checked_key]
            except KeyError:
                # treat missing checked flag as disabled (like you asked)
                messages.append(f"{human}: missing checked flag '{checked_key}', treating as disabled.")
                continue

            checked = bool(raw_checked)
            messages.append(f"{human}: checked={checked}")

            # read raw port value
            try:
                raw = CONFIG[cfg_key]
            except KeyError:
                raw = None
            
                
                
                

            messages.append(f"{human}: value={raw!r}")

            if not checked:
                messages.append(f"{human}: disabled, skipping.")
                continue

            if raw is None or str(raw).strip() == "":
                failures.append(f"{human}: enabled but no value provided.")
                continue

            try:
                p = int(raw)
            except Exception:
                failures.append(f"{human}: value '{raw}' is not a valid integer.")
                continue
                
            if int(raw) in ports.values():
                failures.append(f"{human}: This port is duplicated.")
                continue

            if not (1 <= p <= 65535):
                failures.append(f"{human}: port {p} out of valid range (1-65535).")
                continue

            # Check port free (bind-based). Wrap in try/except and log result.
            try:
                free = is_port_free("127.0.0.1", p)
            except Exception as e:
                free = False
                failures.append(f"{human}: error while checking port: {e}")
                logger.exception("is_port_free error for %s:%s", human, p)
                continue

            if not free:
                failures.append(f"{human}: port {p} not free.")
            else:
                messages.append(f"{human}: port {p} is free.")
                ports[cfg_key] = p

        # finalize messages and ok
        if failures:
            messages.append("Port checks failed.")
            messages.extend(failures)
            ok = False
        else:
            messages.append("All requested ports OK.")
            ok = True

        return json.dumps([ok, ports, messages])

    def _stop_services(self):
        manage_proxy("127.0.0.1", self.proxy.port, "clear")
        self.btn_status.setText("disconnecting . . .")
        self.set_btn_status_style("disconnecting")

        try:
            if self.proxy:
                self.proxy.stop()
                self.logs_widget.update_log("Proxy stopped.")
            if self.tor:
                self.tor.stop()
                self.logs_widget.update_log("Tor stopped.")
        except Exception as e:
            logger.exception("Error stopping services: %s", e)
            self.logs_widget.update_log(f"Error while stopping services: {e}")

        
        self.running = False
        self.connected = False
        self.lbl_percent.setText("0%")
        self.btn_status.setText("disconnected")
        self.set_btn_status_style("disconnected")
        self.connect_btn.connected = False
        self.connect_btn.updateStyle()
        self.connect_btn.setEnabled(True)
