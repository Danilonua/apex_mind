#!/usr/bin/env bash
# Исправленный скрипт для автоматизации Day 2: Capability Manifest System
set -euo pipefail

echo "==> Шаг 1: Создание файла src/capability.rs"
mkdir -p src
cat > src/capability.rs << 'EOL'
use serde::{Deserialize, Serialize};
use std::path::Path;

#[derive(Debug, Serialize, Deserialize)]
pub struct CapabilityManifest {
    pub skill_name: String,
    pub filesystem: FSAccess,
    pub network: bool,
    pub gpu: bool,
}

#[derive(Debug, Serialize, Deserialize)]
pub struct FSAccess {
    pub read: Vec<String>,
    pub write: Vec<String>,
    pub delete: Vec<String>,
}

impl CapabilityManifest {
    pub fn validate(&self, operation: &str, path: &str) -> bool {
        let path = Path::new(path);
        let normalized_path = match path.canonicalize() {
            Ok(p) => p.to_string_lossy().to_string(),
            Err(_) => path.to_string_lossy().to_string(),
        };
        
        match operation {
            "read" => self.filesystem.read.iter().any(|p| normalized_path.starts_with(p)),
            "write" => self.filesystem.write.iter().any(|p| normalized_path.starts_with(p)),
            "delete" => self.filesystem.delete.iter().any(|p| normalized_path.starts_with(p)),
            _ => false,
        }
    }
}
EOL

echo "==> Шаг 2: Обновление зависимостей в Cargo.toml"
# Безопасное добавление зависимостей
if ! grep -q "serde =" Cargo.toml; then
  cat >> Cargo.toml << 'EOL'
serde = { version = "1.0", features = ["derive"] }
serde_json = "1.0"
EOL
fi

echo "==> Шаг 3: Интеграция модуля в src/lib.rs"
# Очищаем предыдущие объявления
grep -v "mod capability;" src/lib.rs | grep -v "use capability::CapabilityManifest;" > src/lib.rs.tmp
mv src/lib.rs.tmp src/lib.rs
echo "mod capability;" >> src/lib.rs

echo "==> Шаг 4: Добавление тестов в src/capability.rs"
cat >> src/capability.rs << 'EOL'
#[cfg(test)]
mod tests {
    use super::*;
    use std::env;

    #[test]
    fn test_manifest_validation() {
        let cwd = env::current_dir().unwrap();
        let cwd_str = cwd.to_string_lossy().to_string();

        let manifest = CapabilityManifest {
            skill_name: "TestSkill".to_string(),
            filesystem: FSAccess {
                read: vec!["/allowed/read".to_string(), cwd_str.clone()],
                write: vec!["/allowed/write".to_string()],
                delete: vec![],
            },
            network: false,
            gpu: false,
        };

        // Абсолютные пути
        assert!(manifest.validate("read", "/allowed/read/file.txt"));
        assert!(manifest.validate("write", "/allowed/write/data.log"));
        assert!(!manifest.validate("read", "/forbidden/file.txt"));
        assert!(!manifest.validate("delete", "/allowed/read/temp.txt"));
        
        // Относительные пути
        let test_path = cwd.join("test.txt");
        assert!(manifest.validate("read", &test_path.to_string_lossy()));
    }
}
EOL

echo "==> Шаг 5: Компиляция и тестирование Rust"
cargo build
cargo test --lib || { echo "Тесты не прошли!"; exit 1; }

echo "==> Шаг 6: Создание примера JSON манифеста"
mkdir -p manifests
cat > manifests/test_skill.json << 'EOL'
{
    "skill_name": "WebSearch",
    "filesystem": {
        "read": ["/tmp", "/data/inputs", "."],
        "write": ["/tmp/outputs"],
        "delete": []
    },
    "network": true,
    "gpu": false
}
EOL

echo "==> Шаг 7: Создание core/wasi_bridge.py"
mkdir -p core
cat > core/wasi_bridge.py << 'EOL'
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
EOL

echo "==> Шаг 8: Полная замена src/lib.rs"
cat > src/lib.rs << 'EOL'
use wasmtime::{Engine, Store};
use wasmtime_wasi::{WasiCtx, WasiCtxBuilder};
use cap_std::fs::Dir;
use ambient_authority::ambient_authority;
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use pyo3::Bound;
use std::path::Path;

mod capability;

#[pyfunction]
fn create_wasi_context(allowed_dirs: Vec<(String, String)>) -> PyResult<()> {
    let mut builder = WasiCtxBuilder::new();

    for (host, guest) in allowed_dirs {
        let dir = Dir::open_ambient_dir(
            Path::new(&host),
            ambient_authority(),
        ).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;

        builder.preopened_dir(dir, guest)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    }

    let wasi_ctx: WasiCtx = builder.build();
    let engine = Engine::default();
    let _store = Store::new(&engine, wasi_ctx);

    Ok(())
}

#[pyfunction]
fn validate_manifest(manifest_json: &str, operation: &str, path: &str) -> PyResult<bool> {
    let manifest: crate::capability::CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    Ok(manifest.validate(operation, path))
}

#[pyclass(name = "CapabilityManifest")]
struct PyCapabilityManifest {
    inner: crate::capability::CapabilityManifest,
}

#[pymethods]
impl PyCapabilityManifest {
    #[new]
    fn new(manifest_json: &str) -> PyResult<Self> {
        let inner = serde_json::from_str(manifest_json)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
        Ok(Self { inner })
    }

    fn validate(&self, operation: &str, path: &str) -> bool {
        self.inner.validate(operation, path)
    }
}

#[pymodule]
fn wasi_security(_py: Python, m: &Bound<'_, PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(create_wasi_context, m)?)?;
    m.add_function(wrap_pyfunction!(validate_manifest, m)?)?;
    m.add_class::<PyCapabilityManifest>()?;
    Ok(())
}
EOL

echo "==> Шаг 9: Проверка Python-интерфейса"
maturin develop || { echo "Ошибка сборки!"; exit 1; }

# Используем явный путь к Python в виртуальном окружении
PYTHON_EXECUTABLE="./.venv/Scripts/python"

cat > test_manifest.py << 'EOL'
import os
from wasi_security import CapabilityManifest

# Тест с абсолютными путями
manifest = CapabilityManifest(r'''{
    "skill_name": "Test",
    "filesystem": {
        "read": ["/data", "/tmp", "."],
        "write": ["/output"],
        "delete": []
    },
    "network": true,
    "gpu": false
}''')

print("Должно быть True:", manifest.validate("read", "/data/file.txt"))
print("Должно быть False:", manifest.validate("write", "/secret/passwd"))

# Тест с относительными путями
cwd = os.getcwd()
test_file = os.path.join(cwd, "test.txt")
print("Должно быть True:", manifest.validate("read", test_file))
EOL

# Используем Python из виртуального окружения
"$PYTHON_EXECUTABLE" test_manifest.py || { echo "Python тесты не прошли!"; exit 1; }

echo "==> Шаг 10: Фиксация изменений"
git add . && git commit -m "Day 2: Capability Manifest System Complete" || echo "Пропуск коммита"

echo "
SUCCESS: Все задачи Day 2 выполнены!"