"""Free-threaded CPython (``python3.14t``) support.

The extension declares that it does not need the GIL (PyO3's ``gil_used = false``)
and free-threaded wheels are published, so these tests pin the two things that
declaration commits us to: importing the module must not make CPython re-enable
the GIL, and sharing objects between threads must never corrupt state. Most of
the file also runs on a regular build, where it documents the same contract.
"""

import os
import subprocess
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor

import cel
import pytest

FREE_THREADED_BUILD = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))

requires_free_threaded = pytest.mark.skipif(
    not FREE_THREADED_BUILD, reason="only meaningful on a free-threaded CPython build"
)


@requires_free_threaded
def test_suite_runs_with_the_gil_disabled():
    """Sanity check for CI: the free-threaded leg really is exercising the GIL-free path.

    CI sets ``PYTHON_GIL=0`` for that leg so a dependency lacking the free-threading
    declaration cannot quietly turn the GIL back on for the whole run.
    """
    assert not sys._is_gil_enabled()


@requires_free_threaded
def test_importing_cel_does_not_reenable_the_gil():
    """Without ``PYTHON_GIL`` forcing the matter, importing ``cel`` alone must leave the GIL off.

    A module that has not declared free-threading support makes CPython re-enable
    the GIL at import and emit a RuntimeWarning naming the module. Run in a fresh
    interpreter so nothing else imported by the test session can mask the result,
    and turn warnings into errors so the RuntimeWarning is loud.
    """
    env = {k: v for k, v in os.environ.items() if k != "PYTHON_GIL"}
    script = (
        "import sys, warnings\n"
        "warnings.simplefilter('error')\n"
        "import cel\n"
        "assert cel.evaluate('1 + 1') == 2\n"
        "assert not sys._is_gil_enabled(), 'importing cel re-enabled the GIL'\n"
    )
    subprocess.run([sys.executable, "-c", script], env=env, check=True, timeout=60)


def test_program_is_immutable():
    """``Program`` is a frozen class, so sharing one between threads needs no locking."""
    program = cel.compile("x + 1")
    with pytest.raises(AttributeError):
        program.source = "y"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        program.anything = 1  # type: ignore[attr-defined]


def test_optional_value_is_immutable():
    opt = cel.OptionalValue.of(1)
    with pytest.raises(AttributeError):
        opt.anything = 1  # type: ignore[attr-defined]


def test_concurrent_mutation_raises_rather_than_races():
    """Mutating one ``Context`` from several threads is unsupported but never unsafe.

    Readers see a consistent snapshot on every evaluation. A writer that collides
    with another borrow of the same ``Context`` gets PyO3's ``RuntimeError: Already
    borrowed`` (only reachable on a free-threaded build); it never corrupts the
    context. Whatever interleaving happens, every value observed must be one that
    some writer actually stored.
    """
    ctx = cel.Context({"v": 0})
    program = cel.compile("v")
    rounds = 500

    def writer(_):
        for n in range(rounds):
            try:
                ctx.add_variable("v", n)
            except RuntimeError as exc:
                assert "borrowed" in str(exc).lower(), exc

    def reader(_):
        for _ in range(rounds):
            try:
                result = program.execute(ctx)
            except RuntimeError as exc:
                assert "borrowed" in str(exc).lower(), exc
                continue
            assert isinstance(result, int) and 0 <= result < rounds, result

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(writer if i % 2 else reader, i) for i in range(8)]
        for future in futures:
            future.result()

    assert 0 <= ctx.variables["v"] < rounds


def test_shared_program_and_context_across_threads_agree():
    """Many threads evaluating one frozen ``Program`` against one ``Context`` all get the same answer."""
    ctx = cel.Context({"items": list(range(200))})
    ctx.add_function("bump", lambda n: n + 1)
    program = cel.compile("bump(items.filter(i, i % 2 == 0).size())")

    def work(_):
        return [program.execute(ctx) for _ in range(200)]

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(work, range(8)))

    assert all(result == [101] * 200 for result in results)
