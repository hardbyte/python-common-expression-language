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
    """Test logical operator behavior to verify CEL specification compliance."""

    def test_or_operator_cel_compliant_behavior(self):
        """
        Test OR operator behavior follows CEL specification requirements.

        Per CEL specification, logical operators require boolean first operands.
        Mixed-type operations like "42 || false" should fail with "No such overload".

        Reference: https://github.com/tektoncd/triggers/issues/644
        """
        # These correctly fail - first operand must be boolean per CEL spec
        with pytest.raises(ValueError, match="No such overload"):
            cel.evaluate("42 || false")  # Non-boolean first operand fails

        with pytest.raises(ValueError, match="No such overload"):
            cel.evaluate('0 || "default"')  # Non-boolean first operand fails

        # CEL's logical operators with boolean first operand work correctly
        assert cel.evaluate("true || 99")  # Short-circuits to True
        assert cel.evaluate("false || 99") == 99  # Returns second operand per CEL spec
        assert cel.evaluate("false || 'default'") == "default"  # Any type for second operand

        # AND operator has stricter requirements for both operands
        assert not cel.evaluate("false && 99")  # Short-circuits to False
        with pytest.raises(ValueError, match="No such overload"):
            cel.evaluate("true && 99")  # AND requires both operands to be boolean when evaluated

    def test_or_operator_correct_boolean_behavior(self):
        """
        Test OR operator with boolean operands follows CEL specification.
        """
        # Boolean logical operations work as expected
        assert cel.evaluate("true || false")
        assert cel.evaluate("false || true")
        assert not cel.evaluate("false || false")
        assert cel.evaluate("true || true")

    def test_and_operator_correct_boolean_behavior(self):
        """
        Test AND operator with boolean operands follows CEL specification.
        """
        # Boolean logical operations work as expected
        assert not cel.evaluate("true && false")
        assert not cel.evaluate("false && true")
        assert not cel.evaluate("false && false")
        assert cel.evaluate("true && true")

    def test_ternary_operator_requires_boolean_condition(self):
        """
        Test ternary operator requires boolean condition per CEL specification.
        """
        # Boolean condition works correctly
        assert cel.evaluate("true ? 42 : 0") == 42
        assert cel.evaluate("false ? 42 : 0") == 0

        # Non-boolean condition fails as expected
        with pytest.raises(ValueError, match="No such overload"):
            cel.evaluate("42 ? true : false")


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


class TestMissingAggregationFunctions:
    """Test aggregation functions that are missing from CEL."""

    def test_sum_function_not_available(self):
        """
        Test that sum() function is not currently available.

        When this test starts failing, sum() has been implemented upstream.
        """
        with pytest.raises(RuntimeError, match="Undefined variable or function.*sum"):
            cel.evaluate("sum([1, 2, 3, 4, 5])")

    def test_fold_function_not_available(self):
        """
        Test that fold() is not available - various syntax attempts.

        When this test starts failing, fold() has been implemented upstream.
        """
        # Method syntax
        with pytest.raises((RuntimeError, ValueError)):
            cel.evaluate("[1, 2, 3, 4, 5].fold(0, (acc, x) -> acc + x)")

        # Global function syntax
        with pytest.raises(RuntimeError, match="Undefined variable or function.*fold"):
            cel.evaluate("fold([1, 2, 3], 0, sum + x)")

    def test_reduce_function_not_available(self):
        """
        Test that reduce() is not available - various syntax attempts.

        When this test starts failing, reduce() has been implemented upstream.
        """
        # Global function syntax
        with pytest.raises(RuntimeError, match="Undefined variable or function.*reduce"):
            cel.evaluate("reduce([1, 2, 3, 4, 5], 0, sum + x)")

        # Method syntax
        with pytest.raises((RuntimeError, ValueError)):
            cel.evaluate("[1, 2, 3].reduce(0, (acc, x) -> acc + x)")

    @pytest.mark.xfail(reason="Aggregation functions not implemented in cel v0.11.1", strict=False)
    def test_aggregation_functions_expected_behavior(self):
        """
        Test expected aggregation function behavior when implemented.

        This test will pass when upstream implements sum(), fold(), reduce().
        """
        # Sum function
        assert cel.evaluate("sum([1, 2, 3, 4, 5])") == 15
        assert cel.evaluate("sum([1.1, 2.2, 3.3])") == pytest.approx(6.6)

        # Fold/reduce functions (syntax may differ when actually implemented)
        assert cel.evaluate("[1, 2, 3, 4].fold(0, (acc, x) -> acc + x)") == 10
        assert cel.evaluate("[1, 2, 3].fold(1, (acc, x) -> acc * x)") == 6


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
        "Missing aggregation functions": ["sum()", "fold()", "reduce()"],
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
        "Logical operators": ["CEL-compliant behavior verified in v0.11.1"],
        "Math functions": ["ceil()", "floor()", "round()"],
        "Validation functions": ["isURL()", "isIP()"],
    }

    # This test documents our monitoring approach
    assert len(improvements_to_watch) > 0
    print(f"Monitoring {len(improvements_to_watch)} categories of upstream improvements")
