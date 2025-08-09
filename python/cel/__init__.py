# Import the Rust extension
# Import CLI functionality
from enum import Enum

from . import cli
from .cel import *


class EvaluationMode(str, Enum):
    """
    Defines the evaluation dialect for a CEL expression.
    """

    PYTHON = "python"
    """
    Enables Python-friendly type promotions (e.g., int -> float). (Default)
    """
    STRICT = "strict"
    """
    Enforces strict cel-rust type rules with no automatic coercion to match Wasm behavior.
    """


__doc__ = cel.__doc__
if hasattr(cel, "__all__"):
    # Ensure EvaluationMode is always exported even if Rust module defines __all__
    __all__ = list(cel.__all__) + ["EvaluationMode"]
else:
    __all__ = [
        "evaluate",
        "Context",
        "EvaluationMode",
    ]
