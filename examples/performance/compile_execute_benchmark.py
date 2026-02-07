"""Compare evaluate() vs compile()+execute() performance.

Run:
  uv run python examples/performance/compile_execute_benchmark.py
"""

import json
import statistics
import time
from typing import Any, Callable

import cel


def bench_case(
    func: Callable[[], Any], iterations: int = 5000, repeats: int = 3
) -> dict[str, float | int]:
    times = []
    for _ in range(repeats):
        func()
        start = time.perf_counter()
        for _i in range(iterations):
            func()
        end = time.perf_counter()
        times.append((end - start) / iterations * 1_000_000)  # us
    avg = statistics.mean(times)
    stdev = statistics.stdev(times) if len(times) > 1 else 0.0
    return {
        "avg_us": avg,
        "stdev_us": stdev,
        "min_us": min(times),
        "max_us": max(times),
        "iterations": iterations,
        "repeats": repeats,
    }


def measure_compile(expr: str) -> tuple[cel.Program, float]:
    start = time.perf_counter()
    program = cel.compile(expr)
    end = time.perf_counter()
    return program, (end - start) * 1_000_000


def main() -> None:
    results: dict[str, dict[str, Any]] = {}

    cases: list[tuple[str, str, Any]] = []

    ctx_simple: dict[str, Any] = {"x": 10, "y": 20}
    ctx_str: dict[str, Any] = {"greet": "hello", "name": "world"}
    ctx_list: dict[str, Any] = {"items": list(range(1000))}
    ctx_map: dict[str, Any] = {"user": {"role": "admin", "active": True}}

    cases.append(("simple_arithmetic", "x + y * 2", ctx_simple))
    cases.append(("string_concat", "greet + ' ' + name", ctx_str))
    cases.append(("list_size", "size(items)", ctx_list))
    cases.append(
        (
            "map_lookup_bool",
            "user.role == 'admin' && user.active",
            ctx_map,
        )
    )

    ctx_func = cel.Context()
    ctx_func.add_function("double", lambda x: x * 2)
    ctx_func.add_variable("x", 21)
    cases.append(("python_function", "double(x)", ctx_func))

    for name, expr, ctx in cases:
        program, compile_us = measure_compile(expr)

        eval_bench = bench_case(lambda expr=expr, ctx=ctx: cel.evaluate(expr, ctx))
        exec_bench = bench_case(lambda program=program, ctx=ctx: program.execute(ctx))

        speedup = eval_bench["avg_us"] / exec_bench["avg_us"] if exec_bench["avg_us"] > 0 else None

        results[name] = {
            "compile_time_us": compile_us,
            "evaluate": eval_bench,
            "compiled_execute": exec_bench,
            "speedup_eval_over_execute": speedup,
        }

    print(json.dumps(results, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
