import datetime

import pytest

import cel

def test_invalid_expression_raises_parse_value_error():
    with pytest.raises(ValueError):
        result = cel.evaluate("1 +")


def test_hello_world():
    assert cel.evaluate("'Hello ' + name", {'name': "World"}) == "Hello World"

def test_calc():
    assert cel.evaluate("1 + 1") == 2

def test_return_bool():
    assert cel.evaluate("1 == 1") == True

def test_return_list():
    assert cel.evaluate("[1, 1]") == [1, 1]

def test_return_dict():
    assert cel.evaluate("foo", {'foo': {'bar': 2}}) == {'bar': 2}

def test_return_null():
    assert cel.evaluate("null") == None

def test_timestamp():
    assert cel.evaluate("timestamp('1996-12-19T16:39:57-08:00')") == datetime.datetime(1996, 12, 19, 16, 39, 57, tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=57600)))

def test_timestamp_utc():
    result = cel.evaluate("timestamp('1996-12-19T16:39:57-08:00')")
    expected = datetime.datetime(1996, 12, 20, 0, 39, 57, tzinfo=datetime.timezone.utc)
    assert result == expected


def test_duration():
    assert cel.evaluate("duration('24h')") == datetime.timedelta(hours=24)


def test_timestamp_context_with_timezone():
    now = datetime.datetime.now(datetime.timezone.utc)
    assert cel.evaluate("now", {'now': now}) == now


def test_timestamp_context_without_timezone():
    now = datetime.datetime.now()
    assert cel.evaluate("now", {'now': now})

def test_size():
    assert cel.evaluate("size([1, 2, 3])") == 3

def test_basic_expressions_evaluate(valid_simple_expression):
    result = cel.evaluate(valid_simple_expression)
    assert type(result) in (int, float, str, bytes, bool, list, dict, type(None), datetime.datetime)


def test_expressions_with_context(expression_context_result):
    expression, context, expected_result = expression_context_result
    result = cel.evaluate(expression, context)
    assert result == expected_result


def test_str_context_expression():
    result = cel.evaluate("word[1]", {"word": "hello"})
    assert result == 'e'


def test_list_context_expression():
    result = cel.evaluate("foo[1]", {"foo": [1, 2, 3]})
    assert result == 2


def test_dict_context_expression():
    result = cel.evaluate("foo['bar']", {"foo": {'bar': 2}})
    assert result == 2

def test_tuple_context_expression():
    result = cel.evaluate("foo[1]", {"foo": (2, 3, 4)})
    assert result == 3


@pytest.mark.xfail()
def test_bytes_context_expression():
    result = cel.evaluate("data[1]", {"data": b'hello'})
    assert result == 2


def test_nested_context_expression():
    result = cel.evaluate('resource.name.startsWith("/groups/" + claim.group)', {
        "resource": {"name": "/groups/hardbyte"},
        "claim": {"group": "hardbyte"}
    })
    assert result == True
