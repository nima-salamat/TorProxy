from PySide6.QtWidgets import (
QApplication, QMessageBox
)
from PySide6.QtGui import QIcon
import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
import sys
from ui import Window, CONFIG, resource_path

import psutil

import os
if __name__ == "__main__":
    
    app = QApplication(sys.argv)
    pid_file = "pid"
    pid = os.getpid()
    process = psutil.Process(pid)
    name = process.name()
    if os.path.exists(resource_path(pid_file)):
        with open(resource_path(pid_file), "r") as f:
            lst = f.readlines()
            
            try:
                pid_past = int(lst[0].strip())
                process_past = psutil.Process(pid_past)
                if process_past.is_running() and process_past.name() == name:
                    reply = QMessageBox.question(
                        None,
                        "Same Program found",
                        f"Do you want to terminate past process with pid={pid_past}",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        process_past.terminate()
                             
                    else:
                        print("exit . . . ")
                        app.quit()
                        sys.exit()

            except Exception as e: 
                print(e)
            
            try:
                if len(lst) > 1:

                        pid_tor = int(lst[1])
                        process_tor = psutil.Process(pid_tor)
                        if process_tor.is_running():
                            print("tor is runnning")
                            process_tor.terminate()  
            except:
                pass
            
    with open(resource_path(pid_file), "w") as f:
        f.write(str(pid))

    print(os.getpid())
    
   
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    CONFIG.load()
    if CONFIG.mode == "light":
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
    else:
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
    win = Window()
    win.show()
    app.exec()