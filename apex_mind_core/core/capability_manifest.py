import json
import os

class CapabilityManifest:
    def __init__(self, manifest_dict):
        self.skill_name = manifest_dict.get("skill_name", "default")
        self.filesystem = manifest_dict.get("filesystem", {"read": [], "write": [], "delete": []})
        self.network = manifest_dict.get("network", False)
        self.gpu = manifest_dict.get("gpu", False)
        self.sensors = manifest_dict.get("sensors", False)  # Добавить
        self.camera = manifest_dict.get("camera", False)    # Добавить

    @classmethod
    def loads(cls, s):
        return cls(json.loads(s))
    
    def validate(self, operation: str, path: str) -> bool:
        """Проверяет разрешен ли доступ к пути"""
        path = os.path.abspath(path.replace("\\", "/"))
        for allowed_path in self.filesystem[operation]:
            # Нормализуем и сравниваем абсолютные пути
            abs_allowed = os.path.abspath(allowed_path.replace("\\", "/"))
            if os.path.commonpath([abs_allowed, path]) == abs_allowed:
                return True
        return False