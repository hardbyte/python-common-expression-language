#!/usr/bin/env python3
"""
CEL TUI - Figma Design Implementation

A professional 3-column TUI implementing the Figma design:
- Left: Expression library with examples
- Middle: Context editor with JSON/YAML/URL loading
- Right: Evaluation and results
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.request import urlopen

import yaml
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import Button, Footer, Header, Input, Label, Static, TextArea

from .cel import Context, evaluate
from .cel_lexer import CELLexer
from .expression_storage import (
    add_expression,
    delete_expression,
    get_expressions_file,
    load_user_expressions,
)
from .stdlib import add_stdlib_to_context

# Register CEL lexer with Pygments so TextArea can use it
try:
    from pygments.lexers import get_lexer_by_name
    from pygments.lexers._mapping import LEXERS

    # Register our custom lexer
    LEXERS["CELLexer"] = (
        "cel.cel_lexer",
        "CEL",
        ("cel",),
        ("*.cel",),
        ("text/x-cel",),
    )
except ImportError:
    pass  # Pygments not available

# Example expressions library
EXPRESSION_LIBRARY = [
    ("Age Check", "Check if user is 18 or older", "user.age >= 18"),
    ("Role Validation", "Check if user has admin role", '"admin" in user.roles'),
    ("String Manipulation", "Check name starts with A and length > 3",
     'user.name.startsWith("A") && user.name.size() > 3'),
    ("List Operations", "Validate all roles are non-empty",
     "user.roles.size() > 0 && user.roles.all(r, r.size() > 0)"),
    ("Conditional Expression", "Return age category",
     'user.age < 18 ? "minor" : "adult"'),
    ("Complex Boolean", "Validate API GET request",
     'request.method == "GET" && request.path.startsWith("/api/")'),
    ("Mathematical", "Age in months > 300", "user.age * 12 > 300"),
    ("Map Access", "Check for company email",
     'has(user.email) && user.email.endsWith("@example.com")'),
]


class ExpressionLibrary(VerticalScroll):
    """Left sidebar with searchable expression examples."""

    DEFAULT_CLASSES = "expression-library"

    def __init__(self) -> None:
        super().__init__()
        self.built_in_expressions = EXPRESSION_LIBRARY
        self.user_expressions: List[Tuple[str, str, str]] = []
        self.load_expressions()

    def load_expressions(self) -> None:
        """Load user expressions from config file."""
        try:
            self.user_expressions = load_user_expressions()
        except Exception:
            self.user_expressions = []
            # Will notify on mount

    def compose(self) -> ComposeResult:
        yield Label("📚 Expression Library", classes="lib-title")
        yield Input(placeholder="🔍 Search...", id="search-input", classes="search-box")

        # Add save button
        with Horizontal(classes="lib-actions"):
            yield Button("💾 Save Current", id="save-expr-btn", variant="primary", classes="save-btn")
            yield Label(f"({len(self.user_expressions)} saved)", id="saved-count", classes="saved-count")

        yield Container(id="expression-list")

    def on_mount(self) -> None:
        """Populate expression list on mount."""
        self._update_list()
        # Show info about config location
        config_file = get_expressions_file()
        self.notify(
            f"User expressions: {config_file}",
            severity="information",
            timeout=3
        )

    @on(Input.Changed, "#search-input")
    def filter_expressions(self, event: Input.Changed) -> None:
        """Filter expressions based on search."""
        self._update_list(event.value.lower())

    def _update_list(self, search: str = "") -> None:
        """Update the expression list."""
        container = self.query_one("#expression-list", Container)
        container.remove_children()

        # Add user expressions first (if any)
        if self.user_expressions:
            user_label = Label("👤 Your Expressions", classes="section-label")
            container.mount(user_label)

            for idx, (title, desc, expr) in enumerate(self.user_expressions):
                if search and search not in title.lower() and search not in expr.lower():
                    continue

                # Create expression card with delete button
                # Use index for ID since titles can have spaces
                card = Container(
                    Horizontal(
                        Label(title, classes="expr-title"),
                        Button("🗑", id=f"delete-{idx}", classes="delete-btn"),
                        classes="expr-title-row"
                    ),
                    Label(desc, classes="expr-desc"),
                    Label(expr, classes="expr-code"),
                    classes="expr-card user-expr-card"
                )
                container.mount(card)

        # Add built-in expressions
        if self.user_expressions:  # Add separator if we have user expressions
            builtin_label = Label("📖 Built-in Examples", classes="section-label")
            container.mount(builtin_label)

        for title, desc, expr in self.built_in_expressions:
            if search and search not in title.lower() and search not in expr.lower():
                continue

            # Create expression card (no delete button for built-ins)
            card = Container(
                Label(title, classes="expr-title"),
                Label(desc, classes="expr-desc"),
                Label(expr, classes="expr-code"),
                classes="expr-card"
            )
            container.mount(card)

        # Update saved count
        try:
            saved_count = self.query_one("#saved-count", Label)
            saved_count.update(f"({len(self.user_expressions)} saved)")
        except Exception:
            pass  # Widget might not be mounted yet

    def on_click(self, event: events.Click) -> None:
        """Handle clicks on expression cards."""
        # Find if we clicked within an expr-card
        widget = event.widget
        while widget and widget != self:
            if "expr-card" in widget.classes:
                code_label = widget.query_one(".expr-code", Label)
                if code_label:
                    expr_area = self.app.query_one("#expression-input", TextArea)
                    expr_area.clear()
                    expr_area.insert(str(code_label.render()))
                    self.notify("Loaded expression", severity="information")
                break
            widget = widget.parent

    @on(Button.Pressed, "#save-expr-btn")
    def handle_save_expression(self) -> None:
        """Handle save expression button."""
        # Get current expression from the input area
        expr_area = self.app.query_one("#expression-input", TextArea)
        expression = expr_area.text.strip()

        if not expression:
            self.notify("No expression to save", severity="warning")
            return

        # Trigger the save dialog in the main app
        self.app.show_save_dialog(expression)

    @on(Button.Pressed, ".delete-btn")
    def handle_delete_expression(self, event: Button.Pressed) -> None:
        """Handle delete button click on user expression."""
        button_id = event.button.id
        if not button_id or not button_id.startswith("delete-"):
            return

        # Extract index from button ID
        try:
            idx = int(button_id[7:])  # Remove "delete-" prefix
            expr_name = self.user_expressions[idx][0]
        except (ValueError, IndexError):
            self.notify("Could not identify expression to delete", severity="error")
            return

        try:
            if delete_expression(expr_name):
                # Reload expressions and update display
                self.load_expressions()
                self._update_list()
                self.notify(f"Deleted '{expr_name}'", severity="information")
            else:
                self.notify(f"Expression '{expr_name}' not found", severity="error")
        except Exception as e:
            self.notify(f"Error deleting expression: {e}", severity="error")


class ContextEditor(VerticalScroll):
    """Middle column for context management."""

    DEFAULT_CLASSES = "context-editor"

    def compose(self) -> ComposeResult:
        yield Label("📄 Context", classes="section-title")

        # Load Context section
        with Container(classes="load-section"):
            yield Label("⬇ Load Context", classes="subsection-title")
            yield Label("From URL", classes="field-label")
            with Horizontal(classes="url-row"):
                yield Input(
                    placeholder="https://api.example.com/context.json",
                    id="url-input",
                    classes="url-input"
                )
                yield Button("🔗", id="load-url-btn", classes="icon-btn")

            yield Label("From File", classes="field-label")
            with Horizontal(classes="file-row"):
                yield Input(
                    placeholder="./context.json or ./config.yaml",
                    id="file-input",
                    classes="file-input"
                )
                yield Button("📤 Upload JSON File", id="upload-btn",
                           variant="success", classes="upload-btn")

        # Context Data section
        with Container(classes="data-section"):
            with Horizontal(classes="data-header"):
                yield Label("📋 Context Data (JSON)", classes="subsection-title")
                yield Label("", id="validation-status", classes="validation")

            yield TextArea(
                '{\n  "user": {\n    "name": "Alice",\n    "age": 30,\n    '
                '"roles": ["admin", "user"]\n  },\n  "request": {\n    '
                '"method": "GET",\n    "path": "/api/data"\n  }\n}',
                language="json",
                theme="monokai",
                id="context-input",
                classes="context-area"
            )


class ResultsPanel(VerticalScroll):
    """Right column for evaluation and results."""

    DEFAULT_CLASSES = "results-panel"

    def compose(self) -> ComposeResult:
        # Evaluate section
        with Container(classes="eval-section"):
            yield Button("▶ Evaluate", id="eval-btn", variant="success",
                        classes="eval-button")

        # Expression input
        with Container(classes="expr-section"):
            yield Label("CEL Expression:", classes="field-label")
            yield TextArea(
                'user.age >= 18',
                language="cel",
                theme="monokai",
                id="expression-input",
                classes="expression-area"
            )

        # Results section
        with Container(classes="results-section"):
            yield Label("◎ Results", classes="subsection-title")
            yield Label("", id="current-expression", classes="current-expr")
            yield Static("", id="result-display", classes="result-content")
            yield Label("", id="result-meta", classes="result-meta")


class CELTuiApp(App):
    """CEL TUI implementing Figma design."""

    CSS = """
    Screen {
        background: #0a0e14;
    }

    Header {
        background: #0d1117;
        color: #00ff41;
    }

    Footer {
        background: #0d1117;
    }

    .main-container {
        layout: horizontal;
        height: 1fr;
    }

    /* Left Column - Expression Library */
    .expression-library {
        width: 1fr;
        background: #0d1117;
        border-right: solid #1a3a1a;
        padding: 1 2;
    }

    .lib-title {
        color: #00ff41;
        text-style: bold;
        margin-bottom: 1;
    }

    .search-box {
        margin-bottom: 1;
        border: solid #1a3a1a;
        background: #0a0e14;
        color: #00ff41;
    }

    #expression-list {
        height: auto;
    }

    .lib-actions {
        height: auto;
        margin-bottom: 1;
    }

    .save-btn {
        width: 1fr;
        background: #1a3a1a;
        color: #00ff41;
    }

    .saved-count {
        color: #6b8e6b;
        margin-left: 1;
        width: auto;
    }

    .section-label {
        color: #00ff41;
        text-style: bold;
        margin-top: 1;
        margin-bottom: 1;
    }

    .expr-card {
        background: #0a0e14;
        border: solid #1a3a1a;
        padding: 1;
        margin-bottom: 1;
    }

    .expr-card:hover {
        background: #0d1a0d;
        border: solid #00ff41;
    }

    .user-expr-card {
        border: solid #00ff41;
        background: #0d1a0d;
    }

    .expr-title-row {
        height: auto;
    }

    .expr-title {
        color: #00ff41;
        text-style: bold;
        width: 1fr;
    }

    .delete-btn {
        width: 5;
        min-width: 5;
        background: #3a1a1a;
        color: #ff4444;
    }

    .delete-btn:hover {
        background: #ff4444;
        color: #0a0e14;
    }

    .expr-desc {
        color: #6b8e6b;
        margin-top: 0;
    }

    .expr-code {
        color: #00cc33;
        text-style: italic;
        margin-top: 1;
    }

    /* Middle Column - Context */
    .context-editor {
        width: 2fr;
        background: #0a0e14;
        border-right: solid #1a3a1a;
        padding: 1 2;
    }

    .section-title {
        color: #00ff41;
        text-style: bold;
        margin-bottom: 1;
    }

    .subsection-title {
        color: #00ff41;
        margin-bottom: 1;
    }

    .load-section {
        margin-bottom: 2;
    }

    .field-label {
        color: #6b8e6b;
        margin-bottom: 1;
        margin-top: 1;
    }

    .url-row, .file-row {
        height: auto;
        margin-bottom: 1;
    }

    .url-input, .file-input {
        width: 1fr;
        border: solid #1a3a1a;
        background: #0d1117;
        color: #00ff41;
    }

    .icon-btn {
        width: 5;
        min-width: 5;
        margin-left: 1;
    }

    .upload-btn {
        margin-left: 1;
        background: #1a3a1a;
        color: #00ff41;
    }

    .data-section {
        height: 1fr;
    }

    .data-header {
        height: auto;
    }

    .validation {
        color: #00ff41;
        margin-left: 1;
    }

    .context-area {
        height: 1fr;
        border: solid #1a3a1a;
    }

    /* Right Column - Results */
    .results-panel {
        width: 1fr;
        background: #0a0e14;
        padding: 1 2;
    }

    .eval-section {
        margin-bottom: 2;
    }

    .eval-button {
        width: 100%;
        background: #1a3a1a;
        color: #00ff41;
    }

    .eval-button:hover {
        background: #00ff41;
        color: #0a0e14;
    }

    .expr-section {
        margin-bottom: 2;
    }

    .expression-area {
        height: 10;
        border: solid #1a3a1a;
    }

    .results-section {
        height: 1fr;
    }

    .current-expr {
        color: #6b8e6b;
        text-style: italic;
        margin-bottom: 1;
        padding: 0 1;
    }

    .result-content {
        background: #0d1117;
        border: solid #1a3a1a;
        padding: 2;
        color: #00ff41;
        min-height: 10;
    }

    .result-meta {
        color: #6b8e6b;
        margin-top: 1;
        text-style: italic;
    }

    Input {
        height: 3;
    }

    Button {
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "quit", "Quit", show=True),
        Binding("ctrl+e", "evaluate", "Evaluate", show=True),
        Binding("f1", "show_help", "Help", show=True),
    ]

    TITLE = "CEL Expression Evaluator"
    SUB_TITLE = "Common Expression Language Testing & Development Environment"

    def __init__(self) -> None:
        super().__init__()
        self.context: Optional[Context] = None
        self.context_dict: Dict[str, Any] = {}

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(classes="main-container"):
            yield ExpressionLibrary()
            yield ContextEditor()
            yield ResultsPanel()
        yield Footer()

    def on_mount(self) -> None:
        """Initialize with default context."""
        self._load_context_from_editor()
        self.notify("CEL Evaluator ready • Press Ctrl+E to evaluate • F1 for help",
                   severity="information")

    @on(Button.Pressed, "#eval-btn")
    def handle_eval_button(self) -> None:
        """Handle evaluate button press."""
        self.action_evaluate()

    @on(Button.Pressed, "#load-url-btn")
    def handle_load_url(self) -> None:
        """Load context from URL."""
        url_input = self.query_one("#url-input", Input)
        url = url_input.value.strip()

        if not url:
            self.notify("Please enter a URL", severity="warning")
            return

        try:
            self.notify(f"Loading from {url}...", severity="information")
            with urlopen(url, timeout=10) as response:
                content = response.read().decode('utf-8')
                data = json.loads(content)

            # Update context editor
            context_area = self.query_one("#context-input", TextArea)
            context_area.clear()
            context_area.insert(json.dumps(data, indent=2))

            self._load_context_from_editor()
            self.notify("✓ Loaded from URL", severity="information")

        except Exception as e:
            self.notify(f"✗ Error loading URL: {e}", severity="error")

    @on(Button.Pressed, "#upload-btn")
    def handle_upload(self) -> None:
        """Load context from file."""
        file_input = self.query_one("#file-input", Input)
        file_path = file_input.value.strip()

        if not file_path:
            self.notify("Please enter a file path", severity="warning")
            return

        try:
            path = Path(file_path).expanduser()
            if not path.exists():
                self.notify(f"✗ File not found: {file_path}", severity="error")
                return

            content = path.read_text()

            # Parse based on extension
            if path.suffix in ['.yaml', '.yml']:
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)

            # Update context editor
            context_area = self.query_one("#context-input", TextArea)
            context_area.clear()
            context_area.insert(json.dumps(data, indent=2))

            self._load_context_from_editor()
            self.notify("✓ Loaded from file", severity="information")

        except Exception as e:
            self.notify(f"✗ Error loading file: {e}", severity="error")

    def _load_context_from_editor(self) -> None:
        """Load context from the JSON editor."""
        try:
            context_area = self.query_one("#context-input", TextArea)
            context_json = context_area.text

            # Parse JSON
            self.context_dict = json.loads(context_json)

            # Create CEL context
            self.context = Context()
            add_stdlib_to_context(self.context)

            for key, value in self.context_dict.items():
                self.context.add_variable(key, value)

            # Update validation status
            validation = self.query_one("#validation-status", Label)
            validation.update("✓ Valid 11 lines")
            validation.styles.color = "#00ff41"

        except json.JSONDecodeError as e:
            validation = self.query_one("#validation-status", Label)
            validation.update("✗ Invalid JSON")
            validation.styles.color = "#ff4444"
            self.notify(f"Invalid JSON: {e}", severity="error")

    @work(exclusive=True, thread=True)
    async def action_evaluate(self) -> None:
        """Evaluate the CEL expression."""
        try:
            # Ensure context is loaded
            if self.context is None:
                self._load_context_from_editor()

            expr_area = self.query_one("#expression-input", TextArea)
            expression = expr_area.text.strip()

            if not expression:
                self.notify("Expression is empty", severity="warning")
                result_display = self.query_one("#result-display", Static)
                result_display.update(
                    '[dim]ℹ️  No expression yet\n\n'
                    'Click "Evaluate" to run the expression[/dim]'
                )
                # Clear current expression display
                current_expr_label = self.query_one("#current-expression", Label)
                current_expr_label.update("")
                return

            # Show what we're evaluating with syntax highlighting
            current_expr_label = self.query_one("#current-expression", Label)
            expr_preview = expression if len(expression) <= 60 else expression[:57] + "..."
            highlighted = self._syntax_highlight_expr(expr_preview)
            current_expr_label.update(f"⟳ Evaluating: {highlighted}")

            # Measure evaluation time
            start_time = datetime.now()
            result = evaluate(expression, self.context)
            end_time = datetime.now()
            elapsed_ms = (end_time - start_time).total_seconds() * 1000

            # Update result display
            self._update_result(result, elapsed_ms, expression)

            self.notify("✓ Evaluated successfully", severity="information")

        except Exception as e:
            self._update_result_error(str(e))
            self.notify(f"✗ Error: {e}", severity="error")

    def _update_result(self, result: Any, elapsed_ms: float, expression: str = "") -> None:
        """Update the result display with success."""
        result_display = self.query_one("#result-display", Static)
        result_meta = self.query_one("#result-meta", Label)
        current_expr_label = self.query_one("#current-expression", Label)

        # Format result
        if isinstance(result, str):
            result_str = f'"{result}"'
        elif isinstance(result, (list, dict)):
            result_str = json.dumps(result, indent=2)
        else:
            result_str = str(result)

        result_display.update(result_str)
        result_meta.update(f"type: {type(result).__name__} | {elapsed_ms:.2f}ms")

        # Update current expression label to show what was evaluated with syntax highlighting
        if expression:
            expr_preview = expression if len(expression) <= 60 else expression[:57] + "..."
            highlighted = self._syntax_highlight_expr(expr_preview)
            current_expr_label.update(f"✓ {highlighted}")

    def _syntax_highlight_expr(self, expr: str) -> str:
        """Apply basic syntax highlighting to CEL expression using Rich markup."""
        import re

        # Use a token-based approach to avoid overlapping markup
        tokens = []
        i = 0

        # Simple tokenizer
        while i < len(expr):
            # Skip whitespace
            if expr[i].isspace():
                tokens.append(('space', expr[i]))
                i += 1
                continue

            # String literals
            if expr[i] in '"\'':
                quote = expr[i]
                j = i + 1
                while j < len(expr) and expr[j] != quote:
                    if expr[j] == '\\' and j + 1 < len(expr):
                        j += 2
                    else:
                        j += 1
                if j < len(expr):
                    j += 1
                tokens.append(('string', expr[i:j]))
                i = j
                continue

            # Numbers
            if expr[i].isdigit():
                j = i
                while j < len(expr) and (expr[j].isdigit() or expr[j] == '.'):
                    j += 1
                tokens.append(('number', expr[i:j]))
                i = j
                continue

            # Identifiers/keywords
            if expr[i].isalpha() or expr[i] == '_':
                j = i
                while j < len(expr) and (expr[j].isalnum() or expr[j] == '_'):
                    j += 1
                word = expr[i:j]
                # Check if keyword
                if word in ['true', 'false', 'null', 'in', 'has']:
                    tokens.append(('keyword', word))
                else:
                    # Check if function (followed by '(')
                    k = j
                    while k < len(expr) and expr[k].isspace():
                        k += 1
                    if k < len(expr) and expr[k] == '(':
                        tokens.append(('function', word))
                    else:
                        tokens.append(('identifier', word))
                i = j
                continue

            # Multi-char operators
            if i + 1 < len(expr):
                two_char = expr[i:i+2]
                if two_char in ['>=', '<=', '==', '!=', '&&', '||']:
                    tokens.append(('operator', two_char))
                    i += 2
                    continue

            # Single char operators and punctuation
            if expr[i] in '+-*/%<>!&|()[]{},.':
                tokens.append(('operator', expr[i]))
                i += 1
                continue

            # Anything else
            tokens.append(('other', expr[i]))
            i += 1

        # Build highlighted string
        result = []
        for token_type, text in tokens:
            if token_type == 'keyword':
                result.append(f'[bold green]{text}[/bold green]')
            elif token_type == 'string':
                result.append(f'[yellow]{text}[/yellow]')
            elif token_type == 'number':
                result.append(f'[cyan]{text}[/cyan]')
            elif token_type == 'function':
                result.append(f'[magenta]{text}[/magenta]')
            elif token_type == 'operator':
                result.append(f'[bold]{text}[/bold]')
            else:
                result.append(text)

        return ''.join(result)

    def _update_result_error(self, error_msg: str) -> None:
        """Update result display with error."""
        result_display = self.query_one("#result-display", Static)
        result_meta = self.query_one("#result-meta", Label)

        result_display.update(f"[red]✗ Error:[/red]\n\n{error_msg}")
        result_meta.update("")

    def show_save_dialog(self, expression: str) -> None:
        """
        Show save dialog for current expression.

        For now, uses a simple prompt system. In future, can be replaced with a modal.
        """
        # For this implementation, we'll use notifications to prompt user
        # A full modal dialog would require more complex Textual screens

        # Prompt for name via notification
        self.notify(
            "💾 To save expression:\n"
            "1. Note your expression\n"
            "2. Edit config file directly\n"
            f"3. Location: {get_expressions_file()}\n"
            "\nOr use the CLI to add expressions programmatically",
            severity="information",
            timeout=10
        )

        # For now, show a simplified save with auto-generated name
        # Count existing user expressions to create unique name
        library = self.query_one(ExpressionLibrary)
        expr_count = len(library.user_expressions) + 1
        auto_name = f"Custom Expression {expr_count}"

        try:
            # Auto-save with generated name and prompt user to edit file for custom name
            add_expression(
                name=auto_name,
                description="User-defined expression (edit config to customize)",
                expression=expression
            )

            # Reload the library
            library.load_expressions()
            library._update_list()

            self.notify(
                f"✓ Saved as '{auto_name}'\n"
                f"Edit {get_expressions_file()} to customize name/description",
                severity="information",
                timeout=8
            )
        except ValueError as e:
            self.notify(f"✗ Error saving: {e}", severity="error")
        except Exception as e:
            self.notify(f"✗ Unexpected error: {e}", severity="error")

    def action_show_help(self) -> None:
        """Show help information."""
        help_text = """
[bold #00ff41]CEL Evaluator - Help[/bold #00ff41]

[#00ff41]Keyboard Shortcuts:[/#00ff41]
• Ctrl+E - Evaluate expression
• Ctrl+Q - Quit application
• F1     - Show this help

[#00ff41]Expression Library (Left):[/#00ff41]
Click any example to load it into the expression editor

[#00ff41]Context Loading (Middle):[/#00ff41]
• Enter URL and click 🔗 to load from API
• Enter file path and click Upload to load from file
• Or edit JSON directly in the editor

[#00ff41]Evaluation (Right):[/#00ff41]
• Edit expression in the text area
• Click "Evaluate" or press Ctrl+E
• Results appear below with timing info
        """
        self.notify(help_text.strip(), severity="information", timeout=15)


def run_tui() -> None:
    """Entry point to run the CEL TUI application."""
    app = CELTuiApp()
    app.run()


if __name__ == "__main__":
    run_tui()
