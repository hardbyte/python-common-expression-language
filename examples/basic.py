import cel
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

for ex in expressions:
    result = cel.evaluate(ex)
    print(ex, '=>', result, type(result))

