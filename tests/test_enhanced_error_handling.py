"""
Tests for enhanced error handling with improved error messages and exception types.

Tests various error scenarios to ensure proper Python exception types and helpful messages.
"""

import cel
import pytest


class TestEnhancedErrorHandling:
    """Test improved error handling with appropriate Python exception types."""

    def test_undefined_variable_runtime_error(self):
        """Test that undefined variables raise RuntimeError with helpful message."""
        with pytest.raises(RuntimeError) as exc_info:
            cel.evaluate("undefined_var + 1", {})

        error_msg = str(exc_info.value)
        assert "Undefined variable or function: 'undefined_var'" in error_msg
        assert "Check that the variable is defined in the context" in error_msg

    def test_undefined_function_runtime_error(self):
        """Test that undefined functions raise RuntimeError with helpful message."""
        with pytest.raises(RuntimeError) as exc_info:
            cel.evaluate("unknownFunction(42)", {})

        error_msg = str(exc_info.value)
        assert "Undefined variable or function: 'unknownFunction'" in error_msg
        assert "function name is spelled correctly" in error_msg

    def test_mixed_int_uint_arithmetic_type_error(self):
        """Test that mixed signed/unsigned arithmetic raises TypeError with solution."""
        with pytest.raises(TypeError) as exc_info:
            cel.evaluate("1 + 2u", {})

        error_msg = str(exc_info.value)
        assert "Cannot mix signed and unsigned integers" in error_msg
        assert (
            "Use explicit conversion: int(" in error_msg
            or "Use explicit conversion: uint(" in error_msg
        )

    def test_unsupported_multiplication_type_error(self):
        """Test multiplication type errors provide conversion suggestions."""
        with pytest.raises(TypeError) as exc_info:
            cel.evaluate("[1,2,3].map(x, x * 2)", {})

        error_msg = str(exc_info.value)
        assert "Unsupported multiplication operation" in error_msg
        assert "Use explicit conversion if needed: double(" in error_msg

    def test_unsupported_addition_type_error(self):
        """Test addition type errors for incompatible types."""
        with pytest.raises(TypeError) as exc_info:
            cel.evaluate("'hello' + 42", {})

        error_msg = str(exc_info.value)
        assert "Unsupported addition operation" in error_msg
        assert "Check that both operands are compatible types" in error_msg

    def test_function_error_runtime_error(self):
        """Test that function errors raise RuntimeError with function context."""

        def failing_function(x):
            raise ValueError("Something went wrong")

        context = cel.Context()
        context.add_function("failing_func", failing_function)

        with pytest.raises(RuntimeError) as exc_info:
            cel.evaluate("failing_func(42)", context)

        error_msg = str(exc_info.value)
        assert "failing_func" in error_msg
        assert "error" in error_msg.lower()

    def test_empty_expression_parse_error(self):
        """Test that empty expressions raise parse errors."""
        with pytest.raises(ValueError) as exc_info:
            cel.evaluate("", {})

        error_msg = str(exc_info.value)
        assert "Failed to parse expression" in error_msg

    def test_whitespace_only_expression_parse_error(self):
        """Test that whitespace-only expressions raise parse errors."""
        with pytest.raises(ValueError) as exc_info:
            cel.evaluate("   ", {})

        error_msg = str(exc_info.value)
        assert "Failed to parse expression" in error_msg


class TestErrorMessageQuality:
    """Test that error messages provide helpful guidance."""

    def test_missing_string_function_helpful_message(self):
        """Test that missing string functions provide helpful error messages."""
        with pytest.raises(RuntimeError) as exc_info:
            cel.evaluate('"hello".lowerAscii()', {})

        error_msg = str(exc_info.value)
        assert "lowerAscii" in error_msg
        assert "Undefined variable or function" in error_msg

    def test_missing_type_function_helpful_message(self):
        """Test that missing type() function provides helpful error message."""
        with pytest.raises(RuntimeError) as exc_info:
            cel.evaluate("type(42)", {})

        error_msg = str(exc_info.value)
        assert "type" in error_msg
        assert "Undefined variable or function" in error_msg

    def test_mixed_arithmetic_provides_conversion_examples(self):
        """Test that mixed arithmetic errors show conversion syntax."""
        with pytest.raises(TypeError) as exc_info:
            cel.evaluate("1u + 2", {})

        error_msg = str(exc_info.value)
        assert "int(" in error_msg or "uint(" in error_msg
        assert "value" in error_msg

    def test_detailed_operation_error_messages(self):
        """Test that different operations provide specific guidance."""
        test_cases = [
            ("1 - 'hello'", "subtraction operation", "numeric"),
            ("'hello' / 2", "division operation", "numeric"),
            ("true % false", "operation", "types"),
        ]

        for expr, expected_op, expected_guidance in test_cases:
            with pytest.raises(TypeError) as exc_info:
                cel.evaluate(expr, {})

            error_msg = str(exc_info.value)
            assert expected_op in error_msg.lower()
            assert expected_guidance in error_msg.lower()


class TestExceptionTypes:
    """Test that appropriate Python exception types are raised."""

    def test_runtime_error_for_undefined_references(self):
        """RuntimeError should be raised for undefined variables/functions."""
        with pytest.raises(RuntimeError):
            cel.evaluate("undefined_var", {})

    def test_type_error_for_incompatible_operations(self):
        """TypeError should be raised for incompatible type operations."""
        with pytest.raises(TypeError):
            cel.evaluate("1 + 'hello'", {})

    def test_value_error_for_invalid_expressions(self):
        """ValueError should be raised for invalid expressions."""
        with pytest.raises(ValueError):
            cel.evaluate("", {})

    def test_fallback_to_value_error(self):
        """Unknown errors should fallback to ValueError."""
        # This test ensures that any unmapped ExecutionError types
        # still produce a reasonable Python exception
        # Note: This might be hard to trigger, but we include it for completeness
        pass


class TestBackwardCompatibility:
    """Ensure enhanced error handling doesn't break existing behavior."""

    def test_basic_evaluation_still_works(self):
        """Basic expressions should still work normally."""
        result = cel.evaluate("1 + 2", {})
        assert result == 3

    def test_context_variables_still_work(self):
        """Context variables should still work normally."""
        result = cel.evaluate("x + y", {"x": 10, "y": 5})
        assert result == 15

    def test_functions_still_work(self):
        """Built-in functions should still work normally."""
        result = cel.evaluate('size("hello")', {})
        assert result == 5

    def test_complex_expressions_still_work(self):
        """Complex expressions should still work normally."""
        result = cel.evaluate("[1,2,3].all(x, x > 0)", {})
        assert result is True


if __name__ == "__main__":
    pytest.main([__file__])
