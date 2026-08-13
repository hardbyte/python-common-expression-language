use ::cel::extractors::Arguments;
use ::cel::objects::TryIntoValue;
use ::cel::{Context as CelContext, ExecutionError, PreparedValue, Value};
use pyo3::exceptions::PyTypeError;
use pyo3::prelude::*;
use pyo3::types::PyTuple;

use crate::{RustyCelType, RustyPyType};

/// An opaque, immutable CEL value prepared for inexpensive context binding.
#[pyclass(name = "PreparedValue", frozen)]
pub struct PyPreparedValue {
    pub(crate) inner: PreparedValue,
}

impl PyPreparedValue {
    pub(crate) fn new(inner: PreparedValue) -> Self {
        Self { inner }
    }
}

#[pymethods]
impl PyPreparedValue {
    fn __repr__(&self) -> String {
        format!("PreparedValue(type='{}')", self.inner.type_name())
    }
}

/// Context is a reusable native CEL evaluation context for expressions.
///
/// Its variables must be converted with `cel.prepare()` before they are added,
/// and its functions are registered as persistent Python callback adapters.
/// The context stores prepared values and Python function adapters directly;
/// executing an expression borrows this native context without rebuilding it.
#[pyclass]
pub struct Context {
    pub(crate) inner: CelContext<'static>,
}

#[pymethods]
impl Context {
    #[new]
    pub fn new() -> Self {
        Self {
            inner: CelContext::default(),
        }
    }

    /// Add or replace the prepared variable binding identified by `name`.
    ///
    /// The value must be returned by `cel.prepare`; raw Python values are not
    /// converted implicitly.
    pub fn add_variable(&mut self, name: String, value: PyRef<'_, PyPreparedValue>) {
        self.inner.add_prepared_variable(name, value.inner.clone());
    }

    /// Register the callable `function` under the CEL function `name`.
    ///
    /// The Python-to-CEL adapter is installed once and reused by every
    /// expression execution.
    pub fn add_function(
        &mut self,
        py: Python<'_>,
        name: String,
        function: Py<PyAny>,
    ) -> PyResult<()> {
        if !function.bind(py).is_callable() {
            return Err(PyTypeError::new_err("function must be callable"));
        }

        let function_name = name.clone();
        self.inner.add_function(
            &name,
            move |Arguments(args): Arguments| -> Result<Value, ExecutionError> {
                Python::attach(|py| {
                    let py_args = args
                        .iter()
                        .map(|value| {
                            RustyCelType(value.clone())
                                .into_pyobject(py)
                                .map(Bound::unbind)
                                .map_err(|error| ExecutionError::FunctionError {
                                    function: function_name.clone(),
                                    message: format!(
                                        "failed to convert argument to Python: {error}"
                                    ),
                                })
                        })
                        .collect::<Result<Vec<_>, _>>()?;
                    let py_args = PyTuple::new(py, py_args).map_err(|error| {
                        ExecutionError::FunctionError {
                            function: function_name.clone(),
                            message: format!("failed to create argument tuple: {error}"),
                        }
                    })?;
                    let result = function.call1(py, py_args).map_err(|error| {
                        ExecutionError::FunctionError {
                            function: function_name.clone(),
                            message: format!("Python function call failed: {error}"),
                        }
                    })?;

                    RustyPyType(result.bind(py))
                        .try_into_value()
                        .map_err(|error| ExecutionError::FunctionError {
                            function: function_name.clone(),
                            message: format!("failed to convert Python result to CEL: {error}"),
                        })
                })
            },
        );
        Ok(())
    }

    fn __repr__(&self) -> &'static str {
        "Context()"
    }
}

impl Default for Context {
    fn default() -> Self {
        Self::new()
    }
}
