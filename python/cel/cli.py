#!/usr/bin/env python3
"""
Common Expression Language (CEL) Command Line Interface

A powerful CLI for evaluating CEL expressions with support for:
- Interactive REPL mode with history and syntax highlighting
- File-based expression evaluation
- JSON context input/output
- Batch processing
- Performance timing
- Beautiful output formatting
"""

import json
import sys
import time
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import typer

# Prompt toolkit imports for enhanced REPL
from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import WordCompleter
from prompt_toolkit.history import FileHistory
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style
from pygments import token

# Pygments imports for syntax highlighting
from pygments.lexer import RegexLexer
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from typing_extensions import Annotated

try:
    from . import cel
except ImportError:
    # Fallback for running as standalone script
    try:
        import cel
    except ImportError:
        console = Console()
        console.print(
            "[red]Error: 'cel' package not found. Please install with: pip install common-expression-language[/red]"
        )
        sys.exit(1)

# Initialize Rich console
console = Console()


def get_version() -> str:
    """Get the version of the CEL package."""
    try:
        return version("common-expression-language")
    except PackageNotFoundError:
        return "unknown (development)"


def version_callback(value: bool):
    """Print version and exit."""
    if value:
        console.print(f"cel {get_version()}")
        raise typer.Exit()


class CELLexer(RegexLexer):
    """Custom Pygments lexer for CEL syntax highlighting in the REPL."""

    name = "CEL"
    aliases = ["cel"]
    filenames = ["*.cel"]

    tokens = {
        "root": [
            # Keywords and constants
            (r"\b(true|false|null)\b", token.Keyword.Constant),
            (r"\b(in|if|else|and|or|not)\b", token.Keyword),
            # Built-in functions
            (
                r"\b(size|has|timestamp|duration|int|uint|double|string|bytes|"
                r"startsWith|endsWith|contains|matches)\b(?=\()",
                token.Name.Function,
            ),
            # String literals
            (r'"([^"\\]|\\.)*"', token.String.Double),
            (r"'([^'\\]|\\.)*'", token.String.Single),
            # Byte literals
            (r'b"([^"\\]|\\.)*"', token.String.Affix),
            (r"b'([^'\\]|\\.)*'", token.String.Affix),
            # Numeric literals
            (r"\b[0-9]+\.[0-9]*([eE][+-]?[0-9]+)?\b", token.Number.Float),
            (r"\b[0-9]+[eE][+-]?[0-9]+\b", token.Number.Float),
            (r"\b[0-9]+u\b", token.Number.Integer),  # unsigned integers
            (r"\b[0-9]+\b", token.Number.Integer),
            # Operators
            (r"[+\-*/%]", token.Operator),
            (r"[<>=!]=?", token.Operator.Comparison),
            (r"&&|\|\||!", token.Operator.Logical),
            (r"\?|:", token.Operator.Conditional),
            # Punctuation
            (r"[\[\]{}().,]", token.Punctuation),
            # Identifiers (variables, fields)
            (r"\b[a-zA-Z_][a-zA-Z0-9_]*\b", token.Name.Variable),
            # Whitespace
            (r"\s+", token.Whitespace),
            # Comments (if we want to support them in REPL)
            (r"#.*$", token.Comment.Single),
        ],
    }


# CLI application
app = typer.Typer(
    name="cel",
    help="Common Expression Language (CEL) Command Line Interface",
    add_completion=False,
    rich_markup_mode="rich",
    context_settings={"help_option_names": ["-h", "--help"]},
)


class CELFormatter:
    """Enhanced formatter using Rich for beautiful output."""

    @staticmethod
    def display(console_obj: Console, result: Any, format_type: str = "auto") -> None:
        """Main entry point for displaying results - uses Rich renderables for efficiency."""
        rich_renderable = CELFormatter.get_rich_renderable(result, format_type)
        console_obj.print(rich_renderable)

    @staticmethod
    def get_rich_renderable(result: Any, format_type: str = "auto") -> Any:
        """Returns a Rich renderable object for the given result and format type."""
        if format_type == "json":
            json_str = json.dumps(result, indent=2, default=str, ensure_ascii=False)
            return Syntax(json_str, "json", theme="monokai", line_numbers=False)
        elif format_type == "pretty":
            return CELFormatter._get_pretty_renderable(result)
        elif format_type == "python":
            return repr(result)
        else:  # auto
            return CELFormatter._get_auto_renderable(result)

    @staticmethod
    def format_result(result: Any, format_type: str = "auto") -> str:
        """Format result as string (for backward compatibility and testing)."""
        rich_renderable = CELFormatter.get_rich_renderable(result, format_type)
        # For Rich objects, we need to capture their output
        if hasattr(rich_renderable, "__rich__") or hasattr(rich_renderable, "__rich_console__"):
            with console.capture() as capture:
                console.print(rich_renderable)
            return capture.get()
        return str(rich_renderable)

    @staticmethod
    def _get_pretty_renderable(result: Any) -> Any:
        """Get Rich renderable for pretty-formatted result."""
        if isinstance(result, dict):
            table = Table(title="Dictionary Result", show_header=True, header_style="bold magenta")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")
            for k, v in result.items():
                table.add_row(str(k), str(v))
            return table
        elif isinstance(result, list):
            table = Table(title="List Result", show_header=True, header_style="bold magenta")
            table.add_column("Index", style="cyan")
            table.add_column("Value", style="green")
            for i, v in enumerate(result):
                table.add_row(str(i), str(v))
            return table
        else:
            # Use f-string as suggested
            type_name = type(result).__name__
            return f"{result} ({type_name})"

    @staticmethod
    def _get_auto_renderable(result: Any) -> Any:
        """Get Rich renderable for auto-formatted result."""
        if isinstance(result, (dict, list)) and len(str(result)) > 100:
            return CELFormatter._get_pretty_renderable(result)
        return str(result)


class CELEvaluator:
    """Enhanced CEL expression evaluator."""

    def __init__(self, context: Optional[Dict[str, Any]] = None):
        """Initialize evaluator with optional context."""
        self.context = context or {}
        self._cel_context = None
        self._update_cel_context()

    def _update_cel_context(self):
        """Update the internal CEL context object."""
        if self.context:
            self._cel_context = cel.Context(self.context)
        else:
            self._cel_context = None

    def evaluate(self, expression: str) -> Any:
        """Evaluate a CEL expression."""
        if not expression.strip():
            raise ValueError("Empty expression")
        return cel.evaluate(expression, self._cel_context)

    def update_context(self, new_context: Dict[str, Any]):
        """Update the evaluation context."""
        self.context.update(new_context)
        self._update_cel_context()

    def get_context_vars(self) -> Dict[str, Any]:
        """Get current context variables for display."""
        return self.context.copy()


class InteractiveCELREPL:
    """Enhanced REPL with prompt_toolkit features."""

    def __init__(self, evaluator: CELEvaluator, history_limit: int = 10):
        """Initialize REPL with enhanced features."""
        self.evaluator = evaluator
        self.history: list[Tuple[str, Any]] = []
        self.history_limit = history_limit

        # CEL keywords and functions for completion - stored as instance variables
        self.cel_keywords = [
            "true",
            "false",
            "null",
            "if",
            "else",
            "in",
            "and",
            "or",
            "not",
        ]
        self.cel_functions = [
            "size",
            "has",
            "timestamp",
            "duration",
            "int",
            "uint",
            "double",
            "string",
            "bytes",
        ]

        # Command dispatch dictionary for cleaner organization
        self.commands = {
            "help": self._show_help,
            "history": self._show_history,
        }

        # Setup prompt session with history, autocompletion, and syntax highlighting
        history_file = Path.home() / ".cel_history"
        self.session: PromptSession[str] = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            complete_while_typing=True,
            lexer=PygmentsLexer(CELLexer),  # Add real-time syntax highlighting
        )
        self._update_completer()

        # Rich styling for the REPL
        self.style = Style.from_dict(
            {
                "prompt": "#00aa00 bold",
                "result": "#0088ff",
                "error": "#ff0066",
            }
        )

    def run(self):
        """Run the enhanced REPL."""
        console.print(
            Panel.fit(
                "[bold green]CEL Interactive REPL[/bold green]\n"
                "Enhanced with history, autocompletion, and syntax highlighting\n"
                "Type 'help' for commands, 'exit' to quit",
                border_style="green",
            )
        )

        while True:
            try:
                # Get input with enhanced prompt
                expression = self.session.prompt("cel> ", style=self.style)

                if not expression.strip():
                    continue

                # Handle REPL commands
                command_parts = expression.strip().split()
                command = command_parts[0].lower() if command_parts else ""

                if command in ["exit", "quit"]:
                    console.print("[yellow]Goodbye![/yellow]")
                    break
                elif command == "context":
                    if len(command_parts) > 1:
                        # Setting context: context {"key": "value"}
                        context_json = " ".join(command_parts[1:])
                        self._set_context(context_json)
                    else:
                        # Showing context: context
                        self._show_context()
                    continue
                elif command in self.commands:
                    self.commands[command]()
                    continue
                elif command == "load" and len(command_parts) > 1:
                    filename = " ".join(command_parts[1:])  # Handle filenames with spaces
                    self._load_context(filename)
                    continue

                # Evaluate expression
                start_time = time.time()
                result = self.evaluator.evaluate(expression)
                eval_time = time.time() - start_time

                # Display result using streamlined formatter
                CELFormatter.display(console, result, "pretty")

                # Show timing
                console.print(f"[dim]Evaluated in {eval_time * 1000:.2f}ms[/dim]")

                # Add to history (keep limited)
                self.history.append((expression, result))
                if len(self.history) > 100:  # Keep last 100 items
                    self.history = self.history[-100:]

            except KeyboardInterrupt:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            except EOFError:
                console.print("\n[yellow]Goodbye![/yellow]")
                break
            except Exception as e:
                console.print(f"[red]Error: {e}[/red]")

    def _show_help(self):
        """Show enhanced REPL help."""
        help_table = Table(title="REPL Commands", show_header=True, header_style="bold magenta")
        help_table.add_column("Command", style="cyan")
        help_table.add_column("Description", style="green")

        help_table.add_row("help", "Show this help message")
        help_table.add_row("context", "Show current context variables")
        help_table.add_row("context <json>", "Set context variables from JSON")
        help_table.add_row("history", "Show expression history")
        help_table.add_row("load <file>", "Load JSON context from file")
        help_table.add_row("exit/quit", "Exit the REPL")
        help_table.add_row("Ctrl-C", "Exit the REPL")

        console.print(help_table)

        console.print("\n[bold]CEL Examples:[/bold]")
        examples = [
            "1 + 2",
            '"hello" + " world"',
            "[1, 2, 3].size()",
            "timestamp('2024-01-01T00:00:00Z')",
            'age > 21 ? "adult" : "minor"',
        ]
        for example in examples:
            console.print(f"  [dim]cel>[/dim] [cyan]{example}[/cyan]")

    def _show_context(self):
        """Show current context variables with Rich formatting."""
        context_vars = self.evaluator.get_context_vars()

        if not context_vars:
            console.print("[dim]No context variables set[/dim]")
            return

        table = Table(title="Context Variables", show_header=True, header_style="bold magenta")
        table.add_column("Variable", style="cyan")
        table.add_column("Type", style="yellow")
        table.add_column("Value", style="green")

        for name, value in context_vars.items():
            table.add_row(name, type(value).__name__, str(value))

        console.print(table)

    def _set_context(self, context_json: str):
        """Set context variables from JSON string."""
        try:
            new_context = json.loads(context_json)
            if not isinstance(new_context, dict):
                console.print("[red]Error: Context must be a JSON object (dictionary)[/red]")
                return

            # Update the context
            self.evaluator.update_context(new_context)

            # Update completer with new context variables
            self._update_completer()

            # Show what was updated
            context_keys = list(new_context.keys())
            if len(context_keys) == 1:
                console.print(f"[green]Context updated: {context_keys[0]}[/green]")
            elif len(context_keys) <= 3:
                console.print(f"[green]Context updated: {', '.join(context_keys)}[/green]")
            else:
                console.print(f"[green]Context updated: {len(context_keys)} variables[/green]")

        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON - {e}[/red]")
        except Exception as e:
            console.print(f"[red]Error updating context: {e}[/red]")

    def _show_history(self):
        """Show expression history with Rich formatting."""
        if not self.history:
            console.print("[dim]No history available[/dim]")
            return

        table = Table(title="Expression History", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Expression", style="cyan")
        table.add_column("Result", style="green")

        # Show last N items based on history_limit
        recent_history = self.history[-self.history_limit :]
        for i, (expr, result) in enumerate(recent_history, 1):
            # Truncate long results
            result_str = str(result)
            if len(result_str) > 50:
                result_str = result_str[:47] + "..."
            table.add_row(str(i), expr, result_str)

        console.print(table)

    def _update_completer(self):
        """Update the completer with current context variables."""
        words = self.cel_keywords + self.cel_functions + list(self.evaluator.context.keys())
        self.session.completer = WordCompleter(words)

    def _load_context(self, filename: str):
        """Load context from JSON file."""
        try:
            with open(filename, "r") as f:
                context = json.load(f)
            self.evaluator.update_context(context)
            console.print(f"[green]Loaded context from {filename}[/green]")
            # Update completer with new context variables
            self._update_completer()
        except Exception as e:
            console.print(f"[red]Error loading context: {e}[/red]")


def load_context_from_file(filename: Path) -> Dict[str, Any]:
    """Load context from JSON file with Rich error handling."""
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        console.print(f"[red]Error: Invalid JSON in {filename}: {e}[/red]")
        raise typer.Exit(1) from e
    except FileNotFoundError as e:
        console.print(f"[red]Error: Context file '{filename}' not found[/red]")
        raise typer.Exit(1) from e


def evaluate_expressions_from_file(
    filename: Path, evaluator: CELEvaluator, output_format: str
) -> None:
    """Evaluate expressions from a file with Rich output."""
    try:
        with open(filename, "r") as f:
            expressions = [
                line.strip() for line in f if line.strip() and not line.strip().startswith("#")
            ]
    except FileNotFoundError as e:
        console.print(f"[red]Error: Expression file '{filename}' not found[/red]")
        raise typer.Exit(1) from e

    if not expressions:
        console.print("[yellow]No expressions found in file[/yellow]")
        return

    results = []

    with console.status(f"[bold green]Evaluating {len(expressions)} expressions..."):
        for i, expression in enumerate(expressions, 1):
            try:
                start_time = time.time()
                result = evaluator.evaluate(expression)
                eval_time = time.time() - start_time

                results.append(
                    {
                        "expression": expression,
                        "result": result,
                        "time_ms": eval_time * 1000,
                    }
                )

            except Exception as e:
                console.print(f"[red]Error in expression {i} '{expression}': {e}[/red]")
                results.append({"expression": expression, "error": str(e)})

    # Display results
    if output_format == "json":
        json_output = json.dumps(results, indent=2, default=str)
        syntax = Syntax(json_output, "json", theme="monokai")
        console.print(syntax)
    else:
        table = Table(title="Expression Results", show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Expression", style="cyan")
        table.add_column("Result", style="green")
        table.add_column("Time (ms)", style="yellow")

        for i, result in enumerate(results, 1):
            if "error" in result:
                table.add_row(
                    str(i),
                    result["expression"],
                    f"[red]Error: {result['error']}[/red]",
                    "—",
                )
            else:
                result_str = str(result["result"])
                if len(result_str) > 50:
                    result_str = result_str[:47] + "..."
                table.add_row(str(i), result["expression"], result_str, f"{result['time_ms']:.2f}")

        console.print(table)


@app.command()
def main(
    expression: Annotated[Optional[str], typer.Argument(help="CEL expression to evaluate")] = None,
    context: Annotated[
        Optional[str], typer.Option("-c", "--context", help="Context as JSON string")
    ] = None,
    context_file: Annotated[
        Optional[Path],
        typer.Option("-f", "--context-file", help="Load context from JSON file"),
    ] = None,
    file: Annotated[
        Optional[Path],
        typer.Option("--file", help="Read expressions from file (one per line)"),
    ] = None,
    output: Annotated[str, typer.Option("-o", "--output", help="Output format")] = "auto",
    interactive: Annotated[
        bool, typer.Option("-i", "--interactive", help="Start interactive REPL mode")
    ] = False,
    timing: Annotated[bool, typer.Option("-t", "--timing", help="Show evaluation timing")] = False,
    verbose: Annotated[bool, typer.Option("-v", "--verbose", help="Verbose output")] = False,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version", callback=version_callback, is_eager=True, help="Show version and exit"
        ),
    ] = None,
):
    """
    Evaluate CEL expressions with enhanced CLI experience.

    Examples:

        # Evaluate a simple expression
        cel '1 + 2'

        # Use context variables
        cel 'age > 21' --context '{"age": 25}'

        # Load context from file
        cel 'user.name' --context-file context.json

        # Interactive REPL mode
        cel --interactive

        # Evaluate expressions from file
        cel --file expressions.cel --output json
    """

    # Load context
    eval_context = {}
    if context:
        try:
            eval_context = json.loads(context)
        except json.JSONDecodeError as e:
            console.print(f"[red]Error: Invalid JSON in context: {e}[/red]")
            raise typer.Exit(1) from e

    if context_file:
        file_context = load_context_from_file(context_file)
        eval_context.update(file_context)

    # Initialize evaluator
    evaluator = CELEvaluator(eval_context)

    # Interactive mode
    if interactive:
        repl = InteractiveCELREPL(evaluator)
        repl.run()
        return

    # File mode
    if file:
        evaluate_expressions_from_file(file, evaluator, output)
        return

    # Single expression evaluation
    if not expression:
        console.print(
            "[red]Error: No expression provided. Use -i for interactive mode or provide an expression.[/red]"
        )
        console.print("\nUse [bold]cel --help[/bold] for more information.")
        raise typer.Exit(1)

    try:
        # Evaluate expression
        start_time = time.time()
        result = evaluator.evaluate(expression)
        eval_time = time.time() - start_time

        # Format and output result using streamlined formatter
        CELFormatter.display(console, result, output)

        # Show timing if requested
        if timing or verbose:
            console.print(f"[dim]Evaluated in {eval_time * 1000:.2f}ms[/dim]")

        # Verbose output
        if verbose:
            console.print(f"[dim]Expression: {expression}[/dim]")
            console.print(f"[dim]Result type: {type(result).__name__}[/dim]")
            if eval_context:
                console.print(f"[dim]Context variables: {len(eval_context)}[/dim]")

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1) from e


def cli_entry():
    """Entry point for the CLI."""
    app()


if __name__ == "__main__":
    cli_entry()
