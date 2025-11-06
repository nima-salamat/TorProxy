"""
Set http proxy to the os system
handle windows linux system first diagnose and set
"""

import os
import platform

import logging
logger = logging.getLogger(__name__)

logger.debug(platform.system())

try:
    import winreg
except Exception as e:
    logger.error(f"[!] winreg not found: {e}")
    winreg = None
try:
    import ctypes
except Exception as e:
    logger.error(f"[!] ctypes not found: {e}")
    ctypes = None

class Os:
    Windows = "Windows"
    Linux = "Linux"

def get_os_name():
    return platform.system()    

class Handler:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        
    def set_windows_proxy(self):
        logger.debug(f"Setting Windows proxy to {self.host}:{self.port}")
        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{self.host}:{self.port}")
            winreg.CloseKey(key)
            ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
            logger.debug(f"Set Windows proxy to {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[!] set_proxy error: {e}")
            return False
        
    
    def clear_windows_proxy(self):
        logger.debug(f"Clearing Windows proxy")
        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
            winreg.CloseKey(key)
            ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
            logger.info(f"Cleared Windows proxy")
            return True
        except Exception as e:
            logger.error(f"[!] set_proxy error: {e}")
            return False

    def set_linux_proxy(self):
        logger.debug(f"Setting Linux proxy")
        if "DISPLAY" in os.environ and os.environ["DISPLAY"]:
            os.system("gsettings set org.gnome.system.proxy mode 'manual'")
            os.system(f"gsettings set org.gnome.system.proxy.http host '{self.host}'")
            os.system(f"gsettings set org.gnome.system.proxy.http port {self.port}")
            return True
        return False

    def clear_linux_proxy(self):
        logger.debug(f"Clearing Linux proxy")
        if "DISPLAY" in os.environ and os.environ["DISPLAY"]:
            os.system("gsettings set org.gnome.system.proxy mode 'none'")
            return True
        return False
            
    
action_list = ["set", "clear"]

def manage_proxy(host, port, action="set"):
    operating_system = get_os_name()
    if operating_system == Os.Windows:
        handler = Handler(host, port)
        if action == action_list[0]:
            handler.set_windows_proxy()
        elif action == action_list[1]:
            handler.clear_windows_proxy()
            
    elif operating_system == Os.Linux:
        handler = Handler(host, port)
        if action == action_list[0]:
            handler.set_linux_proxy()
        elif action == action_list[1]:
            handler.clear_linux_proxy()
            
    else:
        logger.error("Operating system not supported")
        return False
    return True


