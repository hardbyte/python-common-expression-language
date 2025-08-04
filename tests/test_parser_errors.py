"""
Tests for parser error handling.

Tests verify that all malformed expressions raise proper ValueError exceptions
instead of causing panics. Parser panic handling has been implemented with
std::panic::catch_unwind to gracefully handle upstream parser issues.
"""

import cel
import pytest


class TestParserErrors:
    """Test various parser error conditions."""

    def test_unclosed_single_quote_raises_clean_error(self):
        """Test that unclosed single quotes raise proper ValueError exceptions."""
        # Previously caused panics, now gracefully handled with catch_unwind
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate("'unclosed quote", {})

    def test_unclosed_double_quote_raises_clean_error(self):
        """Test that unclosed double quotes raise proper ValueError exceptions."""
        # Previously the original issue: 'timestamp("2024-01-01T00:00:00Z")
        # Now safely handled with panic catching
        with pytest.raises(ValueError, match="Failed to parse expression"):
            cel.evaluate('"unclosed quote', {})

    def test_complex_unclosed_quote_in_function_call(self):
        """Test the specific case from the original user report."""
        # This was the exact expression that previously caused panics
        # Now safely returns a clean ValueError
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
    """Document the current state of parser error handling after panic fixes."""

    def test_good_syntax_works(self):
        """Verify that correct syntax still works."""
        # These should all work fine
        assert cel.evaluate("'hello'", {}) == "hello"
        assert cel.evaluate('"hello"', {}) == "hello"
        assert cel.evaluate("timestamp('2024-01-01T00:00:00Z')", {})
        assert cel.evaluate('timestamp("2024-01-01T00:00:00Z")', {})

    def test_different_error_types(self):
        """Document the different types of errors now properly handled."""
        # Runtime error (undefined variable) - properly mapped to RuntimeError
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("undefined_variable", {})

        # Parse error (invalid syntax) - previously caused panics, now clean ValueError
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

        # All parser errors now give clean ValueError exceptions
        # Previously quote issues caused panics, now properly handled
        with pytest.raises(ValueError, match="Failed to parse expression"):
            evaluator.evaluate("'unclosed quote")

        with pytest.raises(ValueError, match="Failed to parse expression"):
            evaluator.evaluate('"unclosed quote')

        # This gives a clean compile error
        with pytest.raises(ValueError, match="Failed to compile expression"):
            evaluator.evaluate("(1 + 2")
