"""
Type stubs for the CEL Rust extension module.
"""

from typing import Any, Callable, Dict, Literal, Optional, Union, overload

class Context:
    """CEL evaluation context for variables and functions."""

    @overload
    def __init__(self) -> None: ...
    @overload
    def __init__(self, variables: Dict[str, Any]) -> None: ...
    @overload
    def __init__(
        self,
        variables: Optional[Dict[str, Any]] = None,
        *,
        functions: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None: ...
    def add_variable(self, name: str, value: Any) -> None:
        """Add a variable to the context."""
        ...

    def add_function(self, name: str, func: Callable[..., Any]) -> None:
        """Add a function to the context."""
        ...

    def set_variable_resolver(self, resolver: Callable[[str], Any]) -> None:
        """Register a callback for lazy variable resolution.

        The callback receives a variable name and returns the value, or None
        to fall through to variables added via add_variable().
        """
        ...

    def update(self, variables: Dict[str, Any]) -> None:
        """Update context with variables from a dictionary."""
        ...

class Program:
    """Compiled CEL program that can be executed multiple times."""

    @property
    def source(self) -> str:
        """The original CEL source this program was compiled from."""
        ...

    def execute(self, context: Optional[Union[Dict[str, Any], Context]] = None) -> Any:
        """Execute the compiled program with an optional context."""
        ...

    def variables(self) -> list[str]:
        """Return the sorted variable names this expression references.

        Performs static analysis without evaluating the expression. Names bound
        by comprehension macros (e.g. the ``x`` in ``[1, 2].map(x, x * 2)``) are
        included, since they appear as identifiers.
        """
        ...

    def functions(self) -> list[str]:
        """Return the sorted function/operator names this expression references.

        Includes named functions (``size``) and CEL operator overload
        identifiers for operators used in the expression (e.g. ``_+_``).
        """
        ...

    def references(self) -> Dict[str, list[str]]:
        """Return ``{"variables": [...], "functions": [...]}`` for this expression."""
        ...

def compile(expression: str) -> Program:
    """Compile a CEL expression into a reusable Program object."""
    ...

class OptionalValue:
    """Wrapper for CEL optional values."""

    @classmethod
    def of(cls, value: Any) -> OptionalValue: ...
    @classmethod
    def none(cls) -> OptionalValue: ...
    def has_value(self) -> bool: ...
    def value(self) -> Any: ...
    def or_value(self, default: Any) -> Any: ...
    def or_optional(self, other: OptionalValue) -> OptionalValue: ...

def evaluate(
    expression: str,
    context: Optional[Union[Dict[str, Any], Context]] = None,
) -> Any:
    """
    Evaluate a CEL expression.

    Args:
        expression: The CEL expression to evaluate
        context: Optional context with variables and functions

    Returns:
        The result of evaluating the expression
    """
    ...
