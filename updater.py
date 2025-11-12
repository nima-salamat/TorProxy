import requests
from bs4 import BeautifulSoup
from config import TOR_BUNDLE_BASE_URL, OS_NAME, ARCHITECTURE, BUNDLE_DIR, CHECKSUM_FILE
import io
import hashlib
import os
import glob
import shutil
from utils import resource_path
from urllib.parse import urljoin
import logging

logger = logging.getLogger(__name__)

def bundle_path(filename):
    return resource_path(os.path.join(BUNDLE_DIR, filename))

def create_bundle_dir():
    os.makedirs(BUNDLE_DIR ,exist_ok=True)
    
def get_tor_versions(url=TOR_BUNDLE_BASE_URL):
    links = []
    try:
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")    
        for link in soup.find_all("a"):
            if link.text.endswith("/"):
                links.append(link.text)
                #
                get_checksum(link.text)
    except Exception as e:
        logger.error(f"error in get tor version: {e}")
    return links


def get_bundle_links(version, base_url=TOR_BUNDLE_BASE_URL):
    links = []
    try:
        version = version.replace("/", "")
        url = base_url + version
        html = requests.get(url).text
        soup = BeautifulSoup(html, "html.parser")    
        logger.debug(f"tor-expert-bundle-{OS_NAME.lower()}")
        for link in soup.find_all("a"):
            if link.text.startswith(f"tor-expert-bundle-{OS_NAME.lower()}") and link.text.endswith(".gz"):
                
                if "i686" in link.text and ARCHITECTURE == 32:
                    links.append(link.text)
                    
                elif "x86_64" in link.text and ARCHITECTURE == 64:
                    links.append(link.text)
    except Exception as e:
        logger.error(f"error in get bundle links: {e}")
        
    return links


def sha256_file(filename):
    """Compute SHA256 hash of a local file"""
    create_bundle_dir()
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def save_checksum(file, version):
    file.seek(0)
    text = file.read()
    with open(resource_path(os.path.join(BUNDLE_DIR,f"{version}-{CHECKSUM_FILE}")), "w", encoding="utf-8") as f:
        f.write(text.decode())

def get_checksum(version, base_url=TOR_BUNDLE_BASE_URL,):
    file = io.BytesIO()
    version = version.replace("/", "")
    
    url = urljoin(base_url, f"{version}/{CHECKSUM_FILE}")
    with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=8192):
                file.write(chunk)
                    
    save_checksum(file, version)
    
def check_hash(filename, base_url=TOR_BUNDLE_BASE_URL, go_online=False):
    try:
        version = get_version_by_bundle(filename)
        if not os.path.exists(resource_path(os.path.join(BUNDLE_DIR,f"{version}-{CHECKSUM_FILE}"))):
            if go_online:
                
                file = io.BytesIO()
                url = urljoin(base_url, f"{version}/{CHECKSUM_FILE}")
                with requests.get(url, stream=True) as r:
                        for chunk in r.iter_content(chunk_size=8192):
                            file.write(chunk)
                file_hash = sha256_file(bundle_path(filename))
                file.seek(0)
                text = file.read().decode()
                save_checksum(file, version)
            else:
                return True
            
        else:
            with open(resource_path(os.path.join(BUNDLE_DIR,f"{version}-{CHECKSUM_FILE}")), "r") as f:
                
                text = f.read()
        for i in text.splitlines():
            hash, name = i.strip().split(None, 1)
            if name.strip() == filename:
                if hash.strip() == file_hash:
                    return True
    except Exception as e:
        logger.error(f"check hash: {e}")
    return False

def download_file(filename, version, base_url=TOR_BUNDLE_BASE_URL):
    create_bundle_dir()
    version = version if version.endswith("/") else version + "/"
    
    if os.path.exists(bundle_path(filename)):
        return 
    url = base_url + version + filename
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(bundle_path(filename), "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)
    logger.info(f"Downloaded {filename}")

def list_downloaded_bundles():
    return glob.glob(resource_path(BUNDLE_DIR)+"*.gz")

def get_version_by_bundle(filename, with_slash=False):
    return filename.replace(".tar.gz", "").rsplit("-", 1)[-1]

def check_bundle_compatibility(filename):
    name = os.path.splitext(os.path.basename(filename))[0]

    if ((ARCHITECTURE == 64 and "x86_64" in name) or (ARCHITECTURE == 32 and "i868" in name)) and OS_NAME.lower() in name and name.startswith("tor-expert-bundle-"):
        return True
    return False

def get_own_bundles():
    res = []
    for i in glob.glob(resource_path(BUNDLE_DIR)+"tor-expert-bundle*"):
        if os.path.isdir(i):
            res.append(i)
    return res    

def delete_bundle(name):
    name = name.replace(".tar.gz", "")
    
    try:
        shutil.rmtree(os.path.join(BUNDLE_DIR, name), ignore_errors=True)
    except Exception as e:
        logger.error(f"rmdir bundle failed: {e}")
    try:
        os.remove(os.path.join(BUNDLE_DIR, name+".tar.gz"))
    except Exception as e: 
        logger.error(f"remove bundle failed: {e}")

