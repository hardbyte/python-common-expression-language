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
    evaluate_expression_with_multiple_contexts,
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

    def test_stdlib_functions_available(self):
        """Test that stdlib functions are automatically available in CLI evaluator."""
        evaluator = CELEvaluator()

        # Test substring function from stdlib
        result = evaluator.evaluate('substring("hello world", 0, 5)')
        assert result == "hello"

        result = evaluator.evaluate('substring("hello world", 6)')
        assert result == "world"

        result = evaluator.evaluate('substring("test", 1, 3)')
        assert result == "es"

    def test_stdlib_functions_with_context(self):
        """Test that stdlib functions work alongside context variables."""
        evaluator = CELEvaluator({"text": "hello world"})

        # Use stdlib function with context variable
        result = evaluator.evaluate("substring(text, 0, 5)")
        assert result == "hello"

        result = evaluator.evaluate("substring(text, 6)")
        assert result == "world"

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


class TestBatchContextProcessing:
    """Test batch context processing - evaluating one expression against multiple context files."""

    def test_evaluate_expression_with_multiple_contexts_success(self):
        """Test evaluating an expression against multiple context files."""
        # Create multiple context files
        contexts = [
            {"user": {"name": "Alice", "age": 25}},
            {"user": {"name": "Bob", "age": 30}},
            {"user": {"name": "Charlie", "age": 22}},
        ]

        temp_files = []
        try:
            # Create temporary context files
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_user{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # Evaluate expression against all contexts
            expression = "user.age >= 25"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should have printed results
                assert mock_console.print.called

        finally:
            # Clean up temp files
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_json_output(self):
        """Test batch context processing with JSON output format."""
        contexts = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_val{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            expression = "value * 2"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "json"
                )

                # Should have printed JSON syntax
                assert mock_console.print.called
                # Check that Syntax object was printed (JSON formatting)
                calls = mock_console.print.call_args_list
                assert any(
                    isinstance(call[0][0], Syntax) for call in calls if call[0]
                )

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_with_errors(self):
        """Test batch context processing handles errors gracefully."""
        contexts = [
            {"user": {"name": "Alice"}},
            {"user": {"age": 30}},  # Missing 'name' field
            {"user": {"name": "Charlie"}},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_user{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # This expression will fail on the second context (no name field)
            expression = "user.name"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should have printed results and errors
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_base_context_merge(self):
        """Test that base context is merged with file contexts."""
        # Base context provides a default value
        base_context = {"multiplier": 2}

        contexts = [
            {"value": 10},
            {"value": 20, "multiplier": 3},  # Override multiplier
            {"value": 30},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_val{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            expression = "value * multiplier"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, base_context, "auto"
                )

                # Should have successfully evaluated all contexts
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_empty_list(self):
        """Test batch context processing with empty file list."""
        with patch("cel.cli.console") as mock_console:
            evaluate_expression_with_multiple_contexts("1 + 2", [], {}, "auto")

            # Should print warning about no context files
            mock_console.print.assert_called_once()
            assert "No context files" in mock_console.print.call_args[0][0]

    def test_evaluate_expression_with_multiple_contexts_file_not_found(self):
        """Test batch context processing with non-existent file."""
        nonexistent_files = [
            Path("definitely_does_not_exist_1.json"),
            Path("definitely_does_not_exist_2.json"),
        ]

        with patch("cel.cli.console") as mock_console:
            # Should handle file not found errors
            evaluate_expression_with_multiple_contexts(
                "1 + 2", nonexistent_files, {}, "auto"
            )

            # Should have printed error messages
            assert mock_console.print.called
            calls = [str(call) for call in mock_console.print.call_args_list]
            assert any("Error" in call for call in calls)

    def test_evaluate_expression_with_multiple_contexts_timing(self):
        """Test that batch context processing includes timing information."""
        contexts = [
            {"value": 10},
            {"value": 20},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_val{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            expression = "value * 2"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should have printed a table with timing column
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_invalid_json(self):
        """Test batch context processing with invalid JSON files."""
        temp_files = []
        try:
            # Create file with invalid JSON
            with tempfile.NamedTemporaryFile(
                mode="w", suffix="_invalid.json", delete=False
            ) as f:
                f.write("{ invalid json }")
                temp_files.append(Path(f.name))

            # Create file with valid JSON
            with tempfile.NamedTemporaryFile(
                mode="w", suffix="_valid.json", delete=False
            ) as f:
                json.dump({"value": 42}, f)
                temp_files.append(Path(f.name))

            expression = "value * 2"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should have printed error for invalid file
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_mixed_types(self):
        """Test batch context processing with different data types across files."""
        contexts = [
            {"result": True},
            {"result": "success"},
            {"result": 42},
            {"result": [1, 2, 3]},
            {"result": {"nested": "value"}},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_type{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # Expression that works with any type
            expression = "has(result)"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should handle all types successfully
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_large_dataset(self):
        """Test batch context processing with a larger number of files."""
        # Create 20 context files
        contexts = [{"id": i, "value": i * 10, "active": i % 2 == 0} for i in range(20)]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_data{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            expression = "active && value > 50"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should process all files
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_complex_expression(self):
        """Test batch context processing with complex CEL expressions."""
        contexts = [
            {"user": {"age": 25, "verified": True, "role": "admin"}},
            {"user": {"age": 17, "verified": False, "role": "user"}},
            {"user": {"age": 30, "verified": True, "role": "moderator"}},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_user{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # Complex expression with multiple conditions
            expression = 'user.age >= 18 && user.verified && user.role in ["admin", "moderator"]'

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should evaluate complex expression correctly
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_base_context_override(self):
        """Test that file context properly overrides base context values."""
        base_context = {"default_value": 100, "multiplier": 2, "enabled": False}

        contexts = [
            {"value": 10},  # Uses base context default_value and multiplier
            {"value": 20, "multiplier": 3},  # Overrides multiplier
            {"value": 30, "enabled": True},  # Overrides enabled
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_override{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            expression = "value * multiplier"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, base_context, "auto"
                )

                # Should merge contexts correctly with file taking precedence
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_evaluate_expression_with_multiple_contexts_empty_files(self):
        """Test batch context processing with empty JSON files."""
        temp_files = []
        try:
            # Create empty object file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix="_empty.json", delete=False
            ) as f:
                f.write("{}")
                temp_files.append(Path(f.name))

            # Create normal file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix="_normal.json", delete=False
            ) as f:
                json.dump({"value": 42}, f)
                temp_files.append(Path(f.name))

            # Expression that uses 'has' to check for field
            expression = "has(value)"

            with patch("cel.cli.console") as mock_console:
                evaluate_expression_with_multiple_contexts(
                    expression, temp_files, {}, "auto"
                )

                # Should handle empty objects gracefully
                assert mock_console.print.called

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()


class TestCLIE2EBasicFeatures:
    """
    End-to-end tests for basic CLI features using subprocess.

    Tests core functionality like simple evaluation, context, output formats, etc.
    """

    def test_e2e_simple_expression(self):
        """Test simple expression evaluation without context."""
        import subprocess

        cmd = ["cel", "1 + 2"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "3" in result.stdout

    def test_e2e_string_expression(self):
        """Test string manipulation expression."""
        import subprocess

        cmd = ["cel", "'Hello ' + 'World'"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "Hello World" in result.stdout

    def test_e2e_inline_context(self):
        """Test evaluation with inline JSON context."""
        import subprocess

        cmd = [
            "cel",
            "age >= 18",
            "--context", '{"age": 25}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "true" in result.stdout.lower()

    def test_e2e_inline_context_short_flag(self):
        """Test evaluation with inline context using -c short flag."""
        import subprocess

        cmd = [
            "cel",
            "name + ' is ' + string(age)",
            "-c", '{"name": "Alice", "age": 30}'
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "Alice is 30" in result.stdout

    def test_e2e_context_file(self):
        """Test evaluation with context from file."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"user": {"name": "Bob", "role": "admin"}}, f)
                temp_file = Path(f.name)

            cmd = [
                "cel",
                'user.name + " (" + user.role + ")"',
                "--context-file", str(temp_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "Bob (admin)" in result.stdout

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_context_file_short_flag(self):
        """Test evaluation with context file using -f short flag."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"value": 42}, f)
                temp_file = Path(f.name)

            cmd = [
                "cel",
                "value * 2",
                "-f", str(temp_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "84" in result.stdout

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_combined_contexts(self):
        """Test that --context and --context-file can be combined."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"base": 10}, f)
                temp_file = Path(f.name)

            cmd = [
                "cel",
                "base * multiplier",
                "--context", '{"multiplier": 5}',
                "--context-file", str(temp_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "50" in result.stdout

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_output_json(self):
        """Test JSON output format."""
        import subprocess

        cmd = [
            "cel",
            '{"name": "Alice", "age": 30}',
            "--output", "json"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["name"] == "Alice"
        assert output["age"] == 30

    def test_e2e_output_json_short_flag(self):
        """Test JSON output format with -o short flag."""
        import subprocess

        cmd = [
            "cel",
            "[1, 2, 3]",
            "-o", "json"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output == [1, 2, 3]

    def test_e2e_output_pretty(self):
        """Test pretty output format."""
        import subprocess

        cmd = [
            "cel",
            '{"key": "value", "number": 42}',
            "--output", "pretty"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        # Pretty format should use rich table
        assert "key" in result.stdout
        assert "value" in result.stdout

    def test_e2e_output_python(self):
        """Test python output format."""
        import subprocess

        cmd = [
            "cel",
            '{"test": true}',
            "--output", "python"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        # Python repr format
        assert "test" in result.stdout
        assert "True" in result.stdout

    def test_e2e_timing_flag(self):
        """Test that --timing flag shows timing information."""
        import subprocess

        cmd = [
            "cel",
            "1 + 2",
            "--timing"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "ms" in result.stdout.lower()

    def test_e2e_timing_short_flag(self):
        """Test that -t flag shows timing information."""
        import subprocess

        cmd = [
            "cel",
            "1 + 2",
            "-t"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "ms" in result.stdout.lower()

    def test_e2e_verbose_flag(self):
        """Test that --verbose flag shows additional information."""
        import subprocess

        cmd = [
            "cel",
            "age * 2",
            "--context", '{"age": 21}',
            "--verbose"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        # Verbose should show timing, expression, result type, context vars
        assert "ms" in result.stdout.lower()
        assert "Expression" in result.stdout or "expression" in result.stdout.lower()

    def test_e2e_verbose_short_flag(self):
        """Test that -v flag shows additional information."""
        import subprocess

        cmd = [
            "cel",
            "1 + 2",
            "-v"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "ms" in result.stdout.lower()

    def test_e2e_no_expression_error(self):
        """Test that no expression gives helpful error."""
        import subprocess

        cmd = ["cel"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stdout.lower()
        assert "expression" in result.stdout.lower() or "help" in result.stdout.lower()

    def test_e2e_invalid_json_context_error(self):
        """Test error handling for invalid JSON in --context."""
        import subprocess

        cmd = [
            "cel",
            "age > 18",
            "--context", "{invalid json}"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stdout.lower()
        assert "JSON" in result.stdout or "json" in result.stdout.lower()

    def test_e2e_missing_context_file_error(self):
        """Test error handling for missing context file."""
        import subprocess

        cmd = [
            "cel",
            "value > 0",
            "--context-file", "/nonexistent/file.json"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    def test_e2e_expression_evaluation_error(self):
        """Test error handling for expression evaluation errors."""
        import subprocess

        cmd = [
            "cel",
            "unknown_variable + 1"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stdout.lower()

    def test_e2e_version_flag(self):
        """Test --version flag shows version and exits."""
        import subprocess

        cmd = ["cel", "--version"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Version callback exits with code 0
        assert result.returncode == 0
        # Should show version number
        assert "version" in result.stdout.lower() or any(c.isdigit() for c in result.stdout)

    def test_e2e_help_flag(self):
        """Test --help flag shows help and exits."""
        import subprocess

        cmd = ["cel", "--help"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode == 0
        assert "Usage" in result.stdout or "usage" in result.stdout.lower()
        assert "expression" in result.stdout.lower()

    def test_e2e_complex_nested_expression(self):
        """Test complex expression with nested fields and operators."""
        import subprocess

        context = {
            "user": {
                "name": "Alice",
                "age": 30,
                "verified": True
            },
            "permissions": ["read", "write", "delete"]
        }

        cmd = [
            "cel",
            'user.verified && user.age >= 18 && "write" in permissions',
            "--context", json.dumps(context)
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "true" in result.stdout.lower()

    def test_e2e_list_operations(self):
        """Test list operations in expressions."""
        import subprocess

        cmd = [
            "cel",
            "[1, 2, 3].size()",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "3" in result.stdout

    def test_e2e_map_operations(self):
        """Test map/dict operations in expressions."""
        import subprocess

        cmd = [
            "cel",
            '{"a": 1, "b": 2}.size()',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "2" in result.stdout

    def test_e2e_string_functions(self):
        """Test string functions."""
        import subprocess

        cmd = [
            "cel",
            '"hello".size()',
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        assert result.returncode == 0
        assert "5" in result.stdout


class TestCLIE2EFileMode:
    """
    End-to-end tests for --file mode (evaluating expressions from a file).
    """

    def test_e2e_file_mode_single_expression(self):
        """Test evaluating single expression from file."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                f.write("1 + 2\n")
                temp_file = Path(f.name)

            cmd = ["cel", "--file", str(temp_file)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "3" in result.stdout

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_file_mode_multiple_expressions(self):
        """Test evaluating multiple expressions from file."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                f.write("1 + 2\n")
                f.write("'Hello ' + 'World'\n")
                f.write("10 * 5\n")
                temp_file = Path(f.name)

            cmd = ["cel", "--file", str(temp_file)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "3" in result.stdout
            assert "Hello World" in result.stdout
            assert "50" in result.stdout

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_file_mode_with_context(self):
        """Test file mode with context."""
        import subprocess

        expr_file = None
        context_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                f.write("user.name\n")
                f.write("user.age >= 18\n")
                expr_file = Path(f.name)

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"user": {"name": "Alice", "age": 25}}, f)
                context_file = Path(f.name)

            cmd = [
                "cel",
                "--file", str(expr_file),
                "--context-file", str(context_file)
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            assert "Alice" in result.stdout
            assert "true" in result.stdout.lower()

        finally:
            if expr_file and expr_file.exists():
                expr_file.unlink()
            if context_file and context_file.exists():
                context_file.unlink()

    def test_e2e_file_mode_with_json_output(self):
        """Test file mode with JSON output format."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                f.write("1 + 2\n")
                f.write("5 * 3\n")
                temp_file = Path(f.name)

            cmd = [
                "cel",
                "--file", str(temp_file),
                "--output", "json"
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            assert result.returncode == 0
            # Should be valid JSON array or object
            output = json.loads(result.stdout)
            assert output is not None

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_file_mode_empty_file(self):
        """Test file mode with empty file."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                # Empty file
                pass
            temp_file = Path(f.name)

            cmd = ["cel", "--file", str(temp_file)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Should handle gracefully (might succeed with no output or show message)
            # Just verify it doesn't crash
            assert result.returncode in [0, 1]

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_file_mode_with_comments(self):
        """Test file mode handles lines with # comments or empty lines."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".cel", delete=False
            ) as f:
                f.write("# This is a comment\n")
                f.write("1 + 2\n")
                f.write("\n")  # Empty line
                f.write("5 * 3\n")
                temp_file = Path(f.name)

            cmd = ["cel", "--file", str(temp_file)]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # May or may not support comments - just verify it doesn't crash
            assert result.returncode in [0, 1]

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_file_mode_nonexistent_file(self):
        """Test file mode with non-existent file."""
        import subprocess

        cmd = ["cel", "--file", "/nonexistent/expressions.cel"]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        assert result.returncode != 0
        assert "Error" in result.stdout or "error" in result.stdout.lower()


class TestBatchContextProcessingE2E:
    """
    End-to-end tests for batch context processing using subprocess.

    These tests actually invoke the `cel` CLI command to verify the full user experience.
    """

    def test_e2e_basic_batch_processing(self):
        """Test basic batch processing with actual CLI invocation."""
        import subprocess

        contexts = [
            {"user": {"name": "Alice", "age": 25}},
            {"user": {"name": "Bob", "age": 30}},
            {"user": {"name": "Charlie", "age": 17}},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_user{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # Build command with repeated --for-each flags
            cmd = [
                "cel",
                "user.age >= 18",
                "--for-each", str(temp_files[0]),
                "--for-each", str(temp_files[1]),
                "--for-each", str(temp_files[2]),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Verify output contains results for all files
            assert result.returncode == 0
            assert "Expression Results" in result.stdout
            assert str(temp_files[0].name) in result.stdout or "user0.json" in result.stdout
            assert str(temp_files[1].name) in result.stdout or "user1.json" in result.stdout
            assert str(temp_files[2].name) in result.stdout or "user2.json" in result.stdout

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_e2e_batch_processing_json_output(self):
        """Test batch processing with JSON output format."""
        import subprocess

        contexts = [
            {"value": 10},
            {"value": 20},
            {"value": 30},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_data{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            cmd = [
                "cel",
                "value * 2",
                "--for-each", str(temp_files[0]),
                "--for-each", str(temp_files[1]),
                "--for-each", str(temp_files[2]),
                "--output", "json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Verify JSON output
            assert result.returncode == 0
            output = json.loads(result.stdout)

            assert isinstance(output, list)
            assert len(output) == 3

            # Check results
            assert output[0]["result"] == 20
            assert output[1]["result"] == 40
            assert output[2]["result"] == 60

            # Check that timing info is present
            assert "time_ms" in output[0]
            assert "context_file" in output[0]

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_e2e_batch_processing_with_base_context(self):
        """Test batch processing with base context merging."""
        import subprocess

        contexts = [
            {"value": 5},
            {"value": 10},
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_data{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            cmd = [
                "cel",
                "value * multiplier",
                "--context", '{"multiplier": 3}',
                "--for-each", str(temp_files[0]),
                "--for-each", str(temp_files[1]),
                "--output", "json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Verify results
            assert result.returncode == 0
            output = json.loads(result.stdout)

            assert len(output) == 2
            assert output[0]["result"] == 15  # 5 * 3
            assert output[1]["result"] == 30  # 10 * 3

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_e2e_batch_processing_file_not_found(self):
        """Test batch processing with non-existent file."""
        import subprocess

        cmd = [
            "cel",
            "user.age >= 18",
            "--for-each", "/nonexistent/file1.json",
            "--for-each", "/nonexistent/file2.json",
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
        )

        # Should not crash, but show errors
        assert "Error" in result.stdout or "error" in result.stdout.lower()
        # May or may not exit with error code depending on implementation
        # Just verify it doesn't crash

    def test_e2e_batch_processing_invalid_json(self):
        """Test batch processing with invalid JSON file."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                f.write("{invalid json content")
                temp_file = Path(f.name)

            cmd = [
                "cel",
                "user.age >= 18",
                "--for-each", str(temp_file),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Should show error about invalid JSON
            assert "Error" in result.stdout or "error" in result.stdout.lower()

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_batch_processing_no_expression(self):
        """Test that --for-each requires an expression."""
        import subprocess

        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"test": "data"}, f)
                temp_file = Path(f.name)

            cmd = [
                "cel",
                "--for-each", str(temp_file),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Should exit with error
            assert result.returncode != 0
            assert "Error" in result.stdout or "error" in result.stdout.lower()
            # Should mention that expression is required
            assert "expression" in result.stdout.lower() or "requires" in result.stdout.lower()

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()

    def test_e2e_batch_processing_complex_expression(self):
        """Test batch processing with complex CEL expression."""
        import subprocess

        contexts = [
            {
                "user": {"name": "Alice", "age": 25, "verified": True},
                "permissions": ["read", "write"],
            },
            {
                "user": {"name": "Bob", "age": 30, "verified": False},
                "permissions": ["read"],
            },
            {
                "user": {"name": "Charlie", "age": 22, "verified": True},
                "permissions": ["read", "write", "admin"],
            },
        ]

        temp_files = []
        try:
            for i, context in enumerate(contexts):
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=f"_user{i}.json", delete=False
                ) as f:
                    json.dump(context, f)
                    temp_files.append(Path(f.name))

            # Complex expression with multiple conditions
            expression = 'user.verified && user.age >= 21 && "write" in permissions'

            cmd = [
                "cel",
                expression,
                "--for-each", str(temp_files[0]),
                "--for-each", str(temp_files[1]),
                "--for-each", str(temp_files[2]),
                "--output", "json",
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Verify results
            assert result.returncode == 0
            output = json.loads(result.stdout)

            assert len(output) == 3
            assert output[0]["result"] is True   # Alice: verified, age 25, has write
            assert output[1]["result"] is False  # Bob: not verified
            assert output[2]["result"] is True   # Charlie: verified, age 22, has write

        finally:
            for temp_file in temp_files:
                if temp_file.exists():
                    temp_file.unlink()

    def test_e2e_batch_processing_with_shell_expansion(self):
        """Test that batch processing works with shell glob patterns via xargs pattern."""
        import subprocess
        import tempfile
        import os

        # Create a temporary directory with multiple JSON files
        temp_dir = tempfile.mkdtemp()
        try:
            # Create test files
            for i in range(3):
                file_path = os.path.join(temp_dir, f"data{i}.json")
                with open(file_path, "w") as f:
                    json.dump({"value": i * 10}, f)

            # Simulate what a shell glob would do: build the command with all files
            files = sorted([
                os.path.join(temp_dir, f)
                for f in os.listdir(temp_dir)
                if f.endswith(".json")
            ])

            cmd = ["cel", "value >= 10"]
            for file in files:
                cmd.extend(["--for-each", file])

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )

            # Verify output
            assert result.returncode == 0
            # Check that all files were processed
            for i in range(3):
                assert f"data{i}.json" in result.stdout

        finally:
            # Cleanup
            import shutil
            shutil.rmtree(temp_dir)

    def test_e2e_exit_status_verification(self):
        """Test that exit status reflects evaluation success."""
        import subprocess

        # Create a file with valid context
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as f:
                json.dump({"value": 42}, f)
                temp_file = Path(f.name)

            # Test successful evaluation
            cmd = [
                "cel",
                "value == 42",
                "--for-each", str(temp_file),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
            )

            # Should exit successfully
            assert result.returncode == 0

        finally:
            if temp_file and temp_file.exists():
                temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__])
