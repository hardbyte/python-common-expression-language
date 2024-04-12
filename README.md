
# Common Expression Language (CEL)

The Common Expression Language (CEL) is a non-Turing complete language designed for simplicity, 
speed, and safety. CEL is primarily used for evaluating expressions in a variety of applications,
such as policy evaluation, state machine transitions, and graph traversals.

This Python package wraps the Rust implementation [cel-interpreter](https://crates.io/crates/cel-interpreter).

Install from PyPI:
```
pip install common-expression-language
```

Basic usage:

```python
from cel import evaluate
expression = "age > 21"
result = evaluate(expression, {"age": 18})
print(result)  # False
```

Simply pass the CEL expression and a dictionary of context to the `evaluate` function. The function
returns the result of the expression evaluation converted to Python primitive types.

CEL supports a variety of operators, functions, and types

```python
evaluate(
    'resource.name.startsWith("/groups/" + claim.group)', 
    {
        "resource": {"name": "/groups/hardbyte"},
        "claim": {"group": "hardbyte"}
    }
)
```
## Future work

Support for converting Python datetime objects and timedeltas into CEL types.

### Command line interface

The package (plans to) provides a command line interface for evaluating CEL expressions:

```bash
$ python -m cel '1 + 2'
3
```

### Separate compilation and Execution steps
### Custom Python Functions

Ability to add Python functions to the Context object:

```python
from cel import evaluate, Context

def is_adult(age):
    return age > 21

context = Context()
context.add_function("is_adult", is_adult)
print(evaluate("is_adult(age)", {"age": 18}, context))  # False
```
