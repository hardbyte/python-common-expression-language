import datetime

import cel
import pytest


def context(**variables):
    result = cel.Context()
    for name, value in variables.items():
        result.add_variable(name, cel.prepare(value))
    return result


class TestCompileBasics:
    def test_compile_and_execute(self):
        program = cel.compile("1 + 2")
        assert program.execute(context()) == 3

    def test_compile_returns_program(self):
        assert isinstance(cel.compile("true"), cel.Program)

    def test_program_repr(self):
        assert repr(cel.compile("x + y")) == 'Program("x + y")'

    @pytest.mark.parametrize("argument", [None, {}, cel.prepare(1), object()])
    def test_execute_rejects_non_context_arguments(self, argument):
        with pytest.raises(TypeError):
            cel.compile("42").execute(argument)

    def test_execute_requires_exactly_one_argument(self):
        program = cel.compile("42")
        with pytest.raises(TypeError):
            program.execute()
        with pytest.raises(TypeError):
            program.execute(context(), context())

    def test_program_exposes_one_execution_method(self):
        program = cel.compile("42")
        execution_methods = [name for name in dir(program) if name.startswith("execute")]
        assert execution_methods == ["execute"]


class TestCompileWithContext:
    def test_execute_with_variables(self):
        program = cel.compile("name + ' is ' + string(age)")
        assert program.execute(context(name="Alice", age=30)) == "Alice is 30"

    def test_reuse_program_with_multiple_contexts(self):
        program = cel.compile("price * quantity")
        assert program.execute(context(price=10, quantity=5)) == 50
        assert program.execute(context(price=25, quantity=4)) == 100

    def test_nested_dot_and_index_selection(self):
        ctx = context(
            data={
                "objects": [
                    {"active": False, "profile": {"enabled": False}},
                    {"active": True, "profile": {"enabled": True}},
                ]
            }
        )
        assert cel.compile("data.objects[1].profile.enabled").execute(ctx) is True
        assert cel.compile("data['objects'][1].active").execute(ctx) is True

    def test_fixed_index_primitive_predicate(self):
        objects = [
            {"active": index % 2 == 0, "score": index, "padding": list(range(100))}
            for index in range(10)
        ]
        assert (
            cel.compile("data.objects[3].active || data.objects[3].score >= 3").execute(
                context(data={"objects": objects})
            )
            is True
        )


class TestCompileWithFunctions:
    def test_selected_primitive_arguments(self):
        ctx = context(data={"left": 20, "right": 22})
        ctx.add_function("add", lambda left, right: left + right)
        assert cel.compile("add(data.left, data.right)").execute(ctx) == 42

    def test_multiple_functions(self):
        ctx = context(x=3, y=4)
        ctx.add_function("add", lambda a, b: a + b)
        ctx.add_function("multiply", lambda a, b: a * b)
        assert cel.compile("add(x, y) + multiply(x, y)").execute(ctx) == 19


class TestCompileResults:
    @pytest.mark.parametrize(
        ("expression", "expected"),
        [
            ("true", True),
            ("42", 42),
            ("3.5", 3.5),
            ("'hello'", "hello"),
            ("null", None),
            ("b'hello'", b"hello"),
            ("[1, 2, 3]", [1, 2, 3]),
            ("{'answer': 42}", {"answer": 42}),
        ],
    )
    def test_result_types(self, expression, expected):
        assert cel.compile(expression).execute(context()) == expected

    def test_timestamp_and_duration(self):
        timestamp = cel.compile("timestamp('2024-01-01T00:00:00Z')").execute(context())
        duration = cel.compile("duration('1h30m')").execute(context())
        assert isinstance(timestamp, datetime.datetime)
        assert duration == datetime.timedelta(seconds=5400)

    def test_returning_prepared_map_and_list_remains_correct(self):
        data = {"map": {"answer": 42}, "list": [1, 2, 3]}
        ctx = context(data=data)
        assert cel.compile("data.map").execute(ctx) == data["map"]
        assert cel.compile("data.list").execute(ctx) == data["list"]


class TestSelectionSemantics:
    def test_missing_key_and_out_of_range(self):
        ctx = context(data={"items": [1], "record": {"present": True}})
        with pytest.raises(ValueError, match="No such key"):
            cel.compile("data.record.missing").execute(ctx)
        with pytest.raises(ValueError, match="Index out of bounds"):
            cel.compile("data.items[5]").execute(ctx)

    def test_has(self):
        ctx = context(data={"record": {"present": True}})
        assert cel.compile("has(data.record.present)").execute(ctx) is True
        assert cel.compile("has(data.record.missing)").execute(ctx) is False

    def test_optional_values_remain_usable_with_prepared_contexts(self):
        ctx = context(value=cel.OptionalValue.of(42), missing=cel.OptionalValue.none())
        assert cel.compile("value.orValue(0)").execute(ctx) == 42
        assert cel.compile("missing.orValue(0)").execute(ctx) == 0

    def test_selection_from_owned_temporary(self):
        ctx = context()
        assert cel.compile("{'profile': {'enabled': true}}.profile.enabled").execute(ctx) is True
        assert cel.compile("[{'enabled': true}][0].enabled").execute(ctx) is True


class TestCompileErrors:
    @pytest.mark.parametrize("expression", ["1 + + 2", ""])
    def test_compile_invalid_syntax(self, expression):
        with pytest.raises(ValueError, match="Failed to parse"):
            cel.compile(expression)

    def test_execute_undefined_variable(self):
        with pytest.raises(RuntimeError):
            cel.compile("undefined_var + 1").execute(context())

    def test_execute_type_error(self):
        with pytest.raises(TypeError):
            cel.compile("x + y").execute(context(x="hello", y=42))


class TestEvaluate:
    def test_evaluate_uses_context(self):
        assert cel.evaluate("x + y", context(x=20, y=22)) == 42

    @pytest.mark.parametrize("argument", [None, {}, cel.prepare(1), object()])
    def test_evaluate_rejects_non_context_arguments(self, argument):
        with pytest.raises(TypeError):
            cel.evaluate("42", argument)

    def test_evaluate_requires_context(self):
        with pytest.raises(TypeError):
            cel.evaluate("42")
