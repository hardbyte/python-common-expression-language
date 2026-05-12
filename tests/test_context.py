import cel
import pytest


def test_create_empty_context():
    cel.Context()


def test_context_vars_explicit():
    context = cel.Context(variables={"a": 10})
    assert cel.evaluate("a", context) == 10


def test_context_vars_implicit():
    context = cel.Context({"a": 10})
    assert cel.evaluate("a", context) == 10


def test_context_vars_none_value():
    context = cel.Context({"a": None})
    assert cel.evaluate("a", context) is None


def test_adding_to_context():
    context = cel.Context()

    with pytest.raises(
        RuntimeError
    ):  # Enhanced error handling now raises RuntimeError for undefined variables
        assert cel.evaluate("a + 2", context) == 4

    context.add_variable("a", 2)
    assert cel.evaluate("a + 2", context) == 4


def test_explicit_context():
    context = cel.Context()
    context.add_variable("a", 2)
    assert cel.evaluate("a + 2", context) == 4


def test_custom_function_init_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context(functions={"f": custom_function})

    assert cel.evaluate("f(1, 2)", context) == 3


def test_context_init_vars_and_funcs():
    def custom_function(a, b):
        return a + b

    context = cel.Context({"a": 10}, functions={"f": custom_function})

    assert cel.evaluate("f(a, 2)", context) == 12


def test_custom_function_with_explicit_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context()
    context.add_function("custom_function", custom_function)
    assert cel.evaluate("custom_function(1, 2)", context) == 3


def test_updating_explicit_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context()
    context.update(
        {
            "custom_function": custom_function,
            "a": 40,
            "b": 2,
        }
    )
    assert cel.evaluate("custom_function(a, b)", context) == 42


def test_nested_context_none():
    """Test that nested context with None values works correctly"""
    context = {
        "spec": {
            "type": "dns",
            "nameserver": None,
            "host": "github.com",
            "timeout": 30.0,
        },
        "data": {
            "canonical_name": "github.com.",
            "expiration": 1732097106.7902246,
            "A": ["4.237.22.38"],
            "response-code": "NOERROR",
            "startTimestamp": "2024-11-20T10:04:59.789017+00:00",
            "endTimestamp": "2024-11-20T10:04:59.790298+00:00",
        },
    }

    cel_context = cel.Context(variables=context)

    # Test that we can access nested values and None
    assert cel.evaluate("spec.nameserver", cel_context) is None
    assert cel.evaluate("spec.host", cel_context) == "github.com"
    assert cel.evaluate("data['response-code']", cel_context) == "NOERROR"
    assert cel.evaluate("size(data.A)", cel_context) == 1


class TestVariableResolver:
    """Tests for lazy variable resolution via set_variable_resolver."""

    def test_resolver_supplies_variable(self):
        """Resolver callback can provide variables not registered statically."""
        ctx = cel.Context()
        ctx.set_variable_resolver(
            lambda name: {"name": "Alice", "age": 30} if name == "user" else None
        )
        assert cel.evaluate("user.name", ctx) == "Alice"
        assert cel.evaluate("user.age", ctx) == 30

    def test_resolver_is_called_lazily(self):
        """Resolver only fires for names the expression actually references."""
        accessed = []

        def lookup(name):
            accessed.append(name)
            return {"limit": 50}.get(name)

        ctx = cel.Context()
        ctx.set_variable_resolver(lookup)
        assert cel.evaluate("limit > 10", ctx) is True
        assert accessed == ["limit"]

    def test_resolver_none_falls_through_to_static_variables(self):
        """Returning None from the resolver delegates to add_variable()-registered values."""
        ctx = cel.Context(variables={"static_var": 42})
        ctx.set_variable_resolver(lambda name: None)
        assert cel.evaluate("static_var", ctx) == 42

    def test_resolver_undefined_raises(self):
        """When neither the resolver nor static variables supply a name, evaluate raises."""
        ctx = cel.Context()
        ctx.set_variable_resolver(lambda name: None)
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("missing", ctx)

    def test_resolver_exception_is_swallowed(self):
        """An exception from the resolver is treated as 'not handled' rather than propagated."""
        ctx = cel.Context(variables={"x": 7})

        def explosive(name):
            raise ValueError(f"boom on {name}")

        ctx.set_variable_resolver(explosive)
        # Falls through to the static variable
        assert cel.evaluate("x", ctx) == 7

    def test_resolver_works_with_compiled_program(self):
        """Resolver applies through compile()+execute(), not just evaluate()."""
        program = cel.compile("user.name")
        ctx = cel.Context()
        ctx.set_variable_resolver(lambda name: {"name": "Bob"} if name == "user" else None)
        assert program.execute(ctx) == "Bob"

    def test_resolver_returns_various_types(self):
        """Resolver values can be any supported Python type."""

        def lookup(name):
            return {
                "i": 42,
                "f": 3.14,
                "s": "hello",
                "b": True,
                "l": [1, 2, 3],
                "m": {"k": "v"},
            }.get(name)

        ctx = cel.Context()
        ctx.set_variable_resolver(lookup)
        assert cel.evaluate("i", ctx) == 42
        assert cel.evaluate("f", ctx) == 3.14
        assert cel.evaluate("s", ctx) == "hello"
        assert cel.evaluate("b", ctx) is True
        assert cel.evaluate("size(l)", ctx) == 3
        assert cel.evaluate("m.k", ctx) == "v"
