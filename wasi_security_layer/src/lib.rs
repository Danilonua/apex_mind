#![forbid(unsafe_code)]
use wasmtime::{Engine, Store};
use wasmtime_wasi::preview1::WasiP1Ctx;
use wasmtime_wasi::p2::WasiCtxBuilder;
use wasmtime_wasi::{DirPerms, FilePerms};
use pyo3::prelude::*;
use pyo3::wrap_pyfunction;
use sensor_virtualization::read_sensor;
use security_integration::{
    validate_file_access, 
    validate_gpu_access, 
    validate_network_access,
    validate_sensor_access,
    validate_camera_access
};
use manifest_updater::update_manifest;

mod capability;
mod gpu_virtualization;
mod security_integration;
mod manifest_updater;
mod sensor_virtualization;

use capability::CapabilityManifest as RustCapabilityManifest;
pub use gpu_virtualization::safe_gpu_compute;

#[pyfunction]
fn create_wasi_context(allowed_dirs: Vec<(String, String)>) -> PyResult<()> {
    let mut builder = WasiCtxBuilder::new();
    for (host, guest) in allowed_dirs {
        builder.preopened_dir(&host, &guest, DirPerms::all(), FilePerms::all());
    }
    let wasi_ctx: WasiP1Ctx = builder.build_p1();
    let engine = Engine::default();
    let _store = Store::new(&engine, wasi_ctx);
    Ok(())
}

#[pyclass(name = "CapabilityManifest")]
struct PyCapabilityManifest {
    inner: RustCapabilityManifest,
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

#[pyclass]
#[derive(Clone)]
pub enum HardwareOpType {
    GpuCompute,
    FileRead,
    FileWrite,
    SensorRead,
    NetworkRequest,
    CameraCapture,
}

#[pyclass]
pub struct HardwareOp {
    #[pyo3(get)]
    pub op_type: HardwareOpType,
    #[pyo3(get)]
    pub shader_code: Option<String>,
    #[pyo3(get)]
    pub data: Option<Vec<u8>>,
    #[pyo3(get)]
    pub path: Option<String>,
    #[pyo3(get, set)]
    pub url: Option<String>,
    #[pyo3(get, set)]
    pub sensor_type: Option<String>,
    #[pyo3(get, set)]
    pub method: Option<String>,
}

#[pymethods]
impl HardwareOp {
    #[new]
    fn new(op_type: HardwareOpType) -> Self {
        HardwareOp {
            op_type,
            shader_code: None,
            data: None,
            path: None,
            url: None,
            sensor_type: None,
            method: Some("GET".to_string()),
        }
    }

    #[setter] fn set_shader_code(&mut self, code: String) { self.shader_code = Some(code); }
    #[setter] fn set_data(&mut self, data: Vec<u8>)      { self.data = Some(data); }
    #[setter] fn set_path(&mut self, path: String)      { self.path = Some(path.replace('\\', "/")); }
    #[setter] fn set_url(&mut self, url: String)        { self.url = Some(url); }
    #[setter] fn set_sensor_type(&mut self, st: String) { self.sensor_type = Some(st); }
    #[setter] fn set_method(&mut self, m: String)       { self.method = Some(m); }
}

#[pymodule]
fn wasi_security_layer(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    // Функции
    m.add_function(wrap_pyfunction!(create_wasi_context, m)?)?;
    m.add_function(wrap_pyfunction!(safe_gpu_compute, m)?)?;
    m.add_function(wrap_pyfunction!(read_sensor, m)?)?;
    m.add_function(wrap_pyfunction!(validate_file_access, m)?)?;
    m.add_function(wrap_pyfunction!(validate_gpu_access, m)?)?;
    m.add_function(wrap_pyfunction!(validate_network_access, m)?)?;
    m.add_function(wrap_pyfunction!(validate_sensor_access, m)?)?;
    m.add_function(wrap_pyfunction!(validate_camera_access, m)?)?;
    m.add_function(wrap_pyfunction!(update_manifest, m)?)?;

    // Классы
    m.add_class::<PyCapabilityManifest>()?;
    m.add_class::<HardwareOp>()?;
    m.add_class::<HardwareOpType>()?;
    Ok(())
}