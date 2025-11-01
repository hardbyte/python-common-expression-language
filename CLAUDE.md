# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Python package that provides Python bindings for the Common Expression Language (CEL) using a Rust implementation. The project uses PyO3 to create Python bindings for the `cel-interpreter` Rust crate.

## Architecture

### Core Components

- **Rust Core (`src/lib.rs`)**: Main evaluation engine that compiles and executes CEL expressions
- **Context Management (`src/context.rs`)**: Manages variables and Python functions in CEL evaluation context
- **Type Conversion**: Bidirectional conversion between Python types and CEL Value types via `RustyCelType` and `RustyPyType` wrappers

### Key Features

- **Expression Evaluation**: Compile and execute CEL expressions with Python context
- **Custom Functions**: Support for user-defined Python functions callable from CEL expressions
- **Type System**: Handles primitive types (int, float, string, bool), collections (list, dict), timestamps, durations, and bytes
- **Context API**: Both dict-based and explicit Context object for managing evaluation context

## Development Commands

### Building
```bash
# Build the Rust extension module
maturin develop

# Build release version 
maturin build --release
```

### Testing
```bash
# Run all tests with debug logging
uv run pytest --log-cli-level=debug

# Run specific test file
uv run pytest tests/test_basics.py

# Run single test
uv run pytest tests/test_basics.py::test_hello_world
```

### Linting & Formatting
```bash
# Format Rust code
cargo fmt --all

# Check Rust code with clippy
cargo clippy --all-targets --all-features -- -D warnings

# Build workspace to verify compilation
cargo build --workspace
```

## Key Files

- `src/lib.rs`: Main evaluation function and type conversions (src/lib.rs:191 for `evaluate` function)
- `src/context.rs`: Context management and Python function integration
- `tests/`: Comprehensive test suite covering all features
- `pyproject.toml`: Python package configuration with maturin build system
- `Cargo.toml`: Rust dependencies including PyO3 and cel-interpreter

## CLI Architecture

### Command-Line Interface (`python/cel/cli.py`)

The CLI is built with Typer and provides multiple modes:

- **Single expression evaluation**: `cel 'expression'`
- **Interactive REPL**: `cel --interactive` (uses prompt_toolkit)
- **TUI mode**: `cel --tui` (uses textual library)
- **File mode**: `cel --file expressions.cel` (evaluate expressions from file)
- **Batch context processing**: `cel 'expr' --for-each file1.json --for-each file2.json`

### Key CLI Components

- **CELEvaluator** (python/cel/cli.py:~180): Wrapper around core evaluation with context management
- **CELFormatter** (python/cel/cli.py:~90): Rich-based output formatting (JSON, pretty, python, auto)
- **InteractiveCELREPL** (python/cel/cli.py:~250): REPL with command dispatch and history
- **evaluate_expression_with_multiple_contexts** (python/cel/cli.py:~537): Batch processing function

### CLI Design Patterns

#### Batch Processing (`--for-each`)

The `--for-each` flag uses a **repeated flag pattern** (like `cargo test --test`) rather than positional arguments:

```bash
# Correct: Explicit separate evaluation
cel 'user.age >= 18' --for-each user1.json --for-each user2.json --for-each user3.json

# NOT: cel 'expr' file1.json file2.json  (ambiguous: merge or separate?)
```

**Why repeated flags?**
- Makes separate evaluation explicit (vs merging)
- Distinct from `--context-file` (singular, merged)
- Follows precedent: `cargo test --test`, `curl -H`
- Prevents confusion about merge vs separate semantics

See research in `/tmp/cli_patterns_detailed.md` for analysis of 20+ CLI tools.

#### Context Merging

- `--context-file file.json`: Loads ONE merged context
- `--for-each f1.json --for-each f2.json`: Evaluates SEPARATELY for EACH file
- Both can combine: `--context '{"base": 1}' --for-each file.json` → base merged into each file

## Testing Patterns

### Test Organization

- **Unit tests** (`tests/test_*.py`): Test individual functions with mocks
- **E2E tests** (`tests/test_cli.py`): Test full CLI via subprocess
- **Total**: 91 tests (50 unit + 41 E2E)

### Test Files

- `test_basics.py`: Core evaluation functionality and type handling
- `test_context.py`: Context management and variable passing
- `test_functions.py`: Custom Python function integration
- `test_cli.py`: CLI features (both unit and E2E tests)
  - TestCELFormatter: Output formatting tests
  - TestCELEvaluator: Evaluator wrapper tests
  - TestInteractiveCELREPL: REPL functionality tests
  - TestBatchContextProcessing: Unit tests for batch processing
  - **TestCLIE2EBasicFeatures**: E2E tests for basic CLI (25 tests)
  - **TestCLIE2EFileMode**: E2E tests for --file mode (7 tests)
  - **TestBatchContextProcessingE2E**: E2E tests for --for-each (9 tests)

### E2E Testing Strategy

E2E tests use `subprocess.run()` to invoke the actual `cel` CLI command:

```python
# Example E2E test pattern
result = subprocess.run(
    ["cel", "expression", "--context", '{"var": 1}'],
    capture_output=True,
    text=True,
    check=True,
)
assert result.returncode == 0
assert "expected output" in result.stdout
```

**Why E2E tests?**
- Verify actual user experience (CLI flag parsing, exit codes, output)
- Catch integration issues that unit tests miss
- Serve as executable documentation
- Test shell integration (exit codes, pipes)

**Coverage**: ~95% of non-interactive CLI features

Test fixtures in `conftest.py` provide parameterized test cases for various expression types and contexts.

## Common Pitfalls & Gotchas

### CLI Development

1. **Always test both unit AND E2E**: Unit tests verify function logic, E2E tests verify CLI integration
2. **Exit codes matter**: Users rely on exit codes for scripting (`if cel 'expr'; then`)
3. **Flag naming**: Use `--long-flag` for clarity, `-s` for common shortcuts
4. **Repeated flags**: When adding new batch operations, consider `--for-each` pattern

### Testing

1. **E2E tests are slower**: ~141ms per E2E test vs ~30ms per unit test (due to subprocess)
2. **Temp files**: Always use `tempfile.NamedTemporaryFile` with cleanup in `finally` blocks
3. **Output verification**: E2E tests should verify both stdout content AND exit codes
4. **JSON parsing**: When testing JSON output, parse it to verify structure, not just string matching

### Documentation

When adding CLI features, update ALL of:
- README.md (quick example)
- docs/reference/cli-reference.md (complete flag documentation)
- docs/how-to-guides/cli-recipes.md (usage recipes and patterns)
- CLI docstring (examples in `main()` function)

## Performance Notes

- CEL evaluation is microsecond-level (Rust backend)
- CLI overhead is ~1-2ms per invocation (Python startup)
- E2E tests take ~7.5s for 91 tests total
- Batch processing with 20 files: ~50-100ms total (file I/O dominates)