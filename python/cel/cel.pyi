"""
Type stubs for the CEL Rust extension module.
"""

from typing import Any, Dict, Union, Optional, Callable, overload

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
        functions: Optional[Dict[str, Callable[..., Any]]] = None
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

def evaluate(expression: str, context: Optional[Union[Dict[str, Any], Context]] = None) -> Any:
    """
    Evaluate a CEL expression.
    
    Args:
        expression: The CEL expression to evaluate
        context: Optional context with variables and functions
        
    Returns:
        The result of evaluating the expression
    """
    ...