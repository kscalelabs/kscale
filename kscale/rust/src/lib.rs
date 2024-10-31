use pyo3::prelude::*;
use pyo3_stub_gen::define_stub_info_gatherer;
use pyo3_stub_gen::derive::gen_stub_pyfunction;

#[pyfunction]
#[gen_stub_pyfunction]
pub fn hello_world() {
    println!("Hello, world!");
}

#[pymodule]
fn rust(m: &Bound<PyModule>) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(hello_world, m)?)?;
    Ok(())
}

define_stub_info_gatherer!(stub_info);
