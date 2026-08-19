"""Tests for the extended standard library (cel.stdlib)."""

from datetime import timedelta

import cel
import pytest
from cel.stdlib import EXTENSIONS, STDLIB_FUNCTIONS, add_stdlib_to_context


@pytest.fixture
def ctx():
    """A context with every extended-stdlib function registered."""
    context = cel.Context()
    add_stdlib_to_context(context)
    return context


def ev(expr, ctx):
    return cel.evaluate(expr, ctx)


class TestRegistry:
    def test_all_functions_merged(self):
        total = sum(len(lib) for lib in EXTENSIONS.values())
        # "reverse" appears in both strings and lists; the merged map dedupes.
        assert len(STDLIB_FUNCTIONS) == len({n for lib in EXTENSIONS.values() for n in lib})
        assert total >= len(STDLIB_FUNCTIONS)

    def test_selective_extension_loading(self):
        context = cel.Context()
        add_stdlib_to_context(context, extensions=["math"])
        assert cel.evaluate("math.abs(-3)", context) == 3
        with pytest.raises(RuntimeError):
            cel.evaluate('"a".charAt(0)', context)

    def test_unknown_extension_raises(self):
        with pytest.raises(KeyError):
            add_stdlib_to_context(cel.Context(), extensions=["does-not-exist"])


class TestCore:
    def test_bool_from_strings(self, ctx):
        assert ev('bool("true")', ctx) is True
        assert ev('bool("false")', ctx) is False
        assert ev('bool("1")', ctx) is True
        assert ev('bool("0")', ctx) is False
        assert ev("bool(true)", ctx) is True

    def test_bool_invalid_raises(self, ctx):
        with pytest.raises((ValueError, RuntimeError)):
            ev('bool("maybe")', ctx)

    def test_dyn_identity(self, ctx):
        assert ev("dyn(5)", ctx) == 5
        assert ev('dyn("hi")', ctx) == "hi"

    def test_type_names(self, ctx):
        assert ev("type(1)", ctx) == "int"
        assert ev("type(1.5)", ctx) == "double"
        assert ev('type("x")', ctx) == "string"
        assert ev("type(true)", ctx) == "bool"
        assert ev("type([1])", ctx) == "list"
        assert ev("type({'a': 1})", ctx) == "map"

    def test_type_equality(self, ctx):
        assert ev("type(1) == type(2)", ctx) is True
        assert ev("type(1) == type('x')", ctx) is False

    def test_min_max(self, ctx):
        assert ev("min([3, 1, 2])", ctx) == 1
        assert ev("max([3, 1, 2])", ctx) == 3
        assert ev("min(3, 1, 2)", ctx) == 1
        assert ev("max(3, 1, 2)", ctx) == 3

    def test_min_max_on_comparable_non_numbers(self, ctx):
        assert ev('min(["b", "a", "c"])', ctx) == "a"
        assert ev('max(["b", "a", "c"])', ctx) == "c"

    def test_sum_list_and_varargs(self, ctx):
        assert ev("sum([1, 2, 3])", ctx) == 6
        assert ev("sum(1, 2, 3)", ctx) == 6
        assert ev("[1, 2, 3].sum()", ctx) == 6

    def test_sum_promotes_to_double(self, ctx):
        assert ev("sum([1, 2.5])", ctx) == 3.5
        assert ev("[1.5, 2.5].sum()", ctx) == 4.0

    def test_sum_of_empty_list_is_zero(self, ctx):
        assert ev("sum([])", ctx) == 0

    def test_sum_of_durations(self, ctx):
        assert ev('sum([duration("1h"), duration("30m")]) == duration("90m")', ctx) is True

    def test_sum_composes_with_map(self, ctx):
        ctx.update({"items": [{"weight": 0.5}, {"weight": 0.25}, {"weight": 0.25}]})
        assert ev("items.map(i, i.weight).sum() == 1.0", ctx) is True

    def test_sum_of_uints_returns_int(self, ctx):
        # Python has one integer type, so unsignedness cannot survive the callback
        # boundary; the sum is correct but comes back as an int, which means uint
        # arithmetic on the result has no overload. Documented in cel.stdlib.
        assert ev("sum([1u, 2u])", ctx) == 3
        with pytest.raises(TypeError, match="No such overload"):
            ev("sum([1u, 2u]) + 1u", ctx)

    def test_sum_of_durations_is_microsecond_resolution(self, ctx):
        # datetime.timedelta cannot hold nanoseconds, and the conversion happens
        # before sum() runs: plain evaluate() truncates duration("1ns") too.
        assert ev('duration("1ns")', ctx) == timedelta(0)
        assert ev('sum([duration("1ns"), duration("1ns")]) == duration("2ns")', ctx) is False
        assert ev('sum([duration("1500ns")])', ctx) == timedelta(microseconds=1)

    def test_sum_rejects_bools(self, ctx):
        # Python would count True/False as 1/0; CEL has no bool arithmetic.
        with pytest.raises(RuntimeError, match="bool"):
            ev("sum([true, false])", ctx)

    def test_sum_rejects_non_numbers(self, ctx):
        with pytest.raises(RuntimeError, match="numbers or all durations"):
            ev('sum(["a", "b"])', ctx)

    def test_sum_rejects_mixed_numbers_and_durations(self, ctx):
        with pytest.raises(RuntimeError, match="numbers or all durations"):
            ev('sum([1, duration("1h")])', ctx)


class TestStrings:
    def test_char_at(self, ctx):
        assert ev('"hello".charAt(1)', ctx) == "e"
        assert ev('"hello".charAt(5)', ctx) == ""  # index == len -> ""

    def test_index_of(self, ctx):
        assert ev('"hello".indexOf("l")', ctx) == 2
        assert ev('"hello".indexOf("l", 3)', ctx) == 3
        assert ev('"hello".indexOf("z")', ctx) == -1

    def test_last_index_of(self, ctx):
        assert ev('"hello".lastIndexOf("l")', ctx) == 3
        assert ev('"hello".lastIndexOf("z")', ctx) == -1

    def test_substring(self, ctx):
        assert ev('"hello".substring(1, 3)', ctx) == "el"
        assert ev('"hello".substring(2)', ctx) == "llo"

    def test_replace(self, ctx):
        assert ev('"a-a-a".replace("a", "b")', ctx) == "b-b-b"
        assert ev('"a-a-a".replace("a", "b", 1)', ctx) == "b-a-a"

    def test_split(self, ctx):
        assert ev('"a,b,c".split(",")', ctx) == ["a", "b", "c"]
        assert ev('"a,b,c".split(",", 2)', ctx) == ["a", "b,c"]

    def test_join(self, ctx):
        assert ev('["a", "b", "c"].join("-")', ctx) == "a-b-c"
        assert ev('["a", "b"].join()', ctx) == "ab"

    def test_case(self, ctx):
        assert ev('"Hello World".lowerAscii()', ctx) == "hello world"
        assert ev('"Hello World".upperAscii()', ctx) == "HELLO WORLD"

    def test_trim(self, ctx):
        assert ev('"  padded  ".trim()', ctx) == "padded"

    def test_reverse_string(self, ctx):
        assert ev('"abc".reverse()', ctx) == "cba"

    def test_quote(self, ctx):
        assert ev('strings.quote("a\\"b")', ctx) == '"a\\"b"'

    def test_global_call_form(self, ctx):
        # Every string function also works called as a free function.
        assert ev('charAt("hello", 0)', ctx) == "h"
        assert ev('substring("hello", 1, 3)', ctx) == "el"

    def test_split_empty_separator_splits_chars(self, ctx):
        # cel-go splits into characters; Python's str.split("") would raise.
        assert ev('"abc".split("")', ctx) == ["a", "b", "c"]

    def test_substring_out_of_range_raises(self, ctx):
        for expr in (
            '"hello".substring(-1)',
            '"hello".substring(3, 1)',
            '"hello".substring(0, 99)',
        ):
            with pytest.raises((IndexError, RuntimeError)):
                ev(expr, ctx)

    def test_index_of_offset_out_of_range_raises(self, ctx):
        with pytest.raises((IndexError, RuntimeError)):
            ev('"hello".indexOf("l", -1)', ctx)
        with pytest.raises((IndexError, RuntimeError)):
            ev('"hello".lastIndexOf("l", 99)', ctx)


class TestMath:
    def test_greatest_least(self, ctx):
        assert ev("math.greatest(1, 5, 3)", ctx) == 5
        assert ev("math.least([4, 2, 8])", ctx) == 2

    def test_abs_sign(self, ctx):
        assert ev("math.abs(-7)", ctx) == 7
        assert ev("math.abs(-2.5)", ctx) == 2.5
        assert ev("math.sign(-3)", ctx) == -1
        assert ev("math.sign(3)", ctx) == 1
        assert ev("math.sign(0)", ctx) == 0

    def test_rounding(self, ctx):
        assert ev("math.ceil(1.2)", ctx) == 2.0
        assert ev("math.floor(1.8)", ctx) == 1.0
        assert ev("math.trunc(2.9)", ctx) == 2.0
        # round() is half-away-from-zero, not banker's rounding.
        assert ev("math.round(2.5)", ctx) == 3.0
        assert ev("math.round(-2.5)", ctx) == -3.0
        assert ev("math.round(2.4)", ctx) == 2.0

    def test_predicates(self, ctx):
        assert ev("math.isNaN(0.0 / 0.0)", ctx) is True
        assert ev("math.isInf(1.0 / 0.0)", ctx) is True
        assert ev("math.isFinite(1.0)", ctx) is True
        assert ev("math.isFinite(1.0 / 0.0)", ctx) is False

    def test_rounding_infinity_and_nan_pass_through(self, ctx):
        # ceil/floor/round/trunc return inf/nan rather than raising.
        assert ev("math.isInf(math.ceil(1.0 / 0.0))", ctx) is True
        assert ev("math.isInf(math.floor(1.0 / 0.0))", ctx) is True
        assert ev("math.isInf(math.round(1.0 / 0.0))", ctx) is True
        assert ev("math.isNaN(math.trunc(0.0 / 0.0))", ctx) is True

    def test_round_boundary(self, ctx):
        # The largest double below 0.5 must round to 0, not 1.
        assert ev("math.round(0.49999999999999994)", ctx) == 0.0

    def test_sqrt(self, ctx):
        assert ev("math.sqrt(16.0)", ctx) == 4.0

    def test_sqrt_negative_is_nan(self, ctx):
        assert ev("math.isNaN(math.sqrt(-1.0))", ctx) is True

    def test_bit_ops(self, ctx):
        assert ev("math.bitOr(5, 2)", ctx) == 7
        assert ev("math.bitAnd(6, 3)", ctx) == 2
        assert ev("math.bitXor(5, 3)", ctx) == 6
        assert ev("math.bitNot(0)", ctx) == -1
        assert ev("math.bitShiftLeft(1, 4)", ctx) == 16
        assert ev("math.bitShiftRight(16, 2)", ctx) == 4

    def test_bit_shift_wraps_to_int64(self, ctx):
        # Results stay 64-bit integers (two's complement) rather than being
        # silently coerced to a float on overflow.
        assert ev("math.bitShiftLeft(1, 63)", ctx) == -9223372036854775808
        assert ev("math.bitShiftLeft(1, 64)", ctx) == 0
        # Right shift is logical (zero-fill).
        assert ev("math.bitShiftRight(-1, 1)", ctx) == 9223372036854775807


class TestSets:
    def test_contains(self, ctx):
        assert ev("sets.contains([1, 2, 3], [1, 2])", ctx) is True
        assert ev("sets.contains([1, 2, 3], [1, 4])", ctx) is False
        assert ev("sets.contains([1, 2, 3], [])", ctx) is True

    def test_equivalent(self, ctx):
        assert ev("sets.equivalent([1, 2], [2, 1])", ctx) is True
        assert ev("sets.equivalent([1, 2, 2], [2, 1])", ctx) is True
        assert ev("sets.equivalent([1, 2], [1, 3])", ctx) is False

    def test_intersects(self, ctx):
        assert ev("sets.intersects([1, 2], [2, 3])", ctx) is True
        assert ev("sets.intersects([1, 2], [3, 4])", ctx) is False


class TestEncoders:
    def test_round_trip(self, ctx):
        assert ev('base64.encode(b"hello")', ctx) == "aGVsbG8="
        assert ev('base64.decode("aGVsbG8=")', ctx) == b"hello"

    def test_decode_encode_identity(self, ctx):
        assert ev('base64.decode(base64.encode(b"data"))', ctx) == b"data"

    def test_decode_rejects_invalid(self, ctx):
        # Non-alphabet characters are rejected rather than silently dropped.
        with pytest.raises(RuntimeError):
            ev('base64.decode("aG!!VsbG8=")', ctx)


class TestLists:
    def test_contains(self, ctx):
        assert ev("[1, 2, 3].contains(2)", ctx) is True
        assert ev("[1, 2, 3].contains(9)", ctx) is False

    def test_contains_does_not_shadow_string_builtin(self, ctx):
        # The built-in string.contains overload still wins.
        assert ev('"abc".contains("b")', ctx) is True
        assert ev('"abc".contains("z")', ctx) is False

    def test_distinct(self, ctx):
        assert ev("[1, 1, 2, 3, 3, 3].distinct()", ctx) == [1, 2, 3]

    def test_flatten(self, ctx):
        assert ev("[[1, 2], [3], [4, 5]].flatten()", ctx) == [1, 2, 3, 4, 5]
        assert ev("[[1, [2]], [3]].flatten()", ctx) == [1, [2], 3]
        assert ev("[[1, [2]], [3]].flatten(2)", ctx) == [1, 2, 3]

    def test_slice(self, ctx):
        assert ev("[1, 2, 3, 4, 5].slice(1, 3)", ctx) == [2, 3]

    def test_sort(self, ctx):
        assert ev("[3, 1, 2].sort()", ctx) == [1, 2, 3]

    def test_reverse_list(self, ctx):
        assert ev("[1, 2, 3].reverse()", ctx) == [3, 2, 1]

    def test_range(self, ctx):
        assert ev("lists.range(4)", ctx) == [0, 1, 2, 3]
        assert ev("lists.range(0)", ctx) == []

    def test_first_last_return_optionals(self, ctx):
        assert ev("[10, 20, 30].first().value()", ctx) == 10
        assert ev("[10, 20, 30].last().value()", ctx) == 30
        assert ev("[].first().hasValue()", ctx) is False
        assert ev("[].first().orValue(-1)", ctx) == -1


class TestMemberVsGlobalDispatch:
    """A registered function can be called as a method or a free function."""

    def test_member_call_on_literal(self):
        context = cel.Context()
        context.add_function("shout", lambda s: s.upper() + "!")
        assert cel.evaluate('"hi".shout()', context) == "HI!"
        assert cel.evaluate('shout("hi")', context) == "HI!"

    def test_member_call_with_args(self):
        def clamp(x, lo, hi):
            return max(lo, min(hi, x))

        context = cel.Context()
        context.add_function("clamp", clamp)
        context.add_variable("value", 15)
        # Method call: the target becomes the first argument.
        assert cel.evaluate("value.clamp(0, 10)", context) == 10
        # Free-function call is equivalent.
        assert cel.evaluate("clamp(15, 0, 10)", context) == 10

    def test_member_call_on_variable(self):
        context = cel.Context()
        context.add_function("second", lambda lst: lst[1])
        context.add_variable("items", [10, 20, 30])
        assert cel.evaluate("items.second()", context) == 20

    def test_member_call_on_macro_result(self):
        context = cel.Context()
        context.add_function("total", lambda lst: sum(lst))
        assert cel.evaluate("[1, 2, 3].map(x, x * 2).total()", context) == 12
