
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QPushButton, QMessageBox, QLabel, QHBoxLayout
from PySide6.QtCore import QThreadPool
from ui_.worker.worker import Worker
from updater import get_tor_versions, get_bundle_links, get_version_by_bundle, download_file, list_downloaded_bundles, delete_bundle
from updater import get_own_bundles, check_bundle_compatibility, delete_bundle
from config import CONFIG
from config import BUNDLE_DIR
from utils import extract_tar_gz_file, resource_path
import json
import os
import logging

logger = logging.getLogger()

class UpdaterWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_ = parent
        
        main_layout = QHBoxLayout()
        self.setLayout(main_layout)
        
        left_layout = QVBoxLayout()
        main_layout.addLayout(left_layout)
        
        
        self.btn_get_versions = QPushButton("get versions")
        self.btn_get_versions.clicked.connect(self.get_available_versions)
        left_layout.addWidget(self.btn_get_versions)
        
        self.updates_list = QListWidget()
        self.updates_list.itemClicked.connect(self.selected_version)
        left_layout.addWidget(self.updates_list)
        
        self.lbl_status = QLabel()
        left_layout.addWidget(self.lbl_status)
       
        self.thread_pool = QThreadPool()
        
    
        right_layout = QVBoxLayout()
        main_layout.addLayout(right_layout)
        
        self.btn_refresh_version = QPushButton("refresh")
        self.btn_refresh_version.clicked.connect(self.refresh_version)
        right_layout.addWidget(self.btn_refresh_version)

        self.list_tor_versions = QListWidget()
        right_layout.addWidget(self.list_tor_versions)
        
        self.btn_set_default_version = QPushButton("set default version")
        self.btn_set_default_version.clicked.connect(self.set_default_version)
        right_layout.addWidget(self.btn_set_default_version)
        
        self.btn_delete_version = QPushButton("delete version")
        self.btn_delete_version.clicked.connect(self.delete_version)
        right_layout.addWidget(self.btn_delete_version)
    
    def refresh_version(self):
        self.list_tor_versions.clear()
        print(get_own_bundles())
        for i in get_own_bundles():
            if check_bundle_compatibility(i):
                self.list_tor_versions.addItem(i)
                
    def set_default_version(self):
        if items:=self.list_tor_versions.selectedItems():
            item = items[0]
            reply = QMessageBox.question(self, 
                                        "Download", 
                                        f"Do you want set default tor?\n{item.text()}",
                                        QMessageBox.Yes| QMessageBox.No, 
                                        QMessageBox.No)
            if reply == QMessageBox.No:
                return
            
            CONFIG["tor_path"] = item.text()
            self.refresh_version()            
            

            
    def delete_version(self):
        if items:=self.list_tor_versions.selectedItems():
            item = items[0]
            reply = QMessageBox.question(self, 
                                        "Download", 
                                        f"Do you want to download?\n{item.text()}",
                                        QMessageBox.Yes| QMessageBox.No, 
                                        QMessageBox.No)
            if reply == QMessageBox.No:
                return
        delete_bundle(item.text())
        self.refresh_version()            
        
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
            logger.info(f"Downloading {bundle}")
            self.lbl_status.setText(f"Downloading {bundle}")
            
            download_file(bundle, version)
            base_path = os.path.join(BUNDLE_DIR, os.path.basename(bundle).replace(".tar.gz", ""))
            extract_tar_gz_file(resource_path(os.path.join(BUNDLE_DIR, bundle)), base_path)
            
        except Exception as e:
            self.lbl_status.setText(f"Download  {bundle} ended with error")
            delete_bundle(bundle)
            logger.info(f"Download {bundle} ended with error and removed. error {e}")
            
        self.lbl_status.setText(f"Download {bundle} ended.")
        self.updates_list.setEnabled(True)
        

