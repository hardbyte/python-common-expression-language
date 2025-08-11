"""Tests for EvaluationMode functionality."""

import pytest
from cel import Context, EvaluationMode, evaluate


def test_evaluation_mode_enum_values():
    """Test that EvaluationMode enum has expected values."""
    assert EvaluationMode.PYTHON == "python"
    assert EvaluationMode.STRICT == "strict"
    # String representation shows enum name, but equality works with values
    assert str(EvaluationMode.PYTHON) == "EvaluationMode.PYTHON"
    assert str(EvaluationMode.STRICT) == "EvaluationMode.STRICT"


def test_default_mode_is_python_compatible():
    """Test that the default evaluation mode allows mixed arithmetic."""
    # Without explicit mode, should use python by default
    result = evaluate("1 + 2.5")
    assert result == 3.5


def test_python_mode_explicit():
    """Test explicit python mode allows mixed arithmetic."""
    # Using enum
    result = evaluate("1 + 2.5", mode=EvaluationMode.PYTHON)
    assert result == 3.5

    # Using string
    result = evaluate("1 + 2.5", mode="python")
    assert result == 3.5


def test_strict_mode_rejects_mixed_arithmetic():
    """Test that strict mode rejects mixed int/float arithmetic."""
    # Using enum
    with pytest.raises(TypeError, match="Unsupported addition operation"):
        evaluate("1 + 2.5", mode=EvaluationMode.STRICT)

    # Using string
    with pytest.raises(TypeError, match="Unsupported addition operation"):
        evaluate("1 + 2.5", mode="strict")


def test_same_type_arithmetic_works_in_both_modes():
    """Test that same-type arithmetic works in both modes."""
    # Integer arithmetic
    assert evaluate("1 + 2", mode=EvaluationMode.PYTHON) == 3
    assert evaluate("1 + 2", mode=EvaluationMode.STRICT) == 3

    # Float arithmetic
    assert evaluate("1.5 + 2.5", mode=EvaluationMode.PYTHON) == 4.0
    assert evaluate("1.5 + 2.5", mode=EvaluationMode.STRICT) == 4.0


def test_context_with_mixed_types():
    """Test evaluation modes with context containing mixed types."""
    context = {"x": 1, "y": 2.5}

    # Python mode should promote and work
    result = evaluate("x + y", context, mode=EvaluationMode.PYTHON)
    assert result == 3.5

    # Strict should fail
    with pytest.raises(TypeError, match="Unsupported addition operation"):
        evaluate("x + y", context, mode=EvaluationMode.STRICT)


def test_context_object_with_mixed_types():
    """Test evaluation modes with Context object containing mixed types."""
    context = Context(variables={"a": 5, "b": 3.0})

    # Python mode should work
    result = evaluate("a + b", context, mode=EvaluationMode.PYTHON)
    assert result == 8.0

    # Strict should fail
    with pytest.raises(TypeError, match="Unsupported addition operation"):
        evaluate("a + b", context, mode=EvaluationMode.STRICT)


def test_invalid_mode_string():
    """Test that invalid mode strings raise appropriate errors."""
    with pytest.raises(TypeError, match="Invalid EvaluationMode"):
        evaluate("1 + 2", mode="InvalidMode")


def test_context_type_promotion_in_python_mode():
    """Test that python mode promotes context integers when floats are present."""
    context = {"int_val": 10, "float_val": 2.5}

    # This should work in python mode due to type promotion
    result = evaluate("int_val * float_val", context, mode=EvaluationMode.PYTHON)
    assert result == 25.0


def test_expression_preprocessing_in_python_mode():
    """Test that python mode preprocesses integer literals when mixed with floats."""
    # This expression has mixed literals, should work in python mode
    result = evaluate("10 + 2.5", mode=EvaluationMode.PYTHON)
    assert result == 12.5

    # Should fail in strict mode
    with pytest.raises(TypeError):
        evaluate("10 + 2.5", mode=EvaluationMode.STRICT)


def test_non_arithmetic_expressions_work_in_both_modes():
    """Test that non-arithmetic expressions work the same in both modes."""
    # String operations
    assert evaluate('"hello" + " world"', mode=EvaluationMode.PYTHON) == "hello world"
    assert evaluate('"hello" + " world"', mode=EvaluationMode.STRICT) == "hello world"

    # Boolean operations
    assert evaluate("true && false", mode=EvaluationMode.PYTHON) is False
    assert evaluate("true && false", mode=EvaluationMode.STRICT) is False

    # List operations
    assert evaluate("[1, 2, 3].size()", mode=EvaluationMode.PYTHON) == 3
    assert evaluate("[1, 2, 3].size()", mode=EvaluationMode.STRICT) == 3


def test_mode_with_custom_functions():
    """Test that evaluation modes work with custom functions."""

    def add_numbers(a, b):
        return a + b

    context = Context(variables={"x": 1, "y": 2.5}, functions={"add": add_numbers})

    # The Python function itself will handle mixed arithmetic
    result = evaluate("add(x, y)", context, mode=EvaluationMode.STRICT)
    assert result == 3.5  # Python function can handle mixed types

    # But CEL arithmetic still fails in strict mode
    with pytest.raises(TypeError):
        evaluate("x + y", context, mode=EvaluationMode.STRICT)


def test_mode_parameter_positions():
    """Test that mode parameter works in different positions."""
    context = {"a": 1, "b": 2}

    # Mode as third parameter
    result1 = evaluate("a + b", context, EvaluationMode.PYTHON)
    assert result1 == 3

    # Mode as keyword argument
    result2 = evaluate("a + b", context, mode=EvaluationMode.PYTHON)
    assert result2 == 3

    # Mode without context
    result3 = evaluate("1 + 2", mode=EvaluationMode.PYTHON)
    assert result3 == 3
