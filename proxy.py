import os
import json
import socks
import select
import winreg
import ctypes
import socket
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn

# ====== Config & Globals ======
BLOCKED_FILE = 'blocked_hosts.json'
blocked_hosts = []


def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def load_blocked():
    global blocked_hosts
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, 'r') as f:
                blocked_hosts = json.load(f)
        except:
            blocked_hosts = []
    else:
        blocked_hosts = []

def save_blocked():
    with open(BLOCKED_FILE, 'w') as f:
        json.dump(blocked_hosts, f, indent=2)

def set_proxy(enable=True, server="127.0.0.1:8080"):
    path = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1 if enable else 0)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, server if enable else "")
        winreg.CloseKey(key)
        ctypes.windll.Wininet.InternetSetOptionW(0, 37, 0, 0)
        ctypes.windll.Wininet.InternetSetOptionW(0, 39, 0, 0)
        return True
    except Exception as e:
        print(f"[!] set_proxy error: {e}")
        return False

# ====== Proxy Handler ======
class ProxyHandler(BaseHTTPRequestHandler):
    app_window = None
    def do_CONNECT(self):
        host, port = self.path.split(":")
        port = int(port)
        if host in blocked_hosts:
            self.send_error(403, "Forbidden: Blocked")
            return
        try:
            remote = socks.socksocket()
            remote.set_proxy(socks.SOCKS5, "127.0.0.1", self.server.tor_socks_port, rdns=True)
            remote.connect((host, port))
            self.send_response(200, "Connection Established")
            self.end_headers()
            self._tunnel(self.connection, remote)
            log_request(self.command, self.path, app_window=self.app_window)
        except Exception as e:
            self.send_error(502, f"CONNECT error: {e}")

    def do_GET(self): self._handle_http()
    def do_POST(self): self._handle_http()

    def _handle_http(self):
        parsed = urlsplit(self.path)
        host = parsed.hostname
        port = parsed.port or 80
        
        for i in blocked_hosts:
            if i.startswith("*") and "." in i:
                if host.endswith(i.split(".")[-1]):
                    
                    self.send_error(403, "Forbidden: Blocked")
                    return
            elif host in i:
                self.send_error(403, "Forbidden: Blocked")
                return
                 
                           
        try:
            remote = socks.socksocket()
            remote.set_proxy(socks.SOCKS5, "127.0.0.1", self.server.tor_socks_port, rdns=True)
            remote.connect((host, port))
            self.headers["Connection"] = "close"
            req_line = f"{self.command} {parsed.path or '/'}{'?' + parsed.query if parsed.query else ''} HTTP/1.1\r\n"
            hdrs = ''.join(f"{k}: {v}\r\n" for k, v in self.headers.items())
            full = req_line + hdrs + "\r\n"
            body = b''
            if self.command == 'POST' and 'Content-Length' in self.headers:
                body = self.rfile.read(int(self.headers['Content-Length']))
            remote.sendall(full.encode() + body)
            self._tunnel(remote, self.connection)
            log_request(self.command, self.path, len(full.encode() + body), self.app_window)
        except Exception as e:
            self.send_error(502, f"HTTP error: {e}")

    def _tunnel(self, src, dst):
        socks_list = [src, dst]
        try:
            while True:
                r, _, _ = select.select(socks_list, [], [])
                for s in r:
                    data = s.recv(4096)
                    if not data:
                        return
                    (dst if s is src else src).sendall(data)
        except:
            pass
        finally:
            src.close(); dst.close()

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    def __init__(self, addr, handler, tor_socks_port):
        super().__init__(addr, handler)
        self.tor_socks_port = tor_socks_port

# ====== Logging ======
def log_request(cmd, path, size=0, app_window=None): app_window.append_log(f"[{cmd}] {path} ({size} bytes)\n")
