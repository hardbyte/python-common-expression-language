"""
Tests for cel.stdlib module - Python implementations of missing CEL functions.

These are Python-side implementations of CEL functions that are not yet available
in the upstream cel-rust library. When upstream adds these functions, we should
remove our implementations and use the native versions instead.
"""

import cel
import pytest
from cel.stdlib import STDLIB_FUNCTIONS, add_stdlib_to_context, substring
from conftest import evaluate


class TestSubstringFunction:
    """Test the substring() function implementation."""

    def test_substring_with_start_and_end(self):
        """Test substring with both start and end indices."""
        assert substring("hello world", 0, 5) == "hello"
        assert substring("hello world", 6, 11) == "world"
        assert substring("hello", 1, 4) == "ell"

    def test_substring_with_start_only(self):
        """Test substring with only start index (extract to end)."""
        assert substring("hello world", 6) == "world"
        assert substring("hello", 1) == "ello"
        assert substring("test", 0) == "test"

    def test_substring_edge_cases(self):
        """Test substring edge cases."""
        # Empty substring
        assert substring("hello", 2, 2) == ""

        # Full string
        assert substring("hello", 0, 5) == "hello"
        assert substring("hello", 0) == "hello"

        # Single character
        assert substring("hello", 0, 1) == "h"
        assert substring("hello", 4, 5) == "o"

    def test_substring_in_cel_expression(self):
        """Test substring function in CEL expressions."""
        context = cel.Context()
        context.add_function("substring", substring)

        # Basic usage
        result = evaluate('substring("hello world", 0, 5)', context)
        assert result == "hello"

        # With context variable
        context.add_variable("text", cel.prepare("hello world"))
        result = evaluate("substring(text, 6)", context)
        assert result == "world"

        # Chained with other operations
        result = evaluate('substring("HELLO", 0, 2) + substring("world", 0, 3)', context)
        assert result == "HEwor"


class TestAddStdlibToContext:
    """Test the add_stdlib_to_context convenience function."""

    def test_add_stdlib_to_context(self):
        """Test that add_stdlib_to_context adds all functions."""
        context = cel.Context()
        add_stdlib_to_context(context)

        # Verify substring is available
        result = evaluate('substring("test", 1, 3)', context)
        assert result == "es"

    def test_stdlib_functions_dict(self):
        """Test that STDLIB_FUNCTIONS contains expected functions."""
        assert "substring" in STDLIB_FUNCTIONS
        assert callable(STDLIB_FUNCTIONS["substring"])


class TestSubstringWithOtherFunctions:
    """Test substring in combination with other CEL features."""

    def test_substring_with_string_methods(self):
        """Test substring combined with CEL string methods."""
        context = cel.Context()
        add_stdlib_to_context(context)

        # Extract and check
        result = evaluate('substring("hello world", 0, 5).size()', context)
        assert result == 5

        # Extract and test membership
        result = evaluate('substring("hello world", 6, 11).startsWith("wor")', context)
        assert result is True

    def test_substring_with_context_variables(self):
        """Test substring with various context data types."""
        context = cel.Context()
        add_stdlib_to_context(context)

        context.add_variable(
            "data", cel.prepare({"message": "Hello, World!", "start": 0, "end": 5})
        )

        result = evaluate("substring(data.message, data.start, data.end)", context)
        assert result == "Hello"

    def test_substring_in_conditional(self):
        """Test substring in conditional expressions."""
        context = cel.Context()
        add_stdlib_to_context(context)
        context.add_variable("email", cel.prepare("user@example.com"))

        # Extract domain
        result = evaluate('substring(email, 5, 12) == "example" ? "valid" : "invalid"', context)
        assert result == "valid"


class TestSubstringDocumentation:
    """Tests that serve as documentation examples."""

    def test_basic_substring_example(self):
        """Basic substring usage example."""
        import cel
        from cel.stdlib import add_stdlib_to_context

        context = cel.Context()
        add_stdlib_to_context(context)

        # Extract "hello" from "hello world"
        result = evaluate('substring("hello world", 0, 5)', context)
        assert result == "hello"

        # Extract from index to end
        result = evaluate('substring("hello world", 6)', context)
        assert result == "world"

    def test_substring_with_variables(self):
        """Using substring with context variables."""
        import cel
        from cel.stdlib import substring

        context = cel.Context()
        context.add_function("substring", substring)
        context.add_variable("text", cel.prepare("The quick brown fox"))

        # Extract words
        result = evaluate("substring(text, 4, 9)", context)
        assert result == "quick"

    def test_substring_string_manipulation(self):
        """Advanced string manipulation with substring."""
        import cel
        from cel.stdlib import add_stdlib_to_context

        context = cel.Context()
        add_stdlib_to_context(context)

        # Get first 3 characters
        result = evaluate('substring("JavaScript", 0, 3)', context)
        assert result == "Jav"

        # Get last characters (simulate with known length)
        context.add_variable("lang", cel.prepare("Python"))
        result = evaluate("substring(lang, 2)", context)
        assert result == "thon"


class TestUpstreamDetection:
    """
    Detection tests for upstream cel-rust implementations.

    These tests verify which pieces are now available natively in cel-rust
    and which still rely on Python wrappers.
    """

    def test_substring_available_upstream(self):
        """
        Test that substring() is now natively available in cel-rust.

        This guards the native method support added upstream.

        Related upstream issue: https://github.com/cel-rust/cel-rust/issues/200
        """
        assert evaluate('"hello".substring(1, 3)', {}) == "el"

        # Note: test_upstream_improvements.py::TestStringUtilities::test_substring_not_implemented
        # also monitors this behavior.

    def test_our_wrapper_still_needed(self):
        """
        Verify our global wrapper is still providing value if method support
        does not yet cover the standalone function form.

        This test confirms that:
        1. The global substring() helper is not exposed by default
        2. Our wrapper successfully provides it
        """
        # Without wrapper - should fail
        with pytest.raises(RuntimeError):
            evaluate('substring("test", 0, 2)', {})

        # With our wrapper - should succeed
        context = cel.Context()
        add_stdlib_to_context(context)
        result = evaluate('substring("test", 0, 2)', context)
        assert result == "te"
