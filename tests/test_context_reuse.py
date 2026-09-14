"""Behavioural contract for reusing a ``cel.Context`` across evaluations.

A ``Context`` builds its CEL-side environment (converted variables and wrapped
Python functions) once and reuses it for every ``evaluate()``/``execute()``
call until it is modified. These tests pin the observable consequences: every
mutator is visible on the next evaluation, a callback may modify the context it
is running under, evaluation is re-entrant, and a single context can be shared
between threads.
"""

from concurrent.futures import ThreadPoolExecutor

import cel
import pytest
from cel import Context
from cel.stdlib import add_stdlib_to_context


class TestMutationsInvalidateTheCache:
    def test_add_variable_after_first_evaluation(self):
        ctx = Context({"a": 1})
        program = cel.compile("a + b")
        with pytest.raises(RuntimeError, match="Undefined variable"):
            program.execute(ctx)

        ctx.add_variable("b", 2)
        assert program.execute(ctx) == 3

    def test_overwrite_variable_after_first_evaluation(self):
        ctx = Context({"counter": 1})
        assert cel.evaluate("counter", ctx) == 1
        ctx.add_variable("counter", 2)
        assert cel.evaluate("counter", ctx) == 2

    def test_add_function_after_first_evaluation(self):
        ctx = Context({"x": 21})
        assert cel.evaluate("x", ctx) == 21
        with pytest.raises(RuntimeError, match="Undefined variable or function"):
            cel.evaluate("twice(x)", ctx)

        ctx.add_function("twice", lambda v: v * 2)
        assert cel.evaluate("twice(x)", ctx) == 42

    def test_replace_function_after_first_evaluation(self):
        ctx = Context(functions={"f": lambda: "first"})
        assert cel.evaluate("f()", ctx) == "first"
        ctx.add_function("f", lambda: "second")
        assert cel.evaluate("f()", ctx) == "second"

    def test_update_after_first_evaluation(self):
        ctx = Context({"a": 1})
        assert cel.evaluate("a", ctx) == 1
        ctx.update({"a": 10, "b": 5, "add": lambda x, y: x + y})
        assert cel.evaluate("add(a, b)", ctx) == 15

    def test_resolver_set_after_first_evaluation(self):
        ctx = Context({"static_var": 1})
        assert cel.evaluate("static_var", ctx) == 1
        with pytest.raises(RuntimeError, match="Undefined variable"):
            cel.evaluate("dynamic_var", ctx)

        ctx.set_variable_resolver(lambda name: 99 if name == "dynamic_var" else None)
        assert cel.evaluate("dynamic_var", ctx) == 99
        # The resolver is consulted first, then registered variables.
        assert cel.evaluate("static_var", ctx) == 1

    def test_resolver_shadows_registered_variable(self):
        """The resolver keeps precedence over add_variable() values, as documented."""
        ctx = Context({"x": "static"})
        ctx.set_variable_resolver(lambda name: "resolved" if name == "x" else None)
        assert cel.evaluate("x", ctx) == "resolved"

    def test_replacing_resolver_takes_effect(self):
        ctx = Context()
        ctx.set_variable_resolver(lambda name: 1)
        assert cel.evaluate("anything", ctx) == 1
        ctx.set_variable_resolver(lambda name: 2)
        assert cel.evaluate("anything", ctx) == 2


class TestReuseAcrossCalls:
    def test_same_context_serves_many_programs(self):
        ctx = Context({"price": 10, "quantity": 5})
        ctx.add_function("discount", lambda total, rate: total * rate)
        assert cel.compile("price * quantity").execute(ctx) == 50
        assert cel.compile("discount(price * quantity, 0.5)").execute(ctx) == 25.0
        assert cel.evaluate("quantity > 3", ctx) is True

    def test_many_executions_return_consistent_results(self):
        ctx = Context({"items": list(range(100))})
        add_stdlib_to_context(ctx)
        program = cel.compile("size(items.filter(i, i % 2 == 0)) + math.abs(-1)")
        assert [program.execute(ctx) for _ in range(200)] == [51] * 200

    def test_functions_and_resolver_together(self):
        ctx = Context()
        ctx.add_function("shout", lambda s: s.upper() + "!")
        ctx.set_variable_resolver(lambda name: {"greeting": "hi"}.get(name))
        assert cel.evaluate("shout(greeting)", ctx) == "HI!"

    def test_dict_context_still_accepts_callables(self):
        """Dict contexts are rebuilt per call, and keep sorting callables into functions."""
        program = cel.compile("twice(x)")
        assert program.execute({"x": 2, "twice": lambda v: v * 2}) == 4
        assert program.execute({"x": 5, "twice": lambda v: v * 2}) == 10


class TestReentrancy:
    def test_callback_may_mutate_the_context_it_runs_under(self):
        """A function registered on a context can modify that same context.

        The change is not visible to the evaluation already in progress (it runs
        against a snapshot) but is visible to the next one.
        """
        ctx = Context({"n": 1})

        def bump():
            ctx.add_variable("n", 100)
            return "bumped"

        ctx.add_function("bump", bump)
        assert cel.evaluate("[bump(), string(n)]", ctx) == ["bumped", "1"]
        assert cel.evaluate("n", ctx) == 100

    def test_callback_may_evaluate_with_the_same_context(self):
        ctx = Context({"base": 40})

        def nested():
            return cel.evaluate("base + 1", ctx)

        ctx.add_function("nested", nested)
        assert cel.evaluate("nested() + 1", ctx) == 42

    def test_callback_may_execute_a_program_with_the_same_context(self):
        ctx = Context({"depth": 0})
        inner = cel.compile("depth + 1")

        ctx.add_function("inner", lambda: inner.execute(ctx))
        assert cel.compile("inner() * 2").execute(ctx) == 2


class TestThreads:
    def test_shared_context_across_threads(self):
        ctx = Context({"x": 3, "y": 4})
        ctx.add_function("hyp", lambda a, b: (a * a + b * b) ** 0.5)
        program = cel.compile("hyp(x, y) + double(x)")

        def work(_):
            return [program.execute(ctx) for _ in range(100)]

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(work, range(8)))

        assert all(result == [8.0] * 100 for result in results)

    def test_mutation_from_one_thread_is_seen_by_others(self):
        ctx = Context({"v": 1})
        assert cel.evaluate("v", ctx) == 1

        def mutate():
            ctx.add_variable("v", 2)

        with ThreadPoolExecutor(max_workers=1) as pool:
            pool.submit(mutate).result()

        assert cel.evaluate("v", ctx) == 2
