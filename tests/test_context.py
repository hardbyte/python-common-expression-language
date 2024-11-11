import pytest
import cel




def test_create_empty_context():
    context = cel.Context()


def test_context_vars_explicit():
    context = cel.Context(variables={'a': 10})
    assert cel.evaluate("a", context) == 10

def test_context_vars_implicit():
    context = cel.Context({'a': 10})
    assert cel.evaluate("a", context) == 10


def test_adding_to_context():
    context = cel.Context()

    with pytest.raises(ValueError):
        assert cel.evaluate("a + 2", context) == 4

    context.add_variable('a', 2)
    assert cel.evaluate("a + 2", context) == 4


def test_explicit_context():
    context = cel.Context()
    context.add_variable('a', 2)
    assert cel.evaluate("a + 2", context) == 4


def test_custom_function_init_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context(functions={'f': custom_function})

    assert cel.evaluate("f(1, 2)", context) == 3


def test_context_init_vars_and_funcs():
    def custom_function(a, b):
        return a + b

    context = cel.Context({'a': 10}, functions={'f': custom_function})

    assert cel.evaluate("f(a, 2)", context) == 12



def test_custom_function_with_explicit_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context()
    context.add_function('custom_function', custom_function)
    assert cel.evaluate("custom_function(1, 2)", context) == 3



def test_updating_explicit_context():
    def custom_function(a, b):
        return a + b

    context = cel.Context()
    context.update({
        'custom_function': custom_function,
        'a': 40,
        'b': 2,
    })
    assert cel.evaluate("custom_function(a, b)", context) == 42
