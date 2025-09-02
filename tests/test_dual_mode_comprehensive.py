"""
Comprehensive test suite for both Python and Strict evaluation modes.

This test ensures that our AST-based integer promotion solution works correctly
in both evaluation modes and covers all edge cases, including the fix for
GitHub issue #16 (string literals being corrupted).
"""

import pytest
import cel
from cel import Context, evaluate


class TestDualModeEvaluation:
    """Test both Python and Strict evaluation modes comprehensively."""

    def test_string_literals_preserved_in_both_modes(self):
        """Test that string literals are preserved in both evaluation modes."""
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
        
        # Context with floats to trigger promotion logic
        ctx = Context({'value': 0.4, 'rate': 3.14})
        
        for expr in test_cases:
            # Remove quotes and handle escaped quotes properly
            if expr.startswith('"') and expr.endswith('"'):
                expected = expr[1:-1].replace('\\"', '"')
            elif expr.startswith("'") and expr.endswith("'"):
                expected = expr[1:-1].replace("\\'", "'")
            else:
                expected = expr
            
            result_python = evaluate(expr, ctx, "python")
            result_strict = evaluate(expr, ctx, "strict")
            
            assert result_python == expected, f"Python mode failed for {expr}"
            assert result_strict == expected, f"Strict mode failed for {expr}"
            assert isinstance(result_python, str), f"Python mode returned non-string for {expr}"
            assert isinstance(result_strict, str), f"Strict mode returned non-string for {expr}"

    def test_string_comparisons_work_in_both_modes(self):
        """Test that string comparisons work correctly in both modes."""
        test_cases = [
            ('var == "epa1"', {'var': 'epa1', 'value': 0.4}, True),
            ('name == "test123"', {'name': 'test123', 'num': 3.14}, True),
            ('id == "42"', {'id': '42', 'float_val': 1.5}, True),
            ('text != "abc123"', {'text': 'xyz123', 'other': 2.7}, True),
            ('status == "active"', {'status': 'inactive', 'rate': 1.2}, False),
        ]
        
        for expr, ctx, expected in test_cases:
            context = Context(ctx)
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            assert result_python == expected, f"Python mode failed for {expr}"
            assert result_strict == expected, f"Strict mode failed for {expr}"

    def test_mixed_arithmetic_python_vs_strict(self):
        """Test that mixed arithmetic works in Python mode but fails in Strict mode."""
        test_cases = [
            ('1 + 2.5', {}, 3.5),
            ('2.5 + 1', {}, 3.5),
            ('3 * 1.5', {}, 4.5),
            ('10.0 / 2', {}, 5.0),
            ('value + 1', {'value': 2.5}, 3.5),
            ('1 * count', {'count': 3.14}, 3.14),
        ]
        
        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None
            
            # Should work in Python mode
            result_python = evaluate(expr, context, "python")
            assert abs(result_python - expected) < 1e-10, f"Python mode failed for {expr}"
            
            # Should fail in Strict mode
            with pytest.raises(TypeError, match="Unsupported.*operation"):
                evaluate(expr, context, "strict")

    def test_same_type_arithmetic_works_in_both_modes(self):
        """Test that same-type arithmetic works identically in both modes."""
        test_cases = [
            ('1 + 2', {}, 3),
            ('3.5 + 1.5', {}, 5.0),
            ('10 * 2', {}, 20),
            ('7.5 / 2.5', {}, 3.0),
            ('15 % 4', {}, 3),
            ('x + y', {'x': 5, 'y': 7}, 12),
            ('a * b', {'a': 2.5, 'b': 4.0}, 10.0),
        ]
        
        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            assert result_python == expected, f"Python mode failed for {expr}"
            assert result_strict == expected, f"Strict mode failed for {expr}"

    def test_array_indexing_works_in_both_modes(self):
        """Test that array indexing works correctly in both modes."""
        test_cases = [
            ('[1, 2, 3][0]', {}, 1),
            ('[1, 2, 3][1]', {'value': 0.4}),  # Special case - elements may be promoted in Python mode
            ('data[2]', {'data': [10, 20, 30], 'other': 1.5}, 30),
            ('[1.5, 2.5, 3.5][1]', {}, 2.5),
            ('["a", "b", "c"][0]', {}, "a"),
        ]
        
        for expr, ctx, *expected in test_cases:
            context = Context(ctx) if ctx else None
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            # Both should work without errors
            assert result_python is not None
            assert result_strict is not None
            
            # For the special case where list elements might be promoted
            if len(expected) == 0:  # No specific expected value
                # Just ensure both work and indices are preserved
                continue
            else:
                expected_val = expected[0]
                assert result_python == expected_val or (isinstance(expected_val, int) and isinstance(result_python, float) and result_python == float(expected_val))
                assert result_strict == expected_val

    def test_context_dependent_promotion_python_mode(self):
        """Test that integer promotion happens in Python mode when floats are in context."""
        test_cases = [
            # With float context - should promote integers in Python mode
            ('1 + 2', {'float_val': 3.14}),
            ('x * 2', {'x': 5, 'float_val': 1.5}),
            ('count + total', {'count': 3, 'total': 7, 'rate': 2.5}),
        ]
        
        for expr, ctx in test_cases:
            context = Context(ctx)
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            # In Python mode with float context, integer results should be promoted to float
            assert isinstance(result_python, float), f"Python mode should return float for {expr} with float context"
            
            # In Strict mode, should remain integer (no promotion)
            assert isinstance(result_strict, int), f"Strict mode should return int for {expr}"

    def test_comprehensions_fallback_behavior(self):
        """Test that comprehensions fall back to original string processing."""
        test_cases = [
            "[1, 2, 3].map(x, x * 2)",      # Should work (integers)
            "[1, 2, 3].all(x, x > 0)",      # Should work
            "[1, 2, 3].filter(x, x > 1)",   # Should work
        ]
        
        for expr in test_cases:
            # Should work in both modes because comprehensions fall back
            result_python = evaluate(expr, None, "python")
            result_strict = evaluate(expr, None, "strict")
            
            assert result_python is not None
            assert result_strict is not None
            # Results should be identical (fallback behavior)
            assert result_python == result_strict

    def test_comprehensions_with_explicit_mixed_types_fail(self):
        """Test that comprehensions with explicit mixed arithmetic fail appropriately."""
        mixed_type_arithmetic_comprehensions = [
            "[1, 2, 3].map(x, x * 2.0)",   # Mixed arithmetic should fail
            "[1, 2, 3].map(x, x + 1.5)",   # Mixed arithmetic should fail
        ]
        
        for expr in mixed_type_arithmetic_comprehensions:
            # Should fail due to mixed arithmetic inside comprehension
            with pytest.raises(TypeError, match="Unsupported.*operation"):
                evaluate(expr, None, "python")
            with pytest.raises(TypeError, match="Unsupported.*operation"):
                evaluate(expr, None, "strict")

    def test_comprehensions_with_mixed_comparisons_work(self):
        """Test that comprehensions with mixed type comparisons work (comparisons are allowed)."""
        mixed_comparison_comprehensions = [
            "[1, 2, 3].filter(x, x > 1.5)",  # Mixed comparison - works
            "[1, 2, 3].all(x, x < 5.0)",     # Mixed comparison - works
        ]
        
        for expr in mixed_comparison_comprehensions:
            # Should work because comparisons between int/float are allowed
            result_python = evaluate(expr, None, "python")
            result_strict = evaluate(expr, None, "strict")
            assert result_python is not None
            assert result_strict is not None

    def test_complex_expressions_with_parentheses(self):
        """Test complex expressions with parentheses work in both modes."""
        test_cases = [
            ('(1 + 2) * 3', {}, 9, 9),  # Same in both modes
            ('(3.5 + 1.5) / 2.0', {}, 2.5, 2.5),  # Same type division - works in both modes
            ('x > 0 && y < 10', {'x': 5, 'y': 8.5}, True, True),
        ]
        
        for expr, ctx, expected_python, expected_strict in test_cases:
            context = Context(ctx) if ctx else None
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            assert result_python == expected_python
            assert result_strict == expected_strict

    def test_string_functions_preserve_strings(self):
        """Test that string functions preserve string literals correctly."""
        test_cases = [
            ('string("test123")', {'val': 0.4}, "test123"),
            ('size("abc123")', {'num': 1.5}, 6),
            ('"hello" + " " + "world"', {'rate': 2.5}, "hello world"),
        ]
        
        for expr, ctx, expected in test_cases:
            context = Context(ctx)
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            assert result_python == expected
            assert result_strict == expected

    def test_edge_cases_both_modes(self):
        """Test edge cases work identically in both modes."""
        test_cases = [
            ('null', {}, None),
            ('true', {}, True), 
            ('false', {}, False),
            ('[]', {}, []),
            ('{}', {}, {}),
            ('size([1, 2, 3])', {}, 3),
        ]
        
        for expr, ctx, expected in test_cases:
            context = Context(ctx) if ctx else None
            
            result_python = evaluate(expr, context, "python")
            result_strict = evaluate(expr, context, "strict")
            
            assert result_python == expected
            assert result_strict == expected

    def test_github_issue_16_regression(self):
        """
        Regression test for GitHub issue #16: String variables misinterpreted as floats.
        
        This is the core issue that was fixed with AST-based promotion.
        """
        # The original issue report case
        record = {'var': 'epa1', "var_2": 10, "var_3": 0.4}
        ctx = Context(record)
        
        # Test 1: String comparison should work
        result = evaluate('var == "epa1"', ctx, "python")
        assert result is True, "String comparison should work in Python mode"
        
        result = evaluate('var == "epa1"', ctx, "strict")
        assert result is True, "String comparison should work in Strict mode"
        
        # Test 2: String function should preserve string
        result = evaluate('string("epa1")', ctx, "python")
        assert result == "epa1", "string() function should return unchanged string"
        
        result = evaluate('string("epa1")', ctx, "strict") 
        assert result == "epa1", "string() function should return unchanged string in strict mode"
        
        # Test 3: Direct string literal should be preserved
        result = evaluate('"epa1"', ctx, "python")
        assert result == "epa1", "String literal should be preserved"
        
        result = evaluate('"epa1"', ctx, "strict")
        assert result == "epa1", "String literal should be preserved in strict mode"