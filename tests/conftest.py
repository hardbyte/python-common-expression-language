import pytest

expressions = [
    "1 + 2",
    "1 > 2",
    "3 == 3",
    "3.14 * 2",
    ".456789 + 123e4",
    "[]",
    "[1, 2, 3]",
    "[1, 2, 3][1]",
    "size([1, 2, 3]) == 3",
    "{'a': 1, 'b': 2, 'c': 3}",
    "true ? 'result_true' : 'result_false'",
    "false ? 'result_true' : 'result_false'",
    "null",
    "'hello'",
    "b'hello'",
    "timestamp('1996-12-19T16:39:57-08:00')",
]


# Valid expressions fixture
@pytest.fixture(params=expressions)
def valid_simple_expression(request):
    return request.param


expression_context_pairs = [
    ["a + 2", {"a": 1}, 3],
    ["a > 2", {"a": 11.5}, True],
    ["a == 3", {"a": 3}, True],
    ["b * 2", {"b": 3.14}, 6.28],
    ["name", {"name": "alice"}, "alice"],
    ["a[1]", {"a": [1, 2, 3]}, 2],
]


# Valid expressions with context fixture
@pytest.fixture(params=expression_context_pairs)
def expression_context_result(request):
    return request.param
