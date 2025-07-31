"""
Tests for parser error handling.

These tests document known issues with the underlying CEL parser
where invalid syntax causes Rust panics instead of proper error messages.
"""

import pytest
import cel


class TestParserErrors:
    """Test various parser error conditions."""

    def test_unclosed_single_quote_causes_panic(self):
        """Test that unclosed single quotes cause parser panics."""
        # This should ideally return a proper syntax error instead of panicking
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate("'unclosed quote", {})

    def test_unclosed_double_quote_causes_panic(self):
        """Test that unclosed double quotes cause parser panics."""
        # The original issue: 'timestamp("2024-01-01T00:00:00Z")
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate('"unclosed quote', {})

    def test_complex_unclosed_quote_in_function_call(self):
        """Test the specific case from the user report."""
        # This is the exact expression that caused the panic
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate('\'timestamp("2024-01-01T00:00:00Z")', {})

    def test_unclosed_parentheses(self):
        """Test unclosed parentheses handling."""
        with pytest.raises(ValueError):
            cel.evaluate("(1 + 2", {})

    def test_unclosed_brackets(self):
        """Test unclosed square brackets handling."""
        with pytest.raises(ValueError):
            cel.evaluate("[1, 2, 3", {})

    def test_unclosed_braces(self):
        """Test unclosed curly braces handling."""
        with pytest.raises(ValueError):
            cel.evaluate("{'key': 'value'", {})

    def test_mismatched_quotes_in_expressions(self):
        """Test various mismatched quote scenarios."""
        invalid_expressions = [
            "'hello\"",  # Mixed quote types
            "\"hello'",  # Mixed quote types
            "'hello' + \"world",  # Unclosed second string
            '"hello" + \'world',  # Unclosed second string
        ]

        for expr in invalid_expressions:
            with pytest.raises(ValueError, match="Failed to parse expression"):
                cel.evaluate(expr, {})


class TestParserErrorDocumentation:
    """Document the current state of parser error handling."""

    def test_good_syntax_works(self):
        """Verify that correct syntax still works."""
        # These should all work fine
        assert cel.evaluate("'hello'", {}) == "hello"
        assert cel.evaluate('"hello"', {}) == "hello"
        assert cel.evaluate("timestamp('2024-01-01T00:00:00Z')", {})
        assert cel.evaluate('timestamp("2024-01-01T00:00:00Z")', {})

    def test_parser_panic_vs_clean_error(self):
        """Document the difference between clean errors and panics."""
        # This should be a clean error (undefined variable) - enhanced error handling now uses RuntimeError
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("undefined_variable", {})

        # This causes a parser panic (invalid syntax)
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate("'unclosed", {})


class TestCLIErrorHandling:
    """Test that the CLI handles errors appropriately."""

    def test_cli_empty_expression_handling(self):
        """Test that the CLI catches empty expressions."""
        try:
            from cel.cli import CELEvaluator
        except ImportError:
            # CLI not available, skip test
            pytest.skip("CLI module not available")

        evaluator = CELEvaluator()

        # Test empty expression
        with pytest.raises(ValueError, match="Empty expression"):
            evaluator.evaluate("")

        with pytest.raises(ValueError, match="Empty expression"):
            evaluator.evaluate("   ")

    def test_cli_passes_through_parser_errors(self):
        """Test that CLI properly passes through parser errors without modification."""
        try:
            from cel.cli import CELEvaluator
        except ImportError:
            # CLI not available, skip test
            pytest.skip("CLI module not available")

        evaluator = CELEvaluator()

        # These should pass through as-is from the underlying parser
        # Some cause panics (quote issues), others give clean compile errors
        with pytest.raises(ValueError, match="Failed to parse expression"):
            evaluator.evaluate("'unclosed quote")

        with pytest.raises(ValueError, match="Failed to parse expression"):
            evaluator.evaluate('"unclosed quote')

        # This gives a clean compile error (not a panic)
        with pytest.raises(ValueError, match="Failed to compile expression"):
            evaluator.evaluate("(1 + 2")
