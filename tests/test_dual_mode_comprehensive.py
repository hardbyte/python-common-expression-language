"""
Comprehensive test suite for Strict CEL evaluation mode.

This test ensures that core CEL functionality works correctly in strict mode,
including string handling, array indexing, and other essential features.
Also covers the fix for GitHub issue #16 (string literals being corrupted).
"""

import cel
import pytest
from cel import Context, evaluate


class TestStrictModeEvaluation:
    """Test Strict CEL evaluation mode comprehensively."""

    def test_string_literals_preserved_in_strict_mode(self):
        """Test that string literals are preserved in strict evaluation mode."""
        test_cases = [
            '"epa1"',
            '"abc123def"',
            '"123"',
            '"test42test"',
            '""',
            '"42"',
            "'single123'",
            '"with\\"escaped\\"quotes"',
        ]

        # Context with floats
        ctx = Context({"value": 0.4, "rate": 3.14})

        for expr in test_cases:
            # Remove quotes and handle escaped quotes properly
            if expr.startswith('"') and expr.endswith('"'):
                expected = expr[1:-1].replace('\\"', '"')
            elif expr.startswith("'") and expr.endswith("'"):
                expected = expr[1:-1].replace("\\'", "'")
            else:
                expected = expr

            result = evaluate(expr, ctx)

            assert result == expected, f"Strict mode failed for {expr}"
            assert isinstance(result, str), f"Strict mode returned non-string for {expr}"

    def test_string_comparisons_work_in_strict_mode(self):
        """Test that string comparisons work correctly in strict mode."""
        test_cases = [
            ('var == "epa1"', {"var": "epa1", "value": 0.4}, True),
            ('name == "test123"', {"name": "test123", "num": 3.14}, True),
            ('id == "42"', {"id": "42", "float_val": 1.5}, True),
            ('text != "abc123"', {"text": "xyz123", "other": 2.7}, True),
            ('status == "active"', {"status": "inactive", "rate": 1.2}, False),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx)

            result = evaluate(expr, context)

            assert result == expected, f"Strict mode failed for {expr}"

    def test_mixed_arithmetic_fails_in_strict_mode(self):
        """Test that mixed arithmetic fails appropriately in strict mode."""
        test_cases = [
            ("1 + 2.5", {}),
            ("2.5 + 1", {}),
            ("3 * 1.5", {}),
            ("10.0 / 2", {}),
            ("value + 1", {"value": 2.5}),
            ("1 * count", {"count": 3.14}),
        ]

        for expr, ctx in test_cases:
            context = Context(ctx) if ctx else None

            # Should fail in Strict mode
            with pytest.raises(TypeError, match="Unsupported.*operation"):
                evaluate(expr, context)

    def test_same_type_arithmetic_works_in_strict_mode(self):
        """Test that same-type arithmetic works correctly in strict mode."""
        test_cases = [
            ("1 + 2", {}, 3),
            ("3.5 + 1.5", {}, 5.0),
            ("10 * 2", {}, 20),
            ("7.5 / 2.5", {}, 3.0),
            ("15 % 4", {}, 3),
            ("x + y", {"x": 5, "y": 7}, 12),
            ("a * b", {"a": 2.5, "b": 4.0}, 10.0),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None

            result = evaluate(expr, context)

            assert result == expected, f"Strict mode failed for {expr}"

    def test_array_indexing_works_in_strict_mode(self):
        """Test that array indexing works correctly in strict mode."""
        test_cases = [
            ("[1, 2, 3][0]", {}, 1),
            ("[1, 2, 3][1]", {"value": 0.4}, 2),
            ("data[2]", {"data": [10, 20, 30], "other": 1.5}, 30),
            ("[1.5, 2.5, 3.5][1]", {}, 2.5),
            ('["a", "b", "c"][0]', {}, "a"),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None

            result = evaluate(expr, context)

            assert result == expected, f"Array indexing failed for {expr}"

    def test_integer_arithmetic_stays_integer_in_strict_mode(self):
        """Test that integer arithmetic returns integers in strict mode (no promotion)."""
        test_cases = [
            ("1 + 2", {"float_val": 3.14}, 3),
            ("x * 2", {"x": 5, "float_val": 1.5}, 10),
            ("count + total", {"count": 3, "total": 7, "rate": 2.5}, 10),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx)

            result = evaluate(expr, context)

            # In Strict mode, should remain integer (no promotion)
            assert isinstance(result, int), f"Strict mode should return int for {expr}"
            assert result == expected, f"Strict mode failed for {expr}"

    def test_comprehensions_work_in_strict_mode(self):
        """Test that comprehensions work correctly in strict mode."""
        test_cases = [
            "[1, 2, 3].map(x, x * 2)",  # Should work (integers)
            "[1, 2, 3].all(x, x > 0)",  # Should work
            "[1, 2, 3].filter(x, x > 1)",  # Should work
        ]

        for expr in test_cases:
            result = evaluate(expr)
            assert result is not None, f"Comprehension failed: {expr}"

    def test_comprehensions_with_explicit_mixed_types_fail(self):
        """Test that comprehensions with explicit mixed arithmetic fail appropriately in strict mode."""
        mixed_type_arithmetic_comprehensions = [
            "[1, 2, 3].map(x, x * 2.0)",  # Mixed arithmetic should fail
            "[1, 2, 3].map(x, x + 1.5)",  # Mixed arithmetic should fail
        ]

        for expr in mixed_type_arithmetic_comprehensions:
            # Should fail due to mixed arithmetic inside comprehension
            with pytest.raises(TypeError, match="Unsupported.*operation"):
                evaluate(expr)

    def test_comprehensions_with_mixed_comparisons_work(self):
        """Test that comprehensions with mixed type comparisons work in strict mode (comparisons are allowed)."""
        mixed_comparison_comprehensions = [
            "[1, 2, 3].filter(x, x > 1.5)",  # Mixed comparison - works
            "[1, 2, 3].all(x, x < 5.0)",  # Mixed comparison - works
        ]

        for expr in mixed_comparison_comprehensions:
            # Should work because comparisons between int/float are allowed
            result = evaluate(expr)
            assert result is not None, f"Mixed comparison comprehension failed: {expr}"

    def test_complex_expressions_with_parentheses(self):
        """Test complex expressions with parentheses work in strict mode."""
        test_cases = [
            ("(1 + 2) * 3", {}, 9),
            ("(3.5 + 1.5) / 2.0", {}, 2.5),  # Same type division - works in strict mode
            ("x > 0 && y < 10", {"x": 5, "y": 8.5}, True),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None

            result = evaluate(expr, context)

            assert result == expected, f"Complex expression failed: {expr}"

    def test_string_functions_preserve_strings(self):
        """Test that string functions preserve string literals correctly in strict mode."""
        test_cases = [
            ('string("test123")', {"val": 0.4}, "test123"),
            ('size("abc123")', {"num": 1.5}, 6),
            ('"hello" + " " + "world"', {"rate": 2.5}, "hello world"),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx)

            result = evaluate(expr, context)

            assert result == expected, f"String function failed: {expr}"

    def test_edge_cases_strict_mode(self):
        """Test edge cases work correctly in strict mode."""
        test_cases = [
            ("null", {}, None),
            ("true", {}, True),
            ("false", {}, False),
            ("[]", {}, []),
            ("{}", {}, {}),
            ("size([1, 2, 3])", {}, 3),
        ]

        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None

            result = evaluate(expr, context)

            assert result == expected, f"Edge case failed: {expr}"

    def test_github_issue_16_regression(self):
        """
        Regression test for GitHub issue #16: String variables misinterpreted as floats.

        This is the core issue that was fixed - string literals should be preserved.
        """
        # The original issue report case
        record = {"var": "epa1", "var_2": 10, "var_3": 0.4}
        ctx = Context(record)

        # Test 1: String comparison should work
        result = evaluate('var == "epa1"', ctx)
        assert result is True, "String comparison should work in strict mode"

        # Test 2: String function should preserve string
        result = evaluate('string("epa1")', ctx)
        assert result == "epa1", "string() function should return unchanged string in strict mode"

        # Test 3: Direct string literal should be preserved
        result = evaluate('"epa1"', ctx)
        assert result == "epa1", "String literal should be preserved in strict mode"
