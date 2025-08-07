use ::cel::objects::TryIntoValue;
use ::cel::Value;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

#[pyo3::pyclass]
/// Manages the evaluation environment for CEL expressions.
///
/// The `Context` class provides a structured, efficient way to handle variables
/// and custom functions for CEL expression evaluation. It is the recommended
/// approach for managing complex evaluation environments and offers better
/// performance than using dictionaries for repeated evaluations.
///
/// Key Benefits:
/// - **Type Safety**: Automatic conversion and validation of Python types to CEL types
/// - **Performance**: Optimized for reuse across multiple evaluations
/// - **Flexibility**: Support for both variables and custom Python functions
/// - **Memory Efficiency**: Shared context reduces overhead for multiple expressions
///
/// Use this class when you need to:
/// - Register custom Python functions for use in CEL expressions
/// - Build a reusable context for multiple evaluations with the same variables
/// - Dynamically add, update, or manage variables and functions
/// - Ensure type safety and proper error handling for context data
/// - Optimize performance for applications with frequent CEL evaluations
///
/// Attributes:
///     variables (dict): A dictionary mapping variable names (str) to their
///         values (automatically converted to appropriate CEL types).
///     functions (dict): A dictionary mapping function names (str) to their
///         corresponding Python callable objects.
///
/// Thread Safety:
///     Context objects are not thread-safe. Create separate Context instances
///     for concurrent use or implement your own synchronization.
///
/// Performance Tips:
///     - Reuse Context objects for multiple evaluations when possible
///     - Pre-populate Context with all needed variables and functions
///     - Avoid frequent add_variable/add_function calls in hot code paths
pub struct Context {
    pub variables: HashMap<String, Value>,
    pub functions: HashMap<String, Py<PyAny>>,
}

#[pyo3::pymethods]
impl Context {
    #[new]
    #[pyo3(signature = (variables=None, functions=None))]
    /// Creates a new `Context` object.
    ///
    /// Initializes a CEL evaluation context with optional variables and functions.
    /// This constructor provides a convenient way to set up a complete evaluation
    /// environment in a single call.
    ///
    /// Args:
    ///     variables (Optional[dict]): A dictionary of initial variables to
    ///         populate the context with. Keys must be strings (variable names),
    ///         and values can be any Python type supported by CEL (bool, int,
    ///         float, str, list, dict, datetime, bytes). Values are automatically
    ///         converted to their corresponding CEL types.
    ///     functions (Optional[dict]): A dictionary of initial custom functions
    ///         to register. Keys are the function names as they will appear in
    ///         CEL expressions (must be strings), and values are the corresponding
    ///         Python callable objects (functions, methods, or any callable).
    ///
    /// Raises:
    ///     ValueError: If variable names are not strings, or if variable values
    ///         cannot be converted to supported CEL types.
    ///
    /// Examples:
    ///     Creating an empty context:
    ///
    ///     >>> from cel import Context
    ///     >>> context = Context()
    ///
    ///     Creating a context with variables:
    ///
    ///     >>> context = Context(variables={
    ///     ...     "user_id": 123,
    ///     ...     "user_name": "alice",
    ///     ...     "permissions": ["read", "write"],
    ///     ...     "metadata": {"created": "2023-01-01", "active": True}
    ///     ... })
    ///
    ///     Creating a context with custom functions:
    ///
    ///     >>> def greet(name):
    ///     ...     return f"Hello, {name}!"
    ///     >>> def calculate_tax(amount, rate=0.1):
    ///     ...     return amount * rate
    ///     >>>
    ///     >>> context = Context(functions={
    ///     ...     "greet": greet,
    ///     ...     "tax": calculate_tax
    ///     ... })
    ///
    ///     Creating a complete context with both variables and functions:
    ///
    ///     >>> context = Context(
    ///     ...     variables={
    ///     ...         "product_price": 99.99,
    ///     ...         "tax_rate": 0.08,
    ///     ...         "user_name": "Bob"
    ///     ...     },
    ///     ...     functions={
    ///     ...         "greet": lambda name: f"Hi {name}!",
    ///     ...         "format_currency": lambda x: f"${x:.2f}"
    ///     ...     }
    ///     ... )
    ///     >>> from cel import evaluate
    ///     >>> evaluate("greet(user_name)", context)
    ///     'Hi Bob!'
    ///     >>> evaluate("format_currency(product_price * (1 + tax_rate))", context)
    ///     '$107.99'
    pub fn new(
        variables: Option<&Bound<'_, PyDict>>,
        functions: Option<&Bound<'_, PyDict>>,
    ) -> PyResult<Self> {
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

    /// Registers a Python function for use within CEL expressions.
    ///
    /// The registered function becomes available as a native CEL function and can
    /// be called with the same syntax as built-in CEL functions. Function arguments
    /// are automatically converted from CEL types to Python types, and return values
    /// are converted back to CEL types.
    ///
    /// Function Requirements:
    /// - Must be a Python callable (function, method, lambda, or callable object)
    /// - Arguments should accept CEL-compatible Python types
    /// - Return value must be convertible to a CEL type
    /// - Should handle potential type conversion errors gracefully
    ///
    /// Args:
    ///     name (str): The name of the function as it will be called from CEL
    ///         expressions. Must be a valid CEL identifier (alphanumeric and
    ///         underscores, starting with a letter or underscore).
    ///     function (Callable): The Python function or callable to register.
    ///         Can be a function, method, lambda, or any callable object.
    ///
    /// Examples:
    ///     Registering built-in Python functions:
    ///
    ///     >>> from cel import Context, evaluate
    ///     >>> context = Context()
    ///     >>> context.add_function("string_length", len)
    ///     >>> context.add_function("absolute_value", abs)
    ///     >>> evaluate('string_length("hello world")', context)
    ///     11
    ///     >>> evaluate('absolute_value(-42)', context)
    ///     42
    ///
    ///     Registering custom functions:
    ///
    ///     >>> def is_valid_email(email):
    ///     ...     return "@" in email and "." in email
    ///     >>> def calculate_discount(price, percentage):
    ///     ...     return price * (percentage / 100.0)
    ///     >>>
    ///     >>> context.add_function("is_email", is_valid_email)
    ///     >>> context.add_function("discount", calculate_discount)
    ///     >>> evaluate('is_email("user@example.com")', context)
    ///     True
    ///     >>> evaluate('discount(100.0, 15)', context)
    ///     15.0
    ///
    ///     Registering lambda functions:
    ///
    ///     >>> context.add_function("square", lambda x: x * x)
    ///     >>> context.add_function("greeting", lambda name: f"Welcome, {name}!")
    ///     >>> evaluate('square(7)', context)
    ///     49
    ///
    ///     Registering methods from objects:
    ///
    ///     >>> import re
    ///     >>> context.add_function("regex_match", re.match)
    ///     >>> # Note: This would need proper error handling in practice
    fn add_function(&mut self, name: String, function: Py<PyAny>) {
        self.functions.insert(name, function);
    }

    /// Adds a variable to the context.
    ///
    /// Variables added to the context become available for use in CEL expressions.
    /// The value is automatically converted from Python types to the corresponding
    /// CEL types. If a variable with the same name already exists, it will be
    /// overwritten with the new value.
    ///
    /// Supported Python Types and Their CEL Equivalents:
    /// - bool → CEL bool
    /// - int → CEL int (signed 64-bit)
    /// - float → CEL double
    /// - str → CEL string
    /// - list/tuple → CEL list
    /// - dict → CEL map
    /// - datetime.datetime → CEL timestamp
    /// - datetime.timedelta → CEL duration
    /// - bytes/bytearray → CEL bytes
    /// - None → CEL null
    ///
    /// Args:
    ///     name (str): The name of the variable as it will be used in CEL
    ///         expressions. Must be a valid CEL identifier (alphanumeric
    ///         characters and underscores, starting with a letter or underscore).
    ///     value (Any): The Python value of the variable. Must be one of the
    ///         supported Python types listed above.
    ///
    /// Raises:
    ///     ValueError: If the value cannot be converted to a supported CEL type,
    ///         or if the variable name is not a string.
    ///
    /// Examples:
    ///     Adding basic data types:
    ///
    ///     >>> from cel import Context, evaluate
    ///     >>> context = Context()
    ///     >>> context.add_variable("user_id", 123)
    ///     >>> context.add_variable("username", "alice")
    ///     >>> context.add_variable("is_active", True)
    ///     >>> evaluate("username + ' (ID: ' + string(user_id) + ')'", context)
    ///     'alice (ID: 123)'
    ///
    ///     Adding collections:
    ///
    ///     >>> context.add_variable("permissions", ["read", "write", "admin"])
    ///     >>> context.add_variable("user_data", {
    ///     ...     "name": "Alice",
    ///     ...     "department": "Engineering",
    ///     ...     "level": 5
    ///     ... })
    ///     >>> evaluate("'admin' in permissions", context)
    ///     True
    ///     >>> evaluate("user_data.department", context)
    ///     'Engineering'
    ///
    ///     Adding datetime objects:
    ///
    ///     >>> from datetime import datetime, timedelta
    ///     >>> context.add_variable("now", datetime.now())
    ///     >>> context.add_variable("one_hour", timedelta(hours=1))
    ///
    ///     Overwriting existing variables:
    ///
    ///     >>> context.add_variable("counter", 1)
    ///     >>> evaluate("counter", context)
    ///     1
    ///     >>> context.add_variable("counter", 2)  # Overwrites previous value
    ///     >>> evaluate("counter", context)
    ///     2
    pub fn add_variable(&mut self, name: String, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let value = crate::RustyPyType(value).try_into_value().map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "Failed to convert variable '{name}': {e}"
            ))
        })?;
        self.variables.insert(name, value);
        Ok(())
    }

    /// Updates the context from a dictionary of variables and functions.
    ///
    /// This method provides a convenient way to populate the context from a single
    /// dictionary. It automatically distinguishes between variables and functions
    /// based on whether values are callable. Non-callable values are added as
    /// variables, while callable values are registered as functions.
    ///
    /// This is particularly useful for:
    /// - Bulk updates to context data
    /// - Dynamic context construction from configuration
    /// - Integration with existing codebases that use dictionaries
    /// - Merging multiple data sources into a single context
    ///
    /// Behavior:
    /// - Callable values (functions, lambdas, methods) → registered as functions
    /// - Non-callable values → added as variables
    /// - Existing variables/functions with the same names are overwritten
    /// - Keys must be strings (valid CEL identifiers)
    ///
    /// Args:
    ///     variables (dict): A dictionary where keys are strings representing
    ///         names for variables or functions. Values can be either:
    ///         - Data values (for variables): any CEL-compatible Python type
    ///         - Callable objects (for functions): functions, methods, lambdas
    ///
    /// Raises:
    ///     ValueError: If any key is not a string, or if a non-callable value
    ///         cannot be converted to a supported CEL type.
    ///
    /// Examples:
    ///     Basic mixed update with variables and functions:
    ///
    ///     >>> from cel import Context, evaluate
    ///     >>> context = Context()
    ///     >>> def say_hi(name):
    ///     ...     return f"Hi, {name}!"
    ///     >>> def calculate_total(price, tax_rate=0.1):
    ///     ...     return price * (1 + tax_rate)
    ///     >>>
    ///     >>> context.update({
    ///     ...     "user_name": "Alice",
    ///     ...     "user_id": 12345,
    ///     ...     "is_premium": True,
    ///     ...     "greet": say_hi,
    ///     ...     "total": calculate_total
    ///     ... })
    ///     >>> evaluate('greet(user_name)', context)
    ///     'Hi, Alice!'
    ///     >>> evaluate('total(99.99)', context)
    ///     109.989
    ///
    ///     Updating with built-in functions:
    ///
    ///     >>> context.update({
    ///     ...     "numbers": [1, -2, 3, -4, 5],
    ///     ...     "text": "Hello World",
    ///     ...     "length": len,
    ///     ...     "abs_value": abs,
    ///     ...     "upper": str.upper
    ///     ... })
    ///     >>> evaluate('length(text)', context)
    ///     11
    ///     >>> evaluate('abs_value(-42)', context)
    ///     42
    ///
    ///     Dynamic context from configuration:
    ///
    ///     >>> config = {
    ///     ...     "api_endpoint": "https://api.example.com",
    ///     ...     "timeout": 30,
    ///     ...     "retries": 3,
    ///     ...     "format_url": lambda base, path: f"{base}/{path.strip('/')}"
    ///     ... }
    ///     >>> context.update(config)
    ///     >>> evaluate('format_url(api_endpoint, "/users/123")', context)
    ///     'https://api.example.com/users/123'
    ///
    ///     Merging multiple data sources:
    ///
    ///     >>> user_data = {"name": "Bob", "age": 30}
    ///     >>> system_config = {"debug": True, "version": "1.0"}
    ///     >>> utilities = {"join": "-".join, "format": "{:.2f}".format}
    ///     >>>
    ///     >>> context.update({**user_data, **system_config, **utilities})
    ///     >>> evaluate('join(["user", name, string(age)])', context)
    ///     'user-Bob-30'
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
