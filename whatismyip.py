
from doctest import Example
import requests

def check_connectivity(timeout=5):
    try:
        requests.head("https://www.google.com", timeout=timeout)
        print("heeeey")
        return True
    except requests.RequestException:
        print("hey")
        return False
    except Exception as e:
        print(e)


def what_is_my_ip(proxy=None, timeout=10):
    url = "https://api.ipify.org?format=json"
    proxies = None

    if proxy:
        proxies = {
            "http": proxy,
            "https": proxy,
        }

    try:
        r = requests.get(url, proxies=proxies, timeout=timeout)
        r.raise_for_status()
        return r.json().get("ip")
    except requests.RequestException as e:
        raise Exception(f"Error: {e}")
