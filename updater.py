import requests
from bs4 import BeautifulSoup
from config import TOR_BUNDLE_BASE_URL, OS_NAME, ARCHITECTURE, BUNDLE_DIR
import io
import hashlib
import os
import glob
from utils import resource_path, extract_tar_gz_file
import logging

logger = logging.getLogger(__name__)

def bundle_path(filename):
    return resource_path(os.path.join(BUNDLE_DIR, filename))

def create_bundle_dir():
    os.makedirs(BUNDLE_DIR ,exist_ok=True)
    
def get_tor_versions(url=TOR_BUNDLE_BASE_URL):
    links = []
    html = requests.get(url).text
    soup = BeautifulSoup(html, "html.parser")    
    for link in soup.find_all("a"):
        if link.text.endswith("/"):
            links.append(link.text)
    return links


def get_bundle_links(version, base_url=TOR_BUNDLE_BASE_URL):
    links = []
    version = version if version.endswith("/") else version + "/"
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
    return links



def sha256_file(filename):
    """Compute SHA256 hash of a local file"""
    create_bundle_dir()
    h = hashlib.sha256()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def check_hash(filename, version, base_url=TOR_BUNDLE_BASE_URL):
    file = io.BytesIO()
    url = base_url + version + "sha256sums.txt"
    with requests.get(url, stream=True) as r:
            for chunk in r.iter_content(chunk_size=8192):
                file.write(chunk)
    file_hash = sha256_file(bundle_path(filename))
    file.seek(0)
    text = file.read().decode()
    for i in text.splitlines():
        hash, name = i.strip().split(None, 1)
        if name.strip() == filename:
            if hash.strip() == file_hash:
                return True
    return False

    
def download_file(filename, version, base_url=TOR_BUNDLE_BASE_URL):
    create_bundle_dir()
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
    return filename.rsplit("-", 1)[1].rsplit(".",2)[0] + ("/" if with_slash else "")

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


# filename = list_downloaded_bundles()[0]
# dst = os.path.join(BUNDLE_DIR,filename.rsplit("\\",1)[-1].split("tar.gz")[0])
# print(filename, dst)
# extract_tar_gz_file(filename, dst)

# print(get_version_by_bundle(list_downloaded_bundles()[0], with_slash=True))
# versions = get_tor_versions()
# print("v:", versions)
# bundles = get_bundle_links(versions[0])
# print("b:", bundles)

# download_file(bundles[0], versions[0])
# print("check:", check_hash(bundles[0], versions[0]))

