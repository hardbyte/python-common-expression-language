"""
Test that documentation is properly exposed to Python users.

This tests that docstrings and help text are available and contain
expected information for users discovering the API.
"""

import inspect

import cel


def test_module_has_evaluate_function():
    """Test that the main evaluate function is available."""
    assert hasattr(cel, "evaluate")
    assert callable(cel.evaluate)


def test_module_has_context_class():
    """Test that the Context class is available."""
    assert hasattr(cel, "Context")
    assert inspect.isclass(cel.Context)


def test_evaluate_function_docstring():
    """Test that evaluate function has helpful docstring."""
    docstring = cel.evaluate.__doc__
    assert docstring is not None
    assert "CEL expression" in docstring or "expression" in docstring
    assert len(docstring.strip()) > 20  # Should be substantive


def test_context_class_docstring():
    """Test that Context class has helpful docstring."""
    docstring = cel.Context.__doc__
    assert docstring is not None
    assert "Context" in docstring
    assert "variables" in docstring or "functions" in docstring
    assert len(docstring.strip()) > 50  # Should be substantive


def test_context_methods_have_docstrings():
    """Test that Context methods have docstrings."""
    # Check add_variable method
    add_variable_doc = cel.Context.add_variable.__doc__
    assert add_variable_doc is not None
    assert "variable" in add_variable_doc.lower()
    assert "name" in add_variable_doc.lower()

    # Check add_function method
    add_function_doc = cel.Context.add_function.__doc__
    assert add_function_doc is not None
    assert "function" in add_function_doc.lower()
    assert "name" in add_function_doc.lower()

    # Check update method
    update_doc = cel.Context.update.__doc__
    assert update_doc is not None
    assert "dictionary" in update_doc.lower() or "variables" in update_doc.lower()


def test_context_constructor_signature():
    """Test that Context constructor has proper signature."""
    sig = inspect.signature(cel.Context)
    params = list(sig.parameters.keys())

    # Should accept variables and functions parameters
    assert "variables" in params
    assert "functions" in params

    # Both should be optional (have defaults)
    assert sig.parameters["variables"].default is None
    assert sig.parameters["functions"].default is None


def test_evaluate_function_signature():
    """Test that evaluate function has proper signature."""
    sig = inspect.signature(cel.evaluate)
    params = list(sig.parameters.keys())

    # Should have src as required parameter
    assert "src" in params
    assert sig.parameters["src"].default == inspect.Parameter.empty

    # Should have optional evaluation_context
    assert "evaluation_context" in params
    assert sig.parameters["evaluation_context"].default is None


def test_help_text_contains_examples():
    """Test that help text includes usage examples."""
    import io
    import sys
    from contextlib import redirect_stdout

    # Capture help output for Context
    f = io.StringIO()
    with redirect_stdout(f):
        help(cel.Context)
    help_text = f.getvalue()

    # Should contain example code
    assert "context = cel.Context" in help_text or "Context(" in help_text
    assert "add_function" in help_text or "add_variable" in help_text


def test_docstring_formatting():
    """Test that docstrings are properly formatted for Python users."""
    context_doc = cel.Context.__doc__

    # Should not contain Rust-specific formatting
    assert "PyResult" not in context_doc or "Success or" in context_doc
    assert "Vec<" not in context_doc
    assert "HashMap" not in context_doc

    # Should contain helpful information
    assert "CEL" in context_doc
    assert "expression" in context_doc.lower()


def test_api_discoverability():
    """Test that the API is discoverable through standard Python tools."""
    # dir() should show main functions
    module_attrs = dir(cel)
    assert "evaluate" in module_attrs
    assert "Context" in module_attrs

    # Context should show methods
    context_attrs = dir(cel.Context)
    assert "add_variable" in context_attrs
    assert "add_function" in context_attrs
    assert "update" in context_attrs
