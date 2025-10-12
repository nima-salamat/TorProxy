"""
Set http proxy to the os system
handle windows linux system first diagnose and set
"""

import os
import platform

print(platform.system())


try:
    import winreg
except Exception as e:
    print(f"[!] winreg not found: {e}")
    winreg = None
try:
    import ctypes
except Exception as e:
    print(f"[!] ctypes not found: {e}")
    ctypes = None

class Os:
    Windows = "Windows"
    Linux = "Linux"


class Handler:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        
    def set_windows_proxy(self):
        print(f"Setting Windows proxy to {self.host}:{self.port}")
        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"{self.host}:{self.port}")
            winreg.CloseKey(key)
            ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
            return True
        except Exception as e:
            print(f"[!] set_proxy error: {e}")
            return False
        
    
    def clear_windows_proxy(self):
        print(f"Clearing Windows proxy")
        path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
            winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
            winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, "")
            winreg.CloseKey(key)
            ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
            ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
            return True
        except Exception as e:
            print(f"[!] set_proxy error: {e}")
            return False
        
    
action_list = ["set", "clear"]

def manage_proxy(host, port, action="set"):
    
    operating_system = platform.system()
    if operating_system == Os.Windows:
        handler = Handler(host, port)
        if action == action_list[0]:
            handler.set_windows_proxy()
        elif action == action_list[1]:
            handler.clear_windows_proxy()
    # linux system not implemented yet
    else:
        print("Operating system not supported")
        return False
    return True


