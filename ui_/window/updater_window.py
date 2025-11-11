
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel
from PySide6.QtCore import QThreadPool
from ui_.worker.worker import Worker
from updater import get_tor_versions, get_bundle_links, get_version_by_bundle, download_file, list_downloaded_bundles, delete_bundle
from config import BUNDLE_DIR
from utils import extract_tar_gz_file, resource_path
import json
import os

class UpdaterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ = parent
        
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)
        
        
        self.btn_get_versions = QPushButton("get versions")
        self.btn_get_versions.clicked.connect(self.get_available_versions)
        main_layout.addWidget(self.btn_get_versions)
        
        self.updates_list = QListWidget()
        self.updates_list.itemClicked.connect(self.selected_version)
        main_layout.addWidget(self.updates_list)
       
        self.thread_pool = QThreadPool()
        
    def get_available_versions(self):
        self.btn_get_versions.setDisabled(True)
        self.worker = Worker(get_tor_versions)
        self.worker.signals.finished.connect(self.set_tor_versions)
        self.thread_pool.start(self.worker)
        
    def set_tor_versions(self, data):
        
        try:
            data = json.loads(data.replace("'", "\""))
        except json.JSONDecodeError:
            data = []
        
        
        self.worker = Worker(self.get_download_links, data)
        self.worker.signals.finished.connect(self.set_download_links)
        self.thread_pool.start(self.worker)
        
        
    
    def get_download_links(self, data):        
        lst = []
        
        for i in data:
            lst.extend(get_bundle_links(i))
        return lst
    
    def set_download_links(self, data):
        
        try:
            data = json.loads(data.replace("'", "\""))
        except json.JSONDecodeError:
            data = [] 
        
        self.updates_list.clear()
        
        downloaded_bundles = list_downloaded_bundles()
        downloaded_bundles = list(map(lambda x: os.path.basename(x), downloaded_bundles))
        print(downloaded_bundles)
        for i in data:
            if i not in downloaded_bundles:
                self.updates_list.addItem(i)
        
        self.btn_get_versions.setDisabled(False)
        

    
    def selected_version(self, item):
        reply = QMessageBox.question(self, 
                                     "Download", 
                                     f"Do you want to download?\n{item.text()}",
                                     QMessageBox.Yes| QMessageBox.No, 
                                     QMessageBox.No)
        if reply == QMessageBox.No:
            return
        self.updates_list.setEnabled(False)
        bundle = item.text()
        version = get_version_by_bundle(bundle)
        self.worker = Worker(self.download_bundle, bundle , version)
        self.thread_pool.start(self.worker)
    
    def download_bundle(self, bundle, version):
        try:
            print("download started . . . . ")
            
            download_file(bundle, version)
            base_path = os.path.join(BUNDLE_DIR, os.path.basename(bundle).replace(".tar.gz", ""))
            extract_tar_gz_file(resource_path(os.path.join(BUNDLE_DIR, bundle)), base_path)
            
        except Exception as e:
            print("download ended with error", e)
            
            delete_bundle(bundle)
        print("download ended . . . . ")
        self.updates_list.setEnabled(True)
        
