"""Small compile/execute benchmark using the strict prepared-context API.

For the full 50/500/5,000-object benchmark, run
`prepared_context_benchmark.py` in this directory.
"""

import json
import statistics
import time
from collections.abc import Callable
from typing import Any

import cel


def bench(operation: Callable[[], Any], iterations: int = 5_000) -> dict[str, float]:
    samples = []
    for _ in range(3):
        operation()
        started = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        samples.append((time.perf_counter_ns() - started) / iterations)
    return {"median_ns": statistics.median(samples), "min_ns": min(samples)}


def make_context(**values: Any) -> cel.Context:
    context = cel.Context()
    for name, value in values.items():
        context.add_variable(name, cel.prepare(value))
    return context


def main() -> None:
    cases = [
        ("simple_arithmetic", "x + y * 2", make_context(x=10, y=20)),
        ("string_concat", "greet + ' ' + name", make_context(greet="hello", name="world")),
        ("list_size", "size(items)", make_context(items=list(range(1_000)))),
        (
            "map_lookup_bool",
            "user.role == 'admin' && user.active",
            make_context(user={"role": "admin", "active": True}),
        ),
    ]

    callback_context = make_context(x=21)
    callback_context.add_function("double_value", lambda value: value * 2)
    cases.append(("python_function", "double_value(x)", callback_context))

    results = {}
    for name, expression, context in cases:
        started = time.perf_counter_ns()
        program = cel.compile(expression)
        compile_ns = time.perf_counter_ns() - started
        results[name] = {
            "compile_ns": compile_ns,
            "compiled_execute": bench(
                lambda program=program, context=context: program.execute(context)
            ),
            "evaluate": bench(
                lambda expression=expression, context=context: cel.evaluate(expression, context)
            ),
        }

    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
