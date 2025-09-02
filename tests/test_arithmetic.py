"""
Arithmetic operations tests for CEL bindings.

- Basic arithmetic operations (+ - * / %)
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


class TestArithmeticWithContext:
    """Test arithmetic operations with context variables."""

    def test_datetime_arithmetic_context(self):
        """Test datetime arithmetic operations with context."""
        now = datetime.datetime.now(datetime.timezone.utc)
        result = cel.evaluate("start_time + duration('1h')", {"start_time": now})
        expected = now + datetime.timedelta(hours=1)
        assert result == expected


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
