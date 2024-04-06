import cel
expression_context_pairs = [
    ["a + 2", { 'a': 1 }],
    ["a > 2", { 'a': 11.5 }],
    ["a == 3", { 'a': 3 }],
    ["b * 2", { 'b': 3.14 }],
    ["name", { 'name': "alice" }],
    ["a[1]", { 'a': [1, 2, 3] }],
]


for ex, context in expression_context_pairs:
    print(f"Evaluating '{ex}' with context {context} => {cel.evaluate(ex, context)}")

