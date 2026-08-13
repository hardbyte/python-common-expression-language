import cel


def test_reduce_macro_via_compile_execute():
    program = cel.compile("[1, 2, 3, 4].reduce(acc, x, 0, acc + x)")

    assert program.execute(cel.Context()) == 10
