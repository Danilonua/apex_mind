class CapabilityRegistry:
    def __init__(self):
        self.capabilities = {
            "WebSearch": {"network": True, "risk_level": 1, "paths": []},
            "FileRead": {"filesystem": True, "risk_level": 2, "paths": ["/workspace/read/*"]}
        }
    
    def check_capability(self, skill_name: str, path: str = "") -> bool:
        if skill_name not in self.capabilities:
            return False
            
        caps = self.capabilities[skill_name]
        if "paths" in caps and path:
            # Поддерживаем wildcard '*' и относительные пути
            for allowed in caps["paths"]:
                if allowed.endswith("*"):
                    prefix = allowed[:-1]
                    # разрешаем и "/workspace/read/" и "workspace/read/"
                    if path.startswith(prefix) or path.startswith(prefix.lstrip("/")):
                        return True
                else:
                    # точное совпадение с учетом возможного отсутствия ведущего '/'
                    if path == allowed or (allowed.startswith("/") and path == allowed.lstrip("/")):
                        return True
            return False
            
        return True

# WASI-compatible permission check
def wasi_validate(skill_name: str, operation: str, path: str) -> bool:
    # Actual WASI validation will be implemented in Phase 1.2
    return True if operation == "read" else False
