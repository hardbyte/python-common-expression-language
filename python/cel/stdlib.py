"""Extended standard-library functions for CEL.

The Rust ``cel`` crate that powers this package implements the CEL core
specification (the ``has``/``all``/``exists``/``exists_one``/``map``/``filter``
macros, the ``int``/``uint``/``double``/``string``/``bytes``/``timestamp``/
``duration`` conversions, ``size``, and the string predicates
``contains``/``startsWith``/``endsWith``/``matches``). It does **not** ship a
number of functions that
other CEL implementations — notably `cel-go <https://github.com/google/cel-go>`_
and its extension libraries — make available.

This module fills those gaps with pure-Python implementations, registered as
ordinary CEL functions. They are grouped into libraries that mirror cel-go:

========== ================================================================
Library    Functions
========== ================================================================
core       ``bool``, ``dyn``, ``type``, ``min``, ``max``, ``sum``
strings    ``charAt``, ``indexOf``, ``lastIndexOf``, ``substring``,
           ``replace``, ``split``, ``join``, ``lowerAscii``, ``upperAscii``,
           ``trim``, ``reverse``, ``strings.quote``
math       ``math.greatest``, ``math.least``, ``math.abs``, ``math.sign``,
           ``math.ceil``, ``math.floor``, ``math.round``, ``math.trunc``,
           ``math.isNaN``, ``math.isInf``, ``math.isFinite``, ``math.sqrt``,
           ``math.bitOr``, ``math.bitAnd``, ``math.bitXor``, ``math.bitNot``,
           ``math.bitShiftLeft``, ``math.bitShiftRight``
sets       ``sets.contains``, ``sets.equivalent``, ``sets.intersects``
encoders   ``base64.encode``, ``base64.decode``
lists      ``contains``, ``distinct``, ``flatten``, ``slice``, ``sort``,
           ``reverse``, ``first``, ``last``, ``lists.range``
========== ================================================================

Because CEL treats ``x.f(a)`` as sugar for ``f(x, a)``, every function here can
be called either as a method (``"hello".charAt(1)``) or as a free function
(``charAt("hello", 1)``). Namespaced functions such as ``math.greatest`` are
called with their dotted name.

These functions are **opt-in**: :func:`cel.evaluate` and :func:`cel.compile`
expose only the Rust-native standard library by default. Use
:func:`add_stdlib_to_context` (or the ``cel`` command-line tool, which enables
them automatically) to make them available.

Compatibility notes / known limitations versus cel-go:

* ``type(x)`` returns the CEL type *name* as a string (e.g. ``"int"``) rather
  than a first-class CEL type value, so ``type(x) == type(y)`` works but
  comparing against a bare type identifier (``type(x) == int``) does not.
  Because Python has a single ``int`` type, a CEL ``uint`` is reported as
  ``"int"``.
* The cel-go ``strings.format`` and ``strings.quote`` verbs are only partially
  covered: ``strings.quote`` performs CEL-style escaping but ``strings.format``
  is not implemented.
* ``distinct``/``sort`` and the ``sets`` functions compare elements with
  Python equality, which treats ``True == 1`` and ``False == 0``. Lists that
  mix booleans with the integers ``0``/``1`` may therefore behave differently
  from a spec-strict CEL implementation, which keeps the types distinct.
* Every function here runs as a Python callback, so results are converted back
  through Python's type system. Two CEL types survive that round trip lossily:
  ``uint`` returns as ``int`` (Python has a single integer type), which means
  ``sum([1u, 2u]) + 1u`` raises a no-such-overload ``TypeError`` where the native
  ``[1u, 2u][0] + 1u`` succeeds; and ``duration`` is carried by
  :class:`datetime.timedelta`, whose resolution is microseconds, so sub-microsecond
  durations are rounded before a function ever sees them (plain
  :func:`cel.evaluate` truncates ``duration("1ns")`` the same way). Keep uint
  arithmetic and nanosecond durations inside native CEL expressions.
* ``min``/``max``/``sum`` are aggregation helpers rather than spec functions:
  CEL itself has none, cel-go keeps only ``math.greatest``/``math.least``, and
  cel-rust 0.14 deliberately dropped ``min``/``max`` from its default overloads.
  The spellings here follow Kubernetes' CEL list library instead.
* ``fold``/``reduce`` are **not** provided. They cannot be implemented as CEL
  functions, because a function receives evaluated arguments while a fold needs
  its accumulator expression left unevaluated and re-bound per element. In
  cel-rust the comprehension macros (``all``/``exists``/``map``/``filter``) are
  expanded by the parser from a fixed table, so a ``fold`` macro has to be added
  upstream: https://github.com/cel-rust/cel-rust
* ``dyn`` is kept for callers that enable the ``core`` library on older builds;
  cel-rust ships a native ``dyn()`` since 0.14.1, and the native one is used when
  the extensions are not registered.
"""

from __future__ import annotations

import base64 as _base64
import math as _math
from datetime import datetime, timedelta
from typing import Any, Callable

from .cel import OptionalValue

# ---------------------------------------------------------------------------
# Core specification functions missing from cel-rust
# ---------------------------------------------------------------------------

# String spellings cel-go accepts for bool() conversion.
_BOOL_TRUE = {"1", "t", "true", "TRUE", "True"}
_BOOL_FALSE = {"0", "f", "false", "FALSE", "False"}


def bool_(value: Any) -> bool:
    """Convert a value to a boolean, following CEL's ``bool()`` conversion.

    Booleans pass through unchanged. Strings are converted using the set of
    spellings CEL recognises (``"1"``, ``"t"``, ``"true"``, ``"TRUE"``,
    ``"True"`` are true; ``"0"``, ``"f"``, ``"false"``, ``"FALSE"``, ``"False"``
    are false). Any other value raises ``ValueError``.
    """
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        if value in _BOOL_TRUE:
            return True
        if value in _BOOL_FALSE:
            return False
        raise ValueError(f"cannot convert string {value!r} to bool")
    raise ValueError(f"cannot convert {type(value).__name__} to bool")


def dyn(value: Any) -> Any:
    """Return the value unchanged.

    CEL's ``dyn()`` erases static type information; at runtime it is the
    identity function.
    """
    return value


def type_(value: Any) -> str:
    """Return the CEL type name of a value as a string.

    See the module docstring for the limitations of this shim (notably that it
    returns a string rather than a CEL type value, and cannot distinguish
    ``uint`` from ``int``).
    """
    if value is None:
        return "null"
    if isinstance(value, OptionalValue):
        return "optional_type"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "double"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (bytes, bytearray)):
        return "bytes"
    if isinstance(value, datetime):
        return "timestamp"
    if isinstance(value, timedelta):
        return "duration"
    if isinstance(value, (list, tuple)):
        return "list"
    if isinstance(value, dict):
        return "map"
    return type(value).__name__


def _flatten_args(args: tuple[Any, ...]) -> list[Any]:
    """Accept either a single list argument or several scalar arguments."""
    if len(args) == 1 and isinstance(args[0], (list, tuple)):
        return list(args[0])
    return list(args)


def _collect_numbers(args: tuple[Any, ...]) -> list[Any]:
    """Normalise ``greatest``/``least``/``min``/``max`` arguments to a list.

    Accepts either a single list argument or several scalar arguments.
    """
    items = _flatten_args(args)
    if not items:
        raise ValueError("at least one argument is required")
    return items


def min_(*args: Any) -> Any:
    """Return the smallest of the arguments (or of a single list argument)."""
    return min(_collect_numbers(args))


def max_(*args: Any) -> Any:
    """Return the largest of the arguments (or of a single list argument)."""
    return max(_collect_numbers(args))


def sum_(*args: Any) -> Any:
    """Return the sum of the arguments (or of a single list argument).

    Follows the ``sum`` of Kubernetes' CEL list library: ``int``, ``uint`` and
    ``double`` are supported, as is ``duration``. Summing an empty list yields
    ``0``. Booleans are rejected rather than counted as ``1``/``0``, and numbers
    cannot be mixed with durations, because CEL has no implicit conversion
    between those types.

    Two consequences of running inside a Python callback apply here as they do to
    every function in this module — see the module docstring: a sum of ``uint``
    values comes back as an ``int``, and durations are microsecond-resolution.
    """
    items = _flatten_args(args)
    if not items:
        return 0
    if any(isinstance(item, bool) for item in items):
        raise TypeError("sum() is not defined for bool values")
    if all(isinstance(item, timedelta) for item in items):
        return sum(items, timedelta())
    if not all(isinstance(item, (int, float)) for item in items):
        raise TypeError("sum() requires either all numbers or all durations")
    return sum(items)


# ---------------------------------------------------------------------------
# strings extension (mirrors cel-go's ext.Strings)
# ---------------------------------------------------------------------------


def char_at(s: str, index: int) -> str:
    """Return the character at ``index``. ``index == len(s)`` yields ``""``."""
    if index == len(s):
        return ""
    if index < 0 or index > len(s):
        raise IndexError(f"charAt: index {index} out of range for string of length {len(s)}")
    return s[index]


def index_of(s: str, substr: str, offset: int = 0) -> int:
    """Return the index of the first occurrence of ``substr`` at or after ``offset`` (or -1).

    ``offset`` must be within ``[0, len(s)]`` (cel-go raises otherwise).
    """
    if offset < 0 or offset > len(s):
        raise IndexError(f"indexOf: offset {offset} out of range for string of length {len(s)}")
    return s.find(substr, offset)


def last_index_of(s: str, substr: str, offset: int | None = None) -> int:
    """Return the index of the last occurrence of ``substr`` (or -1).

    When ``offset`` is given (which must be within ``[0, len(s)]``), only
    occurrences starting at or before ``offset`` are considered.
    """
    if offset is None:
        return s.rfind(substr)
    if offset < 0 or offset > len(s):
        raise IndexError(f"lastIndexOf: offset {offset} out of range for string of length {len(s)}")
    return s.rfind(substr, 0, offset + len(substr))


def substring(s: str, start: int, end: int | None = None) -> str:
    """Extract a substring from ``start`` (inclusive) to ``end`` (exclusive).

    Indices must satisfy ``0 <= start <= end <= len(s)`` (cel-go raises on
    out-of-range or reversed indices rather than clamping).
    """
    length = len(s)
    if end is None:
        end = length
    if start < 0 or end > length or start > end:
        raise IndexError(f"substring: [{start}:{end}] out of range for string of length {length}")
    return s[start:end]


def replace(s: str, old: str, new: str, limit: int = -1) -> str:
    """Replace occurrences of ``old`` with ``new``.

    ``limit`` bounds the number of replacements; a negative ``limit`` (the
    default) replaces every occurrence.
    """
    if limit < 0:
        return s.replace(old, new)
    return s.replace(old, new, limit)


def split(s: str, sep: str, limit: int | None = None) -> list[str]:
    """Split ``s`` on ``sep``.

    ``limit`` bounds the number of returned pieces: ``limit`` of 0 returns an
    empty list, a negative ``limit`` returns all pieces, and a positive
    ``limit`` returns at most ``limit`` pieces.
    """
    # An empty separator splits into individual characters (matching cel-go);
    # Python's str.split("") raises instead.
    if sep == "":
        chars = list(s)
        if limit is None or limit < 0 or limit >= len(chars):
            return chars
        if limit == 0:
            return []
        return chars[: limit - 1] + ["".join(chars[limit - 1 :])]
    if limit is None or limit < 0:
        return s.split(sep)
    if limit == 0:
        return []
    return s.split(sep, limit - 1)


def join(items: list[Any], sep: str = "") -> str:
    """Join a list of strings with ``sep``."""
    return sep.join(items)


def lower_ascii(s: str) -> str:
    """Lowercase the ASCII letters in ``s``, leaving other characters unchanged."""
    return "".join(chr(ord(c) + 32) if "A" <= c <= "Z" else c for c in s)


def upper_ascii(s: str) -> str:
    """Uppercase the ASCII letters in ``s``, leaving other characters unchanged."""
    return "".join(chr(ord(c) - 32) if "a" <= c <= "z" else c for c in s)


def trim(s: str) -> str:
    """Remove leading and trailing whitespace from ``s``."""
    return s.strip()


_QUOTE_ESCAPES = {
    "\\": "\\\\",
    '"': '\\"',
    "\n": "\\n",
    "\r": "\\r",
    "\t": "\\t",
    "\x07": "\\a",
    "\x08": "\\b",
    "\x0c": "\\f",
    "\x0b": "\\v",
}


def quote(s: str) -> str:
    """Return ``s`` as a double-quoted CEL string literal with escapes applied."""
    escaped = "".join(_QUOTE_ESCAPES.get(c, c) for c in s)
    return f'"{escaped}"'


def reverse(value: Any) -> Any:
    """Reverse a string or a list."""
    if isinstance(value, str):
        return value[::-1]
    if isinstance(value, (list, tuple)):
        return list(value)[::-1]
    raise TypeError(f"reverse: unsupported type {type(value).__name__}")


# ---------------------------------------------------------------------------
# math extension (mirrors cel-go's ext.Math, namespaced under ``math.``)
# ---------------------------------------------------------------------------


def math_greatest(*args: Any) -> Any:
    """Return the greatest argument (or greatest element of a single list)."""
    return max(_collect_numbers(args))


def math_least(*args: Any) -> Any:
    """Return the least argument (or least element of a single list)."""
    return min(_collect_numbers(args))


def math_abs(x: Any) -> Any:
    """Return the absolute value of ``x``, preserving int/double."""
    return abs(x)


def math_sign(x: Any) -> Any:
    """Return -1, 0 or 1 with the sign of ``x``, preserving int/double."""
    if isinstance(x, float):
        if x > 0:
            return 1.0
        if x < 0:
            return -1.0
        return 0.0
    return (x > 0) - (x < 0)


def math_ceil(x: float) -> float:
    """Return the ceiling of ``x`` as a double (NaN/±inf pass through)."""
    if not _math.isfinite(x):
        return x
    return float(_math.ceil(x))


def math_floor(x: float) -> float:
    """Return the floor of ``x`` as a double (NaN/±inf pass through)."""
    if not _math.isfinite(x):
        return x
    return float(_math.floor(x))


def math_round(x: float) -> float:
    """Return ``x`` rounded to the nearest integer, halves away from zero.

    NaN and ±inf pass through unchanged.
    """
    if not _math.isfinite(x):
        return x
    floor = _math.floor(x)
    frac = x - floor
    if frac < 0.5:
        return float(floor)
    if frac > 0.5:
        return float(floor + 1)
    # Exactly halfway: round away from zero.
    return float(floor + 1) if x > 0 else float(floor)


def math_trunc(x: float) -> float:
    """Return ``x`` truncated toward zero, as a double (NaN/±inf pass through)."""
    if not _math.isfinite(x):
        return x
    return float(_math.trunc(x))


def math_is_nan(x: float) -> bool:
    """Return whether ``x`` is NaN."""
    return _math.isnan(x)


def math_is_inf(x: float) -> bool:
    """Return whether ``x`` is positive or negative infinity."""
    return _math.isinf(x)


def math_is_finite(x: float) -> bool:
    """Return whether ``x`` is neither NaN nor infinite."""
    return _math.isfinite(x)


def math_sqrt(x: Any) -> float:
    """Return the square root of ``x`` as a double (NaN for negative inputs)."""
    if x < 0:
        return _math.nan
    return _math.sqrt(x)


_U64_MASK = (1 << 64) - 1


def _wrap_i64(n: int) -> int:
    """Wrap an integer into the signed 64-bit range (two's complement).

    CEL integers are 64-bit; bit operations therefore wrap rather than growing
    without bound (which would silently be coerced to a double when converted
    back to a CEL value).
    """
    n &= _U64_MASK
    return n - (1 << 64) if n >= (1 << 63) else n


def math_bit_or(a: int, b: int) -> int:
    """Bitwise OR of two integers."""
    return _wrap_i64(a | b)


def math_bit_and(a: int, b: int) -> int:
    """Bitwise AND of two integers."""
    return _wrap_i64(a & b)


def math_bit_xor(a: int, b: int) -> int:
    """Bitwise XOR of two integers."""
    return _wrap_i64(a ^ b)


def math_bit_not(a: int) -> int:
    """Bitwise NOT of an integer."""
    return _wrap_i64(~a)


def math_bit_shift_left(a: int, n: int) -> int:
    """Left-shift ``a`` by ``n`` bits (result wraps to 64 bits)."""
    if n < 0:
        raise ValueError("negative shift amount")
    if n >= 64:
        return 0
    return _wrap_i64(a << n)


def math_bit_shift_right(a: int, n: int) -> int:
    """Logically right-shift ``a`` by ``n`` bits (zero-fill, 64-bit)."""
    if n < 0:
        raise ValueError("negative shift amount")
    if n >= 64:
        return 0
    return _wrap_i64((a & _U64_MASK) >> n)


# ---------------------------------------------------------------------------
# sets extension (mirrors cel-go's ext.Sets, namespaced under ``sets.``)
# ---------------------------------------------------------------------------


def sets_contains(container: list[Any], sublist: list[Any]) -> bool:
    """Return whether every element of ``sublist`` appears in ``container``."""
    return all(item in container for item in sublist)


def sets_equivalent(a: list[Any], b: list[Any]) -> bool:
    """Return whether ``a`` and ``b`` contain the same set of elements."""
    return all(item in b for item in a) and all(item in a for item in b)


def sets_intersects(a: list[Any], b: list[Any]) -> bool:
    """Return whether ``a`` and ``b`` share at least one element."""
    return any(item in b for item in a)


# ---------------------------------------------------------------------------
# encoders extension (mirrors cel-go's ext.Encoders, namespaced under ``base64.``)
# ---------------------------------------------------------------------------


def base64_encode(data: bytes) -> str:
    """Base64-encode bytes, returning a string."""
    if isinstance(data, str):
        data = data.encode("utf-8")
    return _base64.b64encode(data).decode("ascii")


def base64_decode(data: str) -> bytes:
    """Base64-decode a string, returning bytes.

    Validation is strict: non-alphabet characters raise rather than being
    silently discarded.
    """
    return _base64.b64decode(data, validate=True)


# ---------------------------------------------------------------------------
# lists extension (mirrors cel-go's ext.Lists)
# ---------------------------------------------------------------------------


def contains(container: Any, item: Any) -> bool:
    """Return whether ``item`` is in ``container`` (list, map or string).

    This restores the multi-type ``contains`` that cel-rust 0.14 dropped: its
    built-in ``contains`` is string-only, so this shim handles lists and maps
    (for maps, membership tests the keys). The built-in string overload still
    takes precedence for ``string.contains(string)``.
    """
    return item in container


def distinct(items: list[Any]) -> list[Any]:
    """Return the elements of ``items`` with duplicates removed, order preserved."""
    result: list[Any] = []
    for item in items:
        if item not in result:
            result.append(item)
    return result


def flatten(items: list[Any], depth: int = 1) -> list[Any]:
    """Flatten nested lists up to ``depth`` levels (default 1)."""
    if depth < 0:
        raise ValueError("flatten: depth must be non-negative")
    result: list[Any] = []
    for item in items:
        if isinstance(item, (list, tuple)) and depth > 0:
            result.extend(flatten(list(item), depth - 1))
        else:
            result.append(item)
    return result


def slice_(items: list[Any], start: int, end: int) -> list[Any]:
    """Return the sub-list ``items[start:end]``."""
    if start < 0 or end > len(items) or start > end:
        raise IndexError(f"slice: [{start}:{end}] out of range for list of length {len(items)}")
    return items[start:end]


def sort(items: list[Any]) -> list[Any]:
    """Return a new list with ``items`` sorted in ascending order."""
    return sorted(items)


def first(items: list[Any]) -> OptionalValue:
    """Return the first element as an optional, or ``optional.none()`` if empty."""
    if items:
        return OptionalValue.of(items[0])
    return OptionalValue.none()


def last(items: list[Any]) -> OptionalValue:
    """Return the last element as an optional, or ``optional.none()`` if empty."""
    if items:
        return OptionalValue.of(items[-1])
    return OptionalValue.none()


def lists_range(n: int) -> list[int]:
    """Return the list ``[0, 1, ..., n - 1]``."""
    return list(range(n))


# ---------------------------------------------------------------------------
# Registries
# ---------------------------------------------------------------------------

#: Extension libraries, each a mapping of CEL function name -> implementation.
EXTENSIONS: dict[str, dict[str, Callable[..., Any]]] = {
    "core": {
        "bool": bool_,
        "dyn": dyn,
        "type": type_,
        "min": min_,
        "max": max_,
        "sum": sum_,
    },
    "strings": {
        "charAt": char_at,
        "indexOf": index_of,
        "lastIndexOf": last_index_of,
        "substring": substring,
        "replace": replace,
        "split": split,
        "join": join,
        "lowerAscii": lower_ascii,
        "upperAscii": upper_ascii,
        "trim": trim,
        "reverse": reverse,
        "strings.quote": quote,
    },
    "math": {
        "math.greatest": math_greatest,
        "math.least": math_least,
        "math.abs": math_abs,
        "math.sign": math_sign,
        "math.ceil": math_ceil,
        "math.floor": math_floor,
        "math.round": math_round,
        "math.trunc": math_trunc,
        "math.isNaN": math_is_nan,
        "math.isInf": math_is_inf,
        "math.isFinite": math_is_finite,
        "math.sqrt": math_sqrt,
        "math.bitOr": math_bit_or,
        "math.bitAnd": math_bit_and,
        "math.bitXor": math_bit_xor,
        "math.bitNot": math_bit_not,
        "math.bitShiftLeft": math_bit_shift_left,
        "math.bitShiftRight": math_bit_shift_right,
    },
    "sets": {
        "sets.contains": sets_contains,
        "sets.equivalent": sets_equivalent,
        "sets.intersects": sets_intersects,
    },
    "encoders": {
        "base64.encode": base64_encode,
        "base64.decode": base64_decode,
    },
    "lists": {
        "contains": contains,
        "distinct": distinct,
        "flatten": flatten,
        "slice": slice_,
        "sort": sort,
        "reverse": reverse,
        "first": first,
        "last": last,
        "lists.range": lists_range,
    },
}

#: All extended-stdlib functions merged into a single ``name -> callable`` map.
STDLIB_FUNCTIONS: dict[str, Callable[..., Any]] = {
    name: func for library in EXTENSIONS.values() for name, func in library.items()
}


def add_stdlib_to_context(context: Any, extensions: list[str] | None = None) -> None:
    """Register the extended standard-library functions on a CEL context.

    Args:
        context: A :class:`cel.Context` to register functions on.
        extensions: Optional list of extension library names to add (any of
            ``"core"``, ``"strings"``, ``"math"``, ``"sets"``, ``"encoders"``,
            ``"lists"``). When ``None`` (the default) every library is added.

    Raises:
        KeyError: If an unknown extension name is requested.

    Example:
        >>> import cel
        >>> from cel.stdlib import add_stdlib_to_context
        >>> context = cel.Context()
        >>> add_stdlib_to_context(context)
        >>> cel.evaluate('"hello".charAt(0)', context)
        'h'
        >>> cel.evaluate("math.greatest([3, 1, 2])", context)
        3
    """
    if extensions is None:
        libraries = list(EXTENSIONS.values())
    else:
        libraries = [EXTENSIONS[name] for name in extensions]

    for library in libraries:
        for name, func in library.items():
            context.add_function(name, func)
