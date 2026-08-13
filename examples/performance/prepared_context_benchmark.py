"""Benchmark preparation, prepared binding, and direct context execution.

Build the extension in release mode first:

    uv run maturin develop --release
    uv run python examples/performance/prepared_context_benchmark.py
"""

import json
import statistics
import time
from collections.abc import Callable
from typing import Any

import cel

OBJECT_COUNTS = (50, 500, 5_000)
ITERATIONS = 100_000
EXPRESSIONS = {
    "nested_bool": "data.objects[3].profile.enabled",
    "primitive_predicate": "data.objects[3].active && data.objects[3].score >= 3",
}


def fixture(object_count: int) -> dict[str, Any]:
    return {
        "objects": [
            {
                "id": index,
                "active": index % 2 == 0,
                "score": index,
                "profile": {"enabled": True, "padding": list(range(20))},
            }
            for index in range(object_count)
        ]
    }


def benchmark(operation: Callable[[], Any], iterations: int, repeats: int = 5) -> dict[str, float]:
    samples = []
    for _ in range(repeats):
        for _ in range(1_000):
            operation()
        started = time.perf_counter_ns()
        for _ in range(iterations):
            operation()
        samples.append((time.perf_counter_ns() - started) / iterations)
    return {
        "median_ns": statistics.median(samples),
        "min_ns": min(samples),
        "max_ns": max(samples),
    }


def main() -> None:
    report: dict[str, Any] = {}
    for object_count in OBJECT_COUNTS:
        source = fixture(object_count)

        started = time.perf_counter_ns()
        prepared = cel.prepare(source)
        preparation_ns = time.perf_counter_ns() - started

        context = cel.Context()
        started = time.perf_counter_ns()
        context.add_variable("data", prepared)
        first_insertion_ns = time.perf_counter_ns() - started

        case: dict[str, Any] = {
            "preparation_ns": preparation_ns,
            "first_insertion_ns": first_insertion_ns,
            "replacement": benchmark(
                lambda context=context, prepared=prepared: context.add_variable("data", prepared),
                ITERATIONS,
            ),
            "expressions": {},
        }
        for name, expression in EXPRESSIONS.items():
            program = cel.compile(expression)
            case["expressions"][name] = {
                "execute": benchmark(
                    lambda program=program, context=context: program.execute(context), ITERATIONS
                ),
                "replace_and_execute": benchmark(
                    lambda context=context, prepared=prepared, program=program: (
                        context.add_variable("data", prepared),
                        program.execute(context),
                    ),
                    ITERATIONS,
                ),
            }

        callback_context = cel.Context()
        callback_context.add_variable("data", prepared)
        callback_context.add_function("enabled", lambda value: value)
        callback_program = cel.compile("enabled(data.objects[3].profile.enabled)")
        case["selected_primitive_callback"] = benchmark(
            lambda callback_program=callback_program, callback_context=callback_context: (
                callback_program.execute(callback_context)
            ),
            ITERATIONS,
        )
        report[str(object_count)] = case

    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
