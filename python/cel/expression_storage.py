"""
Expression storage for CEL TUI.

Manages user-defined expressions stored in OS-specific configuration directory.
"""

import json
from pathlib import Path
from typing import List, Tuple

try:
    from platformdirs import user_config_dir
    HAS_PLATFORMDIRS = True
except ImportError:
    HAS_PLATFORMDIRS = False


def get_config_dir() -> Path:
    """Get OS-specific configuration directory for CEL."""
    if HAS_PLATFORMDIRS:
        # Use platformdirs for proper cross-platform config directory
        config_dir = Path(user_config_dir("cel", appauthor=False))
    else:
        # Fallback for when platformdirs is not available
        import sys
        if sys.platform == "win32":
            # Windows: %APPDATA%\cel
            base = Path.home() / "AppData" / "Roaming"
            config_dir = base / "cel"
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/cel
            base = Path.home() / "Library" / "Application Support"
            config_dir = base / "cel"
        else:
            # Linux/Unix: ~/.config/cel (XDG Base Directory spec)
            xdg_config = Path.home() / ".config"
            config_dir = xdg_config / "cel"

    # Create directory if it doesn't exist
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def get_expressions_file() -> Path:
    """Get path to user expressions JSON file."""
    return get_config_dir() / "expressions.json"


def load_user_expressions() -> List[Tuple[str, str, str]]:
    """
    Load user-defined expressions from config file.

    Returns:
        List of tuples: (name, description, expression)
    """
    expressions_file = get_expressions_file()

    if not expressions_file.exists():
        return []

    try:
        with expressions_file.open("r", encoding="utf-8") as f:
            data = json.load(f)

        # Validate structure
        if not isinstance(data, list):
            return []

        expressions = []
        for item in data:
            if isinstance(item, dict) and all(k in item for k in ("name", "description", "expression")):
                expressions.append((
                    item["name"],
                    item["description"],
                    item["expression"]
                ))

        return expressions
    except (json.JSONDecodeError, IOError):
        # If file is corrupted or unreadable, return empty list
        return []


def save_user_expressions(expressions: List[Tuple[str, str, str]]) -> None:
    """
    Save user-defined expressions to config file.

    Args:
        expressions: List of tuples (name, description, expression)
    """
    expressions_file = get_expressions_file()

    # Convert to list of dicts for JSON serialization
    data = [
        {
            "name": name,
            "description": description,
            "expression": expression
        }
        for name, description, expression in expressions
    ]

    try:
        with expressions_file.open("w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Failed to save expressions: {e}") from e


def add_expression(name: str, description: str, expression: str) -> None:
    """
    Add a new expression to user's library.

    Args:
        name: Display name for the expression
        description: Human-readable description
        expression: The CEL expression string

    Raises:
        ValueError: If an expression with the same name already exists
    """
    expressions = load_user_expressions()

    # Check for duplicate names
    existing_names = {expr[0] for expr in expressions}
    if name in existing_names:
        raise ValueError(f"Expression '{name}' already exists")

    # Add new expression
    expressions.append((name, description, expression))
    save_user_expressions(expressions)


def delete_expression(name: str) -> bool:
    """
    Delete an expression from user's library.

    Args:
        name: Name of the expression to delete

    Returns:
        True if expression was deleted, False if not found
    """
    expressions = load_user_expressions()

    # Filter out the expression to delete
    new_expressions = [expr for expr in expressions if expr[0] != name]

    # Check if anything was deleted
    if len(new_expressions) == len(expressions):
        return False

    save_user_expressions(new_expressions)
    return True


def update_expression(old_name: str, new_name: str, description: str, expression: str) -> None:
    """
    Update an existing expression.

    Args:
        old_name: Current name of the expression
        new_name: New name for the expression
        description: New description
        expression: New expression string

    Raises:
        ValueError: If expression not found or new name conflicts
    """
    expressions = load_user_expressions()

    # Find the expression to update
    found_index = None
    for i, (name, _, _) in enumerate(expressions):
        if name == old_name:
            found_index = i
            break

    if found_index is None:
        raise ValueError(f"Expression '{old_name}' not found")

    # Check if new name conflicts (unless it's the same name)
    if new_name != old_name:
        existing_names = {expr[0] for i, expr in enumerate(expressions) if i != found_index}
        if new_name in existing_names:
            raise ValueError(f"Expression '{new_name}' already exists")

    # Update the expression
    expressions[found_index] = (new_name, description, expression)
    save_user_expressions(expressions)
