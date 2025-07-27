use pyo3::prelude::*;
use crate::capability::CapabilityManifest;
use serde_json;

#[pyfunction]
pub fn validate_file_access(path: &str, manifest_json: &str) -> PyResult<bool> {
    let manifest: CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    // Используем только нормализацию без проверки существования пути
    let normalized_path = CapabilityManifest::normalize_path(path);
    
    if normalized_path.contains("..") {
        return Ok(false);
    }
    
    let operation = if normalized_path.ends_with(".tmp") || normalized_path.contains("/temp/") {
        "write"
    } else {
        "read"
    };
    
    Ok(manifest.validate(operation, &normalized_path))
}

#[pyfunction]
pub fn validate_gpu_access(manifest_json: &str) -> PyResult<bool> {
    let manifest: CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(manifest.gpu)
}

#[pyfunction]
pub fn validate_network_access(manifest_json: &str) -> PyResult<bool> {
    let manifest: CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(manifest.network)
}

#[pyfunction]
pub fn validate_sensor_access(manifest_json: &str) -> PyResult<bool> {
    let manifest: CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(manifest.sensors)
}

#[pyfunction]
pub fn validate_camera_access(manifest_json: &str) -> PyResult<bool> {
    let manifest: CapabilityManifest = serde_json::from_str(manifest_json)
        .map_err(|e| PyErr::new::<pyo3::exceptions::PyValueError, _>(e.to_string()))?;
    
    Ok(manifest.camera)
}