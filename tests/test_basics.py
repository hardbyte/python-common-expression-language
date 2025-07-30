import datetime

import pytest

import cel

def test_invalid_expression_raises_parse_value_error():
    """Test that invalid expressions raise proper ValueError"""
    with pytest.raises(ValueError, match="Failed to parse expression"):
        result = cel.evaluate("1 +")


def test_readme_example():
    assert cel.evaluate(
        'resource.name.startsWith("/groups/" + claim.group)',
        {
            "resource": {"name": "/groups/hardbyte"},
            "claim": {"group": "hardbyte"}
        }
    )

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


def test_timestamp_add_duration():
    now = datetime.datetime.now(datetime.timezone.utc)
    cel.evaluate("start_time + duration('1h')", {'start_time': now}) == now + datetime.timedelta(hours=1)

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

def test_bytes_size():
    result = cel.evaluate("size(b'hello')")
    assert result == 5


def test_bytes_inequality():
    result = cel.evaluate("b'hello' != b'world'")
    assert result == True

def test_bytes_equality_via_context():
    result = cel.evaluate("b'hello' == foo", {'foo': b'hello'})
    assert result


@pytest.mark.xfail(reason="cel-interpreter 0.10.0 does not implement bytes concatenation (CEL spec requires it)")
def test_bytes_concatenation_context():
    """CEL spec requires bytes concatenation with + operator, but cel-interpreter 0.10.0 doesn't implement it"""
    part1 = b'hello'
    part2 = b'world'
    result = cel.evaluate("part1 + b' ' + part2", {"part1": part1, "part2": part2})
    assert result == b'hello world'


def test_bytes_concatenation_direct():
    """Test direct bytes concatenation (CEL spec requires this but cel-interpreter 0.10.0 doesn't support it)"""
    with pytest.raises(ValueError, match="Unsupported binary operator"):
        cel.evaluate("b'hello' + b'world'")


def test_bytes_string_conversion():
    """Test bytes <-> string conversion functions that ARE supported by CEL"""
    # Convert string to bytes
    result = cel.evaluate('bytes("hello")')
    assert result == b'hello'
    
    # Convert bytes to string
    result = cel.evaluate('string(b"hello")')
    assert result == "hello"


def test_bytes_concatenation_workaround():
    """Test workaround for bytes concatenation using string conversion"""
    part1 = b'hello'
    part2 = b'world'
    # Workaround: convert to strings, concatenate, then convert back to bytes
    result = cel.evaluate('bytes(string(part1) + " " + string(part2))', {"part1": part1, "part2": part2})
    assert result == b'hello world'


def test_nested_context_expression():
    result = cel.evaluate('resource.name.startsWith("/groups/" + claim.group)', {
        "resource": {"name": "/groups/hardbyte"},
        "claim": {"group": "hardbyte"}
    })
    assert result == True
