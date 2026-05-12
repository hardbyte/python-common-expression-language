# Error Handling

CEL evaluation surfaces failures as Python exceptions. This guide covers the exception types you'll encounter and a canonical pattern for safely evaluating untrusted expressions.

## Exception types

| Exception      | When it's raised                                                          |
|----------------|---------------------------------------------------------------------------|
| `ValueError`   | Parse / compile errors, including malformed syntax and empty expressions. |
| `RuntimeError` | Undefined variables, undefined functions, custom-function failures.       |
| `TypeError`    | Type mismatches — incompatible operands, no matching overload, etc.       |

### `ValueError` — parse and compile errors

```python
from cel import evaluate

try:
    evaluate("1 + + 2")
except ValueError as e:
    assert "Failed to parse expression" in str(e)

try:
    evaluate("")
except ValueError as e:
    assert "Failed to parse expression" in str(e)
```

Malformed input (unclosed quotes, mixed quote types, invalid syntax) raises `ValueError` cleanly — the library never panics or crashes the process.

### `RuntimeError` — variable and function errors

```python
try:
    evaluate("undefined_var", {})
except RuntimeError as e:
    assert "Undefined variable or function" in str(e)

try:
    evaluate("missing_func()", {})
except RuntimeError as e:
    assert "Undefined variable or function" in str(e)
```

### `TypeError` — incompatible operand types

```python
try:
    evaluate("1 + 2u")  # mixed signed/unsigned int
except TypeError as e:
    assert "overload" in str(e).lower() or "signed and unsigned" in str(e)

try:
    evaluate('"hello" && true')  # non-bool in a logical op
except TypeError as e:
    assert "No such overload" in str(e)
```

CEL has no implicit numeric coercion: `int + double`, `int + uint`, and similar combinations all raise `TypeError`. Use `int(x)`, `uint(x)`, or `double(x)` to convert explicitly.

## Safe evaluation wrapper

For untrusted input, wrap evaluation with a single handler that converts all CEL exceptions to a sentinel value:

```python
from cel import evaluate
from typing import Any, Optional, Dict
import logging

log = logging.getLogger(__name__)


def safe_evaluate(
    expression: str,
    context: Optional[Dict[str, Any]] = None,
) -> Optional[Any]:
    """Evaluate a CEL expression, returning None on any failure."""
    try:
        return evaluate(expression, context)
    except (ValueError, RuntimeError, TypeError) as e:
        log.warning("CEL evaluation failed: %s (expr=%r)", e, expression)
        return None


# Examples
assert safe_evaluate("user.age >= 18", {"user": {"age": 25}}) is True
assert safe_evaluate("1 + + 2") is None             # parse error
assert safe_evaluate("missing", {}) is None         # undefined variable
assert safe_evaluate("1 + 'oops'") is None          # type error
```

## Defensive expression patterns

Within the expression itself, use `has()` and ternaries to short-circuit around missing fields rather than relying on exception handling:

```python
# Safe field access using has()
expr = '''
    has(user.profile) && has(user.profile.email)
        ? user.profile.email
        : "no-email"
'''
result = evaluate(expr, {"user": {"profile": {"email": "alice@example.com"}}})
assert result == "alice@example.com"

# Default values for optional fields
result = evaluate(
    'has(config.timeout) ? config.timeout : 30',
    {"config": {}},
)
assert result == 30
```

## Pre-compilation for performance

If you're evaluating the same expression many times, compile once and reuse the program. Parse errors surface at `compile()` time; runtime errors at `execute()` time, which lets you handle the two failure modes separately:

```python
from cel import compile

program = compile("user.age >= 18")

# Then on each call:
try:
    allowed = program.execute({"user": {"age": 25}})
except (RuntimeError, TypeError) as e:
    log.warning("Policy evaluation failed: %s", e)
    allowed = False

assert allowed is True
```

## Testing error scenarios

When testing code that evaluates CEL expressions, assert on the exception type — not the exact message, which can drift with cel-rust releases:

```python
import pytest
from cel import evaluate

def test_invalid_syntax():
    with pytest.raises(ValueError):
        evaluate("1 + + 2")

def test_undefined_variable():
    with pytest.raises(RuntimeError):
        evaluate("missing_var", {})

def test_type_mismatch():
    with pytest.raises(TypeError):
        evaluate("1 + 2u")
```

## Best practices

- **Catch by type, not message.** Exception classes are part of the public API; message text is not.
- **Use `has()` for optional fields** rather than catching exceptions from inside an expression.
- **Pre-compile hot-path expressions** with `compile()` so parse errors surface once, at startup.
- **Log the failing expression** when you catch an evaluation error — the expression text is usually the most useful debugging info.
- **Don't sandbox by exception handling alone** if the expression source is untrusted; also limit input size, expression depth, and execution time.
