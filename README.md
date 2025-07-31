# Common Expression Language (CEL) for Python

The Common Expression Language (CEL) is a non-Turing complete language designed for simplicity, 
speed, and safety. CEL is primarily used for evaluating expressions in a variety of applications,
such as policy evaluation, state machine transitions, and graph traversals.

This Python package wraps the Rust implementation [cel-interpreter](https://crates.io/crates/cel-interpreter) v0.10.0, providing fast and safe CEL expression evaluation with seamless Python integration.

## Features

✅ **Core CEL Types**: Integers (signed/unsigned), floats, booleans, strings, bytes, lists, maps, null  
✅ **Arithmetic Operations**: `+`, `-`, `*`, `/`, `%` with mixed-type support  
✅ **Comparison Operations**: `==`, `!=`, `<`, `>`, `<=`, `>=`  
✅ **Logical Operations**: `&&`, `||`, `!` with short-circuit evaluation  
✅ **String Operations**: Concatenation, indexing, `startsWith()`, `size()`  
✅ **Collection Operations**: List/map indexing, `size()` function  
✅ **Datetime Support**: `timestamp()` and `duration()` functions  
✅ **Python Integration**: Custom functions, automatic type conversion  
✅ **Performance**: Microsecond-level expression evaluation  

📋 **Compliance**: ~65% of CEL specification (see [cel-compliance.md](cel-compliance.md) for details)

## Installation

```bash
pip install common-expression-language
```

Or using uv:
```bash
uv add common-expression-language
```

After installation, both the Python library and the `cel` command-line tool will be available.

## Quick Start

### CLI Quick Start

For immediate CEL evaluation, use the enhanced command-line interface:

```bash
# Simple expressions
cel '1 + 2'                    # → 3
cel '"Hello " + "World"'       # → Hello World  
cel '[1, 2, 3].size()'        # → 3

# With context
cel 'age >= 21' --context '{"age": 25}'  # → true

# Interactive REPL with rich features
cel --interactive
```

### Python Quick Start

```python
from cel import evaluate

# Simple comparison
result = evaluate("age > 21", {"age": 18})
print(result)  # False

# String operations
result = evaluate("name.startsWith('Hello')", {"name": "Hello World"})
print(result)  # True

# Arithmetic with mixed types
result = evaluate("3.14 * radius * radius", {"radius": 2})
print(result)  # 12.56

# Collections and indexing
result = evaluate("items[0] + items[1]", {"items": [10, 20, 30]})
print(result)  # 30

# Complex expressions
result = evaluate(
    'resource.name.startsWith("/groups/" + claim.group)', 
    {
        "resource": {"name": "/groups/hardbyte"},
        "claim": {"group": "hardbyte"}
    }
)
print(result)  # True
```

### Python Type Mappings

CEL expressions return native Python types:

| CEL Type | Python Type | Example |
|----------|-------------|---------|
| `int` | `int` | `1 + 2` → `3` |
| `uint` | `int` | `1u + 2u` → `3` |
| `double` | `float` | `3.14 * 2` → `6.28` |
| `bool` | `bool` | `true && false` → `False` |
| `string` | `str` | `"hello" + " world"` → `"hello world"` |
| `bytes` | `bytes` | `b"hello"` → `b'hello'` |
| `list` | `list` | `[1, 2, 3]` → `[1, 2, 3]` |
| `map` | `dict` | `{"key": "value"}` → `{'key': 'value'}` |
| `null` | `None` | `null` → `None` |
| `timestamp` | `datetime.datetime` | `timestamp('2024-01-01T00:00:00Z')` |
| `duration` | `datetime.timedelta` | `duration('1h')` |

### Custom Python Functions

Integrate Python functions directly into CEL expressions:

```python
from cel import evaluate

def is_adult(age):
    return age >= 21

def calculate_tax(amount, rate=0.1):
    return amount * rate

# Use functions in expressions
result = evaluate("is_adult(age)", {
    'is_adult': is_adult, 
    'age': 18
})
print(result)  # False

# Functions with multiple arguments
result = evaluate("price + calculate_tax(price, 0.15)", {
    'calculate_tax': calculate_tax,
    'price': 100
})
print(result)  # 115.0
```

### Context Objects

For more control, use explicit Context objects:

```python
from cel import evaluate, Context

def is_admin(user):
    return user.get('role') == 'admin'

context = Context()
context.add_function("is_admin", is_admin)
context.update({
    "user": {"name": "Alice", "role": "admin"},
    "resource": "sensitive_data"
})

result = evaluate("is_admin(user)", context)
print(result)  # True
```

### Datetime Operations

CEL provides built-in support for timestamps and durations:

```python
import datetime
from cel import evaluate

# Parse timestamps
result = evaluate("timestamp('2024-01-01T12:00:00Z')")
print(type(result))  # <class 'datetime.datetime'>

# Parse durations  
result = evaluate("duration('2h30m')")
print(type(result))  # <class 'datetime.timedelta'>

# Datetime arithmetic
now = datetime.datetime.now(datetime.timezone.utc)
result = evaluate("start_time + duration('1h')", {"start_time": now})
print(result)  # One hour from now

# Comparisons
result = evaluate("timestamp('2024-01-01T00:00:00Z') < timestamp('2024-12-31T23:59:59Z')")
print(result)  # True
```

## Command Line Interface

A powerful and beautiful CLI with enhanced developer experience is available for evaluating CEL expressions. Install the package and use either the `cel` command or `python -m cel`:

### Basic Usage

```bash
# Simple evaluation
cel '1 + 2'

# With context variables  
cel 'age > 21' --context '{"age": 25}'

# Load context from JSON file
cel 'user.name' --context-file context.json

# Multiple evaluation modes
python -m cel 'timestamp("2024-01-01T00:00:00Z")' --timing
```

### Enhanced Interactive REPL

The CLI includes a professional interactive REPL with modern shell features:

```bash
# Start enhanced REPL
cel --interactive
```

**REPL Features**:
- 🏛️ **Persistent history** across sessions (stored in `~/.cel_history`)  
- ⬆️ **Arrow key navigation** through command history
- 💡 **Auto-suggestions** based on previous commands  
- 🔤 **Auto-completion** for CEL keywords, functions, and context variables
- 🌈 **Real-time syntax highlighting** as you type (custom CEL lexer)
- 🎨 **Rich-powered output** formatting with tables and colors
- 📊 **Context inspection** with beautiful tables
- ⚡ **Built-in timing** for every expression

**REPL Commands**:
- `help` - Show available commands and CEL examples
- `context` - Display current context variables in a formatted table
- `history` - Show recent expression history
- `load <file>` - Load JSON context from file
- `exit` or `quit` - Exit the REPL
- `Ctrl-C` - Exit the REPL

### Beautiful Output Formatting  

Multiple output formats with Rich-powered styling:

```bash  
# JSON with syntax highlighting
cel '{"users": [{"name": "Alice", "age": 30}]}' --output json

# Pretty tables for structured data
cel '{"name": "Alice", "active": true, "score": 95.5}' --output pretty

# Standard formats
cel '[1, 2, 3, 4, 5]' --output python
```

### File Processing

Batch process expressions from files:

```bash
# Process expressions from file
cel --file expressions.cel --output json
```

**Example expressions.cel**:
```
# Comments are ignored
1 + 2 
"hello" + " world"
timestamp('2024-01-01T00:00:00Z')
```

### Performance Analysis

Built-in timing and verbose analysis:

```bash
# Show evaluation timing
cel 'expensive_calculation()' --timing --context-file context.json

# Verbose output with metadata
cel 'complex_expression' --verbose --context '{"data": [1,2,3]}'
```

### CLI Features Summary

✨ **Enhanced Experience**:
- Built with **Typer** for clean, type-safe CLI definition
- **Rich** integration for beautiful terminal output
- **prompt_toolkit** REPL with professional shell features
- Color-coded error messages and progress indicators

🚀 **Functionality**:
- **Multiple entry points**: `cel` command and `python -m cel`
- **Context management**: JSON strings, files, and REPL loading
- **Output formats**: auto, json (highlighted), pretty (tables), python
- **Batch processing**: File-based expression evaluation
- **Performance timing**: Built-in microsecond precision timing
- **Error handling**: Graceful error messages with syntax highlighting

📊 **Professional Output**:
- Dictionary results displayed as formatted tables
- JSON output with syntax highlighting
- Progress bars for batch operations  
- Color-coded success/error messages

## Supported CEL Features

### Operators

- **Arithmetic**: `+`, `-`, `*`, `/`, `%`
- **Comparison**: `==`, `!=`, `<`, `>`, `<=`, `>=` 
- **Logical**: `&&` (AND), `||` (OR), `!` (NOT)
- **Conditional**: `condition ? value_if_true : value_if_false`
- **Indexing**: `list[index]`, `map["key"]`, `string[index]`
- **Member access**: `object.field`

### Built-in Functions

- **`size(collection)`**: Get length of strings, lists, or maps
- **`string(value)`**: Convert value to string representation
- **`bytes(value)`**: Convert value to bytes
- **`timestamp(rfc3339_string)`**: Parse RFC3339 timestamp
- **`duration(duration_string)`**: Parse duration string

### Control Flow

```python
# Ternary conditional
result = evaluate("age >= 21 ? 'adult' : 'minor'", {"age": 25})
print(result)  # "adult"

# Short-circuit evaluation
result = evaluate("false && expensive_function()", {"expensive_function": lambda: 1/0})
print(result)  # False (expensive_function not called)
```

## Limitations

Some CEL features are not yet implemented in the underlying cel-interpreter:

❌ **Missing Features**:
- Mixed signed/unsigned arithmetic (`1 + 2u`) - use `int(2u) + 1` or `uint(1) + 2u`
- Bytes concatenation (`b'hello' + b'world'`) - use string conversion workaround
- String methods: `contains()`, `endsWith()`, `indexOf()`, `replace()`, etc.
- Macros: `has()`, `all()`, `exists()`  
- Math functions: `math.ceil()`, `math.floor()`, `math.round()`
- Regular expressions
- Optional values and optional chaining

⚠️ **Behavioral Notes**:
- OR operator with non-boolean operands returns the first truthy value: `42 || false` → `42`
- No automatic numeric type conversion between int/uint/double
- Empty strings, empty collections, and zero values are falsy

For complete details, see [cel-compliance.md](cel-compliance.md).

## Testing

Run the test suite:

```bash
# Using uv (recommended)
uv run pytest

# Or with regular pytest  
pytest

# With verbose output
uv run pytest -v

# With coverage
uv run pytest --cov=cel
```

## Performance

This implementation is designed for high-performance expression evaluation:

- **Expression parsing**: Handled efficiently by Rust cel-interpreter
- **Evaluation speed**: Microsecond-level for typical expressions  
- **Memory usage**: Optimized for frequent evaluations
- **Type conversion**: Efficient Python ↔ Rust boundary crossing

Benchmark results on typical hardware:
- Simple expressions (`1 + 2`): ~1-10 microseconds
- Complex expressions with context: ~10-100 microseconds  
- Large collection processing: Handles 10,000+ elements efficiently

## Contributing

We welcome contributions! Areas where help is especially needed:

1. **Testing**: Add test cases for edge cases and missing features
2. **Documentation**: Improve examples and usage patterns
3. **Performance**: Optimize type conversion and memory usage
4. **Upstream**: Contribute to [cel-interpreter](https://crates.io/crates/cel-interpreter) for missing CEL features

See [cel-compliance.md](cel-compliance.md) for detailed information about CEL specification compliance and missing features.

## Resources

- **CEL Homepage**: https://cel.dev/
- **CEL Specification**: https://github.com/google/cel-spec
- **Language Definition**: https://github.com/google/cel-spec/blob/master/doc/langdef.md
- **cel-interpreter crate**: https://crates.io/crates/cel-interpreter

## License

This project is licensed under the same terms as the original cel-inspector crate.