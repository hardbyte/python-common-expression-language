"""
Regression tests for GitHub issue #16:
String variables misinterpreted as floats when floats exist in context

Tests ensure that string literals are preserved correctly in strict CEL mode
and are not corrupted during evaluation.
"""

import pytest
from cel import Context, evaluate


class TestIssue16StringLiteralRegression:
    """Test cases for string literal preservation issue."""

    def test_string_comparison_with_float_context(self):
        """Test that string comparisons work correctly with floats in context."""
        record = {"var": "epa1", "var_2": 10, "var_3": 0.4}
        ctx = Context(record)

        result = evaluate('var == "epa1"', ctx)
        assert result is True, "String comparison should work with floats in context"

    def test_string_literal_with_number_suffix(self):
        """Test that string literals ending with numbers are not modified."""
        ctx = Context({"value": 0.4})  # Float in context

        result = evaluate('"epa1"', ctx)
        assert result == "epa1", f"String literal should be unchanged, got {result}"

    def test_string_literal_with_embedded_numbers(self):
        """Test that string literals with numbers in the middle are not modified."""
        ctx = Context({"value": 0.4})  # Float in context

        test_cases = [
            '"abc123def"',
            '"123abc"',
            '"abc123"',
            '"1a2b3c"',
        ]

        for expr in test_cases:
            expected = expr.strip('"')  # Remove quotes to get expected string
            result = evaluate(expr, ctx)
            assert result == expected, (
                f"Expression {expr} should evaluate to {expected}, got {result}"
            )

    def test_string_literal_pure_numbers(self):
        """Test that string literals that look like pure numbers are not modified."""
        ctx = Context({"value": 0.4})  # Float in context

        test_cases = [
            '"123"',
            '"456.789"',
            '"0"',
            '"-42"',
        ]

        for expr in test_cases:
            expected = expr.strip('"')  # Remove quotes to get expected string
            result = evaluate(expr, ctx)
            assert result == expected, (
                f"Expression {expr} should evaluate to {expected}, got {result}"
            )

    def test_string_function_with_numeric_strings(self):
        """Test that the string() function works correctly with numeric strings."""
        ctx = Context({"value": 0.4})  # Float in context

        result = evaluate('string("epa1")', ctx)
        assert result == "epa1", f"string() function should return unchanged string, got {result}"

    def test_single_quote_strings(self):
        """Test that single-quoted strings are also handled correctly."""
        ctx = Context({"value": 0.4})  # Float in context

        test_cases = [
            "'epa1'",
            "'abc123def'",
            "'123'",
        ]

        for expr in test_cases:
            expected = expr.strip("'")  # Remove quotes to get expected string
            result = evaluate(expr, ctx)
            assert result == expected, (
                f"Expression {expr} should evaluate to {expected}, got {result}"
            )

    def test_escaped_quotes_in_strings(self):
        """Test that strings with escaped quotes are handled correctly."""
        ctx = Context({"value": 0.4})  # Float in context

        # Test escaped double quotes
        result = evaluate('"He said \\"hello123\\""', ctx)
        assert result == 'He said "hello123"', "Escaped quotes should be handled correctly"

        # Test escaped single quotes
        result = evaluate("'Don\\'t change123'", ctx)
        assert result == "Don't change123", "Escaped single quotes should be handled correctly"

    def test_control_case_without_floats(self):
        """Control test: verify behavior without floats in context."""
        ctx = Context({"var": "epa1", "var_2": 10})  # No floats

        result = evaluate('var == "epa1"', ctx)
        assert result is True, "Control test should pass without floats in context"

    def test_mixed_expressions_with_actual_numbers(self):
        """Test that mixed arithmetic fails appropriately in strict mode."""
        ctx = Context({"value": 0.4})  # Float in context

        # Mixed arithmetic should fail in strict mode
        with pytest.raises(TypeError, match="Unsupported.*operation"):
            evaluate("1 + 2.5", ctx)

        # Mixed type with context variables should also fail
        with pytest.raises(TypeError, match="Unsupported.*operation"):
            evaluate("value + 1", ctx)  # 0.4 + 1 should fail in strict mode

    def test_complex_expressions_with_strings_and_numbers(self):
        """Test complex expressions mixing strings and numbers."""
        ctx = Context({"name": "test123", "value": 0.5})

        # String comparison should work
        result = evaluate('name == "test123" && value > 0.4', ctx)
        assert result is True, "Complex expression with strings and numbers should work"

        # String in ternary operator
        result = evaluate('value > 0.3 ? "yes123" : "no456"', ctx)
        assert result == "yes123", "Ternary operator with strings should work"

    def test_edge_case_empty_strings(self):
        """Test edge cases with empty strings."""
        ctx = Context({"value": 0.4})

        result = evaluate('""', ctx)
        assert result == "", "Empty string should remain empty"

    def test_issue_specific_reproduction(self):
        """Direct reproduction of the original issue report."""
        record = {"var": "epa1", "var_2": 10, "var_3": 0.4}
        ctx = Context(record)

        # Test 1: The main issue - string comparison
        result = evaluate('var == "epa1"', ctx)
        assert result is True, "Original issue case should return True"

        # Test 2: String function behavior
        result2 = evaluate('string("epa1")', ctx)
        assert result2 == "epa1", "string() function should return original string"

        # Test 3: The edge case mentioned in the issue
        # Note: In the original issue, "epa1epa" worked correctly
        result3 = evaluate('"epa1epa"', ctx)
        assert result3 == "epa1epa", "String without trailing number should work"
