# Installation

Getting Python CEL up and running is quick and easy.

## Requirements

- **Python 3.11+** (required for compiled wheels)
- **pip** or **uv** package manager

## Install from PyPI

=== "uv"

    ```bash
    uv add common-expression-language
    # → Adding common-expression-language to dependencies
    # → Resolved 15 packages in 1.23s
    # → Installed common-expression-language-0.11.0
    ```

=== "uv tool (CLI only)"

    Install the CLI tool globally:
    
    ```bash
    uv tool install common-expression-language
    # → Installed common-expression-language 0.11.0
    # → Installed executables: cel
    ```

=== "pip"

    ```bash
    pip install common-expression-language
    # → Collecting common-expression-language
    # → Successfully installed common-expression-language-0.11.0
    ```


## Verify Installation

After installation, you should have both the Python library and CLI tool available:

### Python Library

```python
import cel
result = cel.evaluate("1 + 2")
# → 3
assert result == 3
print("✓ Basic evaluation working correctly")
# → ✓ Basic evaluation working correctly
```

### CLI Tool

```bash
cel --version
# → cel 0.11.0

cel '1 + 2'
# → 3
```

## Development Installation

If you want to contribute or build from source:

### Prerequisites

- **Rust** (latest stable)
- **Python 3.11+**
- **maturin** (for building)

### From Source

```bash
# Clone the repository
git clone https://github.com/hardbyte/python-common-expression-language.git
cd python-common-expression-language

# Install in development mode
pip install maturin
# → Successfully installed maturin-1.4.0

maturin develop
# → 🔗 Found pyo3 bindings
# → 📦 Built wheel for CPython 3.11 to target/wheels/
# → 📦 Installed common-expression-language-0.11.0

# Or with uv
uv run maturin develop
# → 🔗 Found pyo3 bindings
# → 📦 Built wheel and installed successfully
```

## Troubleshooting


### Platform Issues

Pre-built wheels are available for:

- **Linux**: x86_64, aarch64
- **macOS**: x86_64, ARM64 (Apple Silicon)
- **Windows**: x86_64

If your platform isn't supported, the package will try to build from source, which requires Rust to be installed.


## What's Installed

After installation, you get:

- **`cel` module**: Python library for embedding in your applications
- **`cel` command**: CLI tool for interactive use and scripting
- **All dependencies**: Rich, Typer, Pygments for CLI functionality

## Next Steps

- [**Quick Start**](quick-start.md) - Your first CEL expressions
- [**Your First Integration**](../tutorials/your-first-integration.md) - Using the Python API
- [**Thinking in CEL**](../tutorials/thinking-in-cel.md) - Core concepts and philosophy