from PySide6.QtWidgets import (
QApplication, QMessageBox
)
from PySide6.QtGui import QIcon
from PySide6.QtCore import QTimer

import qdarkstyle
from qdarkstyle.dark.palette import DarkPalette
from qdarkstyle.light.palette import LightPalette
import sys
from ui import Window, resource_path
from config import CONFIG
import psutil
import os
import signal
import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from set_proxy import get_os_name, Os
logger.info(f"os type: {get_os_name()}")
if get_os_name() == Os.Windows:
    import ctypes
    HWND = ctypes.wintypes.HWND
    WDA_MONITOR = 1 
    SetWindowDisplayAffinity = ctypes.windll.user32.SetWindowDisplayAffinity
    SetWindowDisplayAffinity.argtypes = [HWND, ctypes.wintypes.DWORD]
    SetWindowDisplayAffinity.restype = ctypes.wintypes.BOOL


PID_FILE = "pid"

def check_old_processes():
    
    pid = os.getpid()
    process = psutil.Process(pid)
    name = process.name()
    
    if os.path.exists(resource_path(PID_FILE)):
        with open(resource_path(PID_FILE), "r") as f:
            lst = f.readlines()
            
            try:
                app_pid = int(lst[0].strip())
                app_process = psutil.Process(app_pid)
                if app_process.is_running() and app_process.name() == name:
                    reply = QMessageBox.question(
                        None,
                        "Same Program found",
                        f"Do you want to terminate past process with pid={app_pid}",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        app_process.terminate()
                        logger.info("YES:User decieded to end old program.")
                        
                        
                    else:
                        logger.info("NO:User decieded to end program.")
                        logger.info("Exiting...")
                        
                        close_program()
                        sys.exit()

            except Exception as e: 
                logger.error(f"Error {e}")
            
            if len(lst) > 1:
                lst.pop(0)
                for tor_pid in lst:
                    try: 
                        tor_process = psutil.Process(int(tor_pid))
                        logger.info(f"PID:{tor_pid} running")
                        if tor_process.is_running() and tor_process.name() == "tor.exe":
                            tor_process.terminate()
                            logger.info("Old tor process terminated")
                            
                    except Exception as e:
                        logger.error(f"Failed to terminate old tor process with PID:{tor_pid} Error:{e}")
            else:
                logger.info(f"There is not any old tor process in pid file: {PID_FILE}")       

   
def save_current_pid():
    pid = os.getpid()
    with open(resource_path(PID_FILE), "w") as f:
        f.write(str(pid)) 

def close_program(*_, **__):
    logger.info("Exiting . . .")
    win.proxyWidget._stop_services()
    QTimer.singleShot(0, app.quit)
    
    

if __name__ == "__main__":
    app = QApplication(sys.argv)
    signal.signal(signal.SIGINT, close_program)
    
    logger.info(f" App PID={os.getpid()}")
    check_old_processes()
    save_current_pid()
    app.setWindowIcon(QIcon(resource_path("assets/icon.ico")))
    CONFIG.load()
    if CONFIG.mode == "light":
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=LightPalette()))
    else:
        app.setStyleSheet(qdarkstyle.load_stylesheet(palette=DarkPalette()))  
    win = Window()
    
    if get_os_name() == Os.Windows:
        hwnd = int(win.winId())
        SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
    
    win.show()
    
    try:
        app.exec()
    finally:
        logger.info("Application exited")
