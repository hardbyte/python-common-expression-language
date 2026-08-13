import datetime

import cel
import pytest
from conftest import evaluate


def test_readme_example():
    assert evaluate(
        'resource.name.startsWith("/groups/" + claim.group)',
        {"resource": {"name": "/groups/hardbyte"}, "claim": {"group": "hardbyte"}},
    )


def test_return_bool():
    assert evaluate("1 == 1")


def test_return_list():
    assert evaluate("[1, 1]") == [1, 1]


def test_return_dict():
    assert evaluate("foo", {"foo": {"bar": 2}}) == {"bar": 2}


def test_return_null():
    assert evaluate("null") is None


def test_timestamp():
    assert evaluate("timestamp('1996-12-19T16:39:57-08:00')") == datetime.datetime(
        1996,
        12,
        19,
        16,
        39,
        57,
        tzinfo=datetime.timezone(datetime.timedelta(days=-1, seconds=57600)),
    )


def test_timestamp_utc():
    result = evaluate("timestamp('1996-12-19T16:39:57-08:00')")
    expected = datetime.datetime(1996, 12, 20, 0, 39, 57, tzinfo=datetime.timezone.utc)
    assert result == expected


def test_duration():
    assert evaluate("duration('24h')") == datetime.timedelta(hours=24)


def test_timestamp_context_with_timezone():
    now = datetime.datetime.now(datetime.timezone.utc)
    assert evaluate("now", {"now": now}) == now


def test_timestamp_add_duration():
    now = datetime.datetime.now(datetime.timezone.utc)
    result = evaluate("start_time + duration('1h')", {"start_time": now})
    assert result == now + datetime.timedelta(hours=1)


def test_timestamp_context_without_timezone():
    now = datetime.datetime.now()
    assert evaluate("now", {"now": now})


def test_size():
    assert evaluate("size([1, 2, 3])") == 3


def test_basic_expressions_evaluate(valid_simple_expression):
    result = evaluate(valid_simple_expression)
    assert type(result) in (int, float, str, bytes, bool, list, dict, type(None), datetime.datetime)


def test_expressions_with_context(expression_context_result):
    expression, context, expected_result = expression_context_result
    result = evaluate(expression, context)
    assert result == expected_result


@pytest.mark.xfail(
    reason="String indexing not supported in cel-interpreter 0.11.x - see test_upstream_improvements.py",
    strict=True,
)
def test_str_context_expression():
    """Test string indexing - currently not supported by cel-interpreter."""
    result = evaluate("word[1]", {"word": "hello"})
    assert result == "e"


def test_list_context_expression():
    result = evaluate("foo[1]", {"foo": [1, 2, 3]})
    assert result == 2


def test_dict_context_expression():
    result = evaluate("foo['bar']", {"foo": {"bar": 2}})
    assert result == 2


def test_tuple_context_expression():
    result = evaluate("foo[1]", {"foo": (2, 3, 4)})
    assert result == 3


def test_bytes_size():
    result = evaluate("size(b'hello')")
    assert result == 5


def test_bytes_inequality():
    result = evaluate("b'hello' != b'world'")
    assert result


def test_bytes_equality_via_context():
    result = evaluate("b'hello' == foo", {"foo": b"hello"})
    assert result


def test_bytes_string_conversion():
    """Test bytes <-> string conversion functions that ARE supported by CEL"""
    # Convert string to bytes
    result = evaluate('bytes("hello")')
    assert result == b"hello"

    # Convert bytes to string
    result = evaluate('string(b"hello")')
    assert result == "hello"
