"""
Standard library functions for CEL that aren't available in cel-rust.

This module provides Python implementations of CEL standard library functions
that are missing from the upstream cel-rust implementation.
"""

from typing import Any


def substring(s: str, start: int, end: int | None = None) -> str:
    """
    Extract a substring from a string.

    This implements the CEL substring() function which is not yet available
    in cel-rust upstream. See https://github.com/cel-rust/cel-rust/issues/200

    Args:
        s: The source string
        start: Starting index (0-based, inclusive)
        end: Optional ending index (0-based, exclusive). If not provided,
             extracts to the end of the string.

    Returns:
        The extracted substring

    Examples:
        >>> substring("hello world", 0, 5)
        'hello'
        >>> substring("hello world", 6)
        'world'
        >>> substring("hello", 1, 4)
        'ell'
    """
    if end is None:
        return s[start:]
    return s[start:end]


# Dictionary mapping function names to their implementations
# This makes it easy to add all stdlib functions to a Context at once
STDLIB_FUNCTIONS = {
    "substring": substring,
}


def add_stdlib_to_context(context: Any) -> None:
    """
    Add all stdlib functions to a CEL Context.

    Args:
        context: A cel.Context object

    Example:
        >>> import cel
        >>> from cel.stdlib import add_stdlib_to_context
        >>> context = cel.Context()
        >>> add_stdlib_to_context(context)
        >>> cel.evaluate('substring("hello", 0, 2)', context)
        'he'
    """
    for name, func in STDLIB_FUNCTIONS.items():
        context.add_function(name, func)
