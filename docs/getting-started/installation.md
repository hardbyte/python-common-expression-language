# Installation

Getting Python CEL up and running is quick and easy.

## Requirements

- **Python 3.11+** (required for compiled wheels)
- **pip** or **uv** package manager

## Install from PyPI

=== "pip"

    ```bash
    pip install common-expression-language
    ```

=== "uv"

    ```bash
    uv add common-expression-language
    ```

=== "pipx (CLI only)"

    If you only want the CLI tool:
    
    ```bash
    pipx install common-expression-language
    ```

## Verify Installation

After installation, you should have both the Python library and CLI tool available:

### Python Library

```python
import cel
result = cel.evaluate("1 + 2")
assert result == 3
print("✓ Basic evaluation working correctly")
```

### CLI Tool

```bash
cel --version
cel '1 + 2'  # Should print: 3
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
maturin develop

# Or with uv
uv run maturin develop
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