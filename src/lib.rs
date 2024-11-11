mod context;

use cel_interpreter::objects::{Key, TryIntoValue};
use cel_interpreter::{ExecutionError, Program, Value};
use log::{debug, info, warn};
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;

use chrono::{DateTime, Duration as ChronoDuration, Offset, TimeZone, Utc};
use pyo3::types::{PyDelta, PyFunction};
use pyo3::types::{PyBytes, PyDateTime, PyDict, PyList, PyTuple};
use std::time::{Duration, SystemTime, UNIX_EPOCH};

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::ops::Deref;
use std::sync::Arc;

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
            RustyCelType(Value::Timestamp(ts)) => {
                debug!("Converting a fixed offset datetime to python type");
                ts.into_py(py)
            }
            RustyCelType(Value::Duration(d)) => d.into_py(py),
            RustyCelType(Value::String(s)) => s.as_ref().to_string().into_py(py),
            RustyCelType(Value::List(val)) => {
                let list = val
                    .as_ref()
                    .into_iter()
                    .map(|v| RustyCelType(v.clone()).into_py(py))
                    .collect::<Vec<PyObject>>();
                list.into_py(py)
            }
            RustyCelType(Value::Bytes(val)) => PyBytes::new_bound(py, &val).into_py(py),

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
        match self {
            CelError::ConversionError(msg) => write!(f, "Conversion Error: {}", msg),
        }
    }
}
impl Error for CelError {}

/// We can't implement TryIntoValue for PyAny, so we implement for our wrapper RustyPyType
impl TryIntoValue for RustyPyType<'_> {
    type Error = CelError;

    fn try_into_value(self) -> Result<Value, Self::Error> {
        let val = match self {
            RustyPyType(pyobject) => {
                if let Ok(value) = pyobject.extract::<bool>() {
                    Ok(Value::Bool(value))
                } else if let Ok(value) = pyobject.extract::<i64>() {
                    Ok(Value::Int(value))
                } else if let Ok(value) = pyobject.extract::<f64>() {
                    Ok(Value::Float(value))
                } else if let Ok(value) = pyobject.extract::<DateTime<chrono::FixedOffset>>() {
                    Ok(Value::Timestamp(value))
                } else if let Ok(value) = pyobject.extract::<chrono::NaiveDateTime>() {
                    // Handle naive datetime - assuming the naive datetime is in local time
                    let local_timezone = chrono::Local;
                    if let Some(datetime_local) =
                        local_timezone.from_local_datetime(&value).single()
                    {
                        let datetime_fixed: DateTime<chrono::FixedOffset> =
                            datetime_local.with_timezone(&datetime_local.offset().fix());
                        Ok(Value::Timestamp(datetime_fixed))
                    } else {
                        // Ambiguous or invalid local datetime
                        Err(CelError::ConversionError(
                            "Ambiguous or invalid local datetime".to_string(),
                        ))
                    }
                } else if let Ok(value) = pyobject.extract::<ChronoDuration>() {
                    Ok(Value::Duration(value))
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
                            map.insert(key, dict_value);
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
                    Err(CelError::ConversionError(format!(
                        "Failed to convert Python object of type {} to Value",
                        pyobject
                            .get_type()
                            .name()
                            .map(|ps| ps.to_string())
                            .unwrap_or("<unknown>".into())
                    )))
                }
            }
        };
        val
    }
}

/// Evaluate a CEL expression
/// Returns a String representation of the result
#[pyfunction(signature = (src, evaluation_context=None))]
fn evaluate(src: String, evaluation_context: Option<&PyAny>) -> PyResult<RustyCelType> {
    debug!("Evaluating CEL expression: {}", src);

    let program = Program::compile(&src)
        .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;

    debug!("Compiled program: {:?}", program);

    debug!("Preparing context");
    let mut environment = cel_interpreter::Context::default();

    // Custom Rust functions can also be added to the environment...
    //environment.add_function("add", |a: i64, b: i64| a + b);


    if let Some(py_context) = evaluation_context {
        let py_context = py_context.extract::<PyRef<context::Context>>()?;

        // Add any variables from the passed in Python context
        for (name, value) in &py_context.variables {
            environment.add_variable(name.clone(), value.clone())
                .map_err(|e| pyo3::exceptions::PyValueError::new_err(e.to_string()))?;
        }

        // Add functions
        for (name, py_function) in &py_context.functions {

            let function_name = name.clone();

            environment.add_function(&name, move |ftx: &cel_interpreter::FunctionContext| -> cel_interpreter::ResolveResult  {
                Python::with_gil(|py| {
                    // Convert arguments from Expression in ftx.args to PyObjects
                    let mut py_args = Vec::new();
                    for arg_expr in &ftx.args {
                        let arg_value = ftx.ptx.resolve(arg_expr)?;
                        let py_arg = RustyCelType(arg_value).into_py(py);
                        py_args.push(py_arg);
                    }
                    let py_args = PyTuple::new_bound(py, py_args);

                    // Call the Python function
                    // let py_result = py_function.call1(py, py_args)
                    //     .map_err(|e|  ExecutionError::FunctionError {
                    //         function: function_name.clone(),
                    //         message: e.to_string(),
                    //     })?;
                    // // Convert the PyObject to &PyAny
                    // let py_result_ref = py_result.as_ref(py);
                    //
                    // // Convert the result back to Value
                    // let value = RustyPyType(py_result_ref).try_into_value().map_err(|e| {
                    //     ExecutionError::FunctionError {
                    //         function: function_name.clone(),
                    //         message: e.to_string(),
                    //     }
                    // })?;
                    // Ok(value)

                    ftx.error("Function arguments are not yet supported").into()

                })

            });
        }
    }

    let result = program.execute(&environment);
    match result {
        Err(error) => {
            warn!("An error occurred during execution");
            warn!("Execution error: {:?}", error);
            // errors
            //     .into_iter()
            //     .for_each(|e| println!("Execution error: {:?}", e));
            Err(PyValueError::new_err("Execution Error"))
        }

        Ok(value) => return Ok(RustyCelType(value)),
    }

}

/// A Python module implemented in Rust.
#[pymodule]
fn cel<'py>(py: Python<'py>, m: &PyModule) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    Ok(())
}
