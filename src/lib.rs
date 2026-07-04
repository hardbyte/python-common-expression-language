mod context;

use ::cel::context::VariableResolver;
use ::cel::objects::{Key, OptionalValue, TryIntoValue};
use ::cel::{Context as CelContext, Env, ExecutionError, FunctionContext, Program, Value};
use log::warn;
use pyo3::exceptions::{
    PyIndexError, PyKeyError, PyOverflowError, PyRuntimeError, PyTypeError, PyValueError,
    PyZeroDivisionError,
};
use pyo3::prelude::*;
use pyo3::BoundObject;
use std::panic::{self, AssertUnwindSafe};

use chrono::{DateTime, Duration as ChronoDuration, Offset, TimeZone};
use pyo3::types::{PyBool, PyBytes, PyDict, PyList, PyMapping, PyTuple, PyType, PyTypeMethods};
use pyo3::PyTypeInfo;

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::sync::{Arc, LazyLock};

/// The CEL standard-library environment (built-in functions, overloads and
/// macros), built once and shared across every evaluation.
///
/// `Context::default()` rebuilds `Env::stdlib()` on each call, which re-registers
/// every built-in overload. Since the standard library never changes, we build it
/// a single time and hand out cheap `Arc` clones via [`stdlib_env`], letting
/// `evaluate()` and `Program.execute()` reuse the same environment. User-supplied
/// variables and functions still live on the per-call `Context`, so this sharing
/// is safe and has no observable effect beyond being faster.
static STDLIB_ENV: LazyLock<Arc<Env>> = LazyLock::new(|| Arc::new(Env::stdlib()));

/// Returns a cheap `Arc` clone of the shared standard-library [`Env`].
fn stdlib_env() -> Arc<Env> {
    STDLIB_ENV.clone()
}

/// Builds a fresh execution environment backed by the shared standard library.
fn new_environment() -> CelContext<'static> {
    CelContext::with_env(stdlib_env())
}

/// A compiled CEL program that can be executed multiple times with different contexts.
///
/// This is useful when you need to evaluate the same expression many times with different
/// variable bindings. Compiling once and executing multiple times is significantly faster
/// than calling `evaluate()` repeatedly.
///
/// # Example
///
/// ```python
/// from cel import compile
///
/// # Compile once
/// program = compile("price * quantity > 100")
///
/// # Execute many times with different contexts
/// result1 = program.execute({"price": 10, "quantity": 20})  # True
/// result2 = program.execute({"price": 5, "quantity": 10})   # False
/// ```
#[pyclass(name = "Program")]
struct PyProgram {
    program: Program,
    source: String,
}

#[pymethods]
impl PyProgram {
    /// Execute the compiled program with the given context.
    ///
    /// Args:
    ///     context: Optional evaluation context (dict or Context object)
    ///
    /// Returns:
    ///     The result of the expression evaluation
    #[pyo3(signature = (context=None))]
    fn execute(&self, context: Option<&Bound<'_, PyAny>>) -> PyResult<Py<PyAny>> {
        execute_compiled_program(&self.program, &self.source, context)
    }

    /// The variable names referenced by this expression.
    ///
    /// This performs static analysis of the compiled expression without
    /// evaluating it, returning the names of the variables the expression
    /// reads. Useful for validating that a context supplies everything an
    /// expression needs, or for restricting which variables an expression may
    /// touch.
    ///
    /// Note: names bound by comprehension macros (the ``x`` in
    /// ``[1, 2].map(x, x * 2)``) are reported as variables, since they appear
    /// as identifiers in the expression.
    ///
    /// Returns:
    ///     A sorted list of referenced variable names.
    fn variables(&self) -> Vec<String> {
        let mut names: Vec<String> = self
            .program
            .references()
            .variables()
            .into_iter()
            .map(|s| s.to_string())
            .collect();
        names.sort();
        names
    }

    /// The function names referenced by this expression.
    ///
    /// This performs static analysis of the compiled expression without
    /// evaluating it. Both named functions (``size``, ``startsWith``) and the
    /// CEL operator overload identifiers for operators used in the expression
    /// (e.g. ``_+_`` or ``_>_``) are included.
    ///
    /// Returns:
    ///     A sorted list of referenced function/operator names.
    fn functions(&self) -> Vec<String> {
        let mut names: Vec<String> = self
            .program
            .references()
            .functions()
            .into_iter()
            .map(|s| s.to_string())
            .collect();
        names.sort();
        names
    }

    /// Static analysis of the names this expression references.
    ///
    /// Returns:
    ///     A dict with two keys, ``"variables"`` and ``"functions"``, each
    ///     mapping to a sorted list of names. Equivalent to calling
    ///     :meth:`variables` and :meth:`functions`.
    fn references<'py>(&self, py: Python<'py>) -> PyResult<Bound<'py, PyDict>> {
        let dict = PyDict::new(py);
        dict.set_item("variables", self.variables())?;
        dict.set_item("functions", self.functions())?;
        Ok(dict)
    }

    /// The original CEL source this program was compiled from.
    #[getter]
    fn source(&self) -> &str {
        &self.source
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
            .map_err(|e| PyValueError::new_err(e.to_string()))?;
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
                .map(|obj| obj.unbind()),
            None => Err(PyValueError::new_err("optional.none() dereference")),
        }
    }

    fn or_value(&self, default: &Bound<'_, PyAny>, py: Python<'_>) -> PyResult<Py<PyAny>> {
        match &self.value {
            Some(value) => RustyCelType(value.clone())
                .into_pyobject(py)
                .map(|obj| obj.unbind()),
            None => Ok(default.clone().unbind()),
        }
    }

    fn or_optional(&self, other: PyRef<'_, PyOptionalValue>) -> PyOptionalValue {
        if self.value.is_some() {
            PyOptionalValue {
                value: self.value.clone(),
            }
        } else {
            PyOptionalValue {
                value: other.value.clone(),
            }
        }
    }

    fn __bool__(&self) -> bool {
        self.value.is_some()
    }

    fn __repr__(&self) -> String {
        match &self.value {
            Some(value) => format!("OptionalValue({value:?})"),
            None => "OptionalValue.none()".to_string(),
        }
    }
}

/// Compile a CEL expression into a reusable Program object.
///
/// This function parses and compiles a CEL expression, returning a Program object
/// that can be executed multiple times with different contexts. This is more efficient
/// than calling `evaluate()` repeatedly with the same expression.
///
/// Args:
///     expression: The CEL expression to compile
///
/// Returns:
///     A compiled Program object
///
/// Raises:
///     ValueError: If the expression has syntax errors or is malformed
///
/// Example:
///     >>> from cel import compile
///     >>> program = compile("x + y")
///     >>> program.execute({"x": 1, "y": 2})
///     3
///     >>> program.execute({"x": 10, "y": 20})
///     30
#[pyfunction]
fn compile(expression: String) -> PyResult<PyProgram> {
    let program = panic::catch_unwind(|| Program::compile(&expression))
        .map_err(|_| {
            warn!("CEL parser panic for expression: '{}'", expression);
            PyValueError::new_err(format!(
                "Failed to parse expression '{expression}': Invalid syntax or malformed string"
            ))
        })?
        .map_err(|e| {
            PyValueError::new_err(format!("Failed to parse expression '{expression}': {e}"))
        })?;

    Ok(PyProgram {
        program,
        source: expression,
    })
}

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
            RustyCelType(Value::Timestamp(ts)) => ts.into_pyobject(py)?.into_any(),
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

            RustyCelType(Value::Opaque(opaque)) => {
                if opaque.runtime_type_name() == "optional_type" {
                    if let Some(optional) = opaque.downcast_ref::<OptionalValue>() {
                        Py::new(
                            py,
                            PyOptionalValue {
                                value: optional.value().cloned(),
                            },
                        )?
                        .into_bound(py)
                        .into_any()
                    } else {
                        format!("{:?}", Value::Opaque(opaque.clone()))
                            .into_pyobject(py)?
                            .into_any()
                    }
                } else {
                    format!("{:?}", Value::Opaque(opaque.clone()))
                        .into_pyobject(py)?
                        .into_any()
                }
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

impl<'a> RustyPyType<'a> {
    fn key_from_py(key: &Bound<'_, PyAny>) -> Result<Key, CelError> {
        if key.is_none() {
            return Err(CelError::ConversionError(
                "None cannot be used as a key in dictionaries".to_string(),
            ));
        }

        if let Ok(k) = key.extract::<i64>() {
            Ok(Key::Int(k))
        } else if let Ok(k) = key.extract::<u64>() {
            Ok(Key::Uint(k))
        } else if let Ok(k) = key.extract::<bool>() {
            Ok(Key::Bool(k))
        } else if let Ok(k) = key.extract::<String>() {
            Ok(Key::String(k.into()))
        } else {
            Err(CelError::ConversionError(
                "Failed to convert Python mapping key to Key".to_string(),
            ))
        }
    }

    fn mapping_to_value(mapping: &Bound<'_, PyMapping>) -> Result<Value, CelError> {
        let keys = mapping
            .keys()
            .map_err(|e| CelError::ConversionError(format!("Failed to read mapping keys: {e}")))?;

        let mut map: HashMap<Key, Value> = HashMap::new();
        for key in keys.iter() {
            let key_converted = Self::key_from_py(&key)?;
            let value = mapping.get_item(&key).map_err(|e| {
                CelError::ConversionError(format!("Failed to read mapping item: {e}"))
            })?;
            let value_converted = RustyPyType(&value).try_into_value().map_err(|e| {
                CelError::ConversionError(format!("Failed to convert mapping value: {e}"))
            })?;
            map.insert(key_converted, value_converted);
        }

        Ok(Value::Map(map.into()))
    }
}

/// Bridges a Python callable to cel-rust's `VariableResolver` trait so users
/// can resolve variables lazily on demand instead of materializing them up front.
///
/// The callback receives the variable name as a string and returns either a
/// supported Python value or `None` (meaning "not handled — fall back to the
/// statically-defined variables map"). Any exception raised by the callback
/// is treated as "not handled" and a warning is logged.
struct PyVariableResolver {
    callback: Py<PyAny>,
}

impl VariableResolver for PyVariableResolver {
    fn resolve(&self, variable: &str) -> Option<Value> {
        Python::attach(|py| {
            let result = match self.callback.call1(py, (variable,)) {
                Ok(r) => r,
                Err(e) => {
                    warn!("Variable resolver raised for '{variable}': {e}");
                    return None;
                }
            };
            if result.is_none(py) {
                return None;
            }
            let bound = result.bind(py);
            match RustyPyType(bound).try_into_value() {
                Ok(v) => Some(v),
                Err(e) => {
                    warn!("Variable resolver for '{variable}' returned an unsupported value: {e}");
                    None
                }
            }
        })
    }
}

/// Build a CEL execution environment from an optional evaluation context.
///
/// This consolidates the shared logic used by `evaluate()` and `Program.execute()`
/// to keep behavior consistent between the two entrypoints.
fn build_environment<'r>(
    evaluation_context: Option<&Bound<'_, PyAny>>,
    environment: &mut CelContext<'r>,
    resolver_out: &'r mut Option<PyVariableResolver>,
) -> PyResult<()> {
    let mut ctx = context::Context::new(None, None)?;

    // Process the evaluation context if provided
    if let Some(evaluation_context) = evaluation_context {
        // Attempt to extract directly as a Context object
        if let Ok(py_context_ref) = evaluation_context.extract::<PyRef<context::Context>>() {
            // Clone variables and functions into our local Context
            ctx.variables = py_context_ref.variables.clone();
            ctx.functions = py_context_ref.functions.clone();
            if let Some(cb) = py_context_ref.resolver.as_ref() {
                *resolver_out = Some(PyVariableResolver {
                    callback: Python::attach(|py| cb.clone_ref(py)),
                });
            }
        } else if let Ok(py_dict) = evaluation_context.cast::<PyDict>() {
            // User passed in a dict - let's process variables and functions from the dict
            ctx.update(py_dict)?;
        } else {
            return Err(PyValueError::new_err(
                "evaluation_context must be a Context object or a dict",
            ));
        };

        // Add any variables from the processed context. The values are already
        // `cel::Value`s, so `add_variable_from_value` (infallible, `Into<Value>`)
        // is the right entry point — no conversion or error handling needed here.
        for (name, value) in &ctx.variables {
            environment.add_variable_from_value(name.clone(), value.clone());
        }

        // Register Python functions
        for (function_name, py_function) in ctx.functions.iter() {
            // Create a wrapper function
            let py_func_clone = Python::attach(|py| py_function.clone_ref(py));
            let func_name_clone = function_name.clone();

            // Register a wrapper that bridges the CEL call to the Python callable.
            //
            // We take the raw `FunctionContext` (rather than the `Arguments`
            // extractor) so that method-call syntax works: when an expression
            // calls `target.func(a, b)`, CEL puts `target` in `ftx.this` and
            // `[a, b]` in `ftx.args`. We prepend `this` to the argument list so
            // the Python function receives `(target, a, b)`. This means a Python
            // function `f(x, y)` can be invoked as either `f(x, y)` or
            // `x.f(y)` — matching CEL's "receiver call is sugar for a function
            // call with the receiver as the first argument" semantics and the
            // way the standard library extensions (e.g. `list.contains(x)`,
            // `"s".charAt(i)`) are written.
            environment.add_function(
                function_name,
                move |ftx: &FunctionContext| -> Result<Value, ExecutionError> {
                    let py_func = py_func_clone.clone();
                    let func_name = func_name_clone.clone();

                    // Collect the CEL argument values: the method target (if
                    // this was a receiver-style call) first, then the explicit
                    // arguments.
                    let mut cel_args: Vec<Value> = Vec::with_capacity(ftx.args.len() + 1);
                    if let Some(this) = &ftx.this {
                        cel_args.push(this.as_ref().try_into()?);
                    }
                    for arg in ftx.args.iter() {
                        cel_args.push(arg.as_ref().try_into()?);
                    }

                    Python::attach(|py| {
                        // Convert CEL arguments to Python objects
                        let mut py_args = Vec::with_capacity(cel_args.len());
                        for cel_value in cel_args {
                            let py_arg = RustyCelType(cel_value)
                                .into_pyobject(py)
                                .map_err(|e| ExecutionError::FunctionError {
                                    function: func_name.clone(),
                                    message: format!("Failed to convert argument to Python: {e}"),
                                })?
                                .into_any()
                                .unbind();
                            py_args.push(py_arg);
                        }

                        let py_args_tuple = PyTuple::new(py, py_args).map_err(|e| {
                            ExecutionError::FunctionError {
                                function: func_name.clone(),
                                message: format!("Failed to create arguments tuple: {e}"),
                            }
                        })?;

                        // Call the Python function
                        let py_result = py_func.call1(py, py_args_tuple).map_err(|e| {
                            warn!("Python function '{}' failed: {}", func_name, e);
                            ExecutionError::FunctionError {
                                function: func_name.clone(),
                                message: format!("Python function call failed: {e}"),
                            }
                        })?;

                        // Convert the result back to CEL Value
                        let py_result_ref = py_result.bind(py);
                        let cel_value =
                            RustyPyType(py_result_ref).try_into_value().map_err(|e| {
                                ExecutionError::FunctionError {
                                    function: func_name.clone(),
                                    message: format!(
                                        "Failed to convert Python result to CEL value: {e}"
                                    ),
                                }
                            })?;

                        Ok(cel_value)
                    })
                },
            );
        }
    }

    // Attach the lazy resolver if one was provided. The resolver lives in
    // `*resolver_out` (caller-owned), and the cel::Context borrows it for
    // its lifetime `'r`.
    if let Some(resolver) = resolver_out.as_ref() {
        environment.set_variable_resolver(resolver);
    }

    Ok(())
}

/// Human-readable CEL type name for a value (e.g. `int`, `uint`, `string`).
///
/// Used to build type-focused error messages. `Value::type_of()` returns a
/// `ValueType` whose `Display` impl already yields the canonical CEL type name.
fn cel_type_name(value: &Value) -> String {
    value.type_of().to_string()
}

/// A concise, user-facing rendering of a value for error messages.
///
/// Scalars render as their bare value (`5`, `hello`) rather than leaking the
/// internal `Debug` wrapper (`Int(5)`, `String("hello")`); anything else falls
/// back to `Debug`.
fn cel_value_display(value: &Value) -> String {
    match value {
        Value::Int(i) => i.to_string(),
        Value::UInt(u) => u.to_string(),
        Value::Float(f) => f.to_string(),
        Value::Bool(b) => b.to_string(),
        Value::String(s) => s.as_ref().clone(),
        Value::Null => "null".to_string(),
        other => format!("{other:?}"),
    }
}

/// Maps CEL execution errors to the most appropriate Python exception type with
/// an actionable message.
///
/// The goal is that CEL runtime failures surface as the Python exception a
/// developer would expect (`ZeroDivisionError` for `1/0`, `KeyError` for a
/// missing map key, `OverflowError` for integer overflow, and so on) rather
/// than a single opaque error type.
fn map_execution_error_to_python(error: &ExecutionError) -> PyErr {
    match error {
        ExecutionError::UndeclaredReference(name) => {
            PyRuntimeError::new_err(format!(
                "Undefined variable or function: '{name}'. Check that the variable is defined in the context or that the function name is spelled correctly."
            ))
        },
        ExecutionError::UnsupportedBinaryOperator(op, left, right) => {
            let left_type = cel_type_name(left);
            let right_type = cel_type_name(right);
            let symbol = match *op {
                "add" => "+",
                "sub" => "-",
                "mul" => "*",
                "div" => "/",
                "rem" => "%",
                other => other,
            };
            if (left_type == "int" && right_type == "uint")
                || (left_type == "uint" && right_type == "int")
            {
                PyTypeError::new_err(format!(
                    "Cannot mix signed and unsigned integers: {left_type} {symbol} {right_type}. \
                     Convert explicitly with int(value) or uint(value)."
                ))
            } else {
                PyTypeError::new_err(format!(
                    "Unsupported operation: {left_type} {symbol} {right_type}. CEL does not coerce \
                     between types — both operands must be the same type. Convert explicitly with \
                     int(x), uint(x), double(x) or string(x) as appropriate."
                ))
            }
        },
        ExecutionError::UnsupportedIndex(container, index) => {
            PyTypeError::new_err(format!(
                "Cannot index a {} value with a {} key.",
                cel_type_name(container),
                cel_type_name(index)
            ))
        },
        ExecutionError::ValuesNotComparable(left, right) => {
            PyTypeError::new_err(format!(
                "Values of type {} and {} cannot be compared.",
                cel_type_name(left),
                cel_type_name(right)
            ))
        },
        ExecutionError::UnexpectedType { got, want } => {
            PyTypeError::new_err(format!("Unexpected type: got '{got}', want '{want}'."))
        },
        ExecutionError::UnsupportedKeyType(value) => {
            PyTypeError::new_err(format!(
                "Value of type {} cannot be used as a map key. Keys must be int, uint, bool or string.",
                cel_type_name(value)
            ))
        },
        ExecutionError::InvalidArgumentCount { expected, actual } => {
            PyTypeError::new_err(format!(
                "Invalid number of arguments: expected {expected}, got {actual}."
            ))
        },
        ExecutionError::NotSupportedAsMethod { method, target } => {
            PyTypeError::new_err(format!(
                "Method '{method}' is not supported on a {} value.",
                cel_type_name(target)
            ))
        },
        ExecutionError::UnsupportedTargetType { target } => {
            PyTypeError::new_err(format!(
                "Unsupported target type: {} cannot be used here.",
                cel_type_name(target)
            ))
        },
        ExecutionError::MissingArgumentOrTarget => {
            PyTypeError::new_err(
                "A function was called without a required argument or method target.",
            )
        },
        ExecutionError::FunctionError { function, message } => {
            PyRuntimeError::new_err(format!(
                "Function '{function}' error: {message}. Check function arguments and their types."
            ))
        },
        ExecutionError::NoSuchOverload => {
            PyTypeError::new_err(
                "No such overload: the operation is not defined for the given operand types. \
                 CEL does not coerce between types, so common causes are mixing int with uint or \
                 double (1 + 2u, 1 + 2.5), indexing into a string, or calling a function with the \
                 wrong argument types. Convert explicitly with int(x), uint(x), double(x) or \
                 string(x), or check the CEL specification."
            )
        },
        ExecutionError::Overflow(op, left, right) => {
            PyOverflowError::new_err(format!(
                "Arithmetic overflow in '{op}' on {} and {}.",
                cel_value_display(left),
                cel_value_display(right)
            ))
        },
        ExecutionError::DivisionByZero(_) => {
            PyZeroDivisionError::new_err("division by zero in CEL expression")
        },
        ExecutionError::RemainderByZero(_) => {
            PyZeroDivisionError::new_err("modulo by zero in CEL expression")
        },
        ExecutionError::IndexOutOfBounds(value) => {
            PyIndexError::new_err(format!("index out of bounds: {}", cel_value_display(value)))
        },
        ExecutionError::NoSuchKey(name) => {
            PyKeyError::new_err(name.to_string())
        },
        ExecutionError::InternalError(message) => {
            PyRuntimeError::new_err(format!("Internal CEL error: {message}"))
        },
        // `ExecutionError` is `#[non_exhaustive]`; keep a helpful catch-all for any
        // variant added upstream that we do not yet map explicitly.
        _ => PyValueError::new_err(format!(
            "CEL execution error: {error}. This may indicate an unsupported operation or invalid expression."
        )),
    }
}

/// We can't implement TryIntoValue for PyAny, so we implement for our wrapper RustyPyType
impl TryIntoValue for RustyPyType<'_> {
    type Error = CelError;

    fn try_into_value(self) -> Result<Value, Self::Error> {
        let val = match self {
            RustyPyType(pyobject) => {
                if let Ok(py_optional) = pyobject.extract::<PyRef<PyOptionalValue>>() {
                    Ok(py_optional.to_cel_value())
                } else if pyobject.is_none() {
                    Ok(Value::Null)
                } else if let Ok(value) = pyobject.extract::<bool>() {
                    Ok(Value::Bool(value))
                } else if let Ok(value) = pyobject.extract::<i64>() {
                    Ok(Value::Int(value))
                } else if let Ok(value) = pyobject.extract::<u64>() {
                    Ok(Value::UInt(value))
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
                } else if let Ok(value) = pyobject.cast::<PyList>() {
                    let list = value
                        .iter()
                        .map(|item| RustyPyType(&item).try_into_value())
                        .collect::<Result<Vec<Value>, Self::Error>>();
                    list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.cast::<PyTuple>() {
                    let list = value
                        .iter()
                        .map(|item| RustyPyType(&item).try_into_value())
                        .collect::<Result<Vec<Value>, Self::Error>>();
                    list.map(|v| Value::List(Arc::new(v)))
                } else if let Ok(value) = pyobject.cast::<PyDict>() {
                    let py = pyobject.py();
                    let is_exact_dict =
                        pyobject.get_type().as_type_ptr() == PyDict::type_object(py).as_type_ptr();

                    if is_exact_dict {
                        let mut map: HashMap<Key, Value> = HashMap::new();
                        for (key, value) in value.into_iter() {
                            let key = Self::key_from_py(&key)?;
                            let dict_value = RustyPyType(&value).try_into_value().map_err(|e| {
                                CelError::ConversionError(format!(
                                    "Failed to convert PyDict value to Value: {e}"
                                ))
                            })?;
                            map.insert(key, dict_value);
                        }
                        Ok(Value::Map(map.into()))
                    } else {
                        let mapping = pyobject.cast::<PyMapping>().map_err(|e| {
                            CelError::ConversionError(format!(
                                "Failed to cast dict subclass to mapping: {e}"
                            ))
                        })?;
                        Self::mapping_to_value(mapping)
                    }
                } else if let Ok(mapping) = pyobject.cast::<PyMapping>() {
                    Self::mapping_to_value(mapping)
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

/// Evaluate a Common Expression Language (CEL) expression.
///
/// This is the main entry point for the CEL library. It parses, compiles, and
/// evaluates a CEL expression within an optional context, returning the result
/// as a native Python type.
///
/// CEL expressions support a wide range of operations including arithmetic,
/// logical operations, string manipulation, list/map operations, and custom
/// function calls. For detailed language reference, see the CEL specification
/// documentation.
///
/// Args:
///     src (str): The CEL expression to evaluate. Must be a valid CEL expression
///         according to the CEL language specification.
///     evaluation_context (Optional[Union[cel.Context, dict]]): An optional
///         context for the evaluation. This can be either:
///         - A `cel.Context` object (recommended for reusable contexts)
///         - A standard Python dictionary containing variables and functions
///         - None (for expressions that don't require external variables)
///
/// Returns:
///     Union[bool, int, float, str, list, dict, datetime.datetime, bytes, None]:
///         The result of the expression, automatically converted to the appropriate
///         Python type. Common return types include:
///         - bool: For logical expressions (e.g., "1 < 2")
///         - int/float: For arithmetic expressions
///         - str: For string operations
///         - list: For list expressions and operations
///         - dict: For map/object expressions
///         - datetime.datetime: For timestamp operations
///         - bytes: For byte array operations
///         - None: For null values
///
/// Raises:
///     ValueError: If the expression has a syntax error, fails to parse, or
///         is malformed. This includes issues such as:
///         - Unclosed quotes or parentheses
///         - Invalid CEL syntax
///         - Empty expressions
///     TypeError: If an operation is attempted on incompatible types, such as:
///         - Adding incompatible types (e.g., string + int without conversion)
///         - Mixing signed and unsigned integers in arithmetic
///         - Using unsupported operators between specific types
///     RuntimeError: For evaluation errors that occur during execution:
///         - Referencing undefined variables or functions
///         - Errors from custom Python functions
///         - Internal evaluation failures
///
/// Performance Notes:
///     - For multiple evaluations with the same context, use a `cel.Context`
///       object for better performance and memory efficiency.
///     - Complex expressions are compiled once and can be cached internally.
///
/// Examples:
///     Basic arithmetic and logical operations:
///
///     >>> from cel import evaluate
///     >>> evaluate("1 + 2 * 3")
///     7
///     >>> evaluate("'Hello' + ' ' + 'World'")
///     'Hello World'
///     >>> evaluate("[1, 2, 3].size() > 2")
///     True
///
///     Using variables from a dictionary context:
///
///     >>> user_data = {"name": "Alice", "age": 30, "roles": ["admin", "user"]}
///     >>> evaluate("name + ' is ' + string(age) + ' years old'", user_data)
///     'Alice is 30 years old'
///     >>> evaluate("'admin' in roles", user_data)
///     True
///
///     Working with nested data structures:
///
///     >>> context = {
///     ...     "user": {"profile": {"name": "Bob", "verified": True}},
///     ...     "settings": {"theme": "dark", "notifications": False}
///     ... }
///     >>> evaluate("user.profile.verified && settings.theme == 'dark'", context)
///     True
///
///     Using custom Python functions:
///
///     >>> def calculate_discount(price, percentage):
///     ...     return price * (1 - percentage / 100)
///     >>> context = {
///     ...     "price": 100.0,
///     ...     "discount_rate": 15,
///     ...     "calculate_discount": calculate_discount
///     ... }
///     >>> evaluate("calculate_discount(price, discount_rate)", context)
///     85.0
///
///     Error handling example:
///
///     >>> try:
///     ...     evaluate("undefined_variable + 5")
///     ... except RuntimeError as e:
///     ...     print(f"Error: {e}")
///     Error: Undefined variable or function: 'undefined_variable'...
///
///     Using Context object for reusable evaluations:
///
///     >>> from cel import Context
///     >>> context = Context(
///     ...     variables={"base_url": "https://api.example.com"},
///     ...     functions={"len": len}
///     ... )
///     >>> evaluate("base_url + '/users'", context)
///     'https://api.example.com/users'
///     >>> evaluate("len('hello world')", context)
///     11
///
///     Type safety and error handling:
///
///     >>> # Strict CEL mode enforces type compatibility
///     >>> evaluate("1.0 + 2.5")  # Same type - works
///     3.5
///     >>> try:
///     ...     evaluate("1 + 2.5")  # Mixed types - fails
///     ... except TypeError as e:
///     ...     print("Type error:", e)
///     Type error: Unsupported addition operation: Int + Double...
///
///     >>> # Use explicit conversion for mixed arithmetic
///     >>> evaluate("double(1) + 2.5")
///     3.5
///
/// See Also:
///     - cel.Context: For managing reusable evaluation contexts
///     - CEL Language Guide: For comprehensive language documentation
///     - Python API Reference: For detailed API documentation
#[pyfunction(signature = (src, evaluation_context=None))]
fn evaluate(src: String, evaluation_context: Option<&Bound<'_, PyAny>>) -> PyResult<RustyCelType> {
    let mut environment = new_environment();
    let mut resolver_slot: Option<PyVariableResolver> = None;
    build_environment(evaluation_context, &mut environment, &mut resolver_slot)?;

    // Use panic::catch_unwind to handle parser panics gracefully
    let program = panic::catch_unwind(|| Program::compile(&src))
        .map_err(|_| {
            warn!("CEL parser panic for expression: '{}'", src);
            PyValueError::new_err(format!(
                "Failed to parse expression '{src}': Invalid syntax or malformed string"
            ))
        })?
        .map_err(|e| PyValueError::new_err(format!("Failed to parse expression '{src}': {e}")))?;

    // Use panic::catch_unwind to handle execution panics gracefully
    // AssertUnwindSafe is needed because the environment contains function closures
    let result =
        panic::catch_unwind(AssertUnwindSafe(|| program.execute(&environment))).map_err(|_| {
            warn!("CEL execution panic for expression: '{}'", src);
            PyValueError::new_err(format!(
                "Failed to execute expression '{src}': Internal parser error"
            ))
        })?;

    match result {
        Err(error) => Err(map_execution_error_to_python(&error)),
        Ok(value) => Ok(RustyCelType(value)),
    }
}

/// Internal helper to execute a pre-compiled program with the given context.
/// Used by both `evaluate()` (after compiling) and `PyProgram.execute()`.
fn execute_compiled_program(
    program: &Program,
    src: &str,
    evaluation_context: Option<&Bound<'_, PyAny>>,
) -> PyResult<Py<PyAny>> {
    let mut environment = new_environment();
    let mut resolver_slot: Option<PyVariableResolver> = None;
    build_environment(evaluation_context, &mut environment, &mut resolver_slot)?;

    // Use panic::catch_unwind to handle execution panics gracefully
    // AssertUnwindSafe is needed because the environment contains function closures
    let result =
        panic::catch_unwind(AssertUnwindSafe(|| program.execute(&environment))).map_err(|_| {
            warn!("CEL execution panic for expression: '{}'", src);
            PyValueError::new_err(format!(
                "Failed to execute expression '{src}': Internal parser error"
            ))
        })?;

    match result {
        Err(error) => Err(map_execution_error_to_python(&error)),
        Ok(value) => Python::attach(|py| {
            RustyCelType(value)
                .into_pyobject(py)
                .map(|obj| obj.unbind())
        }),
    }
}

#[pymodule]
fn cel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    m.add_function(wrap_pyfunction!(compile, m)?)?;
    m.add_class::<context::Context>()?;
    m.add_class::<PyProgram>()?;
    m.add_class::<PyOptionalValue>()?;
    Ok(())
}
