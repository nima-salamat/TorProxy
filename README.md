# TorProxy

Repository: [https://github.com/nima-salamat/TorProxy](https://github.com/nima-salamat/TorProxy)

**TorProxy** is a small Python proxy that routes traffic through the Tor network. The repository includes a bundled Tor binary (Windows) so you can run Tor without installing it separately.

## What it does

* Provides a local HTTP proxy that forwards traffic via Tor.
* A GUI (implemented with PySide6 + QDarkStyle) is the primary control interface.
* **Running `main.py` launches the GUI**, and from the GUI you start/stop Tor and the local proxy.

## Clone

To clone the repository into a local folder named `TorProxy`, run:

```bash
git clone https://github.com/nima-salamat/TorProxy.git TorProxy
cd TorProxy
```

## Requirements

Make sure these packages are available (listed in `requirements.txt`):

* PySide6
* QDarkStyle
* stem
* PySocks
* opencv-python
* numpy
* pyzbar (may require system `zbar`)
* keyboard

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

## Run

1. Launch the GUI (single command):

```bash
python main.py
```

2. In the GUI, press the Start/Run button to launch Tor and the local HTTP proxy. Use the GUI to stop services when finished.

*Do not run other scripts directly unless you know what you are doing — the GUI manages service lifecycle.*

## Files you should know

* `main.py` — launches the GUI (primary entry point).
* `ui.py` — GUI code (can be used for development/testing).
* `proxy.py` — proxy server implementation.
* `tor.py` — Tor controller/launcher (uses `tor_bundle/` when present).
* `set_proxy.py` — sets the Windows system HTTP proxy when requested.
* `config.json` / `config.py` — runtime settings.
* `blocked_hosts.json` — domains/IPs to block.
* `tor_bundle/` — bundled Tor binaries and data (Windows).

## Notes

* Keep it simple: `python main.py` opens the GUI; start the services from there.
* Check `tor_log.txt` for Tor runtime logs.
* Verify permissions before distributing any bundled binaries.

---

If you want the README even shorter or to add a small `config.json` example, tell me and I’ll update it.
