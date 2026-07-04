"""Documents the behaviour of cel-rust 0.14 that this release depends on.

These tests pin down the semantics that changed (or are easy to get wrong)
between cel-rust 0.13 and 0.14 so regressions are caught early:

* ``contains`` is a string-only built-in; list/map membership uses ``in``.
* ``min``/``max`` are not part of the core stdlib (moved to ``cel.stdlib``).
* Built-in functions take precedence over same-named user functions.
* Integer overflow raises rather than wrapping.
* Bytes concatenation works.
* Logical operators are error-resilient per the CEL spec.
"""

import cel
import pytest


class TestContainsIsStringOnly:
    def test_string_contains_builtin(self):
        assert cel.evaluate('"hello".contains("ell")') is True
        assert cel.evaluate('"hello".contains("xyz")') is False

    def test_list_contains_not_builtin(self):
        # cel-rust 0.14 dropped the list/map contains overloads.
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("[1, 2, 3].contains(2)")

    def test_list_membership_uses_in(self):
        assert cel.evaluate("2 in [1, 2, 3]") is True
        assert cel.evaluate("9 in [1, 2, 3]") is False

    def test_map_membership_uses_in(self):
        assert cel.evaluate('"a" in {"a": 1, "b": 2}') is True
        assert cel.evaluate('"z" in {"a": 1}') is False


class TestMinMaxRemoved:
    def test_min_not_in_core(self):
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("min([1, 2, 3])")

    def test_max_not_in_core(self):
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("max([1, 2, 3])")


class TestBuiltinsShadowUserFunctions:
    def test_builtin_double_wins_over_user_function(self):
        # `double` is a built-in conversion; a user function of the same name
        # does not override it. This is intentional CEL behaviour.
        context = cel.Context()
        context.add_function("double", lambda x: x * 999)
        assert cel.evaluate("double(21)", context) == 21.0

    def test_user_function_with_unique_name_is_used(self):
        context = cel.Context()
        context.add_function("my_double", lambda x: x * 2)
        assert cel.evaluate("my_double(21)", context) == 42


class TestOverflow:
    def test_int_addition_overflow_raises(self):
        with pytest.raises(OverflowError):
            cel.evaluate("9223372036854775807 + 1")

    def test_int_multiplication_overflow_raises(self):
        with pytest.raises(OverflowError):
            cel.evaluate("9223372036854775807 * 2")


class TestBytesConcatenation:
    def test_bytes_concat_works(self):
        assert cel.evaluate("b'hello' + b'world'") == b"helloworld"


class TestLogicalOperatorsAreErrorResilient:
    def test_and_short_circuits_to_false(self):
        # `X && false` is false even when X errors, per the CEL spec.
        assert cel.evaluate("(1 / 0 == 0) && false") is False

    def test_or_short_circuits_to_true(self):
        assert cel.evaluate("(1 / 0 == 0) || true") is True


class TestArithmeticIsStrict:
    def test_no_int_double_coercion(self):
        with pytest.raises(TypeError):
            cel.evaluate("1 + 2.5")

    def test_no_signed_unsigned_mix(self):
        with pytest.raises(TypeError):
            cel.evaluate("1 + 2u")

    def test_explicit_conversion_works(self):
        assert cel.evaluate("double(1) + 2.5") == 3.5
        assert cel.evaluate("1 + int(2u)") == 3
