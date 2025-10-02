from PySide6.QtWidgets import (
QApplication
)
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
import sys
from ui import Window
import ui
if __name__ == "__main__":
    app = QApplication(sys.argv)
    ui.__dict__["app"] = app
    app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette())) 
    win = Window()
    win.show()
    app.exec()
