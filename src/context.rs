use cel_interpreter::objects::TryIntoValue;
use cel_interpreter::Value;
use pyo3::exceptions::PyValueError;
use pyo3::prelude::*;
use pyo3::types::PyDict;
use std::collections::HashMap;

#[pyo3::pyclass]
#[doc = "Context for CEL expression evaluation containing variables and functions.

A Context object holds the variables and custom functions that can be used when 
evaluating CEL expressions. Variables are key-value pairs where keys are strings
and values can be any supported Python type. Functions are callable Python objects
that can be invoked from within CEL expressions.

Example:
    >>> import cel
    >>> context = cel.Context()
    >>> context.add_variable('name', 'world') 
    >>> context.add_function('greet', lambda x: f'Hello {x}!')
    >>> cel.evaluate('greet(name)', context)
    'Hello world!'
"]
pub struct Context {
    pub variables: HashMap<String, Value>,
    pub functions: HashMap<String, Py<PyAny>>,
}

#[pyo3::pymethods]
impl Context {
    #[new]
    #[pyo3(signature = (variables=None, functions=None))]
    #[doc = "Create a new Context with optional variables and functions.
    
    Args:
        variables: Optional dictionary of variable names to values
        functions: Optional dictionary of function names to callable objects
        
    Returns:
        A new Context instance ready for CEL evaluation
    "]
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

    #[doc = "Add a custom function to the context.
    
    Args:
        name: The function name as it will appear in CEL expressions
        function: A callable Python object (function, lambda, etc.)
        
    Example:
        >>> context.add_function('double', lambda x: x * 2)
        >>> cel.evaluate('double(21)', context)
        42
    "]
    fn add_function(&mut self, name: String, function: Py<PyAny>) {
        self.functions.insert(name, function);
    }

    #[doc = "Add a variable to the context.
    
    Args:
        name: The variable name as it will appear in CEL expressions
        value: The variable value (any supported Python type)
        
    Example:
        >>> context.add_variable('user_age', 25)
        >>> cel.evaluate('user_age > 18', context)
        True
    "]
    pub fn add_variable(&mut self, name: String, value: &Bound<'_, PyAny>) -> PyResult<()> {
        let value = crate::RustyPyType(value).try_into_value().map_err(|e| {
            pyo3::exceptions::PyValueError::new_err(format!(
                "Failed to convert variable '{}': {}",
                name, e
            ))
        })?;
        self.variables.insert(name, value);
        Ok(())
    }

    #[doc = "Update the context with variables and functions from a dictionary.
    
    Callable values are automatically added as functions, while non-callable 
    values are added as variables.
    
    Args:
        variables: Dictionary containing variable names/values and function names/callables
        
    Example:
        >>> context.update({'name': 'Alice', 'greet': lambda: 'Hello!'})
        >>> cel.evaluate('greet() + name', context)  
        'Hello!Alice'
    "]
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
