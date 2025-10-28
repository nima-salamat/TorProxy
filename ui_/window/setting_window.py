from PySide6.QtWidgets import (
    QApplication,
    QLabel,
    QWidget,
    QButtonGroup,
    QRadioButton,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QCheckBox,
    QTextEdit,
    QLineEdit,
)

import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette

from PySide6.QtCore import QThreadPool


from pyzbar.pyzbar import decode

import logging

logger = logging.getLogger(__name__)


from config import CONFIG
from ui_.worker.worker import Worker
from ui_.window.qrcode_widget import QrCodeFloatingWindow


        
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
          