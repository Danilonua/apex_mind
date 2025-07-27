from curses import raw
import os
import json
import logging
import sys
import requests
from urllib.parse import urlparse
from pathlib import Path

from .capability_manifest import CapabilityManifest
from apex_mind_core.common.types import HardwareOpType



try:
    from wasi_security_layer.wasi_security_layer import (
        create_wasi_context,
        HardwareOp as _RustHardwareOp,
        HardwareOpType as _RustHardwareOpType,
        safe_gpu_compute as _orig_safe_gpu_compute,
        read_sensor,
        validate_file_access,
        validate_gpu_access,
        validate_network_access
    )
except ImportError:
    from wasi_security_layer import (
        create_wasi_context,
        HardwareOp as _RustHardwareOp,
        HardwareOpType as _RustHardwareOpType,
        safe_gpu_compute as _orig_safe_gpu_compute,
        read_sensor,
        validate_file_access,
        validate_gpu_access,
        validate_network_access
    )

RUST_HARDWARE_OP_TYPES = [
    _RustHardwareOpType.GpuCompute,
    _RustHardwareOpType.FileRead,
    _RustHardwareOpType.FileWrite,
    _RustHardwareOpType.SensorRead,
    _RustHardwareOpType.NetworkRequest,
    _RustHardwareOpType.CameraCapture,
]

print("=== Rust HardwareOpType variants ===")
print([v.__class__.__name__ for v in RUST_HARDWARE_OP_TYPES])
print("=== Python HardwareOpType variants ===")
from apex_mind_core.common.types import HardwareOpType
print([v.name for v in HardwareOpType])

class HardwareOpWrapper:
    def __init__(self, rust_op, op_name):
        self._rust_op = rust_op
        self._op_name = op_name
        # Добавляем словарь для хранения дополнительных атрибутов
        self.extra_attributes = {}

    def __getattr__(self, name):
        # Сначала проверяем дополнительные атрибуты
        if name in self.extra_attributes:
            return self.extra_attributes[name]
        # Затем пробуем получить атрибут из Rust-объекта
        return getattr(self._rust_op, name)

    def __setattr__(self, name, value):
        if name in ['_rust_op', '_op_name', 'extra_attributes']:
            super().__setattr__(name, value)
        else:
            # Сохраняем в дополнительные атрибуты
            self.extra_attributes[name] = value

def HardwareOp(op_type, *args, **kwargs):
    if isinstance(op_type, HardwareOpType):
        name = op_type.name
        rust_variant = getattr(_RustHardwareOpType, name)
    else:
        name = getattr(op_type, "name", str(op_type)).split('.')[-1]
        rust_variant = op_type

    rust_obj = _RustHardwareOp(rust_variant, *args, **kwargs)
    return HardwareOpWrapper(rust_obj, name)

def safe_gpu_compute(shader_code: str, data: bytes) -> bytes:
    try:
        return _orig_safe_gpu_compute(shader_code, data)
    except RuntimeError:
        raise ImportError("GPU adapter unavailable")

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logger.addHandler(handler)


class FileOperations:
    """Модуль для работы с файловой системой"""
    def __init__(self, manifest: CapabilityManifest):
        self.manifest = manifest
        self.logger = logging.getLogger("FileOperations")

    def _check_permission(self, op: str, path: str):
        if not self.manifest.validate(op, path):
            raise PermissionError(f"{op.title()} access to {path} denied")
        

    def _check_permission(self, op: str, path: str) -> bool:
        """
        Проверка разрешения для операции с файлом
        Возвращает True если разрешено, False если запрещено
        """
        try:
            # Нормализация пути
            normalized_path = os.path.abspath(path).replace("\\", "/")
            
            # Проверка системных путей (Windows)
            if sys.platform == "win32":
                protected_paths = [
                    "C:/Windows/", 
                    "C:/Program Files/",
                    "C:/ProgramData/",
                    "C:/System32/"
                ]
                if any(normalized_path.startswith(p) for p in protected_paths):
                    return False
            
            # Проверка через манифест
            return self.manifest.validate(op, normalized_path)
            
        except Exception:
            return False

    def read_file(self, path: str) -> bytes:
        """Чтение файла с проверкой разрешений"""
        self._check_permission("read", path)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Path does not exist: {path}")

        self.logger.info(f"Reading file: {path}")
        with open(path, "rb") as f:
            return f.read()

    def write_file(self, path: str, data: bytes) -> int:
        """Запись в файл с проверкой разрешений"""
        self._check_permission("write", path)

        self.logger.info(f"Writing to file: {path}")
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as e:
            raise PermissionError(f"Cannot create directory for {path}: {e}")

        with open(path, "wb") as f:
            return f.write(data)

    def path_exists(self, path: str) -> bool:
        """Проверка существования пути с учётом прав чтения"""
        try:
            self._check_permission("read", path)
        except PermissionError:
            return False
        return os.path.exists(path)


class HTTPExecutor:
    """Модуль для выполнения HTTP запросов"""
    ALLOWED_METHODS = {"GET", "POST"}

    def __init__(self, manifest: CapabilityManifest):
        self.manifest = manifest
        self.logger = logging.getLogger("HTTPExecutor")
        self.session = requests.Session()

    def execute_request(self, method: str, url: str, data=None, headers=None) -> dict:
        """Выполнение HTTP запроса с проверкой разрешений"""
        if not self.manifest.network:
            raise PermissionError("Network access not allowed")

        method = method.upper()
        if method not in self.ALLOWED_METHODS:
            raise ValueError(f"Unsupported HTTP method: {method}")

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL: {url}")

        # Дополнительно: проверка разрешённого домена (если поддерживается manifest)
        if hasattr(self.manifest, "allowed_domains"):
            domain = parsed.netloc
            if domain not in self.manifest.allowed_domains:
                raise PermissionError(f"Domain not allowed: {domain}")

        self.logger.info(f"Executing {method} request to: {url}")

        try:
            response = self.session.request(
                method,
                url,
                data=data,
                headers=headers or {},
                timeout=10
            )
            return {
                "status_code": response.status_code,
                "content": response.text,
                "headers": dict(response.headers),
                "url": response.url
            }
        except requests.RequestException as e:
            self.logger.error(f"HTTP request failed: {e}")
            raise


class WASIGuard:
    def __init__(self, manifest_path: str):
        os.makedirs(os.path.dirname(manifest_path), exist_ok=True)

        if not os.path.exists(manifest_path):
            default = {
                "skill_name": "default",
                "filesystem": {"read": [], "write": [], "delete": []},
                "network": False,
                "gpu": False,
                "sensors": False,
                "camera": False
            }
            with open(manifest_path, "w") as f:
                json.dump(default, f)

        with open(manifest_path, "r") as f:
            man = json.load(f)

        # Normalize paths
        for op in ("read", "write", "delete"):
            man["filesystem"][op] = [
                p.replace("\\", "/")
                for p in man["filesystem"].get(op, [])
            ]
        with open(manifest_path, "w") as f:
            json.dump(man, f, indent=2)

        self._manifest_dict = man
        self.manifest = CapabilityManifest(man)
        self.file_ops = FileOperations(self.manifest)
        self.http_executor = HTTPExecutor(self.manifest)
        logger.debug(f"Loaded manifest: {json.dumps(man)}")

        if self.is_arm_environment():
            self.apply_arm_optimizations()

    def is_arm_environment(self):
        import platform
        m = platform.machine().lower()
        return "arm" in m or "aarch" in m

    def apply_arm_optimizations(self):
        logger.info("Applying ARM-specific optimizations")
        self._manifest_dict["filesystem"]["read"] = [
            p for p in self._manifest_dict["filesystem"]["read"]
            if "essential" in p
        ]
        self.manifest.filesystem["read"] = self._manifest_dict["filesystem"]["read"]
        self.manifest.gpu = False
        self._manifest_dict["gpu"] = False

    def __enter__(self):
        fs = self._manifest_dict.get("filesystem", {})
        read_dirs = [(p, p) for p in fs.get("read", [])]
        write_dirs = [(p, p) for p in fs.get("write", [])]
        logger.debug(f"Creating WASI context with read={read_dirs}, write={write_dirs}")
        create_wasi_context(read_dirs + write_dirs)
        return self

    def execute_op(self, operation: HardwareOp) -> any:
        op_name = operation._op_name
        logger.debug(f"Executing operation: {op_name}")

        if op_name == "FileRead":
            return self.file_ops.read_file(operation.path)
        if op_name == "FileWrite":
            return self.file_ops.write_file(operation.path, operation.data)
        if op_name == "NetworkRequest":
            # Получаем метод, данные и заголовки
            method = getattr(operation, "method", "GET") or "GET"
            data = getattr(operation, "data", None)
            headers = getattr(operation, "headers", {}) or {}
            
            result = self.http_executor.execute_request(
                method,
                operation.url,
                data=data,
                headers=headers,
            )
            return result["content"].encode()
        if op_name == "GpuCompute":
            if not self.manifest.gpu:
                raise PermissionError("GPU access not allowed")
            try:
                return safe_gpu_compute(operation.shader_code, operation.data)
            except ImportError:
                return operation.data
        if op_name == "SensorRead":
            if not self.manifest.sensors:
                raise PermissionError("Sensor access not allowed")
            return read_sensor(operation.sensor_type)
        if op_name == "CameraCapture":
            if not self.manifest.camera:
                raise PermissionError("Camera access not allowed")
            return b"Simulated image data"

        raise ValueError(f"Unsupported operation type: {op_name}")

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logger.error(f"WASIGuard exit with error: {exc_val}")


class ReptilianEngine:
    def __init__(self, skill_name: str):
        self.skill_name = skill_name
        # Используем переданное имя навыка для манифеста
        self.manifest_path = f"manifests/{skill_name}.json"
        
        # Если файла нет, создаем default манифест
        if not os.path.exists(self.manifest_path):
            default_manifest = {
                "skill_name": skill_name,
                "filesystem": {"read": [], "write": [], "delete": []},
                "network": True,  # Разрешаем сеть по умолчанию
                "gpu": False,
                "sensors": False,
                "camera": False
            }
            os.makedirs(os.path.dirname(self.manifest_path), exist_ok=True)
            with open(self.manifest_path, "w") as f:
                json.dump(default_manifest, f, indent=2)
        
        logger.info(f"Initialized ReptilianEngine for {skill_name}")
        self._wasi_guard = WASIGuard(self.manifest_path)
        self.file_ops = self._wasi_guard.file_ops
        self.http_executor = self._wasi_guard.http_executor

    def execute_hardware_op(self, operation: HardwareOp):
        # внутри guard возвращаются сырые bytes для NetworkRequest
        with self._wasi_guard as guard:
            raw = guard.execute_op(operation)

        # если это сетевой запрос — оборачиваем в «Response»-подобный объект
        if operation.op_type == HardwareOpType.NetworkRequest:
            # простая «импровизированная» обёртка
            class WasiResponse:
                def __init__(self, data: bytes):
                    # HTTP‑код, можно вынести в manifest, но по умолчанию 200
                    self.status_code = 200
                    # декодируем тело в строку
                    self.text = data.decode('utf-8', errors='replace')
            return WasiResponse(raw)

        # для всех остальных операций возвращаем результат «как есть»
        return raw
