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
       
        # Node selection
        self.ExcludeNodes = []
        self.ExitNodes = [] 
        self.StrictNodes = 0

        # Circuit behavior
        self.MaxCircuitDirtiness = 300
        self.NewCircuitPeriod = 30

        # Network behavior
        self.ClientUseIPv4 = 1
        self.ClientUseIPv6 = 0
         
        self.Log = "notice stdout"        
                        
        self.bridge_types = ["obfs4", "webtunnel", "meek", "snowflake", "scramblesuit", "fte"]
        
    def start(self):
        if self.proc: return
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        logger.debug("Thread tor runner started")
        
    
    def generate_torcc(self):
        config = [
            f"SocksPort {self.socks_port}",
            f"ControlPort {self.contorl_port}", 
            f"DNSPort {self.dns_port}",
            f"GeoIPFile {geoip_path}",
            f"GeoIPv6File {geoip6_path}",
            f"Log {self.Log}",
            f"MaxCircuitDirtiness {self.MaxCircuitDirtiness}",
            f"NewCircuitPeriod {self.NewCircuitPeriod}",
            f"ExcludeNodes {','.join(self.ExcludeNodes)}",
            f"ExitNodes {','.join(self.ExitNodes)}",
            f"StrictNodes {self.StrictNodes}",
            f"ClientUseIPv4 {1 if self.ClientUseIPv4 else 0}",
            f"ClientUseIPv6  {1 if self.ClientUseIPv6  else 0}",
        ]
        
        if self.bridge and self.bridges:
            
            bridge_type = ""
            for i in self.bridge_types:
                if i in self.bridges:
                    bridge_type = i
                    break
            if bridge_type:
                bridges = self.bridges.replace(bridge_type, "Bridge %s"%(bridge_type))
                print(bridges)
                config.extend(
                    [
                       "UseBridges 1",
                       'ClientTransportPlugin %s exec '%(bridge_type)+ lyrebird_path,
                       bridges
                       
                        
                    ]
                )

        return "\n".join(config)  
    
    def _run(self):
        
        torrc_content = self.generate_torcc()
        
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
