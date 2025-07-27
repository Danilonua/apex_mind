use wgpu::{util::DeviceExt, ShaderModuleDescriptor};
use pyo3::{prelude::*, types::PyBytes};
use futures::channel::oneshot;
use pollster;

// Функция оптимизации шейдеров для ARM архитектуры
#[cfg(target_arch = "arm")]
fn optimize_for_arm(shader: &str) -> String {
    // Упрощаем шейдеры для Mali GPU
    shader
        .replace("workgroup_size(64)", "workgroup_size(16)")
        .replace("var<workgroup>", "var<uniform>")
        .replace("storage_buffer", "uniform")
}

#[pyfunction]
pub fn safe_gpu_compute<'a>(py: Python<'a>, shader_code: &str, input: Vec<u8>) -> PyResult<Bound<'a, PyBytes>> {
    // Применяем оптимизацию шейдера только для ARM архитектуры
    #[cfg(target_arch = "arm")]
    let shader_code = optimize_for_arm(shader_code);
    
    let result = pollster::block_on(execute_gpu_task(&shader_code, input));
    
    match result {
        Ok(data) => Ok(PyBytes::new_bound(py, &data)),
        Err(e) => Err(PyErr::new::<pyo3::exceptions::PyRuntimeError, _>(e)),
    }
}

async fn execute_gpu_task(shader_code: &str, input: Vec<u8>) -> Result<Vec<u8>, String> {
    const ALIGNMENT: u64 = 4; // Требование WebGPU к выравниванию

    // Выравниваем размер данных
    let aligned_size = if input.len() as u64 % ALIGNMENT == 0 {
        input.len() as u64
    } else {
        ((input.len() as u64 / ALIGNMENT) + 1) * ALIGNMENT
    };

    // Создаем выровненный буфер с нулевым заполнением
    let mut aligned_input = input.clone();
    aligned_input.resize(aligned_size as usize, 0);

    let instance = wgpu::Instance::default();
    let adapter = instance
        .request_adapter(&wgpu::RequestAdapterOptions::default())
        .await
        .ok_or("Failed to get adapter")?;

    let (device, queue) = adapter
        .request_device(
            &wgpu::DeviceDescriptor {
                required_features: wgpu::Features::empty(),
                required_limits: wgpu::Limits::downlevel_defaults(),
                label: None,
            },
            None,
        )
        .await
        .map_err(|e| e.to_string())?;

    // Компиляция шейдера
    let shader_module = device.create_shader_module(ShaderModuleDescriptor {
        label: Some("Compute Shader"),
        source: wgpu::ShaderSource::Wgsl(shader_code.into()),
    });

    // Создание буферов
    let _input_buffer = device.create_buffer_init(&wgpu::util::BufferInitDescriptor {
        label: Some("Input Buffer"),
        contents: &aligned_input,
        usage: wgpu::BufferUsages::STORAGE,
    });

    let output_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Output Buffer"),
        size: aligned_size,
        usage: wgpu::BufferUsages::STORAGE | wgpu::BufferUsages::COPY_SRC,
        mapped_at_creation: false,
    });

    // Создание вычислительного конвейера
    let compute_pipeline = device.create_compute_pipeline(&wgpu::ComputePipelineDescriptor {
        label: None,
        layout: None,
        module: &shader_module,
        entry_point: "main",
    });

    // Выполнение вычислений
    let mut encoder = device.create_command_encoder(&wgpu::CommandEncoderDescriptor { label: None });
    {
        let mut cpass = encoder.begin_compute_pass(&wgpu::ComputePassDescriptor {
            label: None,
            timestamp_writes: None,
        });
        cpass.set_pipeline(&compute_pipeline);
        cpass.dispatch_workgroups(1, 1, 1);
    }

    // Копирование результатов
    let staging_buffer = device.create_buffer(&wgpu::BufferDescriptor {
        label: Some("Staging Buffer"),
        size: aligned_size,
        usage: wgpu::BufferUsages::MAP_READ | wgpu::BufferUsages::COPY_DST,
        mapped_at_creation: false,
    });

    encoder.copy_buffer_to_buffer(&output_buffer, 0, &staging_buffer, 0, aligned_size);
    queue.submit(Some(encoder.finish()));

    // Чтение результатов
    let buffer_slice = staging_buffer.slice(..);
    let (sender, receiver) = oneshot::channel();
    buffer_slice.map_async(wgpu::MapMode::Read, move |result| {
        sender.send(result).unwrap();
    });

    device.poll(wgpu::Maintain::Wait);
    receiver.await.unwrap().map_err(|_| "Failed to read GPU result")?;

    let data = buffer_slice.get_mapped_range();
    let result = data.to_vec();

    // Возвращаем только исходное количество байт
    Ok(result[..input.len()].to_vec())
}