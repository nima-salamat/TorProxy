import os
import sys
import tarfile
import logging

logger = logging.getLogger(__name__)

def resource_path(relative_path):
    if getattr(sys, "_MEIPASS", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)

def extract_tar_gz_file(filename, dst):
    try:
        tar = tarfile.open(filename, "r:gz")
        tar.extractall(dst)
        tar.close()
    except Exception as e:
        logger.error(f"Extract failed: {e}")