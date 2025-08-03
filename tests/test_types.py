"""
Comprehensive type conversion and handling tests for CEL bindings.

This module consolidates all type-related testing including:
- Basic type conversions (Python ↔ CEL)
- Edge cases and stress testing
- Complex nested structures
- Error conditions and robustness
"""

import datetime
import math

import cel
import pytest


class TestBasicTypeConversion:
    """Test basic type conversion between Python and CEL."""

    def test_none_values(self):
        """Test handling of None values in various contexts."""
        # None in basic context
        result = cel.evaluate("value", {"value": None})
        assert result is None

        # None in comparison
        result = cel.evaluate("value == null", {"value": None})
        assert result is True

        # None in list
        result = cel.evaluate("items[0]", {"items": [None, 1, 2]})
        assert result is None

    def test_boolean_conversion(self):
        """Test boolean type conversion and edge cases."""
        # Basic boolean values
        assert cel.evaluate("value", {"value": True}) is True
        assert cel.evaluate("value", {"value": False}) is False

        # Boolean in expressions
        result = cel.evaluate("a && b", {"a": True, "b": False})
        assert result is False  # CEL returns boolean values for logical ops

        result = cel.evaluate("a || b", {"a": False, "b": True})
        assert result is True

    def test_string_conversion(self):
        """Test string conversion with various edge cases."""
        # Empty string
        result = cel.evaluate("value", {"value": ""})
        assert result == ""

        # Very long string
        long_string = "a" * 10000
        result = cel.evaluate("value", {"value": long_string})
        assert result == long_string

        # Unicode strings
        unicode_string = "Hello 世界 🌍 𝓤𝓷𝓲𝓬𝓸𝓭𝓮"
        result = cel.evaluate("value", {"value": unicode_string})
        assert result == unicode_string

        # String with null bytes (should be handled gracefully)
        string_with_null = "Hello\x00World"
        result = cel.evaluate("value", {"value": string_with_null})
        assert result == string_with_null

    def test_bytes_conversion(self):
        """Test bytes conversion with various edge cases."""
        # Empty bytes
        result = cel.evaluate("value", {"value": b""})
        assert result == b""

        # Bytes with null bytes
        bytes_with_null = b"Hello\x00World\xff"
        result = cel.evaluate("value", {"value": bytes_with_null})
        assert result == bytes_with_null

        # Large bytes object
        large_bytes = b"x" * 10000
        result = cel.evaluate("value", {"value": large_bytes})
        assert result == large_bytes


class TestNumericTypes:
    """Test numeric type conversion and edge cases."""

    def test_mixed_numeric_edge_cases(self):
        """Test edge cases with mixed numeric types."""
        # Very large integers
        large_int = 2**62
        result = cel.evaluate("value", {"value": large_int})
        assert result == large_int

        # Very small integers
        small_int = -(2**62)
        result = cel.evaluate("value", {"value": small_int})
        assert result == small_int

        # Very precise floats
        precise_float = 1.23456789012345678901234567890
        result = cel.evaluate("value", {"value": precise_float})
        assert isinstance(result, float)
        # Note: precision may be lost due to float64 limitations

    def test_special_float_values(self):
        """Test special float values (inf, -inf, nan)."""
        # Positive infinity
        result = cel.evaluate("value", {"value": float("inf")})
        assert math.isinf(result) and result > 0

        # Negative infinity
        result = cel.evaluate("value", {"value": float("-inf")})
        assert math.isinf(result) and result < 0

        # NaN
        result = cel.evaluate("value", {"value": float("nan")})
        assert math.isnan(result)

    def test_large_numbers(self):
        """Test handling of large numbers."""
        large_int = 2**50
        result = cel.evaluate("x + 1", {"x": large_int})
        assert result == large_int + 1

    def test_numeric_precision(self):
        """Test numeric precision in calculations."""
        # Test floating point precision
        a = 0.1
        b = 0.2
        c = 0.3
        result = cel.evaluate("a + b", {"a": a, "b": b})
        # Due to floating point precision, this might not be exactly 0.3
        assert abs(result - c) < 1e-10


class TestCollectionTypes:
    """Test collection type handling (lists, dictionaries)."""

    def test_list_conversion_edge_cases(self):
        """Test list conversion with various edge cases."""
        # Empty list
        result = cel.evaluate("value", {"value": []})
        assert result == []

        # List with mixed types including problematic ones
        mixed_list = [
            1,
            2.5,
            "string",
            b"bytes",
            None,
            True,
            False,
            datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc),
            datetime.timedelta(hours=1),
            [1, 2, 3],  # nested list
            {"key": "value"},  # nested dict
        ]
        result = cel.evaluate("value", {"value": mixed_list})
        assert len(result) == len(mixed_list)
        assert result[0] == 1
        assert result[1] == 2.5
        assert result[2] == "string"
        assert result[3] == b"bytes"
        assert result[4] is None
        assert result[5] is True
        assert result[6] is False
        assert result[7] == mixed_list[7]  # datetime
        assert result[8] == mixed_list[8]  # timedelta
        assert result[9] == [1, 2, 3]  # nested list
        assert result[10] == {"key": "value"}  # nested dict

    def test_dict_conversion_edge_cases(self):
        """Test dictionary conversion with various key and value types."""
        # Dict with different key types
        mixed_dict = {"string_key": "value1", 42: "value2", True: "value3", False: "value4"}

        # Note: Python dicts with True/False keys behave specially
        # True == 1 and False == 0 for dict key purposes
        result = cel.evaluate("value", {"value": mixed_dict})

        # Verify the dict structure is preserved
        assert isinstance(result, dict)
        assert "string_key" in result
        assert result["string_key"] == "value1"

    def test_mixed_key_types_in_dict(self):
        """Test dictionaries with mixed key types."""
        test_dict = {"str_key": "string value", 123: "int value", True: "bool value"}

        context = {"test_dict": test_dict}

        # Access by string key
        result = cel.evaluate("test_dict['str_key']", context)
        assert result == "string value"

        # Access by integer key
        result = cel.evaluate("test_dict[123]", context)
        assert result == "int value"

    def test_empty_containers(self):
        """Test empty lists, dicts, and strings."""
        assert cel.evaluate("size([])", {}) == 0
        assert cel.evaluate("size({})", {}) == 0
        assert cel.evaluate("size('')", {}) == 0
        assert cel.evaluate("x", {"x": []}) == []
        assert cel.evaluate("x", {"x": {}}) == {}

    def test_list_tuple_equivalence(self):
        """Test that tuples and lists are handled equivalently."""
        list_data = [1, 2, 3]
        tuple_data = (1, 2, 3)

        list_result = cel.evaluate("data[1]", {"data": list_data})
        tuple_result = cel.evaluate("data[1]", {"data": tuple_data})

        assert list_result == tuple_result == 2


class TestComplexStructures:
    """Test complex and nested data structures."""

    def test_complex_nested_structures(self):
        """Test deeply nested data structures."""
        context = {
            "level1": {
                "level2": {
                    "level3": {
                        "level4": {
                            "value": "deep_value",
                            "list": [1, 2, {"nested_key": "nested_value"}],
                        }
                    }
                }
            }
        }

        result = cel.evaluate("level1.level2.level3.level4.value", context)
        assert result == "deep_value"

        result = cel.evaluate("level1.level2.level3.level4.list[2].nested_key", context)
        assert result == "nested_value"

    def test_complex_nested_with_datetime(self):
        """Test type conversion with deeply nested data structures."""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": {
                        "datetime": datetime.datetime(
                            2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc
                        ),
                        "numbers": [1, 2.5, 3],
                        "mixed_list": [{"inner": True}, [1, 2, 3], "string"],
                    }
                }
            },
            "timedelta": datetime.timedelta(hours=2),
        }

        # Access nested datetime
        result = cel.evaluate("data.level1.level2.level3.datetime", {"data": complex_data})
        assert result == complex_data["level1"]["level2"]["level3"]["datetime"]

        # Access nested numbers
        result = cel.evaluate("data.level1.level2.level3.numbers[1]", {"data": complex_data})
        assert result == 2.5

        # Access timedelta at root level
        result = cel.evaluate("data.timedelta", {"data": complex_data})
        assert result == complex_data["timedelta"]


class TestTypeErrors:
    """Test error conditions and edge cases."""

    def test_invalid_context_key_type(self):
        """Test that non-string keys in context raise appropriate errors."""
        with pytest.raises(ValueError, match="Variable name must be strings"):
            cel.Context({123: "value"})

    def test_function_with_error(self):
        """Test that Python function errors are properly handled."""

        def error_function():
            raise ValueError("Custom error")

        with pytest.raises(RuntimeError, match="Function 'error_function' error"):
            cel.evaluate("error_function()", {"error_function": error_function})

    def test_function_with_wrong_args(self):
        """Test that function argument mismatch is handled."""

        def two_arg_function(a, b):
            return a + b

        with pytest.raises(RuntimeError, match="Function 'two_arg_function' error"):
            cel.evaluate("two_arg_function(1)", {"two_arg_function": two_arg_function})

    def test_error_propagation_in_conversions(self):
        """Test that conversion errors are properly propagated."""
        # This test ensures that if we have invalid objects,
        # they are handled gracefully rather than causing crashes

        # Most valid Python objects should convert successfully
        # so this is more about ensuring robust error handling exists

        valid_data = {
            "number": 42,
            "string": "test",
            "boolean": True,
            "none_value": None,  # Changed from "null" which is a CEL keyword
            "list": [1, 2, 3],
            "dict": {"key": "value"},
        }

        for key, value in valid_data.items():
            result = cel.evaluate("data." + key, {"data": valid_data})
            assert result == value


class TestCELKeywordHandling:
    """Test handling of CEL keywords and reserved words."""

    def test_cel_keyword_conflicts(self):
        """Test handling of Python field names that conflict with CEL keywords."""
        # Test that we can access data with field names that are CEL keywords using indexing
        problematic_data = {
            "null": "not_null_value",
            "true": "not_boolean_true",
            "false": "not_boolean_false",
            "size": "not_function_size",
        }

        # These should work using bracket notation
        result = cel.evaluate("data['null']", {"data": problematic_data})
        assert result == "not_null_value"

        result = cel.evaluate("data['true']", {"data": problematic_data})
        assert result == "not_boolean_true"

        result = cel.evaluate("data['false']", {"data": problematic_data})
        assert result == "not_boolean_false"

        result = cel.evaluate("data['size']", {"data": problematic_data})
        assert result == "not_function_size"


class TestContextHandling:
    """Test context object and variable handling."""

    def test_context_update_overwrite(self):
        """Test that context updates overwrite existing variables."""
        context = cel.Context({"x": 1})
        result = cel.evaluate("x", context)
        assert result == 1

        # Update context with new value
        context.update({"x": 2})
        result = cel.evaluate("x", context)
        assert result == 2

    def test_unicode_strings(self):
        """Test Unicode string handling."""
        unicode_text = "Hello, 世界! 🌍"
        result = cel.evaluate("text", {"text": unicode_text})
        assert result == unicode_text

        result = cel.evaluate("text + ' suffix'", {"text": unicode_text})
        assert result == unicode_text + " suffix"


class TestDatetimeIntegration:
    """Test datetime integration with type system."""

    def test_datetime_operations(self):
        """Test datetime operations with type system."""
        dt = datetime.datetime(2024, 1, 1, 12, 0, 0, tzinfo=datetime.timezone.utc)
        delta = datetime.timedelta(hours=1)

        context = {"dt": dt, "delta": delta}

        # Test datetime arithmetic
        result = cel.evaluate("dt + delta", context)
        assert isinstance(result, datetime.datetime)

        # Test datetime comparison
        result = cel.evaluate("dt < (dt + delta)", context)
        assert result is True
