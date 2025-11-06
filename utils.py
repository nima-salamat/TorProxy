import os
import sys

def resource_path(relative_path):
    if getattr(sys, "_MEIPASS", False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, relative_path)