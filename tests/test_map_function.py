"""Test the map() function with its documented PARTIAL support and limitations."""

import pytest
from cel import evaluate


class TestMapFunctionSupport:
    """Test map() function capabilities and documented limitations."""

    def test_working_map_operations(self):
        """Test map() operations that should work correctly."""

        # String operations
        result = evaluate('["hello", "world"].map(s, s + "!")')
        assert result == ["hello!", "world!"]

        result = evaluate('["hello", "world"].map(s, s.size())')
        assert result == [5, 5]

        # Boolean operations
        result = evaluate("[true, false, true].map(b, !b)")
        assert result == [False, True, False]

        # Float operations (same type)
        result = evaluate("[1.0, 2.0, 3.0].map(x, x * 2.0)")
        assert result == [2.0, 4.0, 6.0]

    def test_map_with_context_variables(self):
        """Test map() operations with context variables."""

        # Simple context mapping
        context = {"numbers": [1, 2, 3], "multiplier": 2}
        result = evaluate("numbers.map(x, x * multiplier)", context)
        assert result == [2, 4, 6]

        # Object field mapping
        context = {"users": [{"name": "Alice"}, {"name": "Bob"}]}
        result = evaluate("users.map(u, u.name)", context)
        assert result == ["Alice", "Bob"]

        # Complex object operations
        context = {"items": [{"price": 10.0}, {"price": 20.0}]}
        result = evaluate("items.map(i, i.price * 1.1)", context)
        assert result == [11.0, 22.0]

    def test_documented_map_limitations(self):
        """Test documented limitations of map() function (PARTIAL support)."""

        # This is the documented issue: mixed int/float arithmetic in map()
        # See docs/reference/cel-compliance.md for details
        with pytest.raises(TypeError, match="Unsupported.*operation.*Int.*Float"):
            evaluate("[1, 2, 3].map(x, x * 2.0)")

        # Complex mixed arithmetic should also fail
        with pytest.raises(TypeError, match="Unsupported.*operation.*Int.*Float"):
            evaluate("[1, 2, 3].map(x, x * 2 + 1.5)")

        # Integer + float literal fails due to type mismatch
        with pytest.raises(TypeError, match="Unsupported.*operation.*Int.*Float"):
            evaluate("[1, 2, 3].map(x, x + 1.0)")

    def test_map_function_workarounds(self):
        """Test workarounds for map() limitations."""

        # Workaround: Use addition instead of multiplication to avoid auto-promotion
        result = evaluate("[1, 2, 3].map(x, x + x)")  # All integers
        assert result == [2, 4, 6]

        result = evaluate("[1.0, 2.0, 3.0].map(x, x * 2.5)")  # All floats
        assert result == [2.5, 5.0, 7.5]

        # Note: The auto-promotion feature works for top-level expressions
        # but not within map() operations - this is the documented limitation

    def test_map_edge_cases(self):
        """Test edge cases for map() function."""

        # Empty list
        result = evaluate("[].map(x, x + x)")
        assert result == []

        # Single element (using addition to avoid auto-promotion issues)
        result = evaluate("[42].map(x, x + x)")
        assert result == [84]

        # Nested operations
        result = evaluate("[[1, 2], [3, 4]].map(arr, arr.size())")
        assert result == [2, 2]

    def test_map_function_documentation_examples(self):
        """Test examples from the documentation to ensure they behave as documented."""

        # Example from cel-language-basics.md that may have type restrictions
        # This should fail according to documentation
        with pytest.raises(TypeError):
            evaluate("[1, 2, 3].map(x, x * 2.0)")  # Mixed int/float

        # Examples that should work
        context = {"users": [{"active": True, "name": "Alice"}, {"active": False, "name": "Bob"}]}
        result = evaluate("users.filter(u, u.active).map(u, u.name)", context)
        assert result == ["Alice"]
