"""
Arithmetic operations tests for CEL bindings.

- Basic arithmetic operations (+ - * / %)
- Mixed-type arithmetic (int/float combinations)
- Arithmetic with context variables
- Edge cases and precedence
- String concatenation (a form of arithmetic)
"""

import datetime

import cel
import pytest


class TestBasicArithmetic:
    """Test basic arithmetic operations."""

    def test_basic_addition(self):
        """Test basic integer addition."""
        assert cel.evaluate("1 + 1") == 2

    def test_basic_subtraction(self):
        """Test basic integer subtraction."""
        assert cel.evaluate("5 - 3") == 2

    def test_basic_multiplication(self):
        """Test basic integer multiplication."""
        assert cel.evaluate("3 * 4") == 12

    def test_basic_division(self):
        """Test basic division."""
        assert cel.evaluate("10 / 2") == 5.0

    def test_integer_modulo(self):
        """Test integer modulo operation."""
        assert cel.evaluate("10 % 3") == 1

    def test_string_concatenation(self):
        """Test string concatenation with + operator."""
        assert cel.evaluate("'Hello ' + name", {"name": "World"}) == "Hello World"

    def test_complex_string_concatenation(self):
        """Test complex string concatenation from context."""
        result = cel.evaluate(
            'resource.name.startsWith("/groups/" + claim.group)',
            {"resource": {"name": "/groups/hardbyte"}, "claim": {"group": "hardbyte"}},
        )
        assert result is True


class TestMixedTypeArithmetic:
    """Test arithmetic operations with mixed numeric types."""

    def test_float_times_int(self):
        """Test that 3.14 * 2 works (float * int)."""
        result = cel.evaluate("3.14 * 2")
        assert result == 6.28

    def test_int_times_float(self):
        """Test that 2 * 3.14 works (int * float)."""
        result = cel.evaluate("2 * 3.14")
        assert result == 6.28

    def test_float_plus_int(self):
        """Test that 10.5 + 5 works (float + int)."""
        result = cel.evaluate("10.5 + 5")
        assert result == 15.5

    def test_int_plus_float(self):
        """Test that 5 + 10.5 works (int + float)."""
        result = cel.evaluate("5 + 10.5")
        assert result == 15.5

    def test_float_minus_int(self):
        """Test that 10.5 - 3 works (float - int)."""
        result = cel.evaluate("10.5 - 3")
        assert result == 7.5

    def test_int_minus_float(self):
        """Test that 10 - 3.5 works (int - float)."""
        result = cel.evaluate("10 - 3.5")
        assert result == 6.5

    def test_float_divide_int(self):
        """Test that 15.0 / 3 works (float / int)."""
        result = cel.evaluate("15.0 / 3")
        assert result == 5.0

    def test_int_divide_float(self):
        """Test that 15 / 3.0 works (int / float)."""
        result = cel.evaluate("15 / 3.0")
        assert result == 5.0

    def test_mixed_arithmetic_preserves_python_behavior(self):
        """Test that our mixed arithmetic matches Python's behavior."""
        # These should match what Python would do
        python_result = 3.14 * 2
        cel_result = cel.evaluate("3.14 * 2")
        assert cel_result == python_result

        python_result = 2 * 3.14
        cel_result = cel.evaluate("2 * 3.14")
        assert cel_result == python_result

        python_result = 10.5 + 5
        cel_result = cel.evaluate("10.5 + 5")
        assert cel_result == python_result


class TestArithmeticWithContext:
    """Test arithmetic operations with context variables."""

    def test_mixed_arithmetic_with_context(self):
        """Test mixed arithmetic with variables from context."""
        context = {"pi": 3.14159, "radius": 2}
        result = cel.evaluate("pi * radius * radius", context)
        assert abs(result - 12.56636) < 0.00001

    def test_datetime_arithmetic_context(self):
        """Test datetime arithmetic operations with context."""
        now = datetime.datetime.now(datetime.timezone.utc)
        result = cel.evaluate("start_time + duration('1h')", {"start_time": now})
        expected = now + datetime.timedelta(hours=1)
        assert result == expected


class TestArithmeticPrecedenceAndGrouping:
    """Test operator precedence and parentheses in arithmetic."""

    def test_mixed_arithmetic_with_parentheses(self):
        """Test mixed arithmetic with parentheses."""
        result = cel.evaluate("(3.14 + 1) * 2")
        assert abs(result - 8.28) < 0.000001

    def test_mixed_arithmetic_precedence(self):
        """Test that operator precedence is preserved with mixed types."""
        result = cel.evaluate("2 + 3.14 * 2")
        assert abs(result - 8.28) < 0.000001

    def test_multiple_operators_in_expression(self):
        """Test expressions with multiple different operators."""
        result = cel.evaluate("10.5 + 2 * 3 - 1")
        assert result == 15.5

    def test_complex_mixed_expression(self):
        """Test complex expressions with multiple mixed operations."""
        result = cel.evaluate("3.14 * 2 + 1")
        assert result == 7.28


class TestArithmeticEdgeCases:
    """Test edge cases in arithmetic operations."""

    def test_no_preprocessing_for_pure_int_operations(self):
        """Test that pure integer operations are not modified."""
        result = cel.evaluate("5 + 3")
        assert result == 8
        assert isinstance(result, int)

    def test_no_preprocessing_for_pure_float_operations(self):
        """Test that pure float operations are not modified."""
        result = cel.evaluate("5.5 + 3.2")
        assert result == 8.7
        assert isinstance(result, float)

    def test_mixed_arithmetic_with_negative_numbers(self):
        """Test mixed arithmetic with negative numbers."""
        result = cel.evaluate("-3.14 * 2")
        assert result == -6.28

    def test_mixed_arithmetic_with_spaces(self):
        """Test that spacing doesn't affect mixed arithmetic."""
        result = cel.evaluate("3.14*2")  # No spaces
        assert result == 6.28

        result = cel.evaluate("3.14 * 2")  # With spaces
        assert result == 6.28

        result = cel.evaluate("3.14  *  2")  # Extra spaces
        assert result == 6.28

    def test_mixed_arithmetic_edge_cases(self):
        """Test edge cases for mixed arithmetic."""
        # Zero cases
        assert cel.evaluate("0.0 * 5") == 0.0
        assert cel.evaluate("5 * 0.0") == 0.0

        # One cases
        assert cel.evaluate("1.0 * 7") == 7.0
        assert cel.evaluate("7 * 1.0") == 7.0

        # Large numbers
        result = cel.evaluate("1000000.0 * 2")
        assert result == 2000000.0

    def test_invalid_expression_raises_parse_value_error(self):
        """Test that invalid arithmetic expressions raise proper ValueError."""
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate("1 +")


class TestBytesArithmetic:
    """Test bytes operations and concatenation."""

    @pytest.mark.xfail(
        reason="cel-interpreter 0.10.0 does not implement bytes concatenation (CEL spec requires it)"
    )
    def test_bytes_concatenation_context(self):
        """CEL spec requires bytes concatenation with + operator, but cel-interpreter 0.10.0 doesn't implement it."""
        part1 = b"hello"
        part2 = b"world"
        result = cel.evaluate("part1 + b' ' + part2", {"part1": part1, "part2": part2})
        assert result == b"hello world"

    def test_bytes_concatenation_not_supported(self):
        """Test direct bytes concatenation (CEL spec requires this but cel-interpreter 0.10.0 doesn't support it)."""
        with pytest.raises(TypeError, match="Unsupported addition operation"):
            cel.evaluate("b'hello' + b'world'")

    def test_bytes_concatenation_workaround(self):
        """Test bytes concatenation workaround using string conversion."""
        part1 = b"hello"
        part2 = b"world"
        # Workaround: convert to strings, concatenate, then convert back to bytes
        result = cel.evaluate(
            'bytes(string(part1) + " " + string(part2))', {"part1": part1, "part2": part2}
        )
        assert result == b"hello world"
