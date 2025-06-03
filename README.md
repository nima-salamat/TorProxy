# TorProxy
**TorProxy** is a lightweight Python-based proxy server that integrates the Tor network to route your internet traffic, enhancing privacy and helping to bypass censorship. Notably, it includes the `tor.exe` executable, allowing the Tor service to run without requiring a separate installation.

## 🚀 Features

* **Integrated Tor Executable**: Bundles `tor.exe` to run the Tor service directly.
* **Python-Based Proxy Server**: Handles proxy connections through a simple Python script.
* **User Interface**: Includes a basic UI (`ui.py`) for running the proxy.
* **Modular Design**: Structured with separate modules for Tor connection (`tor.py`), proxy handling (`proxy.py`), and initialization (`__init__.py`).

## 🛠 Installation

1. **Clone the Repository**:

   ```bash
   git clone https://github.com/nima-salamat/TorProxy.git
   cd TorProxy
   ```


## ⚙️ Usage

1. **Start the Proxy**:

   ```bash
   python ui.py
   ```

## 📁 Project Structure

* `Tor/`: Contains the `tor.exe` executable and related files.
* `tor.py`: Handles connections to the Tor network.
* `proxy.py`: Manages the proxy server functionality.
* `ui.py`: Provides a user interface for easier control.
* `__init__.py`: Initializes the Python package.

## 📝 Notes

* Ensure that `tor.exe` has the necessary permissions to run on your system.
* Modify configurations in `tor.py` and `proxy.py` as needed to suit your requirements.
