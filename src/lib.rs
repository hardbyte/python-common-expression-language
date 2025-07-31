mod context;

use cel_interpreter::objects::{Key, TryIntoValue};
use cel_interpreter::{ExecutionError, Program, Value};
use log::{debug, warn};
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::BoundObject;
use std::panic;

use chrono::{DateTime, Duration as ChronoDuration, Offset, TimeZone};
use pyo3::types::{PyBool, PyBytes, PyDict, PyList, PyTuple};

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::sync::Arc;

#[derive(Debug)]
struct RustyCelType(Value);

impl<'py> IntoPyObject<'py> for RustyCelType {
    type Target = PyAny;
    type Output = Bound<'py, Self::Target>;
    type Error = PyErr;

    fn into_pyobject(self, py: Python<'py>) -> Result<Self::Output, Self::Error> {
        let obj = match self {
            // Primitive Types
            RustyCelType(Value::Null) => py.None().into_bound(py),
            RustyCelType(Value::Bool(b)) => PyBool::new(py, b).into_bound().into_any(),
            RustyCelType(Value::Int(i64)) => i64.into_pyobject(py)?.into_any(),
            RustyCelType(Value::UInt(u64)) => u64.into_pyobject(py)?.into_any(),
            RustyCelType(Value::Float(f)) => f.into_pyobject(py)?.into_any(),
            RustyCelType(Value::Timestamp(ts)) => {
                debug!("Converting a fixed offset datetime to python type");
                ts.into_pyobject(py)?.into_any()
            }
            RustyCelType(Value::Duration(d)) => d.into_pyobject(py)?.into_any(),
            RustyCelType(Value::String(s)) => s.as_ref().to_string().into_pyobject(py)?.into_any(),
            RustyCelType(Value::List(val)) => {
                let list = PyList::empty(py);
                for v in val.as_ref().iter() {
                    let item = RustyCelType(v.clone()).into_pyobject(py)?;
                    list.append(&item)?;
                }
                list.into_any()
            }
            RustyCelType(Value::Bytes(val)) => PyBytes::new(py, &val).into_any(),

            RustyCelType(Value::Map(val)) => {
                // Create a PyDict with the converted Python key and values.
                let python_dict = PyDict::new(py);

                for (k, v) in val.map.as_ref().iter() {
                    // Key is an enum with String, Uint, Int and Bool variants. Value is any RustyCelType
                    let key = match k {
                        Key::String(s) => s.as_ref().into_pyobject(py)?.into_any(),
                        Key::Uint(u64) => u64.into_pyobject(py)?.into_any(),
                        Key::Int(i64) => i64.into_pyobject(py)?.into_any(),
                        Key::Bool(b) => PyBool::new(py, *b).into_bound().into_any(),
                    };
                    let value = RustyCelType(v.clone()).into_pyobject(py)?;
                    python_dict.set_item(&key, &value)?;
                }

                python_dict.into_any()
            }

            // Turn everything else into a String:
            nonprimitive => format!("{nonprimitive:?}").into_pyobject(py)?.into_any(),
        };
        Ok(obj)
    }
}

#[derive(Debug)]
struct RustyPyType<'a>(&'a Bound<'a, PyAny>);

#[derive(Debug, PartialEq, Clone)]
pub enum CelError {
    ConversionError(String),
}

impl fmt::Display for CelError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CelError::ConversionError(msg) => write!(f, "Conversion Error: {msg}"),
        }
    }
}
impl Error for CelError {}

/// Enhanced error handling that maps CEL execution errors to appropriate Python exceptions
fn map_execution_error_to_python(error: &ExecutionError) -> PyErr {
    match error {
        ExecutionError::UndeclaredReference(name) => {
            PyRuntimeError::new_err(format!(
                "Undefined variable or function: '{name}'. Check that the variable is defined in the context or that the function name is spelled correctly."
            ))
        },
        ExecutionError::UnsupportedBinaryOperator(op, left_type, right_type) => {
            let left_type_str = format!("{left_type:?}");
            let right_type_str = format!("{right_type:?}");
            match *op {
                "add" => {
                    if (left_type_str.contains("Int") && right_type_str.contains("UInt")) ||
                       (left_type_str.contains("UInt") && right_type_str.contains("Int")) {
                        PyTypeError::new_err(format!(
                            "Cannot mix signed and unsigned integers in arithmetic: {left_type:?} + {right_type:?}. Use explicit conversion: int(value) or uint(value)"
                        ))
                    } else {
                        PyTypeError::new_err(format!(
                            "Unsupported addition operation: {left_type:?} + {right_type:?}. Check that both operands are compatible types (int+int, double+double, string+string, etc.)"
                        ))
                    }
                },
                "mul" => {
                    PyTypeError::new_err(format!(
                        "Unsupported multiplication operation: {left_type:?} * {right_type:?}. Ensure both operands are numeric and of compatible types. Use explicit conversion if needed: double(value)*double(value)"
                    ))
                },
                "sub" => {
                    PyTypeError::new_err(format!(
                        "Unsupported subtraction operation: {left_type:?} - {right_type:?}. Ensure both operands are numeric and of compatible types."
                    ))
                },
                "div" => {
                    PyTypeError::new_err(format!(
                        "Unsupported division operation: {left_type:?} / {right_type:?}. Ensure both operands are numeric and of compatible types."
                    ))
                },
                _ => {
                    PyTypeError::new_err(format!(
                        "Unsupported operation '{op}' between {left_type:?} and {right_type:?}. Check the CEL specification for supported operations between these types."
                    ))
                }
            }
        },
        ExecutionError::FunctionError { function, message } => {
            PyRuntimeError::new_err(format!(
                "Function '{function}' error: {message}. Check function arguments and their types."
            ))
        },
        _ => {
            // Fallback for any other execution errors - provide helpful message based on error content
            let error_str = format!("{error:?}");
            if error_str.contains("UndeclaredReference") {
                PyRuntimeError::new_err(format!(
                    "Undefined variable or function. Check that all variables are defined in the context and function names are spelled correctly. Error: {error}"
                ))
            } else if error_str.contains("UnsupportedBinaryOperator") {
                PyTypeError::new_err(format!(
                    "Unsupported operation between incompatible types. Check the CEL specification for supported operations. Error: {error}"
                ))
            } else {
                PyValueError::new_err(format!(
                    "CEL execution error: {error}. This may indicate an unsupported operation or invalid expression."
                ))
            }
        }
    }
}

/// Analyzes context for mixed int/float usage and returns whether to promote integers to floats
fn should_promote_integers_to_floats(variables: &HashMap<String, Value>) -> bool {
    // If we have floats in context, we should promote integers to floats for compatibility
    // This handles cases where expression has integer literals but context has floats
    for value in variables.values() {
        if matches!(value, Value::Float(_)) {
            return true;
        }
    }
    false
}

/// Promotes integers to floats in the context for better mixed arithmetic compatibility
fn promote_integers_in_context(variables: &mut HashMap<String, Value>) {
    for value in variables.values_mut() {
        if let Value::Int(int_val) = value {
            *value = Value::Float(*int_val as f64);
        }
    }
}

/// Analyzes expression for mixed int/float literals (simple heuristic)
fn expression_has_mixed_numeric_literals(expr: &str) -> bool {
    // If expression contains float literals (decimal point), assume mixed arithmetic is likely
    expr.contains('.') && expr.chars().any(|c| c.is_ascii_digit())
}

/// Find all integer literal positions in the expression
fn find_integer_literals(expr: &str) -> Vec<(usize, usize)> {
    let mut matches = Vec::new();
    let chars: Vec<char> = expr.chars().collect();
    let len = chars.len();
    let mut i = 0;

    while i < len {
        if chars[i].is_ascii_digit()
            || (chars[i] == '.' && i + 1 < len && chars[i + 1].is_ascii_digit())
        {
            let start = i;

            // Handle numbers that start with decimal point (like .456789)
            let starts_with_decimal = chars[i] == '.';
            if starts_with_decimal {
                i += 1; // Skip the initial '.'
            }

            // Skip all digits
            while i < len && chars[i].is_ascii_digit() {
                i += 1;
            }

            // Check if this is already a float (has decimal point) - but only if it didn't start with one
            if !starts_with_decimal && i < len && chars[i] == '.' {
                // This is already a float, skip the decimal part
                i += 1;
                while i < len && chars[i].is_ascii_digit() {
                    i += 1;
                }
                continue;
            }

            // Check if this is scientific notation (e.g., 123e4)
            if i < len && (chars[i] == 'e' || chars[i] == 'E') {
                // Skip scientific notation
                i += 1;
                if i < len && (chars[i] == '+' || chars[i] == '-') {
                    i += 1;
                }
                while i < len && chars[i].is_ascii_digit() {
                    i += 1;
                }
                continue;
            }

            // Skip this if it starts with decimal point (already a float)
            if starts_with_decimal {
                continue;
            }

            // Check if this integer is in a context where it shouldn't be converted to float
            // e.g., array indices [2], or other contexts where integers are expected
            if should_skip_integer_conversion(expr, start, i) {
                continue;
            }

            // This is an integer literal that should be converted
            matches.push((start, i));
        } else {
            i += 1;
        }
    }

    matches
}

/// Check if an integer at the given position should not be converted to float
fn should_skip_integer_conversion(expr: &str, start: usize, _end: usize) -> bool {
    let chars: Vec<char> = expr.chars().collect();

    // Check if this integer is used as an array/list index [integer]
    if start > 0 && chars[start - 1] == '[' {
        return true;
    }

    // Check if this integer is immediately after a '[' with possible whitespace
    let mut check_pos = start;
    while check_pos > 0 {
        check_pos -= 1;
        if chars[check_pos] == '[' {
            // Found opening bracket, this is likely an array index
            return true;
        } else if !chars[check_pos].is_whitespace() {
            // Found non-whitespace that isn't '[', not an array index
            break;
        }
    }

    false
}

/// Always preprocesses expression to promote integer literals to floats (used when context has mixed types)
fn preprocess_expression_for_mixed_arithmetic_always(expr: &str) -> String {
    debug!("Always preprocessing expression: {}", expr);

    // Convert all integer literals to floats
    // This is a more comprehensive approach than operator-by-operator processing
    let mut result = expr.to_string();

    // Use regex-like approach to find integer literals and convert them to floats
    // This approach modifies the string directly, which is more reliable
    let mut offset = 0;
    let original_result = result.clone();

    for (match_start, match_end) in find_integer_literals(&original_result) {
        let adjusted_start = match_start + offset;
        let adjusted_end = match_end + offset;

        // Extract the integer
        let integer_str = &result[adjusted_start..adjusted_end];
        let float_str = format!("{integer_str}.0");

        // Replace in the result string
        result.replace_range(adjusted_start..adjusted_end, &float_str);

        // Update offset for subsequent replacements (we added ".0", so +2)
        offset += 2;
    }
    debug!("Final processed expression: {}", result);
    result
}

/// We can't implement TryIntoValue for PyAny, so we implement for our wrapper RustyPyType
impl TryIntoValue for RustyPyType<'_> {
    type Error = CelError;

    fn try_into_value(self) -> Result<Value, Self::Error> {
        let val = match self {
            RustyPyType(pyobject) => {
                if pyobject.is_none() {
                    Ok(Value::Null)
                } else if let Ok(value) = pyobject.extract::<bool>() {
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
                        .map(|item| RustyPyType(&item).try_into_value())
                        .collect::<Result<Vec<Value>, Self::Error>>();
                    list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.downcast::<PyTuple>() {
                    let list = value
                        .iter()
                        .map(|item| RustyPyType(&item).try_into_value())
                        .collect::<Result<Vec<Value>, Self::Error>>();
                    list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.downcast::<PyDict>() {
                    let mut map: HashMap<Key, Value> = HashMap::new();
                    for (key, value) in value.into_iter() {
                        let key = if key.is_none() {
                            return Err(CelError::ConversionError(
                                "None cannot be used as a key in dictionaries".to_string(),
                            ));
                        } else if let Ok(k) = key.extract::<i64>() {
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
                        if let Ok(dict_value) = RustyPyType(&value).try_into_value() {
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
                    let type_name = pyobject
                        .get_type()
                        .name()
                        .map(|ps| ps.to_string())
                        .unwrap_or("<unknown>".into());
                    Err(CelError::ConversionError(format!(
                        "Failed to convert Python object of type {type_name} to Value"
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
fn evaluate(src: String, evaluation_context: Option<&Bound<'_, PyAny>>) -> PyResult<RustyCelType> {
    debug!("Evaluating CEL expression: {}", src);

    // Preprocess expression for better mixed int/float arithmetic compatibility
    // First check if expression itself has mixed literals
    let mut processed_src = if expression_has_mixed_numeric_literals(&src) {
        preprocess_expression_for_mixed_arithmetic_always(&src)
    } else {
        src.clone()
    };

    debug!("Preparing context");
    let mut environment = cel_interpreter::Context::default();
    let mut ctx = context::Context::new(None, None)?;
    let mut variables_for_env = HashMap::new();

    // Custom Rust functions can also be added to the environment...
    //environment.add_function("add", |a: i64, b: i64| a + b);

    // Process the evaluation context if provided first to determine if we need preprocessing
    if let Some(evaluation_context) = evaluation_context {
        // Attempt to extract directly as a Context object
        if let Ok(py_context_ref) = evaluation_context.extract::<PyRef<context::Context>>() {
            // Clone variables and functions into our local Context
            ctx.variables = py_context_ref.variables.clone();
            ctx.functions = py_context_ref.functions.clone();
        } else if let Ok(py_dict) = evaluation_context.downcast::<PyDict>() {
            // User passed in a dict - let's process variables and functions from the dict
            ctx.update(py_dict)?;
        } else {
            return Err(PyValueError::new_err(
                "evaluation_context must be a Context object or a dict",
            ));
        };

        // Smart numeric coercion for mixed int/float arithmetic compatibility
        variables_for_env = ctx.variables.clone();

        // Check if we should promote integers to floats for better compatibility
        let should_promote = should_promote_integers_to_floats(&variables_for_env)
            || expression_has_mixed_numeric_literals(&src);

        if should_promote {
            promote_integers_in_context(&mut variables_for_env);

            // Always preprocess the expression when we're promoting types
            // This handles cases where context has floats but expression has integer literals
            processed_src = preprocess_expression_for_mixed_arithmetic_always(&src);
            debug!("Processed expression: {} -> {}", src, processed_src);
        }
    }

    // Use panic::catch_unwind to handle parser panics gracefully
    let program = panic::catch_unwind(|| Program::compile(&processed_src))
        .map_err(|_| {
            PyValueError::new_err(format!(
                "Failed to parse expression '{src}': Invalid syntax"
            ))
        })?
        .map_err(|e| PyValueError::new_err(format!("Failed to compile expression '{src}': {e}")))?;

    debug!("Compiled program: {:?}", program);

    // Add variables and functions if we have a context
    if evaluation_context.is_some() {
        // Add any variables from the processed context
        for (name, value) in &variables_for_env {
            environment
                .add_variable(name.clone(), value.clone())
                .map_err(|e| {
                    PyValueError::new_err(format!("Failed to add variable '{name}': {e}"))
                })?;
        }

        // Add functions
        let collected_functions: Vec<(String, Py<PyAny>)> = Python::with_gil(|py| {
            ctx.functions
                .iter()
                .map(|(name, py_function)| (name.clone(), py_function.clone_ref(py)))
                .collect()
        });

        for (name, py_function) in collected_functions.into_iter() {
            environment.add_function(
                &name.clone(),
                move |ftx: &cel_interpreter::FunctionContext| -> cel_interpreter::ResolveResult {
                    Python::with_gil(|py| {
                        // Convert arguments from Expression in ftx.args to PyObjects
                        let mut py_args = Vec::new();
                        for arg_expr in &ftx.args {
                            let arg_value = ftx.ptx.resolve(arg_expr)?;
                            let py_arg = RustyCelType(arg_value)
                                .into_pyobject(py)
                                .map_err(|e| {
                                    ExecutionError::function_error(
                                        "argument_conversion",
                                        format!("Failed to convert argument: {e}"),
                                    )
                                })?
                                .into_any()
                                .unbind();
                            py_args.push(py_arg);
                        }
                        let py_args = PyTuple::new(py, py_args).map_err(|e| {
                            ExecutionError::function_error(
                                "tuple_creation",
                                format!("Failed to create tuple: {e}"),
                            )
                        })?;

                        // Call the Python function
                        let py_result = py_function.call1(py, py_args).map_err(|e| {
                            ExecutionError::FunctionError {
                                function: name.clone(),
                                message: e.to_string(),
                            }
                        })?;
                        // Convert the PyObject to &Bound<PyAny>
                        let py_result_ref = py_result.bind(py);

                        // Convert the result back to Value
                        let value = RustyPyType(py_result_ref).try_into_value().map_err(|e| {
                            ExecutionError::FunctionError {
                                function: name.clone(),
                                message: format!("Error calling function '{name}': {e}"),
                            }
                        })?;
                        Ok(value)
                    })
                },
            );
        }
    }

    let result = program.execute(&environment);
    match result {
        Err(error) => {
            warn!("An error occurred during execution");
            warn!("Execution error: {error:?}");
            Err(map_execution_error_to_python(&error))
        }

        Ok(value) => Ok(RustyCelType(value)),
    }
}

/// A Python module implemented in Rust.
#[pymodule]
fn cel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(evaluate, m)?)?;

    m.add_class::<context::Context>()?;
    Ok(())
}
