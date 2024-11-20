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

def test_context_vars_none_value():
    context = cel.Context({'a': None})
    assert cel.evaluate("a", context) == None


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

def test_nested_context_none():

    context = {
        'spec': {
            'type': 'dns',
            'nameserver': None,
            'host': 'github.com',
            'timeout': 30.0,
            'pattern': "\ndata['response-code'] == 'NOERROR' &&\nsize(data['A']) >= 1 && \n(timestamp(data["
        },
        'data': {
            'canonical_name': 'github.com.',
            'expiration': 1732097106.7902246,
            'response': 'id 25\nopcode QUERY\nrcode NOERROR\nflags QR RD RA\nedns 0\npayload 65494\n;QUESTION\ng',
            'A': ['4.237.22.38'],
            'response-code': 'NOERROR',
            'startTimestamp': '2024-11-20T10:04:59.789017+00:00',
            'endTimestamp': '2024-11-20T10:04:59.790298+00:00'
        }
    }

    context = cel.Context(variables=context)