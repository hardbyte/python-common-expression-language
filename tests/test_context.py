import datetime

import cel
import pytest


def bind(context, name, value):
    context.add_variable(name, cel.prepare(value))


def test_context_is_empty_and_accepts_no_constructor_arguments():
    context = cel.Context()
    assert repr(context) == "Context()"

    with pytest.raises(TypeError):
        cel.Context({"a": 1})
    with pytest.raises(TypeError):
        cel.Context(variables={"a": 1})
    with pytest.raises(TypeError):
        cel.Context(functions={"f": lambda: None})


def test_context_exposes_only_narrow_mutation_api():
    context = cel.Context()
    assert not hasattr(context, "variables")
    assert not hasattr(context, "functions")
    assert not hasattr(context, "update")
    with pytest.raises(TypeError):
        len(context)


def test_add_and_replace_prepared_variable():
    context = cel.Context()
    program = cel.compile("data.value")

    bind(context, "data", {"value": 1})
    assert program.execute(context) == 1

    bind(context, "data", {"value": 2})
    assert program.execute(context) == 2


def test_repeated_and_alternating_prepared_bindings():
    context = cel.Context()
    one = cel.prepare({"value": 1})
    two = cel.prepare({"value": 2})
    program = cel.compile("data.value")

    for prepared, expected in [(one, 1), (one, 1), (two, 2), (one, 1), (two, 2)]:
        context.add_variable("data", prepared)
        assert program.execute(context) == expected


def test_replacing_one_variable_preserves_others():
    context = cel.Context()
    bind(context, "a", 1)
    bind(context, "b", 2)
    bind(context, "a", 40)
    assert cel.compile("a + b").execute(context) == 42


@pytest.mark.parametrize(
    "raw_value",
    [
        1,
        True,
        1.5,
        "value",
        b"value",
        [1],
        (1,),
        {"value": 1},
        datetime.datetime.now(),
        datetime.timedelta(seconds=1),
        cel.OptionalValue.none(),
    ],
)
def test_add_variable_rejects_raw_python_values(raw_value):
    with pytest.raises(TypeError):
        cel.Context().add_variable("value", raw_value)


def test_undefined_variable_is_an_execution_error():
    context = cel.Context()
    with pytest.raises(RuntimeError, match="Undefined variable"):
        cel.compile("missing").execute(context)


def test_function_registration_and_repeated_execution():
    calls = []

    def add(a, b):
        calls.append((a, b))
        return a + b

    context = cel.Context()
    context.add_function("add", add)
    bind(context, "data", {"left": 20, "right": 22})
    program = cel.compile("add(data.left, data.right)")

    assert program.execute(context) == 42
    assert program.execute(context) == 42
    assert calls == [(20, 22), (20, 22)]


def test_function_must_be_callable():
    with pytest.raises(TypeError, match="callable"):
        cel.Context().add_function("not_callable", 42)


def test_function_results_are_converted_to_cel():
    context = cel.Context()
    context.add_function("make", lambda: {"answer": [40, 42]})
    assert cel.compile("make().answer[1]").execute(context) == 42


def test_function_exceptions_become_execution_errors():
    def fail():
        raise ValueError("useful callback failure")

    context = cel.Context()
    context.add_function("fail", fail)
    with pytest.raises(RuntimeError, match="useful callback failure"):
        cel.compile("fail()").execute(context)


def test_nested_data_and_none():
    context = cel.Context()
    bind(
        context,
        "data",
        {
            "spec": {"nameserver": None, "host": "github.com"},
            "response": {"response-code": "NOERROR", "addresses": ["4.237.22.38"]},
        },
    )

    assert cel.compile("data.spec.nameserver").execute(context) is None
    assert cel.compile("data.spec.host").execute(context) == "github.com"
    assert cel.compile("data.response['response-code']").execute(context) == "NOERROR"
    assert cel.compile("size(data.response.addresses)").execute(context) == 1
