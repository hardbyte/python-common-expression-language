"""Parsing releases the GIL.

``cel.compile()`` and the parse inside ``cel.evaluate()`` run with the GIL
released for expressions of 32 bytes or more, so other Python threads make
progress while an expression is parsed. Shorter expressions parse in a few
microseconds, comparable to the cost of re-acquiring a contended GIL, so they keep
it. Execution of a compiled program still holds the GIL (see issue #45 for why: a
sub-microsecond evaluation loses badly to the cost of re-acquiring a contended
GIL, and a work-aware gate for execution is a separate change).

The tests below detect release by *overlap* rather than by speed: a spinning
thread counts iterations while the main thread parses. With the GIL held for the
whole parse the spinner cannot run and the count stays at essentially zero; with
it released the spinner gets a core and the count climbs into the millions. That
is a binary signal, so it does not depend on the runner's core count or load.
"""

import sys
import sysconfig
import threading

import cel
import pytest

# A list literal parses in time linear in its length; 20,000 elements is a few
# hundred milliseconds of pure parsing, long enough for the spinner to show up.
BIG_EXPRESSION = "[" + ", ".join(str(i) for i in range(20_000)) + "]"

# On a free-threaded build the spinner runs regardless, so overlap proves nothing;
# the contract there is simply "still works", covered by the whole suite.
requires_gil_build = pytest.mark.skipif(
    sys.implementation.name != "cpython" or bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
    reason="overlap is only observable on a CPython build with a GIL",
)


def ticks_during(action):
    """Run ``action`` on this thread while another thread spins; return the spinner's count."""
    ticks = 0
    started = threading.Event()
    stop = threading.Event()

    def spin():
        nonlocal ticks
        started.set()
        while not stop.is_set():
            ticks += 1

    spinner = threading.Thread(target=spin)
    spinner.start()
    started.wait()
    # Let the spinner settle so a switch-interval handoff right at the start does
    # not count as overlap.
    threading.Event().wait(0.02)
    before = ticks
    action()
    after = ticks
    stop.set()
    spinner.join()
    return after - before


@requires_gil_build
def test_compile_releases_the_gil():
    assert ticks_during(lambda: cel.compile(BIG_EXPRESSION)) > 10_000


@requires_gil_build
def test_evaluate_releases_the_gil_while_parsing():
    assert ticks_during(lambda: cel.evaluate(BIG_EXPRESSION)) > 10_000


def test_parse_results_are_unchanged():
    """Detaching changes where the parse runs, not what it produces or raises.

    Covers both sides of the length threshold: short expressions parse attached,
    long ones detached, and errors surface identically from either path.
    """
    assert cel.compile("1 + 2").execute() == 3
    assert cel.evaluate(BIG_EXPRESSION)[-1] == 19_999
    long_policy = 'user.role == "admin" || (resource.owner == user.id && size(user.groups) > 0)'
    assert len(long_policy) >= 32
    assert cel.evaluate(long_policy, {"user": {"role": "admin"}, "resource": {}}) is True
    with pytest.raises(ValueError, match="Failed to parse"):
        cel.compile("1 +")
    with pytest.raises(ValueError, match="Failed to parse"):
        cel.evaluate("'unterminated")
    with pytest.raises(ValueError, match="Failed to parse"):
        cel.compile(
            "this is a long enough expression to be parsed detached but it is not valid CEL !!"
        )


def test_concurrent_compiles_are_independent():
    """Many threads parsing at once each get their own correct program."""
    from concurrent.futures import ThreadPoolExecutor

    def work(i):
        return cel.compile(f"{i} * 2 + 1").execute()

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(work, range(400)))

    assert results == [i * 2 + 1 for i in range(400)]
