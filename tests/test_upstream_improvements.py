"""
Test upstream improvements detection.

This test file contains expected failures that should become passing tests
when upstream cel-rust fixes become available. These tests help us detect
when workarounds can be removed and features can be enabled.
"""

import cel
import pytest


class TestStringUtilities:
    """Test missing string utility functions that should eventually be implemented."""

    def test_lower_ascii_not_implemented(self):
        """
        Test that lowerAscii() is not implemented.

        When this test starts failing (raises different error), it means
        lowerAscii() has been implemented upstream.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*lowerAscii"):
            cel.evaluate('"HELLO".lowerAscii()')

    def test_upper_ascii_not_implemented(self):
        """
        Test that upperAscii() is not implemented.

        When this test starts failing, upperAscii() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*upperAscii"):
            cel.evaluate('"hello".upperAscii()')

    def test_index_of_not_implemented(self):
        """
        Test that indexOf() is not implemented.

        When this test starts failing, indexOf() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*indexOf"):
            cel.evaluate('"hello world".indexOf("world")')

    def test_substring_not_implemented(self):
        """
        Test that substring() is not implemented.

        When this test starts failing, substring() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*substring"):
            cel.evaluate('"hello".substring(1, 3)')


class TestTypeIntrospection:
    """Test missing type introspection that should eventually be implemented."""

    def test_type_function_not_implemented(self):
        """
        Test that type() function is not implemented.

        When this test starts failing, the type() function has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*type"):
            cel.evaluate("type(42)")

    @pytest.mark.xfail(
        reason="type() function not implemented in cel v0.11.0 - should become available when type infrastructure is complete",
        strict=False,
    )
    def test_type_function_expected_behavior(self):
        """
        Test expected behavior of type() function when implemented.

        This test is marked as expected failure and will start passing
        when type() is implemented upstream.
        """
        assert cel.evaluate("type(42)") == "int"
        assert cel.evaluate('type("hello")') == "string"
        assert cel.evaluate("type(true)") == "bool"
        assert cel.evaluate("type([1, 2, 3])") == "list"
        assert cel.evaluate('type({"key": "value"})') == "map"


class TestMixedArithmetic:
    """Test mixed signed/unsigned arithmetic that currently fails."""

    def test_mixed_int_uint_addition_fails(self):
        """
        Test that mixed int/uint addition currently fails.

        When this test starts failing, mixed arithmetic has been fixed.
        """
        with pytest.raises(TypeError, match="Cannot mix signed and unsigned integers"):
            cel.evaluate("1 + 2u")

    def test_mixed_int_uint_multiplication_fails(self):
        """
        Test that mixed int/uint multiplication currently fails.

        When this test starts failing, mixed arithmetic has been fixed.
        """
        with pytest.raises(TypeError, match="Unsupported.*operation"):
            cel.evaluate("3 * 2u")

    @pytest.mark.xfail(
        reason="Mixed signed/unsigned arithmetic not supported in cel v0.11.0", strict=False
    )
    def test_mixed_arithmetic_expected_behavior(self):
        """
        Test expected behavior when mixed arithmetic is fixed.

        This test will pass when upstream supports mixed int/uint operations.
        """
        assert cel.evaluate("1 + 2u") == 3
        assert cel.evaluate("3 * 2u") == 6
        assert cel.evaluate("10u - 3") == 7


class TestOptionalValues:
    """Test optional value functionality that may be implemented in future."""

    def test_optional_of_not_implemented(self):
        """
        Test that optional.of() is not implemented.

        When this test starts failing, optional values have been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*of"):
            cel.evaluate("optional.of(42)")

    def test_optional_chaining_not_implemented(self):
        """
        Test that optional chaining (?.) is not implemented.

        When this test starts failing, optional chaining has been implemented.
        """
        # This currently likely fails with parse error, but when optional chaining
        # is implemented, it should work
        with pytest.raises((ValueError, RuntimeError)):
            cel.evaluate("user?.profile?.name", {"user": {"profile": {"name": "Alice"}}})

    @pytest.mark.xfail(reason="Optional values not implemented in cel v0.11.0", strict=False)
    def test_optional_expected_behavior(self):
        """
        Test expected optional value behavior when implemented.

        This test will pass when upstream implements optional values.
        """
        # These are expectations based on CEL spec
        assert cel.evaluate("optional.of(42).orValue(0)") == 42
        assert cel.evaluate('optional.of(null).orValue("default")') == "default"


class TestMapFunctionImprovements:
    """Test map() function improvements for mixed type handling."""

    def test_map_mixed_arithmetic_currently_fails(self):
        """
        Test that map() with mixed arithmetic currently fails.

        When this test starts failing, map() type coercion has been improved.
        """
        with pytest.raises(TypeError, match="Unsupported.*operation.*Int.*Float"):
            cel.evaluate("[1, 2, 3].map(x, x * 2.0)")

    @pytest.mark.xfail(
        reason="map() function mixed arithmetic not supported in cel v0.11.0", strict=False
    )
    def test_map_mixed_arithmetic_expected_behavior(self):
        """
        Test expected map() behavior with mixed arithmetic when fixed.

        This test will pass when upstream improves type coercion in map().
        """
        assert cel.evaluate("[1, 2, 3].map(x, x * 2.0)") == [2.0, 4.0, 6.0]
        assert cel.evaluate("[1, 2, 3].map(x, x + 1.5)") == [2.5, 3.5, 4.5]


class TestLogicalOperatorBehavior:
    """Test logical operator behavioral differences that should be fixed."""

    def test_or_operator_returns_original_values(self):
        """
        CRITICAL: Test that OR operator currently returns original values, not booleans.

        When this test starts failing, the OR operator behavior has been fixed
        to match CEL specification (should return boolean values).
        """
        # CEL spec: should return boolean true, but we return original value
        result = cel.evaluate("42 || false")
        assert result == 42, f"Expected 42 (current behavior), got {result}"

        result = cel.evaluate('0 || "default"')
        assert result == "default", f"Expected 'default' (current behavior), got {result}"

        # This documents the current non-spec behavior
        result = cel.evaluate("true || 99")
        assert result, f"Expected True, got {result}"  # Short-circuit works

    @pytest.mark.xfail(
        reason="OR operator returns original values instead of booleans in cel v0.11.0",
        strict=False,
    )
    def test_or_operator_expected_cel_spec_behavior(self):
        """
        Test expected OR operator behavior per CEL specification.

        This test will pass when upstream fixes OR operator to return booleans.
        """
        # CEL spec: logical OR should always return boolean values
        assert cel.evaluate("42 || false")
        assert cel.evaluate('0 || "default"')
        assert not cel.evaluate("false || 0")
        assert not cel.evaluate("null || false")


class TestMissingStringFunctions:
    """Test additional missing string functions beyond the core set."""

    def test_last_index_of_not_implemented(self):
        """
        Test that lastIndexOf() is not implemented.

        When this test starts failing, lastIndexOf() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*lastIndexOf"):
            cel.evaluate('"hello world hello".lastIndexOf("hello")')

    def test_replace_not_implemented(self):
        """
        Test that replace() is not implemented.

        When this test starts failing, replace() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*replace"):
            cel.evaluate('"hello world".replace("world", "universe")')

    def test_split_not_implemented(self):
        """
        Test that split() is not implemented.

        When this test starts failing, split() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*split"):
            cel.evaluate('"hello,world,test".split(",")')

    def test_join_not_implemented(self):
        """
        Test that join() is not implemented.

        When this test starts failing, join() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*join"):
            cel.evaluate('["hello", "world"].join(",")')


class TestMathFunctions:
    """Test missing mathematical functions."""

    def test_ceil_not_implemented(self):
        """
        Test that ceil() is not implemented.

        When this test starts failing, ceil() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*ceil"):
            cel.evaluate("ceil(3.14)")

    def test_floor_not_implemented(self):
        """
        Test that floor() is not implemented.

        When this test starts failing, floor() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*floor"):
            cel.evaluate("floor(3.14)")

    def test_round_not_implemented(self):
        """
        Test that round() is not implemented.

        When this test starts failing, round() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*round"):
            cel.evaluate("round(3.14)")


class TestValidationFunctions:
    """Test validation functions that may be part of CEL extensions."""

    def test_is_url_not_implemented(self):
        """
        Test that isURL() is not implemented.

        When this test starts failing, isURL() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*isURL"):
            cel.evaluate('isURL("https://example.com")')

    def test_is_ip_not_implemented(self):
        """
        Test that isIP() is not implemented.

        When this test starts failing, isIP() has been implemented.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*isIP"):
            cel.evaluate('isIP("192.168.1.1")')


# Expected improvements detection helpers
def test_upstream_improvements_summary():
    """
    Summary test that documents what we're watching for.

    This test always passes but serves as documentation of what
    upstream improvements we're monitoring.
    """
    improvements_to_watch = {
        "String functions": [
            "lowerAscii",
            "upperAscii",
            "indexOf",
            "substring",
            "lastIndexOf",
            "replace",
            "split",
            "join",
        ],
        "Type introspection": ["type() function"],
        "Mixed arithmetic": ["int + uint", "int * uint operations"],
        "Optional values": ["optional.of()", "optional chaining (?.)"],
        "Map improvements": ["Mixed type arithmetic in map()"],
        "Bytes operations": ["bytes concatenation with +"],
        "Logical operators": ["OR operator CEL spec compliance (return booleans)"],
        "Math functions": ["ceil()", "floor()", "round()"],
        "Validation functions": ["isURL()", "isIP()"],
    }

    # This test documents our monitoring approach
    assert len(improvements_to_watch) > 0
    print(f"Monitoring {len(improvements_to_watch)} categories of upstream improvements")
