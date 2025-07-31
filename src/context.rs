use cel_interpreter::objects::TryIntoValue;
use cel_interpreter::Value;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

#[pyo3::pyclass]
pub struct Context {
    pub variables: HashMap<String, Value>,
    pub functions: HashMap<String, Py<PyAny>>,
}

#[pyo3::pymethods]
impl Context {
    #[new]
    #[pyo3(signature = (variables=None, functions=None))]
    pub fn new(variables: Option<&Bound<'_, PyDict>>, functions: Option<&Bound<'_, PyDict>>) -> PyResult<Self> {
        let mut context = Context {
            variables: HashMap::new(),
            functions: HashMap::new(),
        };

        if let Some(variables) = variables {
            //context.variables.extend(variables.clone());
            for (k, v) in variables {
                let key = k
                    .extract::<String>()
                    .map_err(|_| PyValueError::new_err("Variable name must be strings"));
                key.map(|key| context.add_variable(key, &v))??;
            }
        };

        if let Some(functions) = functions {
            context.update(functions)?;
        };

        Ok(context)
    }

    fn add_function(&mut self, name: String, function: Py<PyAny>) {
        self.functions.insert(name, function);
    }

    pub fn add_variable(&mut self, name: String, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let value = crate::RustyPyType(&value).try_into_value().map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "Failed to convert variable '{}': {}",
                name, e
            ))
        })?;
        self.variables.insert(name, value);
        Ok(())
    }

    pub fn update(&mut self, variables: &Bound<'_, PyDict>) -> PyResult<()> {
        for (key, value) in variables {
            // Attempt to extract the key as a String
            let key = key
                .extract::<String>()
                .map_err(|_| PyValueError::new_err("Keys must be strings"))?;

            if value.is_callable() {
                // Value is a function, add it to the functions hashmap
                let py_function = value.unbind();
                self.functions.insert(key, py_function);
            } else {
                // Value is a variable, add it to the variables hashmap
                let value = crate::RustyPyType(&value)
                    .try_into_value()
                    .map_err(|e| PyValueError::new_err(e.to_string()))?;

                self.variables.insert(key, value);
            }
        }

        Ok(())
    }
}
