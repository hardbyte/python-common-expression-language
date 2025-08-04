# Import the Rust extension
# Import CLI functionality
from . import cli
from .cel import *

__doc__ = cel.__doc__
if hasattr(cel, "__all__"):
    __all__ = cel.__all__
else:
    __all__ = [
        "evaluate",
        "Context",
    ]
