# Python CEL - Common Expression Language

[![Documentation](https://img.shields.io/badge/docs-readthedocs-blue)](https://python-common-expression-language.readthedocs.io/)
[![PyPI version](https://badge.fury.io/py/common-expression-language.svg)](https://pypi.org/project/common-expression-language/)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

**Fast, Safe, and Expressive evaluation of Google's Common Expression Language (CEL) in Python, powered by Rust.**

The Common Expression Language (CEL) is a non-Turing complete language designed for simplicity, speed, and safety. This Python package wraps the Rust implementation [cel-interpreter](https://crates.io/crates/cel-interpreter) v0.10.0, providing microsecond-level expression evaluation with seamless Python integration.

## 🚀 Use Cases

- 🛡️ **Policy Enforcement**: Define access control rules that can be updated without code changes
- ⚙️ **Configuration Validation**: Validate complex settings with declarative rules  
- 🔄 **Data Transformation**: Transform and filter data with safe, portable expressions
- 📋 **Business Rules**: Implement decision logic that business users can understand
- 🔍 **Query Filtering**: Build dynamic filters for databases and APIs
- 🎯 **Feature Flags**: Create sophisticated feature toggle conditions

## Installation

```bash
pip install common-expression-language
```

Or using uv:
```bash
uv add common-expression-language
```

After installation, both the Python library and the `cel` command-line tool will be available.

> 📖 **Full Documentation**: https://python-common-expression-language.readthedocs.io/

## Quick Start

### Python API

```python
from cel import evaluate

# Simple expressions
result = evaluate("1 + 2")  # 3
result = evaluate("'Hello ' + 'World'")  # "Hello World"
result = evaluate("age >= 18", {"age": 25})  # True

# Complex expressions with context
result = evaluate(
    'user.role == "admin" && "write" in permissions',
    {
        "user": {"role": "admin"},
        "permissions": ["read", "write", "delete"]
    }
)  # True
```

### Command Line Interface

```bash
# Simple evaluation
cel '1 + 2'  # 3

# With context
cel 'age >= 18' --context '{"age": 25}'  # true

# Interactive REPL
cel --interactive
```

### Custom Functions

```python
from cel import Context, evaluate

def calculate_discount(price, rate):
    return price * rate

context = Context()
context.add_function("calculate_discount", calculate_discount)
context.add_variable("price", 100)

result = evaluate("price - calculate_discount(price, 0.1)", context)  # 90.0
```

### Real-World Example

```python
from cel import evaluate, Context

# Access control policy
policy = """
user.role == "admin" || 
(resource.owner == user.id && current_hour >= 9 && current_hour <= 17)
"""

context = Context()
context.update({
    "user": {"id": "alice", "role": "user"},
    "resource": {"owner": "alice"},
    "current_hour": 14  # 2 PM
})

access_granted = evaluate(policy, context)  # True
```

## Features

- ✅ **Fast Evaluation**: Microsecond-level expression evaluation via Rust
- ✅ **Rich Type System**: Integers, floats, strings, lists, maps, timestamps, durations
- ✅ **Python Integration**: Seamless type conversion and custom function support
- ✅ **CLI Tools**: Interactive REPL and batch processing capabilities
- ✅ **Safety First**: Non-Turing complete, safe for untrusted expressions

## Documentation

📚 **Complete documentation available at**: https://python-common-expression-language.readthedocs.io/


### Building Documentation Locally

To build and serve the documentation locally:

```bash
# Install documentation dependencies
uv sync --group docs

# Build the documentation
uv run --group docs mkdocs build

# Serve locally with live reload
uv run --group docs mkdocs serve
```

The documentation will be available at http://localhost:8000

## Development

### Testing

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=cel

# Test all documentation examples (embedded code + standalone files)
uv run --group docs pytest tests/test_docs.py -v
```

### Building from Source

```bash
# Install development dependencies
uv sync --dev

# Build the package
uv run maturin develop

# Run tests
uv run pytest
```

## Contributing

Contributions are welcome! Please see our [documentation](https://python-common-expression-language.readthedocs.io/) for:
- [CEL compliance status](docs/reference/cel-compliance.md)
- Development setup and guidelines
- Areas where help is needed

## License

This project is licensed under the same terms as the original cel-interpreter crate.

## Resources

- [📖 **Documentation**](https://python-common-expression-language.readthedocs.io/)
- [🌐 **CEL Homepage**](https://cel.dev/)
- [📋 **CEL Specification**](https://github.com/google/cel-spec)
- [⚙️ **cel-interpreter Rust crate**](https://crates.io/crates/cel-interpreter)