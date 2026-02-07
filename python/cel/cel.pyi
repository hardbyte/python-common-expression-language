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

    def update(self, variables: Dict[str, Any]) -> None:
        """Update context with variables from a dictionary."""
        ...

class Program:
    """Compiled CEL program that can be executed multiple times."""

    def execute(self, context: Optional[Union[Dict[str, Any], Context]] = None) -> Any:
        """Execute the compiled program with an optional context."""
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
