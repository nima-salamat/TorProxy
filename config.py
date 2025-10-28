import os
from tor import resource_path
import json


class Config:
    file_config = "config.json"
    default_data = {"bridges": "", "bridge":False, "mode": "dark"}
    data = {"bridges": "", "bridge":False, "mode": "dark"}
    
    def __getitem__(self, name):
        if name in self.default_data:
            return self.data.get(name, None) or self.default_data[name]
        return None
    
    def __setitem__(self, name, value):
        self.data[name] = value
        self.save()
        
    def __getattr__(self, name):
        if name in ["bridges", "bridge", "mode"]:
            return self[name]
        return super().__getattr__(name)
    
    def __setattr__(self, name, value):
        if name in ["bridges", "bridge", "mode"]:
            self[name] = value
            return
        super().__setattr__(name, value)        
        
    @staticmethod
    def create_if_is_not_exits(fun):
        def inner_function(*args, **kwargs):
            
            file_path = resource_path(Config.file_config)
            if not os.path.exists(file_path):
                open(file_path, "w").close()
                
            return fun(*args, **kwargs)
            
        return inner_function    
    
    def save_config(self, data):
        with open(resource_path(Config.file_config), "w") as file:
            file.write(data)

    @create_if_is_not_exits
    def get_config(self):
        with open(resource_path(Config.file_config), "r") as file:
            return file.read()
    
    def json_format(self, data):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return self.default_data

    def json_to_text(self, data):
        return json.dumps(data)
        
    
    def load(self):
        data = self.get_config()
        self.data = self.json_format(data)
        return self.data

    def save(self):
        data = self.json_to_text(self.data)
        self.save_config(data)

CONFIG = Config()
