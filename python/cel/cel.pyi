"""
Type stubs for the CEL Rust extension module.

Parameter names match the runtime signatures exposed by PyO3 (see
``cel.evaluate.__text_signature__``), so keyword calls that type-check also
run, and vice versa.
"""

from typing import Any, Callable, Dict, Optional, Union

class Context:
    """CEL evaluation context for variables and functions."""

    def __init__(
        self,
        variables: Optional[Dict[str, Any]] = None,
        functions: Optional[Dict[str, Callable[..., Any]]] = None,
    ) -> None: ...
    @property
    def variables(self) -> Dict[str, Any]:
        """The registered variables, as a new dict of Python values.

        Values come back through the same CEL-to-Python conversion evaluation
        results use, so a variable added as a tuple reads back as a list.
        Mutating the returned dict does not change the context; use
        ``add_variable()`` or ``update()``.
        """
        ...

    @property
    def functions(self) -> Dict[str, Callable[..., Any]]:
        """The registered functions, as a new dict of name to callable.

        Mutating the returned dict does not change the context; use
        ``add_function()`` or ``update()``.
        """
        ...

    def add_variable(self, name: str, value: Any) -> None:
        """Add a variable to the context."""
        ...

    def add_function(self, name: str, function: Callable[..., Any]) -> None:
        """Add a function to the context."""
        ...

    def set_variable_resolver(self, resolver: Callable[[str], Any]) -> None:
        """Register a callback for lazy variable resolution.

        The callback receives a variable name and returns the value, or None
        to fall through to variables added via add_variable().
        """
        ...

    def update(self, variables: Dict[str, Any]) -> None:
        """Update context with variables (and callables, as functions) from a dictionary."""
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
    src: str,
    evaluation_context: Optional[Union[Dict[str, Any], Context]] = None,
) -> Any:
    """
    Evaluate a CEL expression.

    Args:
        src: The CEL expression to evaluate
        evaluation_context: Optional context with variables and functions

    Returns:
        The result of evaluating the expression
    """
    ...
