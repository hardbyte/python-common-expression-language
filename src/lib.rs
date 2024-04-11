use cel_interpreter::objects::{Key, TryIntoValue};
use cel_interpreter::{Context, Program, Value};
use log::debug;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::{PyDateTime, PyDelta, PyDeltaAccess, PyDict, PyList, PyTuple};
use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::sync::Arc;
use pyo3::chrono;
use pyo3::ffi::PyDateTime_Delta;

#[derive(Debug)]
struct RustyCelType(Value);

impl IntoPy<PyObject> for RustyCelType {
    fn into_py(self, py: Python<'_>) -> PyObject {
        // Just use the native rust type's existing
        // IntoPy implementation
        match self {
            // Primitive Types
            RustyCelType(Value::Null) => py.None(),
            RustyCelType(Value::Bool(b)) => b.into_py(py),
            RustyCelType(Value::Int(i64)) => i64.into_py(py),
            RustyCelType(Value::UInt(u64)) => u64.into_py(py),
            RustyCelType(Value::Float(f)) => f.into_py(py),
            RustyCelType(Value::Timestamp(ts)) => ts.into_py(py),
            RustyCelType(Value::String(s)) => s.as_ref().into_py(py),
            RustyCelType(Value::List(val)) => {
                let list = val
                    .as_ref()
                    .into_iter()
                    .map(|v| RustyCelType(v.clone()).into_py(py))
                    .collect::<Vec<PyObject>>();
                list.into_py(py)
            }
            RustyCelType(Value::Bytes(val)) => {
                let bytes = val;
                bytes.as_ref().as_slice().into_py(py)
            }
            RustyCelType(Value::Duration(d)) => d.into_py(py),

            RustyCelType(Value::Map(val)) => {
                // Create a PyDict with the converted Python key and values.
                let python_dict = PyDict::new_bound(py);

                val.map.as_ref().into_iter().for_each(|(k, v)| {
                    // Key is an enum with String, Uint, Int and Bool variants. Value is any RustyCelType
                    let key = match k {
                        Key::String(s) => s.as_ref().into_py(py),
                        Key::Uint(u64) => u64.into_py(py),
                        Key::Int(i64) => i64.into_py(py),
                        Key::Bool(b) => b.into_py(py),
                    };
                    let value = RustyCelType(v.clone()).into_py(py);
                    python_dict
                        .set_item(key, value)
                        .expect("Failed to set item in Python dict");
                });

                python_dict.into()
            }

            // Turn everything else into a String:
            nonprimitive => format!("{:?}", nonprimitive).into_py(py),
        }
    }
}

#[derive(Debug)]
struct RustyPyType<'a>(&'a PyAny);

#[derive(Debug, PartialEq, Clone)]
pub enum CelError {
    ConversionError(String),
}

impl fmt::Display for CelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "Cel Error")
    }
}
impl Error for CelError {}

/// We can't implement TryIntoValue for PyAny, so we implement for our wrapper RustyPyType
impl TryIntoValue for RustyPyType<'_> {
    type Error = CelError;

    fn try_into_value(self) -> Result<Value, Self::Error> {
        let val = match self {
            RustyPyType(pyobject) => {
                if let Ok(value) = pyobject.extract::<i64>() {
                    Ok(Value::Int(value))
                } else if let Ok(value) = pyobject.extract::<f64>() {
                    Ok(Value::Float(value))
                } else if let Ok(value) = pyobject.extract::<bool>() {
                    Ok(Value::Bool(value))
                // TODO: Implement these conversions
                    // } else if let Ok(value) = pyobject.downcast::<PyDateTime>() {
                //     Ok(Value::Timestamp(value.into()))
                // } else if let Ok(value) = pyobject.downcast::<PyDelta>() {
                //     Ok(Value::Duration(value.into()))
                } else if let Ok(value) = pyobject.extract::<String>() {
                    Ok(Value::String(value.into()))
                } else if let Ok(value) = pyobject.downcast::<PyList>() {
                        let list = value
                            .iter()
                            .map(|item| RustyPyType(item).try_into_value())
                            .collect::<Result<Vec<Value>, Self::Error>>();
                        list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.downcast::<PyTuple>() {
                    let list = value
                        .iter()
                        .map(|item| RustyPyType(item).try_into_value())
                        .collect::<Result<Vec<Value>, Self::Error>>();
                    list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.downcast::<PyDict>() {
                    let mut map: HashMap<Key, Value> = HashMap::new();
                    for (key, value) in value.into_iter() {
                        let key = if let Ok(k) = key.extract::<i64>() {
                            Key::Int(k)
                        } else if let Ok(k) = key.extract::<u64>() {
                            Key::Uint(k)
                        } else if let Ok(k) = key.extract::<bool>() {
                            Key::Bool(k)
                        } else if let Ok(k) = key.extract::<String>() {
                            Key::String(k.into())
                        } else {
                            return Err(CelError::ConversionError(
                                "Failed to convert PyDict key to Key".to_string(),
                            ));
                        };
                        if let Ok(dict_value) = RustyPyType(value).try_into_value() {
                            map.insert(
                                key,
                                dict_value,
                            );
                        } else {
                            return Err(CelError::ConversionError(
                                "Failed to convert PyDict value to Value".to_string(),
                            ));

                        }
                    }
                    Ok(Value::Map(map.into()))
                } else if let Ok(value) = pyobject.extract::<Vec<u8>>() {
                    Ok(Value::Bytes(value.into()))
                } else {
                    Err(CelError::ConversionError(
                        "Failed to convert PyAny to Value".to_string(),
                    ))
                }
            }
        };
        val
    }
}

/// Evaluate a CEL expression
/// Returns a String representation of the result
#[pyfunction]
fn evaluate(src: String, context: Option<&PyDict>) -> PyResult<RustyCelType> {
    debug!("Evaluating CEL expression: {}", src);
    debug!("Context: {:?}", context);

    let program = Program::compile(src.as_str());

    // Handle the result of the compilation
    match program {
        Err(compile_error) => {
            debug!("An error occurred during compilation");
            debug!("compile_error: {:?}", compile_error);
            // compile_error
            //     .into_iter()
            //     .for_each(|e| println!("Parse error: {:?}", e));
            return Err(PyValueError::new_err("Parse Error"));
        }
        Ok(program) => {
            let mut environment = Context::default();

            // Custom functions can be added to the environment
            //environment.add_function("add", |a: i64, b: i64| a + b);

            // Add any variables from the passed in Dict context
            if let Some(context) = context {
                for (key, value) in context {
                    debug!("Adding context '{:?}'", key);
                    let key = key.extract::<String>().unwrap();
                    // Each value is of type PyAny, we need to try to extract into a Value
                    // and then add it to the CEL context

                    let wrapped_value = RustyPyType(value);
                    match wrapped_value.try_into_value() {
                        Ok(value) => {
                            debug!("Converted value: {:?}", value);
                            environment
                                .add_variable(key, value)
                                .expect("Failed to add variable to context");
                        }
                        Err(error) => {
                            debug!("An error occurred during context conversion");
                            debug!("Conversion error: {:?}", error);
                            debug!("Key: {:?}", key);

                            return Err(PyValueError::new_err("Conversion Error"));
                        }
                    }
                }
            }

            let result = program.execute(&environment);
            match result {
                Err(error) => {
                    println!("An error occurred during execution");
                    println!("Execution error: {:?}", error);
                    // errors
                    //     .into_iter()
                    //     .for_each(|e| println!("Execution error: {:?}", e));
                    Err(PyValueError::new_err("Execution Error"))
                }

                Ok(value) => return Ok(RustyCelType(value)),
            }
        }
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn cel(_py: Python, m: &PyModule) -> PyResult<()> {
    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    Ok(())
}
