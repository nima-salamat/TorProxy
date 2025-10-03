from PySide6.QtWidgets import (
QApplication
)
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
import sys
from ui import Window, CONFIG
if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    CONFIG.load()
    if CONFIG.mode == "light":
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
    else:
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
    win = Window()
    win.show()
    app.exec()