"""Evaluation mode enum for CEL.

Kept for typing compatibility with cel.pyi.
"""

from enum import Enum


class EvaluationMode(str, Enum):
    PYTHON = "python"
    STRICT = "strict"
