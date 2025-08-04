"""
Test boolean coercion patterns in CEL expressions.

This module comprehensively tests the behavior of boolean operations, coercion,
and truthiness evaluation in the CEL implementation, documenting both expected
and unexpected behaviors.
"""

import pytest
from cel import evaluate


class TestBooleanCoercion:
    """Test boolean coercion and truthiness patterns in CEL expressions."""

    def test_not_operator_basic(self):
        """Test basic NOT operator behavior."""
        # Test with boolean literals - correctly returns booleans
        assert evaluate("!true") is False
        assert evaluate("!false") is True

    def test_not_operator_with_numbers(self):
        """Test NOT operator with numeric values."""
        # Zero is falsy
        assert evaluate("!0") is True
        assert evaluate("!0.0") is True

        # Non-zero numbers are truthy
        assert evaluate("!1") is False
        assert evaluate("!42") is False
        assert evaluate("!-5") is False
        assert evaluate("!3.14") is False

    def test_not_operator_with_strings(self):
        """Test NOT operator with string values."""
        # Empty string is falsy
        assert evaluate("!''") is True
        assert evaluate('!""') is True

        # Non-empty strings are truthy
        assert evaluate("!'hello'") is False
        assert evaluate("!'0'") is False  # String "0" is truthy
        assert evaluate("!' '") is False  # Space character is truthy

    def test_not_operator_with_null(self):
        """Test NOT operator with null values."""
        assert evaluate("!null") is True

    def test_not_operator_with_collections(self):
        """Test NOT operator with lists and maps."""
        # Empty collections are falsy
        assert evaluate("![]") is True
        assert evaluate("!{}") is True

        # Non-empty collections are truthy
        assert evaluate("![1, 2]") is False
        assert evaluate("!{'key': 'value'}") is False

    def test_double_not_operator_parser_bug(self):
        """Test double NOT (!!) operator - documents upstream parser bug."""
        # UPSTREAM BUG: The !! syntax is parsed incorrectly and behaves like single !
        # This is a known issue in the cel-interpreter crate
        assert evaluate("!!true") is False  # BUG: Should be True, behaves like !true
        assert evaluate("!!false") is True  # BUG: Should be False, behaves like !false
        assert evaluate("!!0") is True  # BUG: Should be False, behaves like !0
        assert evaluate("!!1") is False  # BUG: Should be True, behaves like !1
        assert evaluate("!!''") is True  # BUG: Should be False, behaves like !''
        assert evaluate("!!'hello'") is False  # BUG: Should be True, behaves like !'hello'

        # WORKAROUND: Use parentheses for correct double NOT behavior
        assert evaluate("!(!true)") is True  # Correct: NOT(NOT(true)) = True
        assert evaluate("!(!false)") is False  # Correct: NOT(NOT(false)) = False
        assert evaluate("!(!0)") is False  # Correct: NOT(NOT(0)) = False
        assert evaluate("!(!1)") is True  # Correct: NOT(NOT(1)) = True
        assert evaluate("!(!(''))") is False  # Correct: NOT(NOT('')) = False
        assert evaluate("!(!('hello'))") is True  # Correct: NOT(NOT('hello')) = True

    def test_bool_function_unavailable(self):
        """Test that bool() function is not available."""
        with pytest.raises(RuntimeError, match="Undefined variable or function: 'bool'"):
            evaluate("bool(true)")

        with pytest.raises(RuntimeError, match="Undefined variable or function: 'bool'"):
            evaluate("bool(0)")

        with pytest.raises(RuntimeError, match="Undefined variable or function: 'bool'"):
            evaluate("bool('')")

    def test_logical_and_truthiness(self):
        """Test truthiness evaluation in logical AND operations."""
        # AND operator behavior: returns boolean values, not original operands
        # Falsy values in AND return False
        assert evaluate("0 && true") is False
        assert evaluate("false && true") is False
        assert evaluate("'' && true") is False
        assert evaluate("null && true") is False
        assert evaluate("[] && true") is False
        assert evaluate("{} && true") is False

        # Truthy values in AND return True when both operands are truthy
        assert evaluate("1 && true") is True
        assert evaluate("true && 1") is True
        assert evaluate("'hello' && true") is True
        assert evaluate("true && 'hello'") is True

    def test_logical_or_truthiness(self):
        """Test truthiness evaluation in logical OR operations."""
        # OR operator shows behavioral difference from CEL spec - returns original values
        # Falsy values in OR
        assert evaluate("0 || false") is False  # Both falsy -> False
        assert evaluate("false || 0") == 0  # Returns second operand when first is falsy
        assert evaluate("'' || false") is False  # Both falsy -> False
        assert evaluate("null || false") is False  # Both falsy -> False

        # Truthy values in OR - demonstrates the documented behavioral difference
        # CEL spec: should return boolean true/false
        # This implementation: returns original truthy value (JavaScript-like)
        assert evaluate("1 || false") == 1  # Returns original int, not boolean
        assert evaluate("42 || false") == 42  # Returns original int, not boolean
        assert evaluate("'hello' || false") == "hello"  # Returns string, not boolean
        assert evaluate("[1, 2] || false") == [1, 2]  # Returns list, not boolean

    def test_ternary_operator_truthiness(self):
        """Test truthiness evaluation in ternary conditional expressions."""
        # Falsy values
        assert evaluate("0 ? 'truthy' : 'falsy'") == "falsy"
        assert evaluate("false ? 'truthy' : 'falsy'") == "falsy"
        assert evaluate("'' ? 'truthy' : 'falsy'") == "falsy"
        assert evaluate("null ? 'truthy' : 'falsy'") == "falsy"
        assert evaluate("[] ? 'truthy' : 'falsy'") == "falsy"
        assert evaluate("{} ? 'truthy' : 'falsy'") == "falsy"

        # Truthy values
        assert evaluate("1 ? 'truthy' : 'falsy'") == "truthy"
        assert evaluate("true ? 'truthy' : 'falsy'") == "truthy"
        assert evaluate("'hello' ? 'truthy' : 'falsy'") == "truthy"
        assert evaluate("[1] ? 'truthy' : 'falsy'") == "truthy"
        assert evaluate("{'key': 'value'} ? 'truthy' : 'falsy'") == "truthy"

    def test_boolean_coercion_consistency(self):
        """Test consistency of boolean coercion across different contexts."""
        # Test that the same value has consistent truthiness
        test_values = [
            (0, False),  # Zero is falsy
            (1, True),  # One is truthy
            ("", False),  # Empty string is falsy
            ("hello", True),  # Non-empty string is truthy
            ([], False),  # Empty list is falsy
            ([1], True),  # Non-empty list is truthy
            ({}, False),  # Empty map is falsy
            ({"a": 1}, True),  # Non-empty map is truthy
        ]

        for value, is_truthy in test_values:
            # NOT operator returns proper booleans
            not_result = evaluate("!x", {"x": value})
            expected_not = False if is_truthy else True
            assert not_result == expected_not, (
                f"!{value} should be {expected_not}, got {not_result}"
            )

            # Ternary operator
            ternary_result = evaluate("x ? 'T' : 'F'", {"x": value})
            expected_ternary = "T" if is_truthy else "F"
            assert ternary_result == expected_ternary, (
                f"{value} ? 'T' : 'F' should be {expected_ternary}"
            )

    def test_comparison_operators_return_booleans(self):
        """Test that comparison operators properly return boolean values."""
        # Unlike logical operators, comparison operators should return proper booleans
        assert evaluate("1 == 1") is True
        assert evaluate("1 != 2") is True
        assert evaluate("1 < 2") is True
        assert evaluate("2 > 1") is True
        assert evaluate("1 <= 1") is True
        assert evaluate("1 >= 1") is True

        assert evaluate("1 == 2") is False
        assert evaluate("1 != 1") is False
        assert evaluate("2 < 1") is False
        assert evaluate("1 > 2") is False
        assert evaluate("2 <= 1") is False
        assert evaluate("1 >= 2") is False

    def test_mixed_boolean_expressions(self):
        """Test complex expressions mixing different boolean contexts."""
        context = {
            "empty_string": "",
            "non_empty_string": "hello",
            "zero": 0,
            "positive": 42,
            "empty_list": [],
            "non_empty_list": [1, 2, 3],
            "is_valid": True,
            "is_invalid": False,
        }

        # Complex AND/OR with mixed types
        assert evaluate("positive && non_empty_string", context) is True  # AND returns boolean
        assert evaluate("zero || positive", context) == 42  # OR returns original truthy value
        assert (
            evaluate("empty_string || 'default'", context) == "default"
        )  # OR returns original value

        # Mixed with comparisons
        assert evaluate("positive > 0 && non_empty_string", context) is True  # AND returns boolean
        assert evaluate("zero == 0 || is_invalid", context) is True  # OR with boolean

        # Complex ternary expressions
        assert (
            evaluate("positive ? (empty_string || 'fallback') : 'negative'", context) == "fallback"
        )

    def test_boolean_context_with_variables(self):
        """Test boolean coercion with context variables."""
        context = {
            "user": {"name": "Alice", "age": 25},
            "settings": {},
            "items": [1, 2, 3],
            "empty_items": [],
            "config": {"debug": True},
        }

        # Object truthiness
        assert evaluate("user ? 'has_user' : 'no_user'", context) == "has_user"
        assert evaluate("settings ? 'has_settings' : 'no_settings'", context) == "no_settings"

        # List truthiness
        assert evaluate("items ? 'has_items' : 'no_items'", context) == "has_items"
        assert evaluate("empty_items ? 'has_items' : 'no_items'", context) == "no_items"

        # Nested access with boolean logic
        assert evaluate("user && user.age > 18", context)
        assert evaluate("!settings || config.debug", context)

    def test_documented_behavioral_differences(self):
        """Test and document the known behavioral differences from CEL spec."""
        # This test documents the behavioral differences mentioned in cel-compliance.md

        # OR operator returns original values instead of booleans
        # CEL spec: 42 || false should return true (boolean)
        # This implementation: returns 42 (original value)
        result = evaluate("42 || false")
        assert result == 42  # JavaScript-like behavior, not CEL spec

        result = evaluate("0 || 'default'")
        assert result == "default"  # Returns original string, not boolean

        # AND operator behaves differently - returns boolean values
        result = evaluate("'hello' && 42")
        assert result is True  # Returns boolean True when both operands are truthy

        result = evaluate("0 && 'unreachable'")
        assert result is False  # Returns boolean False when first operand is falsy

    def test_edge_cases_and_special_values(self):
        """Test edge cases and special values in boolean contexts."""
        # Unicode strings
        assert evaluate("'🌍' ? 'truthy' : 'falsy'") == "truthy"
        assert evaluate("!''") == 1  # Empty string is falsy

        # Large numbers
        assert evaluate("!9999999999") == 0
        assert evaluate("!0.0000001") == 0

        # Negative numbers
        assert evaluate("!-1") == 0
        assert evaluate("!-42") == 0

        # Floating point edge cases
        assert evaluate("!0.0") == 1
        assert evaluate("!-0.0") == 1
