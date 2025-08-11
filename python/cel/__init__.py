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
