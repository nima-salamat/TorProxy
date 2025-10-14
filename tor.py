import threading
import subprocess
import sys
import platform
import os
from proxy import  ProxyHandler, ThreadedHTTPServer

import logging
logger = logging.getLogger(__name__)

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

logger.debug(f"File \n\tpath[tor path:{tor_path}\n"
             f"\tlyrebird_path{lyrebird_path}\n"
             f"\tgeoip_path{geoip_path}\n"
             f"\tgeoip6_path{geoip6_path}\n"
             "\n]")


class TorRunner:
    def __init__(self, socks_port, contorl_port, dns_port):
        self.proc = None; self.thread = None; self.log_file = "tor_log.txt"
        self.socks_port = socks_port
        self.bridge = False
        self.bridges = ""   
        self.contorl_port = contorl_port
        self.dns_port = dns_port
        self.MaxCircuitDirtiness = 300
        self.bridge_types = ["obfs4", "webtunnel", "meek", "snowflake", "scramblesuit", "fte"]
        
    def start(self):
        if self.proc: return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.debug("Thread tor runner started")
    def _run(self):
        
        torrc_content = f"SocksPort {self.socks_port}\nLog notice stdout\nControlPort {self.contorl_port}\n"
        torrc_content += 'GeoIPFile ' + geoip_path + '\n'
        torrc_content += 'GeoIPv6File ' + geoip6_path + '\n'        
        torrc_content += 'DNSPort ' + str(self.dns_port) + '\n'
        torrc_content += 'AutomapHostsOnResolve 1'+ '\n'
        torrc_content += 'MaxCircuitDirtiness ' + str(self.MaxCircuitDirtiness) + '\n'
        
        
        if self.bridge and self.bridges:
            bridge_type = ""
            for i in self.bridge_types:
                if i in self.bridges:
                    bridge_type = i
                    break
            if bridge_type:
                torrc_content += 'UseBridges 1\n'
                torrc_content += 'ClientTransportPlugin %s exec '%(bridge_type)+ lyrebird_path +'\n'
                torrc_content += self.bridges.replace(bridge_type, "Bridge %s"%(bridge_type))
        
        logger.debug(f"torcc text:{torrc_content}")     
        with open("temp_torrc.txt", "w") as f: f.write(torrc_content)
        
        
        if self.proc: self.proc.terminate(); self.proc.wait(); self.proc=None
        
        flags = subprocess.CREATE_NO_WINDOW if platform.system()=="Windows" else 0
        self.proc = subprocess.Popen([tor_path, "-f", "temp_torrc.txt"],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags)
        with open(resource_path("pid"), "a") as f:
            f.write("\n"+str(self.proc.pid))
        with open(self.log_file, 'w') as f:
            for line in iter(self.proc.stdout.readline, b''):
                f.write(line.decode()); f.flush()
                if "Bootstrapped" in line.decode():
                    lst =  line.decode().split(" ")
                    logger.debug(f"[{line.decode()}]")
                    self.app_window.data.value = lst[lst.index("Bootstrapped") + 1]
                    self.app_window.logs_widget.update_log(line.decode())

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
        logger.debug("Thread proxy server started")
    def stop(self):
        if not self.server: return
        self.server.shutdown(); self.server.server_close(); self.thread.join()
        logger.debug("Proxy server closed")
        self.server=None; self.thread=None
