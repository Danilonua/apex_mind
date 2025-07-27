use pyo3::prelude::*;
use std::time::{SystemTime, UNIX_EPOCH};

// Добавить pub к функции
#[pyfunction]
pub fn read_sensor(sensor_type: &str) -> PyResult<f64> {
    match sensor_type {
        "temperature" => Ok(23.5),
        "humidity" => Ok(45.0),
        "timestamp" => Ok(SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .map_err(|_| PyErr::new::<pyo3::exceptions::PyRuntimeError, _>("Time error"))?
            .as_secs_f64()),
        _ => Err(PyErr::new::<pyo3::exceptions::PyValueError, _>(
            "Unsupported sensor type",
        )),
    }
}