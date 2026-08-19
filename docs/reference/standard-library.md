# Extended Standard Library

The Rust `cel` crate implements the CEL core specification: the
`has`/`all`/`exists`/`exists_one`/`map`/`filter` macros, the
`int`/`uint`/`double`/`string`/`bytes`/`timestamp`/`duration` conversions,
`size`, and the string predicates `contains`/`startsWith`/`endsWith`/`matches`.

`cel.stdlib` adds the functions that the core crate does *not* ship, grouped
into libraries that mirror [cel-go](https://github.com/google/cel-go)'s
extension libraries. These functions are **opt-in**: `evaluate()` and
`compile()` expose only the Rust-native standard library by default.

## Enabling the extensions

Register the functions on a [`Context`][cel.Context] and pass that context to
`evaluate()` (or `Program.execute()`):

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate('"Hello World".lowerAscii()', ctx) == "hello world"
assert cel.evaluate("math.greatest([3, 1, 2])", ctx) == 3
```

To register only some libraries, pass their names:

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx, extensions=["math", "lists"])

assert cel.evaluate("[1, 1, 2, 3].distinct()", ctx) == [1, 2, 3]
```

The `cel` command-line tool enables every extension automatically.

## Calling convention

Because CEL treats `x.f(a)` as sugar for `f(x, a)`, every function below can be
called either as a method or as a free function. Namespaced functions such as
`math.greatest` use their dotted name.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

# Method and free-function forms are equivalent.
assert cel.evaluate('"hello".charAt(0)', ctx) == "h"
assert cel.evaluate('charAt("hello", 0)', ctx) == "h"
```

## Libraries

### core

`bool`, `dyn`, `type`, `min`, `max`, `sum`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate('bool("true")', ctx) is True
assert cel.evaluate("dyn(5)", ctx) == 5
assert cel.evaluate("type(1) == type(2)", ctx) is True
assert cel.evaluate("min(3, 1, 2)", ctx) == 1
assert cel.evaluate("max([4, 9, 2])", ctx) == 9
assert cel.evaluate("sum([1, 2, 3])", ctx) == 6
```

`min`, `max` and `sum` accept either several arguments or a single list, so they
compose with `map()` in the method position:

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

ctx.update({"items": [{"weight": 0.5}, {"weight": 0.25}, {"weight": 0.25}]})
assert cel.evaluate("items.map(i, i.weight).sum() == 1.0", ctx) is True
assert cel.evaluate('sum([duration("1h"), duration("30m")]) == duration("90m")', ctx) is True
```

!!! note "Aggregations are extensions, not spec functions"
    CEL has no aggregation functions of its own, cel-go provides only
    `math.greatest`/`math.least`, and cel-rust 0.14 dropped `min`/`max` from its
    default overloads. `min`, `max` and `sum` here follow Kubernetes' CEL list
    library: `sum` covers every numeric type plus `duration`, and `min`/`max`
    work on any comparable type. `sum` of an empty list is `0`; booleans are
    rejected instead of counting as `1`/`0`, and numbers cannot be mixed with
    durations.

!!! warning "No `fold` or `reduce`"
    General folds cannot be expressed as CEL functions: a function receives its
    arguments already evaluated, whereas a fold needs the accumulator expression
    left unevaluated and re-bound for each element. In cel-rust the comprehension
    macros (`all`, `exists`, `existsOne`, `map`, `filter`) are expanded by the
    parser from a fixed table, so `fold`/`reduce` have to arrive
    [upstream](https://github.com/cel-rust/cel-rust) rather than in this wrapper.
    Most folds in practice are a `map()` plus `sum`/`min`/`max`, as above.

!!! note "`type()` limitations"
    `type(x)` returns the CEL type *name* as a string (e.g. `"int"`), so
    `type(x) == type(y)` works but comparing against a bare type identifier
    (`type(x) == int`) does not. Because Python has a single integer type, a CEL
    `uint` is reported as `"int"`.

### strings

`charAt`, `indexOf`, `lastIndexOf`, `substring`, `replace`, `split`, `join`,
`lowerAscii`, `upperAscii`, `trim`, `reverse`, `strings.quote`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate('"hello world".indexOf("o")', ctx) == 4
assert cel.evaluate('"a,b,c".split(",")', ctx) == ["a", "b", "c"]
assert cel.evaluate('["a", "b", "c"].join("-")', ctx) == "a-b-c"
assert cel.evaluate('"  padded  ".trim()', ctx) == "padded"
assert cel.evaluate('"abc".reverse()', ctx) == "cba"
```

### math

`math.greatest`, `math.least`, `math.abs`, `math.sign`, `math.ceil`,
`math.floor`, `math.round`, `math.trunc`, `math.isNaN`, `math.isInf`,
`math.isFinite`, `math.sqrt`, and the bit operations `math.bitOr`,
`math.bitAnd`, `math.bitXor`, `math.bitNot`, `math.bitShiftLeft`,
`math.bitShiftRight`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate("math.abs(-7)", ctx) == 7
assert cel.evaluate("math.round(2.5)", ctx) == 3.0  # half away from zero
assert cel.evaluate("math.sqrt(16.0)", ctx) == 4.0
assert cel.evaluate("math.bitOr(5, 2)", ctx) == 7
```

### sets

`sets.contains`, `sets.equivalent`, `sets.intersects`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate("sets.contains([1, 2, 3], [1, 2])", ctx) is True
assert cel.evaluate("sets.equivalent([1, 2], [2, 1])", ctx) is True
assert cel.evaluate("sets.intersects([1, 2], [2, 3])", ctx) is True
```

### encoders

`base64.encode`, `base64.decode`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate('base64.encode(b"hello")', ctx) == "aGVsbG8="
assert cel.evaluate('base64.decode("aGVsbG8=")', ctx) == b"hello"
```

### lists

`contains`, `distinct`, `flatten`, `slice`, `sort`, `reverse`, `first`, `last`,
`lists.range`.

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate("[1, 2, 3].contains(2)", ctx) is True
assert cel.evaluate("[1, 1, 2, 3].distinct()", ctx) == [1, 2, 3]
assert cel.evaluate("[[1, 2], [3]].flatten()", ctx) == [1, 2, 3]
assert cel.evaluate("[3, 1, 2].sort()", ctx) == [1, 2, 3]
assert cel.evaluate("lists.range(3)", ctx) == [0, 1, 2]
```

`first` and `last` return CEL optional values, so combine them with the
optional member methods:

```python
import cel
from cel.stdlib import add_stdlib_to_context

ctx = cel.Context()
add_stdlib_to_context(ctx)

assert cel.evaluate("[10, 20, 30].first().value()", ctx) == 10
assert cel.evaluate("[].first().orValue(-1)", ctx) == -1
```

!!! info "`contains` and the built-in string overload"
    The Rust core provides a string-only `contains`. The `lists` extension adds
    a multi-type `contains` for lists and maps, but the built-in string overload
    still takes precedence for `string.contains(string)`.

## Registering your own functions

`cel.stdlib` is built on the ordinary custom-function API, so you can register
your own functions the same way. A function registered under one name is
callable both as `f(x)` and `x.f()`:

```python
import cel

ctx = cel.Context()
ctx.add_function("shout", lambda s: s.upper() + "!")

assert cel.evaluate('"hi".shout()', ctx) == "HI!"
assert cel.evaluate('shout("hi")', ctx) == "HI!"
```

See [Extending CEL](../tutorials/extending-cel.md) for more.
