use std::collections::HashMap;
use cel_interpreter::objects::TryIntoValue;
use cel_interpreter::Value;
use pyo3::prelude::*;
use pyo3::types::{PyDict, PyFunction};

#[pyo3::pyclass]
pub struct Context {
    pub variables: HashMap<String, Value>,
    pub functions: HashMap<String, Py<PyAny>>,
}

#[pyo3::pymethods]
impl Context {
    #[new]
    fn new() -> Self {
        Context {
            variables: HashMap::new(),
            functions: HashMap::new(),
        }
    }

    fn add_function(&mut self, name: String, function: Py<PyAny>) {
        self.functions.insert(name, function);
    }

    pub fn add_variable(&mut self, name: String, value: &PyAny) -> PyResult<()> {
        let value = crate::RustyPyType(value).try_into_value().map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!("Failed to convert variable '{}': {}", name, e))
        })?;
        self.variables.insert(name, value);
        Ok(())
    }

    fn update(&mut self, variables: &PyDict) -> PyResult<()> {
        for (key, value) in variables {
            let key = key.extract::<String>()?;
            let value = crate::RustyPyType(value)
                .try_into_value()
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

            self.variables.insert(key, value);
        }
        Ok(())
    }
}