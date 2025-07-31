# Import the Rust extension
from .cel import *

# Import CLI functionality  
from . import cli

__doc__ = cel.__doc__
if hasattr(cel, "__all__"):
    __all__ = cel.__all__