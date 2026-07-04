# Expression Introspection

`compile()` returns a `Program` that can report which variables and functions
an expression references, without evaluating it. This is useful for validating
that a context supplies everything an expression needs, building autocomplete,
or rejecting expressions that touch disallowed identifiers.

## `Program.variables()`

Returns the sorted list of variable names the expression reads:

```python
import cel

program = cel.compile("user.age >= min_age && size(roles) > 0")
assert program.variables() == ["min_age", "roles", "user"]
```

Only the *root* identifier of a field access is a variable — `user.age`
references `user`, not `age`. Names bound by comprehension macros are reported
as variables because they appear as identifiers:

```python
import cel

program = cel.compile("[1, 2, 3].map(x, x * 2)")
assert "x" in program.variables()
```

## `Program.functions()`

Returns the sorted list of function and operator names. Operators are reported
using their canonical CEL overload identifiers (e.g. `_>_`, `_&&_`):

```python
import cel

program = cel.compile("size(items) > 0")
functions = program.functions()
assert "size" in functions
assert "_>_" in functions
```

## `Program.references()`

Returns both lists together:

```python
import cel

program = cel.compile("price * quantity > threshold")
refs = program.references()
assert refs == {
    "variables": ["price", "quantity", "threshold"],
    "functions": ["_*_", "_>_"],
}
```

## Validating a context

```python
import cel

program = cel.compile("price * quantity")
context = {"price": 10, "quantity": 3}

missing = [name for name in program.variables() if name not in context]
assert missing == []
assert program.execute(context) == 30
```

## Portability

CEL has no portable "bytecode". Cross-implementation interchange in the CEL
ecosystem is done with the protobuf AST (`cel.expr.Expr` and the type-checked
`CheckedExpr`), which the upstream `cel` Rust crate does not currently produce
or consume — it has no protobuf support and no separate type-checking phase.

As a result, a compiled `Program` cannot be serialized and shipped to another
CEL implementation. The portable artifact for this library is the CEL **source
string**, which is standardized and trivially cross-language. Use
`Program.references()` when you need static analysis of an expression.
