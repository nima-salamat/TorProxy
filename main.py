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

import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

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
                        logger.error("exiting  . . .  ")
                        app.quit()
                        sys.exit()

            except Exception as e: 
                logger.error(f"Error {e}")
            
                if len(lst) > 1:
                        lst.pop(0)
                        for pid_tor in lst:
                            try: 
                                process_tor = psutil.Process(int(pid_tor))
                                if process_tor.is_running():
                                    logger.info(f"PID:{pid_tor} running")
                                    logger.error("tor is runnning")
                                    process_tor.terminate()  
                            except Exception as e:
                                 logger.error(e)
            
    with open(resource_path(pid_file), "w") as f:
        f.write(str(pid))

    logger.info(f" App PID={os.getpid()}")
    
   
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    CONFIG.load()
    if CONFIG.mode == "light":
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
    else:
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
    win = Window()
    win.show()
    app.exec()
