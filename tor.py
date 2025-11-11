import threading
import subprocess
import os
from config import IS_WINDOWS, BUNDLE_DIR
from proxy import  ProxyHandler, ThreadedHTTPServer
from utils import resource_path, extract_tar_gz_file
from updater import get_own_bundles, list_downloaded_bundles, check_bundle_compatibility
import logging
logger = logging.getLogger(__name__)


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
        
        self.tor_path = None
        self.lyrebird_path = None
        self.geoip_path = None
        self.geoip6_path = None
        self.path_set = self.update_path()
        
    def update_path(self, base_path=None):
        if base_path and not os.path.exists(base_path):
            base_path = None
        if base_path is None and (lst:=get_own_bundles()):
            for i in lst:
                if check_bundle_compatibility(i):
                    base_path = i
                    break

        elif base_path is not None:
            pass
        else:
            logger.error("[*_0]There is no bundle to run tor.")
            
        if base_path is None: 
            for i in list_downloaded_bundles():
                if check_bundle_compatibility(i):
                    base_path = os.path.join(BUNDLE_DIR, os.path.basename(i).replace(".tar.gz", ""))
                    extract_tar_gz_file(i, base_path)
                    break
               
            else:                
                return False
           
        self.tor_path = os.path.normpath(os.path.join(base_path, "tor/tor.exe" if IS_WINDOWS else "tor/tor"))
        self.lyrebird_path = os.path.normpath(os.path.join(base_path, "tor/pluggable_transports/lyrebird" if IS_WINDOWS else "tor/pluggable_transports/lyrebird"))
        self.geoip_path = os.path.normpath(os.path.join(base_path, "data/geoip"))
        self.geoip6_path = os.path.normpath(os.path.join(base_path, "data/geoip6"))
        self.path_set = True

        return True
    
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
            f"GeoIPFile {self.geoip_path}",
            f"GeoIPv6File {self.geoip6_path}",
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
                config.extend(
                    [
                       "UseBridges 1",
                       'ClientTransportPlugin %s exec '%(bridge_type)+ self.lyrebird_path,
                       bridges
                        
                    ]
                )

        return "\n".join(config)  
    
    def _run(self):
        try:
            if not self.path_set:
                raise ValueError("Required path not set")
            torrc_content = self.generate_torcc()
            
            logger.debug(f"torcc text:{torrc_content}")     
            torrc_file = resource_path("temp_torrc.txt")
            with open(torrc_file, "w") as f: f.write(torrc_content)
            
            
            if self.proc: self.proc.terminate(); self.proc.wait(); self.proc=None
            
            flags = subprocess.CREATE_NO_WINDOW if IS_WINDOWS else 0
            logger.info(f"Tor path: {self.tor_path}")
            logger.info(f"torrc file path: {torrc_file}")
            self.proc = subprocess.Popen([self.tor_path, "-f", torrc_file],
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

                if IS_WINDOWS:
                    self.proc.wait()
        except Exception as e:
            logger.error(f"Error failed to run tor: {e}")
            self.app_window.logs_widget.update_log(f"Error failed to run tor: {e}")
            
            
        finally:
            self.app_window._stop_services()

    def stop(self):
        try:
            if self.proc:
                self.proc.terminate()
                self.proc.wait()
                self.proc = None

            if self.thread and self.thread.is_alive():
                self.thread.join()
            self.thread = None

            if os.path.exists("temp_torrc.txt"):
                os.remove("temp_torrc.txt")
        except Exception as e:
            logger.error(f"Error while stopping: {e}")
            try:
                self.connect_btn.toggle_state()
            except Exception:
                pass

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
