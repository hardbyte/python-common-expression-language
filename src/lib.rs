mod context;

use ::cel::objects::{Key, OptionalValue, TryIntoValue};
use ::cel::{ExecutionError, PreparedValue, Program, Value};
use chrono::{DateTime, Duration as ChronoDuration, Offset, TimeZone};
use context::{Context, PyPreparedValue};
use log::warn;
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::types::{PyBool, PyBytes, PyDict, PyList, PyMapping, PyTuple, PyType, PyTypeMethods};
use pyo3::{BoundObject, PyTypeInfo};
use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::panic::{self, AssertUnwindSafe};
use std::sync::Arc;

/// A compiled CEL program that can be executed repeatedly against reusable contexts.
#[pyclass(name = "Program")]
struct PyProgram {
    program: Program,
    source: String,
}

#[pymethods]
impl PyProgram {
    /// Execute the compiled program against a native `Context` by reference.
    fn execute(&self, context: PyRef<'_, Context>, py: Python<'_>) -> PyResult<Py<PyAny>> {
        let result = execute_program(&self.program, &self.source, &context.inner)?;
        RustyCelType(result).into_pyobject(py).map(Bound::unbind)
    }

    fn __repr__(&self) -> String {
        format!("Program({:?})", self.source)
    }
}

/// A CEL optional value wrapper for Python.
#[pyclass(name = "OptionalValue")]
struct PyOptionalValue {
    value: Option<Value>,
}

impl PyOptionalValue {
    fn to_cel_value(&self) -> Value {
        match &self.value {
            Some(value) => Value::Opaque(Arc::new(OptionalValue::of(value.clone()))),
            None => Value::Opaque(Arc::new(OptionalValue::none())),
        }
    }
}

#[pymethods]
impl PyOptionalValue {
    #[classmethod]
    fn of(_cls: &Bound<'_, PyType>, value: &Bound<'_, PyAny>) -> PyResult<Self> {
        let value = RustyPyType(value)
            .try_into_value()
            .map_err(|error| PyValueError::new_err(error.to_string()))?;
        Ok(Self { value: Some(value) })
    }

    #[classmethod]
    fn none(_cls: &Bound<'_, PyType>) -> Self {
        Self { value: None }
    }

    fn has_value(&self) -> bool {
        self.value.is_some()
    }

    fn value(&self, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.value {
            Some(value) => RustyCelType(value.clone())
                .into_pyobject(py)
                .map(Bound::unbind),
            None => Err(PyValueError::new_err("optional.none() dereference")),
        }
    }

    fn or_value(&self, default: &Bound<'_, PyAny>, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.value {
            Some(value) => RustyCelType(value.clone())
                .into_pyobject(py)
                .map(Bound::unbind),
            None => Ok(default.clone().unbind()),
        }
    }

    fn or_optional(&self, other: PyRef<'_, PyOptionalValue>) -> PyOptionalValue {
        PyOptionalValue {
            value: self.value.clone().or_else(|| other.value.clone()),
        }
    }

    fn __bool__(&self) -> bool {
        self.value.is_some()
    }

    fn __repr__(&self) -> String {
        match &self.value {
            Some(_) => "OptionalValue(...)".to_string(),
            None => "OptionalValue.none()".to_string(),
        }
    }
}

/// Compile a CEL expression into a reusable program.
#[pyfunction]
fn compile(expression: String) -> PyResult<PyProgram> {
    let program = compile_program(&expression)?;
    Ok(PyProgram {
        program,
        source: expression,
    })
}

/// Convert a supported Python value into an immutable reusable CEL value.
#[pyfunction]
fn prepare(value: &Bound<'_, PyAny>) -> PyResult<PyPreparedValue> {
    if let Ok(prepared) = value.extract::<PyRef<'_, PyPreparedValue>>() {
        return Ok(PyPreparedValue::new(prepared.inner.clone()));
    }

    let value = RustyPyType(value)
        .try_into_value()
        .map_err(|error| PyValueError::new_err(format!("Failed to prepare value: {error}")))?;
    let prepared = PreparedValue::try_from_value(value)
        .map_err(|error| PyValueError::new_err(format!("Failed to prepare value: {error}")))?;
    Ok(PyPreparedValue::new(prepared))
}

fn compile_program(source: &str) -> PyResult<Program> {
    panic::catch_unwind(|| Program::compile(source))
        .map_err(|_| {
            warn!("CEL parser panic for expression: '{source}'");
            PyValueError::new_err(format!(
                "Failed to parse expression '{source}': invalid syntax or malformed string"
            ))
        })?
        .map_err(|error| {
            PyValueError::new_err(format!("Failed to parse expression '{source}': {error}"))
        })
}

fn execute_program(
    program: &Program,
    source: &str,
    context: &::cel::Context<'_>,
) -> PyResult<Value> {
    let result =
        panic::catch_unwind(AssertUnwindSafe(|| program.execute(context))).map_err(|_| {
            warn!("CEL execution panic for expression: '{source}'");
            PyValueError::new_err(format!(
                "Failed to execute expression '{source}': internal evaluator error"
            ))
        })?;
    result.map_err(|error| map_execution_error_to_python(&error))
}

#[derive(Debug)]
struct RustyCelType(Value);

impl<'py> IntoPyObject<'py> for RustyCelType {
    type Target = PyAny;
    type Output = Bound<'py, Self::Target>;
    type Error = PyErr;

    fn into_pyobject(self, py: Python<'py>) -> Result<Self::Output, Self::Error> {
        let object = match self.0 {
            Value::Null => py.None().into_bound(py),
            Value::Bool(value) => PyBool::new(py, value).into_bound().into_any(),
            Value::Int(value) => value.into_pyobject(py)?.into_any(),
            Value::UInt(value) => value.into_pyobject(py)?.into_any(),
            Value::Float(value) => value.into_pyobject(py)?.into_any(),
            Value::Timestamp(value) => value.into_pyobject(py)?.into_any(),
            Value::Duration(value) => value.into_pyobject(py)?.into_any(),
            Value::String(value) => value.as_ref().to_string().into_pyobject(py)?.into_any(),
            Value::Bytes(value) => PyBytes::new(py, &value).into_any(),
            Value::List(values) => {
                let list = PyList::empty(py);
                for value in values.iter() {
                    list.append(RustyCelType(value.clone()).into_pyobject(py)?)?;
                }
                list.into_any()
            }
            Value::Map(value) => {
                let dictionary = PyDict::new(py);
                for (key, value) in value.map.iter() {
                    let key = match key {
                        Key::String(value) => value.as_ref().into_pyobject(py)?.into_any(),
                        Key::Uint(value) => value.into_pyobject(py)?.into_any(),
                        Key::Int(value) => value.into_pyobject(py)?.into_any(),
                        Key::Bool(value) => PyBool::new(py, *value).into_bound().into_any(),
                    };
                    dictionary.set_item(key, RustyCelType(value.clone()).into_pyobject(py)?)?;
                }
                dictionary.into_any()
            }
            Value::Opaque(opaque) if opaque.runtime_type_name() == "optional_type" => {
                let optional = opaque
                    .downcast_ref::<OptionalValue>()
                    .ok_or_else(|| PyValueError::new_err("invalid CEL optional value"))?;
                Py::new(
                    py,
                    PyOptionalValue {
                        value: optional.value().cloned(),
                    },
                )?
                .into_bound(py)
                .into_any()
            }
            other => format!("{other:?}").into_pyobject(py)?.into_any(),
        };
        Ok(object)
    }
}

#[derive(Debug)]
struct RustyPyType<'a>(&'a Bound<'a, PyAny>);

#[derive(Debug, PartialEq, Clone)]
pub enum CelError {
    ConversionError(String),
}

impl fmt::Display for CelError {
    fn fmt(&self, formatter: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CelError::ConversionError(message) => write!(formatter, "Conversion Error: {message}"),
        }
    }
}

impl Error for CelError {}

impl RustyPyType<'_> {
    fn key_from_py(key: &Bound<'_, PyAny>) -> Result<Key, CelError> {
        if key.is_none() {
            return Err(CelError::ConversionError(
                "None cannot be used as a dictionary key".to_string(),
            ));
        }
        // `bool` is a subclass of `int` in Python, so it must be checked first.
        if let Ok(value) = key.extract::<bool>() {
            Ok(Key::Bool(value))
        } else if let Ok(value) = key.extract::<i64>() {
            Ok(Key::Int(value))
        } else if let Ok(value) = key.extract::<u64>() {
            Ok(Key::Uint(value))
        } else if let Ok(value) = key.extract::<String>() {
            Ok(Key::String(value.into()))
        } else {
            Err(CelError::ConversionError(
                "failed to convert Python mapping key".to_string(),
            ))
        }
    }

    fn mapping_to_value(mapping: &Bound<'_, PyMapping>) -> Result<Value, CelError> {
        let keys = mapping
            .keys()
            .map_err(|error| CelError::ConversionError(format!("failed to read keys: {error}")))?;
        let mut result = HashMap::new();
        for key in keys.iter() {
            let converted_key = Self::key_from_py(&key)?;
            let value = mapping.get_item(&key).map_err(|error| {
                CelError::ConversionError(format!("failed to read mapping item: {error}"))
            })?;
            result.insert(converted_key, RustyPyType(&value).try_into_value()?);
        }
        Ok(Value::Map(result.into()))
    }
}

impl TryIntoValue for RustyPyType<'_> {
    type Error = CelError;

    fn try_into_value(self) -> Result<Value, Self::Error> {
        let object = self.0;
        if let Ok(optional) = object.extract::<PyRef<'_, PyOptionalValue>>() {
            Ok(optional.to_cel_value())
        } else if object.is_none() {
            Ok(Value::Null)
        } else if let Ok(value) = object.extract::<bool>() {
            Ok(Value::Bool(value))
        } else if let Ok(value) = object.extract::<i64>() {
            Ok(Value::Int(value))
        } else if let Ok(value) = object.extract::<u64>() {
            Ok(Value::UInt(value))
        } else if let Ok(value) = object.extract::<f64>() {
            Ok(Value::Float(value))
        } else if let Ok(value) = object.extract::<DateTime<chrono::FixedOffset>>() {
            Ok(Value::Timestamp(value))
        } else if let Ok(value) = object.extract::<chrono::NaiveDateTime>() {
            let local = chrono::Local
                .from_local_datetime(&value)
                .single()
                .ok_or_else(|| {
                    CelError::ConversionError("ambiguous or invalid local datetime".to_string())
                })?;
            Ok(Value::Timestamp(local.with_timezone(&local.offset().fix())))
        } else if let Ok(value) = object.extract::<ChronoDuration>() {
            Ok(Value::Duration(value))
        } else if let Ok(value) = object.extract::<String>() {
            Ok(Value::String(value.into()))
        } else if let Ok(value) = object.cast::<PyList>() {
            value
                .iter()
                .map(|item| RustyPyType(&item).try_into_value())
                .collect::<Result<Vec<_>, _>>()
                .map(|values| Value::List(Arc::new(values)))
        } else if let Ok(value) = object.cast::<PyTuple>() {
            value
                .iter()
                .map(|item| RustyPyType(&item).try_into_value())
                .collect::<Result<Vec<_>, _>>()
                .map(|values| Value::List(Arc::new(values)))
        } else if let Ok(value) = object.cast::<PyDict>() {
            let is_exact_dict =
                object.get_type().as_type_ptr() == PyDict::type_object(object.py()).as_type_ptr();
            if is_exact_dict {
                let mut result = HashMap::new();
                for (key, value) in value {
                    result.insert(
                        Self::key_from_py(&key)?,
                        RustyPyType(&value).try_into_value()?,
                    );
                }
                Ok(Value::Map(result.into()))
            } else {
                let mapping = object.cast::<PyMapping>().map_err(|error| {
                    CelError::ConversionError(format!("failed to read dict subclass: {error}"))
                })?;
                Self::mapping_to_value(mapping)
            }
        } else if let Ok(mapping) = object.cast::<PyMapping>() {
            Self::mapping_to_value(mapping)
        } else if let Ok(value) = object.extract::<Vec<u8>>() {
            Ok(Value::Bytes(value.into()))
        } else {
            let type_name = object
                .get_type()
                .name()
                .map(|name| name.to_string())
                .unwrap_or_else(|_| "<unknown>".into());
            Err(CelError::ConversionError(format!(
                "failed to convert Python object of type {type_name}"
            )))
        }
    }
}

fn map_execution_error_to_python(error: &ExecutionError) -> PyErr {
    match error {
        ExecutionError::UndeclaredReference(name) => PyRuntimeError::new_err(format!(
            "Undefined variable or function: '{name}'. Check that the variable is defined in the context and that the function name is spelled correctly."
        )),
        ExecutionError::UnsupportedBinaryOperator(operator, left, right) => {
            let left_type = format!("{:?}", left.type_of());
            let right_type = format!("{:?}", right.type_of());
            let is_signed_unsigned =
                (left_type == "Int" && right_type == "UInt")
                    || (left_type == "UInt" && right_type == "Int");
            if is_signed_unsigned {
                return PyTypeError::new_err(format!(
                    "Cannot mix signed and unsigned integers in {operator} operation: {left_type} and {right_type}. Use explicit conversion: int(value) or uint(value)."
                ));
            }

            let operation = match *operator {
                "add" => "addition",
                "sub" => "subtraction",
                "mul" => "multiplication",
                "div" => "division",
                "rem" => "remainder",
                other => other,
            };
            PyTypeError::new_err(format!(
                "Unsupported {operation} operation between {left_type} and {right_type}. Check that both operands are compatible types; use explicit conversion if needed: double(value)."
            ))
        }
        ExecutionError::NoSuchOverload => PyTypeError::new_err("No such overload"),
        ExecutionError::FunctionError { function, message } => {
            PyRuntimeError::new_err(format!("Function '{function}' error: {message}"))
        }
        other => PyValueError::new_err(format!("CEL execution error: {other}")),
    }
}

/// Compile and evaluate a CEL expression against a reusable native Context.
///
/// The context is required and is borrowed directly for the duration of
/// evaluation; dictionaries and implicit contexts are not accepted.
#[pyfunction]
fn evaluate(src: String, context: PyRef<'_, Context>, py: Python<'_>) -> PyResult<Py<PyAny>> {
    let program = compile_program(&src)?;
    let result = execute_program(&program, &src, &context.inner)?;
    RustyCelType(result).into_pyobject(py).map(Bound::unbind)
}

#[pymodule]
fn cel(_py: Python<'_>, module: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();
    module.add_function(wrap_pyfunction!(evaluate, module)?)?;
    module.add_function(wrap_pyfunction!(compile, module)?)?;
    module.add_function(wrap_pyfunction!(prepare, module)?)?;
    module.add_class::<Context>()?;
    module.add_class::<PyPreparedValue>()?;
    module.add_class::<PyProgram>()?;
    module.add_class::<PyOptionalValue>()?;
    Ok(())
}
