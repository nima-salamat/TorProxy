
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,

)
from PySide6.QtCore import Qt

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