import os
import json
import socks
import select
import socket
from urllib.parse import urlsplit
from http.server import BaseHTTPRequestHandler, HTTPServer
from socketserver import ThreadingMixIn
import queue
import logging

logger = logging.getLogger(__name__)
# ====== Config & Globals ======
BLOCKED_FILE = 'blocked_hosts.json'
EXCLUDE_FILE = 'exclude_hosts.json'

blocked_hosts = []
exclude_hosts = []




queue_bytes = queue.Queue()
import threading
running = True
from config import CONFIG
def worker_data_usage_tracker(stop_event):
    while not stop_event.is_set():
        if not queue_bytes.empty():
            byte = queue_bytes.get()
            data_usage = CONFIG["data_usage"]
            data_usage = 0 if data_usage is None else data_usage+byte
            CONFIG["data_usage"] = data_usage

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def is_port_free(host: str, port: int, timeout: float = 0.15) -> bool:
    try:
        for res in socket.getaddrinfo(host, port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, socktype, proto, canonname, sa = res
            s = socket.socket(af, socktype, proto)
            try:
                s.settimeout(timeout)
                rc = s.connect_ex(sa)
                s.close()
                if rc == 0:
                    return False
            except Exception:
                try:
                    s.close()
                except Exception:
                    pass
                continue
        return True
    except Exception:
        return True
    
    
# --- blocked hosts ---
def load_blocked():
    global blocked_hosts
    if os.path.exists(BLOCKED_FILE):
        try:
            with open(BLOCKED_FILE, 'r') as f:              
                blocked_hosts = json.load(f)
        except:
            logger.error('error in loading blocked hosts')
            blocked_hosts = []
    else:
        blocked_hosts = []

def add_to_blocked_hosts(host):
    if host not in blocked_hosts:
            blocked_hosts.append(host)
            return True
    return False


def get_blocked():
    return blocked_hosts

def remove_blocked(host):
    blocked_hosts.remove(host)
    
def save_blocked():
    with open(BLOCKED_FILE, 'w') as f:
        json.dump(blocked_hosts, f, indent=2)

# --- exclude hosts ---
def load_exclude():
    global exclude_hosts
    if os.path.exists(EXCLUDE_FILE):
        try:
            with open(EXCLUDE_FILE, 'r') as f:              
                exclude_hosts = json.load(f)
        except:
            logger.error('error in loading exclude hosts')
            exclude_hosts = []
    else:
        exclude_hosts = []

def add_to_exclude_hosts(host):
    if host not in exclude_hosts:
            exclude_hosts.append(host)
            return True
    return False
      
def get_exclude():
    return exclude_hosts

def remove_exclude(host):
    exclude_hosts.remove(host)

def save_exclude():
    with open(EXCLUDE_FILE, 'w') as f:
        json.dump(exclude_hosts, f, indent=2)

# --- save all ---
def save_all():
    
    with open(EXCLUDE_FILE, 'w') as f:
        json.dump(exclude_hosts, f, indent=2)
    
    with open(BLOCKED_FILE, 'w') as f:
        json.dump(blocked_hosts, f, indent=2)

# ====== Proxy Handler ======
class ProxyHandler(BaseHTTPRequestHandler):
    app_window = None
    def do_CONNECT(self):
        host, port = self.path.split(":")
        port = int(port)
                
        for i in blocked_hosts:
            if i.startswith("*"):
                if host.endswith(i[1:]):
                    self.send_error(403, "Forbidden: Blocked")
                    logger.debug(f"BLOCKED {host}:{port}")
                    return
    
        if host in blocked_hosts or any([host.endswith("."+i) for i in blocked_hosts]):
            self.send_error(403, "Forbidden: Blocked")
            logger.debug(f"BLOCKED {host}:{port}")
            return

        proxy = True
        
        for i in exclude_hosts:
              if i.startswith("*"):
                if host.endswith(i[1:]):
                   proxy = False
        if host in exclude_hosts or any([host.endswith("."+i) for i in exclude_hosts]):
            logger.debug(f"exclude {host}:{port}")
            
            proxy = False

        try:
            
            remote = socks.socksocket()
            if proxy:
                remote.set_proxy(socks.SOCKS5, "127.0.0.1", self.server.tor_socks_port, rdns=True)
            
            remote.connect((host, port))
            self.send_response(200, "Connection Established")
            self.end_headers()
            self._tunnel(self.connection, remote)
            # log_request(self.command, self.path, app_window=self.app_window)
        except Exception as e:
            self.send_error(502, f"CONNECT error: {e}")
            logger.error(f"CONNECT error: {e}")

    def do_GET(self): self._handle_http()
    def do_POST(self): self._handle_http()

    def _handle_http(self):
        parsed = urlsplit(self.path)
        host = parsed.hostname
        port = parsed.port or 80
                         
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
            logger.debug(f"Sent {len(full.encode() + body)} bytes to {host}:{port}")

        except Exception as e:
            self.send_error(502, f"HTTP error: {e}")
            logger.error(f"HTTP error: {e}")

    def _tunnel(self, src, dst):
        socks_list = [src, dst]
        try:
            while True:
                r, _, _ = select.select(socks_list, [], [])
                for s in r:
                    data = s.recv(4096)
                    queue_bytes.put(len(data))
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
