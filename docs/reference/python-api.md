# Python API Reference

The public API uses one explicit pipeline:

```text
Python value -> cel.prepare -> Context.add_variable -> Program.execute(Context)
```

## `prepare(value) -> PreparedValue`

Prepare a supported Python value once. The result is an opaque immutable snapshot that can be reused and shared. Calling `prepare` on a prepared value is idempotent and cheap.

```python
import cel

source = {"profile": {"enabled": True}}
prepared = cel.prepare(source)
source["profile"]["enabled"] = False

context = cel.Context()
context.add_variable("user", prepared)
assert cel.compile("user.profile.enabled").execute(context) is True
```

Supported values include `None`, booleans, signed and unsigned-range integers, floats, strings, bytes, lists, tuples, mappings, timezone-aware and naive datetimes, timedeltas, optional values, and nested combinations. Unsupported values fail during preparation. `PreparedValue` has no public constructor and does not render its payload.

## `Context`

`Context()` accepts no arguments and owns one persistent native CEL context.

```python
import cel

context = cel.Context()
context.add_variable("name", cel.prepare("Alice"))
context.add_function("greet", lambda name: f"Hello, {name}!")
assert cel.evaluate("greet(name)", context) == "Hello, Alice!"
```

### `add_variable(name, value)`

`value` must be a `PreparedValue`; raw Python values raise `TypeError`. Adding a name again replaces its binding. No implicit preparation occurs.

### `add_function(name, function)`

Register a callable directly in the native context. The callback adapter is created once and reused by later executions.

`Context` intentionally has no constructor mappings, `update`, public variable/function dictionaries, mapping behavior, copying, serialization, or introspection API.

## `compile(expression) -> Program`

Compile an expression once and execute it against a `Context`:

```python
import cel

prepared = cel.prepare({
    "objects": [
        {"active": i % 2 == 0, "score": i}
        for i in range(500)
    ]
})
context = cel.Context()
program = cel.compile("data.objects[3].score >= 3")

for _ in range(100_000):
    context.add_variable("data", prepared)
    assert program.execute(context) is True
```

`Program.execute(context)` requires exactly one concrete `Context`. Dictionaries, `None`, prepared values, omitted arguments, and other representations are rejected. Execution borrows the native context and does not rebuild it or reconvert bound values.

## `evaluate(expression, context) -> Any`

`evaluate` also requires a `Context`:

```python
import cel

context = cel.Context()
context.add_variable("answer", cel.prepare(42))
assert cel.evaluate("answer", context) == 42
```

## `OptionalValue`

`OptionalValue.of(value)` and `OptionalValue.none()` expose CEL optional values to Python. Prepare them before binding:

```python
import cel

context = cel.Context()
context.add_variable("value", cel.prepare(cel.OptionalValue.of(42)))
context.add_variable("missing", cel.prepare(cel.OptionalValue.none()))
assert cel.compile("value.orValue(0)").execute(context) == 42
assert cel.compile("missing.orValue(7)").execute(context) == 7
```

## Performance and lifetime notes

For a retained prepared value, replacing a binding clones only a shared handle. Fixed field/index paths returning primitive values do not clone unrelated maps, lists, or objects. Expressions that inspect, return, or pass large values remain proportional to the data examined or materialized.

Retain prepared objects used for hot-path replacement. If a context owns the final reference to a large prepared value, replacing or dropping that final reference can recursively free the value and may take time proportional to its size.
