use pyo3::prelude::*;
use std::fs;
use std::collections::HashMap;
use crate::capability::CapabilityManifest;  // Исправлен импорт
use serde_json;

#[pyfunction]
pub fn update_manifest(skill_name: &str, new_permissions: HashMap<String, bool>) -> PyResult<()> {
    let manifest_path = format!("manifests/{}.json", skill_name);
    let mut manifest: CapabilityManifest = serde_json::from_str(
        &fs::read_to_string(&manifest_path)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    for (key, value) in new_permissions {
        match key.as_str() {
            "network" => manifest.network = value,
            "gpu" => manifest.gpu = value,
            "sensors" => manifest.sensors = value,
            "camera" => manifest.camera = value,
            _ => {} // ignore unknown keys
        }
    }
    
    fs::write(
        &manifest_path,
        serde_json::to_string_pretty(&manifest)
            .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?
    ).map_err(|e| PyErr::new::<pyo3::exceptions::PyIOError, _>(e.to_string()))?;
    
    Ok(())
}