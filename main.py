from PySide6.QtWidgets import (
QApplication
)
from PySide6.QtGui import QIcon
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
import sys
from ui import Window, CONFIG, resource_path

if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    CONFIG.load()
    if CONFIG.mode == "light":
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
    else:
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
    win = Window()
    win.show()
    app.exec()