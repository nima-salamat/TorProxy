import threading
import subprocess
import sys
import platform
import os
from proxy import  ProxyHandler, ThreadedHTTPServer
def resource_path(relative_path):
    if getattr(sys, "_MEIPASS", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

tor_path = resource_path("tor_bundle/tor/tor.exe")
lyrebird_path = resource_path("tor_bundle/tor/pluggable_transports/lyrebird.exe")
geoip_path = resource_path("tor_bundle/data/geoip")
geoip6_path = resource_path("tor_bundle/data/geoip6")

class TorRunner:
    def __init__(self, socks_port):
        self.proc = None; self.thread = None; self.log_file = "tor_log.txt"
        self.socks_port = socks_port
        self.bridge = False
        self.bridge_type = "obfs4"
        self.bridges = ""

        self.bridge_types = ["obfs4"]
        
    def start(self):
        if self.proc: return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
    def _run(self):
        
        torrc_content = f"SocksPort {self.socks_port}\nLog notice stdout\n"
        torrc_content += 'GeoIPFile ' + geoip_path + '\n'
        torrc_content += 'GeoIPv6File ' + geoip6_path + '\n'

        if self.bridge and self.bridges:
            if self.bridge_type == "obfs4":    
                torrc_content += 'UseBridges 1\n'
                torrc_content += 'ClientTransportPlugin obfs4 exec '+ lyrebird_path +'\n'
                torrc_content += self.bridges.replace("obfs4", "Bridge obfs4")
        
        with open("temp_torrc.txt", "w") as f: f.write(torrc_content)
        
        flags = subprocess.CREATE_NO_WINDOW if platform.system()=="Windows" else 0
        self.proc = subprocess.Popen([tor_path, "-f", "temp_torrc.txt"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
        
        with open(self.log_file, 'w') as f:
            for line in iter(self.proc.stdout.readline, b''):
                f.write(line.decode()); f.flush()
                if "Bootstrapped" in line.decode():
                    lst =  line.decode().split(" ")
                    self.app_window.data.value = lst[lst.index("Bootstrapped") + 1]

    def stop(self):
        if self.proc: self.proc.terminate(); self.proc.wait(); self.proc=None
        if self.thread: self.thread.join(); self.thread=None
        if os.path.exists("temp_torrc.txt"): os.remove("temp_torrc.txt")

# ====== Proxy Controller ======
class Runner:
    def __init__(self, port, tor_socks_port, app_window):
        self.app_window = app_window
        self.port=port; self.server=None; self.thread=None; self.tor_socks_port = tor_socks_port
    def start(self):
        if self.server: return
        ProxyHandler.app_window = self.app_window
        self.server = ThreadedHTTPServer(("0.0.0.0", self.port), ProxyHandler, self.tor_socks_port)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
    def stop(self):
        if not self.server: return
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        self.server=None; self.thread=None
