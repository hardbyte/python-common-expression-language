mod context;

use ::cel::objects::{Key, TryIntoValue};
use ::cel::{Context as CelContext, ExecutionError, Program, Value};
use log::{debug, warn};
use pyo3::exceptions::{PyRuntimeError, PyTypeError, PyValueError};
use pyo3::prelude::*;
use pyo3::BoundObject;
use std::panic::{self, AssertUnwindSafe};

use chrono::{DateTime, Duration as ChronoDuration, Offset, TimeZone};
use pyo3::types::{PyBool, PyBytes, PyDict, PyList, PyTuple};

use std::collections::HashMap;
use std::error::Error;
use std::fmt;
use std::sync::Arc;

#[derive(Clone, Debug, PartialEq)]
pub enum EvaluationMode {
    PythonCompatible,
    Strict,
}

impl<'py> FromPyObject<'py> for EvaluationMode {
    fn extract_bound(ob: &Bound<'py, PyAny>) -> PyResult<Self> {
        let s: String = ob.extract()?;
        match s.as_str() {
            "python" => Ok(EvaluationMode::PythonCompatible),
            "strict" => Ok(EvaluationMode::Strict),
            _ => Err(PyTypeError::new_err(format!(
                "Invalid EvaluationMode: expected 'python' or 'strict', got '{s}'"
            ))),
        }
    }
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

/// AST-based preprocessing to promote integer literals to floats
fn preprocess_expression_for_mixed_arithmetic_always(expr: &str) -> String {
    // Try to parse the expression using CEL's parser
    match Program::compile(expr) {
        Ok(program) => {
            // Walk the AST and promote integer literals to floats
            let modified_expr = promote_integers_in_ast(program.expression());

            // If we hit unsupported constructs (like comprehensions), fall back
            if modified_expr.contains("/* comprehension fallback */")
                || modified_expr.contains("/* unsupported expression */")
            {
                warn!("AST promotion encountered unsupported constructs, falling back to original string");
                return expr.to_string();
            }

            modified_expr
        }
        Err(_) => {
            // If parsing fails, fall back to the original string
            // This should rarely happen since we've already validated the expression
            warn!(
                "Failed to parse expression for AST-based promotion: {}",
                expr
            );
            expr.to_string()
        }
    }
}

/// Recursively walks the AST and converts integer literals to floats while preserving the expression structure
fn promote_integers_in_ast(expr: &::cel::parser::Expression) -> String {
    ast_to_string_with_promotion(&expr.expr)
}

/// Converts an AST expression to string, promoting integer literals to floats
fn ast_to_string_with_promotion(expr: &::cel::common::ast::Expr) -> String {
    use ::cel::common::ast::Expr;
    use ::cel::common::value::CelVal;

    match expr {
        Expr::Literal(CelVal::Int(value)) => {
            // Promote integer literals to floats
            format!("{}.0", value)
        }
        Expr::Literal(CelVal::Double(value)) => {
            // Ensure float formatting preserves decimal point for whole numbers
            if value.fract() == 0.0 {
                format!("{:.1}", value) // Force one decimal place
            } else {
                format!("{}", value)
            }
        }
        Expr::Literal(CelVal::String(value)) => {
            // Preserve string literals exactly - this fixes the original issue
            format!("\"{}\"", escape_string(value))
        }
        Expr::Literal(CelVal::Boolean(value)) => {
            format!("{}", value)
        }
        Expr::Literal(CelVal::Null) => "null".to_string(),
        Expr::Literal(CelVal::Bytes(value)) => {
            format!("b\"{}\"", escape_bytes(value))
        }
        Expr::Ident(name) => name.clone(),
        Expr::Call(call_expr) => {
            // Handle operators specially
            match call_expr.func_name.as_str() {
                // Binary operators
                "_+_" => format!(
                    "({} + {})",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_-_" => format!(
                    "({} - {})",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_*_" => format!(
                    "({} * {})",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_/_" => format!(
                    "({} / {})",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_%_" => format!(
                    "({} % {})",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_==_" => format!(
                    "{} == {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_!=_" => format!(
                    "{} != {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_<_" => format!(
                    "{} < {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_<=_" => format!(
                    "{} <= {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_>_" => format!(
                    "{} > {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_>=_" => format!(
                    "{} >= {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_&&_" => format!(
                    "{} && {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                "_||_" => format!(
                    "{} || {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr)
                ),
                // Unary operators
                "!_" => format!("!{}", ast_to_string_with_promotion(&call_expr.args[0].expr)),
                "-_" => format!("-{}", ast_to_string_with_promotion(&call_expr.args[0].expr)),
                // Ternary operator
                "_?_:_" => format!(
                    "{} ? {} : {}",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_with_promotion(&call_expr.args[1].expr),
                    ast_to_string_with_promotion(&call_expr.args[2].expr)
                ),
                // Index operator - keep indices as integers!
                "_[_]" => format!(
                    "{}[{}]",
                    ast_to_string_with_promotion(&call_expr.args[0].expr),
                    ast_to_string_preserve_integers(&call_expr.args[1].expr)
                ),
                // Regular function calls
                _ => {
                    let mut result = String::new();

                    // Handle target (for method calls like obj.method())
                    if let Some(target) = &call_expr.target {
                        result.push_str(&ast_to_string_with_promotion(&target.expr));
                        result.push('.');
                    }

                    result.push_str(&call_expr.func_name);
                    result.push('(');

                    for (i, arg) in call_expr.args.iter().enumerate() {
                        if i > 0 {
                            result.push_str(", ");
                        }
                        result.push_str(&ast_to_string_with_promotion(&arg.expr));
                    }

                    result.push(')');
                    result
                }
            }
        }
        Expr::Select(select_expr) => {
            format!(
                "{}.{}",
                ast_to_string_with_promotion(&select_expr.operand.expr),
                select_expr.field
            )
        }
        Expr::List(list_expr) => {
            let mut result = String::from("[");
            for (i, element) in list_expr.elements.iter().enumerate() {
                if i > 0 {
                    result.push_str(", ");
                }
                result.push_str(&ast_to_string_with_promotion(&element.expr));
            }
            result.push(']');
            result
        }
        Expr::Map(map_expr) => {
            let mut result = String::from("{");
            for (i, entry) in map_expr.entries.iter().enumerate() {
                if i > 0 {
                    result.push_str(", ");
                }
                if let ::cel::common::ast::EntryExpr::MapEntry(map_entry) = &entry.expr {
                    result.push_str(&ast_to_string_with_promotion(&map_entry.key.expr));
                    result.push_str(": ");
                    result.push_str(&ast_to_string_with_promotion(&map_entry.value.expr));
                }
            }
            result.push('}');
            result
        }
        Expr::Comprehension(_) => {
            // Comprehensions are too complex to reliably reconstruct
            // Fall back to original string for these cases
            warn!("Comprehension expressions are not supported in AST promotion - falling back to original string");
            return "/* comprehension fallback */".to_string();
        }
        // Handle other expression types as needed
        _ => {
            // For unsupported expression types, we should implement them
            // For now, return a placeholder to avoid compilation errors
            warn!("Unsupported AST node type in promotion: {:?}", expr);
            "/* unsupported expression */".to_string()
        }
    }
}

/// Escape string content for proper representation
fn escape_string(s: &str) -> String {
    s.chars()
        .map(|c| match c {
            '"' => "\\\"".to_string(),
            '\\' => "\\\\".to_string(),
            '\n' => "\\n".to_string(),
            '\r' => "\\r".to_string(),
            '\t' => "\\t".to_string(),
            c => c.to_string(),
        })
        .collect()
}

/// Converts an AST expression to string WITHOUT promoting integers (for array indices)
fn ast_to_string_preserve_integers(expr: &::cel::common::ast::Expr) -> String {
    use ::cel::common::ast::Expr;
    use ::cel::common::value::CelVal;

    match expr {
        Expr::Literal(CelVal::Int(value)) => {
            // Keep integers as integers for array indices
            format!("{}", value)
        }
        // For other types, delegate to the regular promotion function
        _ => ast_to_string_with_promotion(expr),
    }
}

/// Escape bytes content for proper representation
fn escape_bytes(bytes: &[u8]) -> String {
    bytes
        .iter()
        .map(|&b| {
            if b.is_ascii_graphic() && b != b'"' && b != b'\\' {
                (b as char).to_string()
            } else {
                format!("\\x{:02x}", b)
            }
        })
        .collect()
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
///     mode (Union[str, cel.EvaluationMode]): The evaluation mode to use.
///         Defaults to "python". Can be:
///         - "python" or EvaluationMode.PYTHON: Enables Python-friendly type
///           promotions (e.g., int -> float) for better mixed arithmetic compatibility
///         - "strict" or EvaluationMode.STRICT: Enforces strict CEL type rules
///           with no automatic coercion to match WebAssembly behavior
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
///     >>> from cel import Context, EvaluationMode
///     >>> context = Context(
///     ...     variables={"base_url": "https://api.example.com"},
///     ...     functions={"len": len}
///     ... )
///     >>> evaluate("base_url + '/users'", context)
///     'https://api.example.com/users'
///     >>> evaluate("len('hello world')", context)
///     11
///
///     Using different evaluation modes:
///
///     >>> # Python mode (default) - allows mixed arithmetic
///     >>> evaluate("1 + 2.5")
///     3.5
///     >>> evaluate("1 + 2.5", mode=EvaluationMode.PYTHON)
///     3.5
///     >>> # Strict mode - enforces type matching
///     >>> try:
///     ...     evaluate("1 + 2.5", mode=EvaluationMode.STRICT)
///     ... except TypeError as e:
///     ...     print("Strict mode error:", e)
///     Strict mode error: Unsupported addition operation: Int + Double...
///
/// See Also:
///     - cel.Context: For managing reusable evaluation contexts
///     - CEL Language Guide: For comprehensive language documentation
///     - Python API Reference: For detailed API documentation
#[pyfunction(signature = (src, evaluation_context=None, mode=None))]
fn evaluate(
    src: String,
    evaluation_context: Option<&Bound<'_, PyAny>>,
    mode: Option<EvaluationMode>,
) -> PyResult<RustyCelType> {
    // Use PythonCompatible as default if mode is not provided
    let mode = mode.unwrap_or(EvaluationMode::PythonCompatible);

    let mut environment = CelContext::default();
    let mut ctx = context::Context::new(None, None)?;
    let mut variables_for_env = HashMap::new();

    // Custom Rust functions can also be added to the environment...
    //environment.add_function("add", |a: i64, b: i64| a + b);

    // Process the evaluation context if provided
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

        variables_for_env = ctx.variables.clone();
    }

    // Apply type promotion logic based on evaluation mode (consolidated)
    let processed_src = match mode {
        EvaluationMode::PythonCompatible => {
            // Check if we should promote integers to floats for better compatibility
            let should_promote = should_promote_integers_to_floats(&variables_for_env)
                || expression_has_mixed_numeric_literals(&src);

            if should_promote {
                // Promote integers in context if we have one
                if !variables_for_env.is_empty() {
                    promote_integers_in_context(&mut variables_for_env);
                }
                // Always preprocess the expression when promoting types
                preprocess_expression_for_mixed_arithmetic_always(&src)
            } else if expression_has_mixed_numeric_literals(&src) {
                // Preprocess expression even without context if it has mixed literals
                preprocess_expression_for_mixed_arithmetic_always(&src)
            } else {
                src.clone()
            }
        }
        EvaluationMode::Strict => {
            // Do nothing - preserve strict type behavior with no promotions or rewriting
            src.clone()
        }
    };

    // Use panic::catch_unwind to handle parser panics gracefully
    let program = panic::catch_unwind(|| Program::compile(&processed_src))
        .map_err(|_| {
            PyValueError::new_err(format!(
                "Failed to parse expression '{src}': Invalid syntax or malformed string"
            ))
        })?
        .map_err(|e| PyValueError::new_err(format!("Failed to compile expression '{src}': {e}")))?;

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

        // Register Python functions
        for (function_name, py_function) in ctx.functions.iter() {
            // Create a wrapper function
            let py_func_clone = Python::with_gil(|py| py_function.clone_ref(py));
            let func_name_clone = function_name.clone();

            // Register a function that takes Arguments (variadic) and returns a Value
            environment.add_function(
                function_name,
                move |args: ::cel::extractors::Arguments| -> Result<Value, ExecutionError> {
                    let py_func = py_func_clone.clone();
                    let func_name = func_name_clone.clone();

                    Python::with_gil(|py| {
                        // Convert CEL arguments to Python objects
                        let mut py_args = Vec::new();
                        for cel_value in args.0.iter() {
                            let py_arg = RustyCelType(cel_value.clone())
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

    // Use panic::catch_unwind to handle execution panics gracefully
    // AssertUnwindSafe is needed because the environment contains function closures
    let result =
        panic::catch_unwind(AssertUnwindSafe(|| program.execute(&environment))).map_err(|_| {
            PyValueError::new_err(format!(
                "Failed to execute expression '{src}': Internal parser error"
            ))
        })?;

    match result {
        Err(error) => {
            warn!("An error occurred during execution");
            warn!("Execution error: {error:?}");
            Err(map_execution_error_to_python(&error))
        }

        Ok(value) => Ok(RustyCelType(value)),
    }
}

#[pymodule]
fn cel(_py: Python<'_>, m: &Bound<'_, PyModule>) -> PyResult<()> {
    pyo3_log::init();

    m.add_function(wrap_pyfunction!(evaluate, m)?)?;
    m.add_class::<context::Context>()?;
    Ok(())
}
