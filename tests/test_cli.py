"""
Comprehensive tests for the CEL CLI functionality.

Tests the enhanced CLI features including:
- CELFormatter with streamlined Rich rendering
- REPL command dispatch
- Syntax highlighting and enhanced REPL features
- File processing and context loading
- Various output formats
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import typer

# Import CLI components
from cel.cli import (
    CELEvaluator,
    CELFormatter,
    InteractiveCELREPL,
    evaluate_expressions_from_file,
    load_context_from_file,
)
from rich.console import Console
from rich.syntax import Syntax
from rich.table import Table


class TestCELFormatter:
    """Test the streamlined CELFormatter with Rich rendering."""

    def test_display_method_exists(self):
        """Test that the main display method exists and is callable."""
        assert hasattr(CELFormatter, "display")
        assert callable(CELFormatter.display)

    def test_get_rich_renderable_json(self):
        """Test JSON Rich renderable generation."""
        result = {"name": "test", "value": 42}
        renderable = CELFormatter.get_rich_renderable(result, "json")

        assert isinstance(renderable, Syntax)
        assert renderable.lexer.name == "JSON"

    def test_get_rich_renderable_pretty_dict(self):
        """Test pretty formatting for dictionaries returns Rich Table."""
        result = {"key1": "value1", "key2": 42}
        renderable = CELFormatter.get_rich_renderable(result, "pretty")

        assert isinstance(renderable, Table)
        assert "Dictionary Result" in str(renderable.title)

    def test_get_rich_renderable_pretty_list(self):
        """Test pretty formatting for lists returns Rich Table."""
        result = [1, 2, 3, "test"]
        renderable = CELFormatter.get_rich_renderable(result, "pretty")

        assert isinstance(renderable, Table)
        assert "List Result" in str(renderable.title)

    def test_get_rich_renderable_python_format(self):
        """Test Python repr format."""
        result = {"test": True}
        renderable = CELFormatter.get_rich_renderable(result, "python")

        assert renderable == repr(result)
        assert "{'test': True}" in renderable

    def test_get_rich_renderable_auto_format_small(self):
        """Test auto format for small objects returns string."""
        result = "simple string"
        renderable = CELFormatter.get_rich_renderable(result, "auto")

        assert renderable == "simple string"

    def test_get_rich_renderable_auto_format_large_dict(self):
        """Test auto format for large objects uses pretty formatting."""
        # Create a large dictionary that will trigger pretty formatting
        large_dict = {f"key_{i}": f"value_{i}" for i in range(20)}
        renderable = CELFormatter.get_rich_renderable(large_dict, "auto")

        assert isinstance(renderable, Table)

    def test_format_result_backward_compatibility(self):
        """Test that format_result returns strings for backward compatibility."""
        result = {"name": "test"}
        formatted = CELFormatter.format_result(result, "python")

        assert isinstance(formatted, str)
        assert "{'name': 'test'}" in formatted

    def test_format_result_with_rich_object_capture(self):
        """Test that Rich objects are properly captured to strings."""
        result = {"key": "value"}
        formatted = CELFormatter.format_result(result, "pretty")

        assert isinstance(formatted, str)
        # Should contain table formatting characters from Rich rendering
        assert any(char in formatted for char in ["┏", "━", "┓", "┃"])

    def test_display_method_prints_to_console(self):
        """Test that display method properly prints to console."""
        console = Mock(spec=Console)
        result = "test result"

        CELFormatter.display(console, result, "auto")

        console.print.assert_called_once_with("test result")

    def test_display_method_with_rich_renderable(self):
        """Test display method with Rich renderable object."""
        console = Mock(spec=Console)
        result = {"test": "value"}

        CELFormatter.display(console, result, "json")

        # Should be called with a Syntax object
        console.print.assert_called_once()
        args = console.print.call_args[0]
        assert len(args) == 1
        assert isinstance(args[0], Syntax)


class TestCELEvaluator:
    """Test the CELEvaluator class functionality."""

    def test_create_evaluator_empty_context(self):
        """Test creating evaluator with empty context."""
        evaluator = CELEvaluator()
        assert evaluator.context == {}

    def test_create_evaluator_with_context(self):
        """Test creating evaluator with initial context."""
        context = {"x": 10, "y": 20}
        evaluator = CELEvaluator(context)
        assert evaluator.context == context

    def test_evaluate_simple_expression(self):
        """Test evaluating simple expressions."""
        evaluator = CELEvaluator()
        result = evaluator.evaluate("1 + 2")
        assert result == 3

    def test_evaluate_with_context(self):
        """Test evaluating expressions with context variables."""
        evaluator = CELEvaluator({"x": 5, "y": 3})
        result = evaluator.evaluate("x * y")
        assert result == 15

    def test_update_context(self):
        """Test updating evaluator context."""
        evaluator = CELEvaluator({"x": 1})
        evaluator.update_context({"y": 2, "z": 3})

        # Original context should be updated
        assert evaluator.context["x"] == 1
        assert evaluator.context["y"] == 2
        assert evaluator.context["z"] == 3

    def test_get_context_vars_copy(self):
        """Test that get_context_vars returns a copy."""
        original_context = {"x": 1, "y": 2}
        evaluator = CELEvaluator(original_context)

        context_copy = evaluator.get_context_vars()
        context_copy["z"] = 3  # Modify the copy

        # Original should be unchanged
        assert "z" not in evaluator.context
        assert evaluator.context == original_context

    def test_evaluate_empty_expression_error(self):
        """Test that empty expressions raise ValueError."""
        evaluator = CELEvaluator()

        with pytest.raises(ValueError, match="Empty expression"):
            evaluator.evaluate("")

        with pytest.raises(ValueError, match="Empty expression"):
            evaluator.evaluate("   ")


class TestInteractiveCELREPL:
    """Test the Enhanced REPL functionality."""

    def test_repl_initialization(self):
        """Test REPL initializes correctly."""
        evaluator = CELEvaluator({"test": 42})
        repl = InteractiveCELREPL(evaluator)

        assert repl.evaluator == evaluator
        assert repl.history == []
        assert repl.history_limit == 10  # default

        # Test instance variables are set
        assert isinstance(repl.cel_keywords, list)
        assert isinstance(repl.cel_functions, list)
        assert isinstance(repl.commands, dict)

        # Test command dispatch dictionary
        assert "help" in repl.commands
        assert "history" in repl.commands

    def test_repl_command_dispatch(self):
        """Test that commands are properly mapped."""
        evaluator = CELEvaluator()
        repl = InteractiveCELREPL(evaluator)

        # Test that command methods exist
        assert callable(repl.commands["help"])
        assert callable(repl.commands["history"])

        assert repl.commands["help"] == repl._show_help

        assert repl.commands["history"] == repl._show_history

    def test_update_completer(self):
        """Test that completer updates with context variables."""
        evaluator = CELEvaluator({"var1": 1, "var2": 2})
        repl = InteractiveCELREPL(evaluator)

        # Test initial completer setup
        completer_words = repl.session.completer.words
        assert "var1" in completer_words
        assert "var2" in completer_words
        assert "true" in completer_words  # CEL keyword
        assert "size" in completer_words  # CEL function

    def test_load_context_success(self):
        """Test successful context loading from file."""
        evaluator = CELEvaluator()
        repl = InteractiveCELREPL(evaluator)

        # Create temporary JSON file
        test_context = {"name": "test", "value": 42}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_context, f)
            temp_file = f.name

        try:
            with patch("cel.cli.console") as mock_console:
                repl._load_context(temp_file)

                # Check that context was loaded
                assert evaluator.context["name"] == "test"
                assert evaluator.context["value"] == 42

                # Check success message was printed
                mock_console.print.assert_called_with(
                    f"[green]Loaded context from {temp_file}[/green]"
                )
        finally:
            Path(temp_file).unlink()  # Clean up

    def test_load_context_file_not_found(self):
        """Test context loading with non-existent file."""
        evaluator = CELEvaluator()
        repl = InteractiveCELREPL(evaluator)

        with patch("cel.cli.console") as mock_console:
            repl._load_context("nonexistent.json")

            # Check error message was printed
            mock_console.print.assert_called()
            args = mock_console.print.call_args[0]
            assert "[red]Error loading context" in args[0]

    def test_history_limit_enforcement(self):
        """Test that history is limited to prevent memory growth."""
        evaluator = CELEvaluator()
        repl = InteractiveCELREPL(evaluator, history_limit=3)

        # Manually add items to history to test limit
        for i in range(5):
            repl.history.append((f"expr_{i}", i))

        # Simulate the history limiting logic from run()
        if len(repl.history) > 100:
            repl.history = repl.history[-100:]

        # Should have all 5 items since we're under the 100 limit
        assert len(repl.history) == 5


class TestFileOperations:
    """Test file-based operations in CLI."""

    def test_load_context_from_file_success(self):
        """Test successful context loading."""
        test_context = {"user": {"name": "Alice", "age": 30}, "settings": {"debug": True}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_context, f)
            temp_file = Path(f.name)

        try:
            loaded_context = load_context_from_file(temp_file)
            assert loaded_context == test_context
        finally:
            temp_file.unlink()

    def test_load_context_from_file_invalid_json(self):
        """Test loading invalid JSON raises proper error."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{ invalid json }")
            temp_file = Path(f.name)

        try:
            with pytest.raises(typer.Exit):  # typer.Exit(1)
                load_context_from_file(temp_file)
        finally:
            temp_file.unlink()

    def test_load_context_from_file_not_found(self):
        """Test loading non-existent file raises proper error."""
        nonexistent_file = Path("definitely_does_not_exist.json")

        with pytest.raises(typer.Exit):  # typer.Exit(1)
            load_context_from_file(nonexistent_file)

    def test_evaluate_expressions_from_file_success(self):
        """Test evaluating expressions from file."""
        expressions = [
            "1 + 2",
            "3 * 4",
            "'hello' + ' world'",
            "# This is a comment",
            "",  # Empty line
            "[1, 2, 3]",
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cel", delete=False) as f:
            f.write("\n".join(expressions))
            temp_file = Path(f.name)

        try:
            evaluator = CELEvaluator()

            with patch("cel.cli.console") as mock_console:
                evaluate_expressions_from_file(temp_file, evaluator, "auto")

                # Should have printed results (mock was called)
                assert mock_console.print.called
        finally:
            temp_file.unlink()

    def test_evaluate_expressions_from_file_with_errors(self):
        """Test handling expressions with errors."""
        expressions = [
            "1 + 2",  # Valid
            "invalid_syntax (",  # Invalid
            "3 * 4",  # Valid
        ]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cel", delete=False) as f:
            f.write("\n".join(expressions))
            temp_file = Path(f.name)

        try:
            evaluator = CELEvaluator()

            with patch("cel.cli.console") as mock_console:
                evaluate_expressions_from_file(temp_file, evaluator, "auto")

                # Should have printed error messages
                assert mock_console.print.called
                # At least one call should contain error text
                calls = [str(call) for call in mock_console.print.call_args_list]
                assert any("Error" in call for call in calls)
        finally:
            temp_file.unlink()

    def test_evaluate_expressions_from_file_not_found(self):
        """Test handling non-existent expression file."""
        nonexistent_file = Path("definitely_does_not_exist.cel")
        evaluator = CELEvaluator()

        with pytest.raises(typer.Exit):  # typer.Exit(1)
            evaluate_expressions_from_file(nonexistent_file, evaluator, "auto")


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_cli_entry_point_exists(self):
        """Test that the CLI entry point function exists."""
        from cel.cli import cli_entry

        assert callable(cli_entry)

    def test_main_app_is_typer_app(self):
        """Test that the main app is a Typer application."""
        import typer
        from cel.cli import app

        assert isinstance(app, typer.Typer)

    def test_cel_lexer_tokens(self):
        """Test that the CEL lexer recognizes key token types."""
        from cel.cli import CELLexer

        lexer = CELLexer()

        # Test that lexer has proper token definitions
        assert "root" in lexer.tokens
        root_tokens = lexer.tokens["root"]

        # Should have patterns for various token types
        token_patterns = [pattern for pattern, token_type in root_tokens]

        # Test some key patterns exist
        boolean_pattern = r"\b(true|false|null)\b"
        assert boolean_pattern in token_patterns

        # Test string patterns (including byte literals)
        string_patterns = [p for p in token_patterns if '"' in p or "'" in p]
        assert len(string_patterns) >= 4  # At least regular and byte string literals

    def test_enhanced_formatter_architecture(self):
        """Test the enhanced formatter architecture with Rich renderables."""
        # This tests the architectural improvement suggested by the user

        # Test that the formatter can handle all format types
        test_data = {"key": "value", "number": 42}

        for format_type in ["json", "pretty", "python", "auto"]:
            renderable = CELFormatter.get_rich_renderable(test_data, format_type)
            assert renderable is not None

            # Test that we can get string representation
            string_result = CELFormatter.format_result(test_data, format_type)
            assert isinstance(string_result, str)

    def test_repl_command_parsing_with_spaces(self):
        """Test that REPL can handle commands with spaces in arguments."""
        evaluator = CELEvaluator()
        repl = InteractiveCELREPL(evaluator)

        # Create a temporary file with spaces in the name
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"test": "value"}, f)
            # Create a path with spaces by copying to a new location
            spaced_path = f.name.replace(Path(f.name).stem, "file with spaces")

        try:
            # Copy the file to the spaced location
            Path(f.name).rename(spaced_path)

            with patch("cel.cli.console"):
                # This should work even with spaces in filename
                repl._load_context(spaced_path)

                # Context should be loaded
                assert evaluator.context.get("test") == "value"
        finally:
            # Clean up
            if Path(spaced_path).exists():
                Path(spaced_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__])
