import json
import os
from wasi_security import create_wasi_context, CapabilityManifest

class WASIGuard:
    def __init__(self, manifest_path: str):
        self.manifest_path = manifest_path
        with open(manifest_path) as f:
            self.manifest_data = f.read()
            self.manifest_dict = json.loads(self.manifest_data)
    
    def __enter__(self):
        # Подготовка путей для WASI
        read_dirs = [(p, os.path.abspath(p)) for p in self.manifest_dict["filesystem"]["read"]]
        write_dirs = [(p, os.path.abspath(p)) for p in self.manifest_dict["filesystem"]["write"]]
        create_wasi_context(read_dirs + write_dirs)
        return self
    
    def validate_operation(self, operation: str, path: str) -> bool:
        # Используем класс CapabilityManifest как в инструкции
        manifest = CapabilityManifest(self.manifest_data)
        return manifest.validate(operation, os.path.abspath(path))
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
