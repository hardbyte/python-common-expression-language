# CLI Reference

Complete reference for the `cel` command-line interface.

## Synopsis

```bash
cel [OPTIONS] [EXPRESSION]
cel --interactive
cel --help
cel --version
```

## Description

The `cel` command-line tool provides a convenient way to evaluate CEL expressions from the command line, in scripts, or interactively. It supports context loading, file processing, and various output formats.

## Options

### Global Options

#### `--help`, `-h`
Show help message and exit.

```bash
cel --help
cel -h
```

#### `--version`, `-v`  
Show version information and exit.

```bash
cel --version
cel -v
```

#### `--verbose`
Enable verbose output for debugging.

```bash
cel --verbose 'complex.expression' --context '{"complex": "data"}'
```

#### `--debug`
Enable debug mode with detailed error information.

```bash
cel --debug 'user.role == "admin"' --context-file user.json
```

### Context Options

#### `--context`, `-c`
Provide context as inline JSON string.

```bash
cel 'name + " is " + string(age)' --context '{"name": "Alice", "age": 30}'
cel 'user.role == "admin"' -c '{"user": {"role": "admin"}}'
```

**Format**: Valid JSON object
**Example**: `'{"key": "value", "number": 42, "list": [1, 2, 3]}'`

#### `--context-file`, `-f`
Load context from JSON file.

```bash
cel 'user.role == "admin"' --context-file user.json
cel 'config.valid' -f config.json
```

**Format**: Path to valid JSON file
**Special values**: 
- `/dev/stdin` - Read from standard input
- `-` - Read from standard input (shorthand)

### Interactive Mode

#### `--interactive`, `-i`
Launch interactive REPL mode.

```bash
cel --interactive
cel -i
```

In interactive mode, you can:
- Enter expressions directly
- Use built-in commands (`:help`, `:context`, etc.)
- Load context from files
- View command history

### Output Options

#### `--format`
Specify output format.

```bash
cel '{"name": "Alice", "age": 30}' --format json
cel '[1, 2, 3]' --format yaml
cel 'user.name' --format raw --context-file user.json
```

**Values**:
- `auto` (default) - Automatically detect best format
- `json` - JSON format
- `yaml` - YAML format  
- `raw` - Raw string output (no quotes for strings)
- `pretty` - Pretty-printed format

#### `--compact`
Use compact output format (minimal whitespace).

```bash
cel '{"a": 1, "b": 2}' --compact
# Output: {"a":1,"b":2}

# vs normal:
cel '{"a": 1, "b": 2}'
# Output: {
#   "a": 1,
#   "b": 2
# }
```

### Processing Options

#### `--null-input`
Process with null/empty input context.

```bash
cel --null-input '1 + 2'
cel --null-input 'timestamp("2024-01-01T00:00:00Z").getFullYear()'
```

#### `--raw-output`
Output raw strings without JSON encoding.

```bash
cel '"Hello World"' --raw-output
# Output: Hello World (not "Hello World")

cel 'users.map(u, u.name).join(", ")' --context-file users.json --raw-output
```

#### `--exit-status`
Set exit status based on result (0 for truthy, 1 for falsy).

```bash
cel 'user.role == "admin"' --context-file user.json --exit-status
echo $?  # 0 if admin, 1 if not
```

## Interactive Mode Commands

When in interactive mode (`cel -i`), these commands are available:

### Context Management

#### `:context <var>=<value>`
Set a context variable.

```
CEL> :context name="Alice"
Context updated: name

CEL> :context age=30
Context updated: age

CEL> name + " is " + string(age)
Alice is 30
```

#### `:context <json>`
Set multiple context variables from JSON.

```
CEL> :context {"user": {"name": "Bob", "role": "admin"}, "debug": true}
Context updated: user, debug

CEL> user.role
admin
```

#### `:show-context`
Display current context.

```
CEL> :show-context
{
  "name": "Alice",
  "age": 30,
  "user": {
    "name": "Bob", 
    "role": "admin"
  },
  "debug": true
}
```

#### `:clear-context`
Clear all context variables.

```
CEL> :clear-context
Context cleared

CEL> :show-context
{}
```

#### `:load-context <file>`
Load context from JSON file.

```
CEL> :load-context user.json
Context loaded from user.json

CEL> :load-context /path/to/config.json
Context loaded from /path/to/config.json
```

### History Management

#### `:history`
Show command history.

```
CEL> :history
1: 1 + 2
2: "hello".size()
3: user.name
4: user.role == "admin"
```

#### `:replay <n>`
Replay command number n from history.

```
CEL> :replay 2
4

CEL> :replay -1
true
```

**Special values**:
- `<number>` - Replay specific command number
- `-1` - Replay last command
- `-2` - Replay second-to-last command, etc.

#### `:clear-history`
Clear command history.

```
CEL> :clear-history
History cleared
```

### Utility Commands

#### `:help`
Show help message.

```
CEL> :help
Available commands:
  :context <var>=<value>  - Set context variable
  :show-context          - Show current context
  :clear-context         - Clear all context
  :load-context <file>   - Load context from file
  :history              - Show command history
  :replay <n>           - Replay command n
  :clear-history        - Clear history
  :help                 - Show this help
  :exit                 - Exit REPL
```

#### `:exit`
Exit the interactive REPL.

```
CEL> :exit
Goodbye!
```

**Aliases**: `:quit`, `:q`, `Ctrl+D`

📚 **For practical usage examples, recipes, and integration patterns, see the [CLI Usage Recipes](../how-to-guides/cli-recipes.md) guide.**

## Basic Usage

```bash
# Simple evaluation
cel 'expression'

# With context
cel 'expression' --context '{"key": "value"}'
cel 'expression' --context-file context.json

# Interactive mode
cel --interactive
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |
| 3 | Context file error |
| 4 | Expression syntax error |
| 5 | Expression runtime error |
| 6 | Type error |
| 64 | Usage error (invalid options) |

When using `--exit-status`, codes are:
- 0: Expression evaluated to truthy value
- 1: Expression evaluated to falsy value