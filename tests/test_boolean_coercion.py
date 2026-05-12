"""
Test CEL specification-compliant boolean operations.

This module tests the correct CEL specification behavior where logical operators
require boolean operands. Mixed-type operations should fail with "No such overload".
"""

import pytest
from cel import evaluate


class TestCelCompliantBooleanOperations:
    """Test CEL specification-compliant boolean operations."""

    def test_not_operator_with_boolean(self):
        """Test NOT operator with boolean values (correct CEL behavior)."""
        assert evaluate("!true") is False
        assert evaluate("!false") is True

    def test_not_operator_with_non_boolean_fails(self):
        """Test that NOT operator correctly fails with non-boolean operands."""
        non_bool_exprs = ["!0", "!1", "!42", "!''", "!'hello'", "![]", "!{}", "!null"]
        for expr in non_bool_exprs:
            with pytest.raises(TypeError, match="No such overload"):
                evaluate(expr)

    def test_logical_and_with_boolean_operands(self):
        """Test AND operator with boolean operands (correct CEL behavior)."""
        assert evaluate("true && true") is True
        assert evaluate("true && false") is False
        assert evaluate("false && true") is False
        assert evaluate("false && false") is False

    def test_logical_and_with_mixed_types_fails(self):
        """Test that AND operator fails with mixed-type operands when no short-circuit applies.

        CEL spec: errors short-circuit through AND when the other operand is definitively
        false. So `42 && false` returns false (short-circuit), but cases where the boolean
        operand is true (or both are non-bool) propagate the type error.
        """
        with pytest.raises(TypeError, match="No such overload"):
            evaluate("'string' && true")

        with pytest.raises(TypeError, match="No such overload"):
            evaluate("true && 1")

    def test_logical_and_err_resilient_short_circuit(self):
        """CEL spec: `error && false` short-circuits to false even if LHS isn't a bool."""
        assert evaluate("42 && false") is False
        assert evaluate("'string' && false") is False

    def test_logical_or_with_boolean_operands(self):
        """Test OR operator with boolean operands (correct CEL behavior)."""
        assert evaluate("true || true") is True
        assert evaluate("true || false") is True
        assert evaluate("false || true") is True
        assert evaluate("false || false") is False

    def test_logical_or_err_resilient_short_circuit(self):
        """CEL spec: `X || true` short-circuits to true regardless of LHS type."""
        # When second operand is boolean true, short-circuits to true even if first isn't bool
        assert evaluate("true || 99") is True
        assert evaluate("true || 'anything'") is True
        assert evaluate("'string' || true") is True

    def test_logical_or_propagates_type_error_when_no_short_circuit(self):
        """OR raises when neither operand provides a definitive boolean to short-circuit."""
        with pytest.raises(TypeError, match="No such overload"):
            evaluate("false || 99")

        with pytest.raises(TypeError, match="No such overload"):
            evaluate("false || 'text'")

        with pytest.raises(TypeError, match="No such overload"):
            evaluate("42 || false")

        with pytest.raises(TypeError, match="No such overload"):
            evaluate("0 || 'default'")

    def test_ternary_operator_requires_boolean_condition(self):
        """Test ternary operator requires boolean condition."""
        # Boolean conditions work correctly
        assert evaluate("true ? 'yes' : 'no'") == "yes"
        assert evaluate("false ? 'yes' : 'no'") == "no"

        # Non-boolean conditions should fail
        with pytest.raises(TypeError, match="No such overload"):
            evaluate("42 ? 'yes' : 'no'")

        with pytest.raises(TypeError, match="No such overload"):
            evaluate("'string' ? 'yes' : 'no'")

    def test_boolean_comparisons_work_correctly(self):
        """Test that boolean comparisons work as expected."""
        # Equality comparisons
        assert evaluate("true == true") is True
        assert evaluate("false == false") is True
        assert evaluate("true == false") is False

        # Inequality comparisons
        assert evaluate("true != false") is True
        assert evaluate("true != true") is False

    def test_explicit_boolean_conversion_patterns(self):
        """Test patterns for explicit boolean conversion when needed."""
        # Comparison operators can create booleans from other types
        assert evaluate("42 > 0") is True
        assert evaluate("0 == 0") is True
        assert evaluate("'hello' == 'hello'") is True

        # These boolean results can then be used in logical operations
        assert evaluate("(42 > 0) && true") is True
        assert evaluate("(0 == 1) || false") is False

    def test_has_function_for_optional_field_checking(self):
        """Test has() function for safe optional field access."""
        context = {"user": {"name": "Alice"}}

        # has() returns boolean, can be used in logical operations
        assert evaluate("has(user.name)", context) is True
        assert evaluate("has(user.email)", context) is False
        assert evaluate("has(user.name) && true", context) is True
        assert evaluate("has(user.email) || false", context) is False
