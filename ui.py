from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QMenuBar,
    QMenu,
    QStackedWidget,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox,

    QSystemTrayIcon
)

from PySide6.QtGui import QIcon
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QAction

from set_proxy import manage_proxy
from tor import resource_path

import keyboard
import threading
import time

import logging

logger = logging.getLogger(__name__)


from config import CONFIG
from ui_.worker.worker import Worker
from ui_.window.proxy_window import ProxyWindow
from ui_.window.custom_titlebar import CustomTitleBar
from ui_.window.setting_window import SettingWindow
from ui_.window.block_host_window import BlcokHostsWindow

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
        
    def closeEvent(self, event):
        self.listener_running = False
        self.listener_thread.join()
        self.proxyWidget._stop_services()
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
