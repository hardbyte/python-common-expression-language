"""Documents the behaviour of cel-rust 0.14 that this release depends on.

These tests pin down the semantics that changed (or are easy to get wrong)
between cel-rust 0.13 and 0.14 so regressions are caught early:

* ``contains`` is a string-only built-in; list/map membership uses ``in``.
* ``min``/``max`` are not part of the core stdlib (moved to ``cel.stdlib``).
* Built-in functions take precedence over same-named user functions.
* Integer overflow raises rather than wrapping.
* Bytes concatenation works.
* Logical operators are error-resilient per the CEL spec.
* Since 0.14.4/0.14.5: CEL reserved words are rejected as identifiers,
  ``type()`` is a native function returning a first-class type value,
  ``int()``/``uint()`` reject out-of-range conversions, negative hex literals
  parse, and optional values compare by content.
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


class TestReservedIdentifiersRejected:
    """cel 0.14.4 rejects the CEL spec's reserved words as identifiers.

    This is a parse error, so it surfaces as ``ValueError`` even when the
    context defines a variable of that name.
    """

    @pytest.mark.parametrize(
        "word",
        [
            "as",
            "break",
            "const",
            "continue",
            "else",
            "for",
            "function",
            "if",
            "import",
            "let",
            "loop",
            "package",
            "namespace",
            "return",
            "var",
            "void",
            "while",
        ],
    )
    def test_reserved_word_as_variable(self, word):
        with pytest.raises(ValueError, match="reserved identifier"):
            cel.evaluate(f'{word} == "x"', {word: "x"})

    def test_reserved_word_as_function(self):
        with pytest.raises(ValueError, match="reserved identifier"):
            cel.evaluate("namespace(1)")

    def test_reserved_word_allowed_inside_identifier(self):
        assert cel.evaluate("var_2 + 1", {"var_2": 1}) == 2
        assert cel.evaluate('{"var": 1}["var"]') == 1


class TestNativeTypeFunction:
    def test_type_names(self):
        assert cel.evaluate("type(1)") == "int"
        assert cel.evaluate("type(1u)") == "uint"
        assert cel.evaluate("type(1.5)") == "double"
        assert cel.evaluate('type("x")') == "string"
        assert cel.evaluate("type(b'x')") == "bytes"
        assert cel.evaluate("type(true)") == "bool"
        assert cel.evaluate("type(null)") == "null_type"
        assert cel.evaluate("type([1])") == "list"
        assert cel.evaluate("type({'a': 1})") == "map"
        assert cel.evaluate("type(type(1))") == "type"
        assert cel.evaluate("type(optional.of(1))") == "optional_type"

    def test_type_of_time_values_uses_protobuf_names(self):
        # cel-spec names these after their well-known protobuf types.
        assert cel.evaluate('type(duration("1s"))') == "google.protobuf.Duration"
        assert (
            cel.evaluate('type(timestamp("2020-01-01T00:00:00Z"))') == "google.protobuf.Timestamp"
        )

    def test_type_values_compare_with_type_identifiers(self):
        assert cel.evaluate("type(1) == int") is True
        assert cel.evaluate("type(1u) == uint") is True
        assert cel.evaluate("type(1) == uint") is False
        assert cel.evaluate("type(null) == null_type") is True
        assert cel.evaluate("type(1) in [int, uint]") is True

    def test_type_values_compare_with_each_other(self):
        assert cel.evaluate("type(1) == type(2)") is True
        assert cel.evaluate('type(1) == type("x")') is False

    def test_type_value_is_not_a_string_inside_cel(self):
        # Only the Python conversion turns the type value into its name.
        assert cel.evaluate('type(1) == "int"') is False

    def test_type_values_in_containers(self):
        assert cel.evaluate("[type(1), type(2u)]") == ["int", "uint"]
        assert cel.evaluate("{'k': type(1.0)}") == {"k": "double"}


class TestConversionRangeChecks:
    """cel 0.14.5 rejects int()/uint() conversions that do not fit the target."""

    def test_int_of_large_uint_overflows(self):
        with pytest.raises(OverflowError, match="integer overflow"):
            cel.evaluate("int(9223372036854775808u)")

    def test_int_of_max_fitting_uint(self):
        assert cel.evaluate("int(9223372036854775807u)") == 9223372036854775807

    def test_int_of_huge_double_overflows(self):
        with pytest.raises(OverflowError):
            cel.evaluate("int(1e300)")

    def test_int_of_nan_and_infinity_overflow(self):
        with pytest.raises(OverflowError):
            cel.evaluate('int(double("NaN"))')
        with pytest.raises(OverflowError):
            cel.evaluate('int(double("infinity"))')

    def test_uint_of_negative_overflows(self):
        with pytest.raises(OverflowError, match="unsigned integer overflow"):
            cel.evaluate("uint(-1)")

    def test_user_function_overflow_message_stays_runtime_error(self):
        # Only the native conversions map to OverflowError; a Python callback whose
        # error text ends in "overflow" is an ordinary function failure.
        context = cel.Context()

        def boom(_value):
            raise RuntimeError("buffer overflow")

        context.add_function("boom", boom)
        with pytest.raises(RuntimeError, match="buffer overflow"):
            cel.evaluate("boom(1)", context)

    def test_in_range_conversions_still_work(self):
        assert cel.evaluate("int(1.9)") == 1
        assert cel.evaluate("uint(3)") == 3
        assert cel.evaluate('int("-42")') == -42


class TestParserFixes:
    def test_negative_hex_literal(self):
        assert cel.evaluate("-0x10") == -16
        assert cel.evaluate("0x10") == 16

    def test_stacked_unary_operators_cancel(self):
        assert cel.evaluate("--1") == 1
        assert cel.evaluate("!!true") is True

    def test_bytes_literal_rejects_unicode_escape(self):
        # Per cel-spec, \u escapes are only valid in string literals.
        with pytest.raises(ValueError, match="invalid bytes literal"):
            cel.evaluate("b'\\u00e9'")
        assert cel.evaluate("b'\\303\\251'") == "é".encode()


class TestOptionalEquality:
    def test_optional_values_compare_by_content(self):
        assert cel.evaluate("optional.of(1) == optional.of(1)") is True
        assert cel.evaluate("optional.of(1) == optional.of(2)") is False
        assert cel.evaluate("optional.none() == optional.none()") is True
        assert cel.evaluate("optional.of(1) == optional.none()") is False
