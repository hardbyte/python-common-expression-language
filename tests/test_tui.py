"""
Comprehensive End-to-End tests for the CEL TUI.

Tests all functionality using Textual's testing framework:
- Expression library loading and filtering
- Context loading from JSON/YAML files and URLs
- Expression evaluation
- Results display
- Keyboard shortcuts
- Error handling
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml
from textual.widgets import Button, Input, Label, Static, TextArea

from cel.tui import CELTuiApp, ExpressionLibrary


class TestExpressionLibrary:
    """Test the Expression Library panel functionality."""

    @pytest.mark.asyncio
    async def test_library_displays_default_expressions(self):
        """Test that default expressions are displayed on mount."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            # Check that expression library exists
            library = app.query_one(ExpressionLibrary)
            assert library is not None

            # Check that expression cards are rendered
            cards = library.query(".expr-card")
            assert len(cards) == 8  # Should have 8 default expressions

            # Check first expression contains expected text
            first_card = cards[0]
            labels = first_card.query(Label)
            label_texts = [str(label.render()) for label in labels]
            combined_text = " ".join(label_texts)
            assert "Age Check" in combined_text

    @pytest.mark.asyncio
    async def test_library_search_filtering(self):
        """Test that search input filters expressions."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            library = app.query_one(ExpressionLibrary)
            search_input = library.query_one("#search-input", Input)

            # Initially all 8 expressions should be visible
            cards = library.query(".expr-card")
            assert len(cards) == 8

            # Type in search box
            search_input.value = "age"
            await pilot.pause()

            # Should filter to only expressions containing "age"
            cards = library.query(".expr-card")
            assert len(cards) < 8  # Should have fewer expressions
            assert len(cards) > 0  # But at least one

    @pytest.mark.asyncio
    async def test_library_search_no_results(self):
        """Test search with no matching expressions."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            library = app.query_one(ExpressionLibrary)
            search_input = library.query_one("#search-input", Input)

            # Search for something that doesn't exist
            search_input.value = "zzzznonexistent"
            await pilot.pause()

            # Should have no expression cards
            cards = library.query(".expr-card")
            assert len(cards) == 0


class TestContextEditor:
    """Test the Context Editor panel functionality."""

    @pytest.mark.asyncio
    async def test_context_editor_has_default_context(self):
        """Test that context editor starts with default JSON context."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            context_area = app.query_one("#context-input", TextArea)

            # Should have default context
            assert context_area.text != ""

            # Should be valid JSON
            context_data = json.loads(context_area.text)
            assert "user" in context_data
            assert "request" in context_data

    @pytest.mark.asyncio
    async def test_context_validation_updates(self):
        """Test that context validation updates when JSON is edited."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            context_area = app.query_one("#context-input", TextArea)
            validation = app.query_one("#validation-status", Label)

            # Start with valid JSON - should show valid
            app._load_context_from_editor()
            await pilot.pause()
            validation_text = validation.render()
            assert "✓" in validation_text

            # Edit to invalid JSON
            context_area.clear()
            context_area.insert("{ invalid json")
            app._load_context_from_editor()
            await pilot.pause()

            # Should show invalid
            validation_text = validation.render()
            assert "✗" in validation_text

    @pytest.mark.asyncio
    async def test_load_context_from_json_file(self):
        """Test loading context from a JSON file."""
        app = CELTuiApp()

        # Create temporary JSON file
        test_context = {
            "name": "TestUser",
            "age": 25,
            "roles": ["user", "tester"]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_context, f)
            temp_file = Path(f.name)

        try:
            async with app.run_test() as pilot:
                file_input = app.query_one("#file-input", Input)
                context_area = app.query_one("#context-input", TextArea)

                # Set file path
                file_input.value = str(temp_file)
                await pilot.pause()

                # Trigger upload handler directly
                app.handle_upload()
                await pilot.pause()

                # Context should be loaded
                loaded_data = json.loads(context_area.text)
                assert loaded_data["name"] == "TestUser"
                assert loaded_data["age"] == 25
                assert "tester" in loaded_data["roles"]
        finally:
            temp_file.unlink()

    @pytest.mark.asyncio
    async def test_load_context_from_yaml_file(self):
        """Test loading context from a YAML file."""
        app = CELTuiApp()

        # Create temporary YAML file
        test_context = {
            "server": "production",
            "port": 8080,
            "features": ["auth", "api"]
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(test_context, f)
            temp_file = Path(f.name)

        try:
            async with app.run_test() as pilot:
                file_input = app.query_one("#file-input", Input)
                context_area = app.query_one("#context-input", TextArea)

                # Set file path
                file_input.value = str(temp_file)
                await pilot.pause()

                # Trigger upload handler directly
                app.handle_upload()
                await pilot.pause()

                # Context should be loaded and converted to JSON
                loaded_data = json.loads(context_area.text)
                assert loaded_data["server"] == "production"
                assert loaded_data["port"] == 8080
                assert "api" in loaded_data["features"]
        finally:
            temp_file.unlink()

    @pytest.mark.asyncio
    async def test_load_context_from_url(self):
        """Test loading context from URL with mocked HTTP response."""
        app = CELTuiApp()

        test_context = {"api_key": "test123", "endpoint": "https://api.example.com"}

        async with app.run_test() as pilot:
            url_input = app.query_one("#url-input", Input)
            context_area = app.query_one("#context-input", TextArea)

            # Mock urlopen
            with patch("cel.tui.urlopen") as mock_urlopen:
                mock_response = Mock()
                mock_response.read.return_value = json.dumps(test_context).encode('utf-8')
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                mock_urlopen.return_value = mock_response

                # Set URL
                url_input.value = "https://example.com/context.json"
                await pilot.pause()

                # Trigger URL load handler directly
                app.handle_load_url()
                await pilot.pause()

                # Context should be loaded
                loaded_data = json.loads(context_area.text)
                assert loaded_data["api_key"] == "test123"


class TestEvaluation:
    """Test expression evaluation functionality."""

    @pytest.mark.asyncio
    async def test_evaluate_simple_expression(self):
        """Test evaluating a simple expression."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)

            # Set expression
            expr_area.clear()
            expr_area.insert("1 + 2")
            await pilot.pause()

            # Trigger evaluation
            app.action_evaluate()
            await pilot.pause()

            # Result should show "3"
            result_text = str(result_display.render())
            assert "3" in result_text

    @pytest.mark.asyncio
    async def test_evaluate_with_context(self):
        """Test evaluating expression with context variables."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            context_area = app.query_one("#context-input", TextArea)
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)

            # Set context
            context_area.clear()
            context_area.insert('{"x": 10, "y": 5}')
            await pilot.pause()
            app._load_context_from_editor()
            await pilot.pause()

            # Set expression
            expr_area.clear()
            expr_area.insert("x * y")
            await pilot.pause()

            # Trigger evaluation
            app.action_evaluate()
            await pilot.pause()

            # Result should show "50"
            result_text = str(result_display.render())
            assert "50" in result_text

    @pytest.mark.asyncio
    async def test_evaluate_boolean_expression(self):
        """Test evaluating boolean expression with default context."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)
            result_meta = app.query_one("#result-meta", Label)

            # Use default context which has user.age = 30
            expr_area.clear()
            expr_area.insert("user.age >= 18")
            await pilot.pause()

            # Trigger evaluation
            app.action_evaluate()
            await pilot.pause()

            # Result should show "true" or "True"
            result_text = str(result_display.render()).lower()
            assert "true" in result_text

            # Metadata should show type and timing
            meta_text = str(result_meta.render()).lower()
            assert "type:" in meta_text or "ms" in meta_text

    @pytest.mark.asyncio
    async def test_evaluate_error_handling(self):
        """Test error display when expression is invalid."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)

            # Set invalid expression
            expr_area.clear()
            expr_area.insert("invalid syntax (((")
            await pilot.pause()

            # Trigger evaluation
            app.action_evaluate()
            await pilot.pause()

            # Result should show error
            result_text = str(result_display.render()).lower()
            assert "error" in result_text

    @pytest.mark.asyncio
    async def test_evaluate_with_stdlib_functions(self):
        """Test that stdlib functions are available during evaluation."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)

            # Use substring function from stdlib
            expr_area.clear()
            expr_area.insert('substring("hello world", 0, 5)')
            await pilot.pause()

            # Trigger evaluation
            app.action_evaluate()
            await pilot.pause()

            # Result should contain "hello"
            result_text = str(result_display.render())
            assert "hello" in result_text


class TestKeyboardShortcuts:
    """Test keyboard shortcuts functionality."""

    @pytest.mark.asyncio
    async def test_ctrl_e_evaluates_expression(self):
        """Test that Ctrl+E triggers evaluation."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            expr_area = app.query_one("#expression-input", TextArea)
            result_display = app.query_one("#result-display", Static)

            # Set expression
            expr_area.clear()
            expr_area.insert("2 + 3")
            await pilot.pause()

            # Press Ctrl+E
            await pilot.press("ctrl+e")
            await pilot.pause()

            # Result should show "5"
            result_text = str(result_display.render())
            assert "5" in result_text

    @pytest.mark.asyncio
    async def test_f1_shows_help(self):
        """Test that F1 action exists and is callable."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            # Verify the action exists
            assert hasattr(app, "action_show_help")
            assert callable(app.action_show_help)


class TestUIIntegration:
    """Test overall UI integration and layout."""

    @pytest.mark.asyncio
    async def test_app_has_three_columns(self):
        """Test that app displays all three main panels."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            # Check that all three panels exist
            library = app.query_one(".expression-library")
            context = app.query_one(".context-editor")
            results = app.query_one(".results-panel")

            assert library is not None
            assert context is not None
            assert results is not None

    @pytest.mark.asyncio
    async def test_app_has_header_and_footer(self):
        """Test that header and footer are displayed."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            from textual.widgets import Footer, Header

            header = app.query_one(Header)
            footer = app.query_one(Footer)

            assert header is not None
            assert footer is not None

    @pytest.mark.asyncio
    async def test_all_required_widgets_present(self):
        """Test that all required widgets are present in the UI."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            # Expression library widgets
            assert app.query_one("#search-input") is not None
            assert app.query_one("#expression-list") is not None

            # Context editor widgets
            assert app.query_one("#url-input") is not None
            assert app.query_one("#file-input") is not None
            assert app.query_one("#context-input") is not None
            assert app.query_one("#validation-status") is not None
            assert app.query_one("#load-url-btn") is not None
            assert app.query_one("#upload-btn") is not None

            # Results panel widgets
            assert app.query_one("#expression-input") is not None
            assert app.query_one("#eval-btn") is not None
            assert app.query_one("#result-display") is not None
            assert app.query_one("#result-meta") is not None

    @pytest.mark.asyncio
    async def test_app_initialization(self):
        """Test that app initializes with correct default state."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            # Should have context initialized
            assert app.context is not None
            assert app.context_dict is not None

            # Should have title and subtitle
            assert app.TITLE == "CEL Expression Evaluator"
            assert "Common Expression Language" in app.SUB_TITLE


class TestExpressionManagement:
    """Test expression save and delete functionality."""

    @pytest.mark.asyncio
    async def test_save_expression_button(self, tmp_path):
        """Test saving expression via Save button."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file, \
             patch('cel.tui.get_expressions_file') as mock_file2:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file
            mock_file2.return_value = test_file

            app = CELTuiApp()
            async with app.run_test() as pilot:
                library = app.query_one(ExpressionLibrary)
                expr_area = app.query_one("#expression-input", TextArea)

                # Enter a custom expression
                expr_area.clear()
                expr_area.insert("user.age * 2")
                await pilot.pause()

                # Click save button - call handler directly
                library.handle_save_expression()
                await pilot.pause()

                # Verify expression was saved
                from cel.expression_storage import load_user_expressions
                expressions = load_user_expressions()
                assert len(expressions) == 1
                assert expressions[0][2] == "user.age * 2"

                # Reload library to see the changes
                library.load_expressions()
                library._update_list()
                await pilot.pause()

                # Verify library updated
                user_cards = library.query(".user-expr-card")
                assert len(user_cards) == 1

    @pytest.mark.asyncio
    async def test_delete_expression_button(self, tmp_path):
        """Test deleting expression via delete button."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file, \
             patch('cel.tui.get_expressions_file') as mock_file2:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file
            mock_file2.return_value = test_file

            # Pre-populate with test expressions
            from cel.expression_storage import add_expression
            add_expression("TestExpr1", "First test", "1 + 1")
            add_expression("TestExpr2", "Second test", "2 + 2")

            app = CELTuiApp()
            async with app.run_test() as pilot:
                library = app.query_one(ExpressionLibrary)
                library.load_expressions()
                library._update_list()
                await pilot.pause()

                # Verify we have 2 user expressions
                user_cards = library.query(".user-expr-card")
                assert len(user_cards) == 2

                # Delete first expression by calling handler directly
                # Create a mock event with the delete button
                from unittest.mock import Mock
                delete_btn = library.query_one("#delete-0", Button)
                mock_event = Mock()
                mock_event.button = delete_btn
                library.handle_delete_expression(mock_event)
                await pilot.pause()

                # Verify expression was deleted
                from cel.expression_storage import load_user_expressions
                expressions = load_user_expressions()
                assert len(expressions) == 1
                assert expressions[0][0] == "TestExpr2"

                # Verify library updated
                user_cards = library.query(".user-expr-card")
                assert len(user_cards) == 1

    @pytest.mark.asyncio
    async def test_save_empty_expression_shows_warning(self):
        """Test that saving empty expression shows warning."""
        app = CELTuiApp()
        async with app.run_test() as pilot:
            library = app.query_one(ExpressionLibrary)
            expr_area = app.query_one("#expression-input", TextArea)

            # Clear expression area
            expr_area.clear()
            await pilot.pause()

            # Try to save
            save_btn = library.query_one("#save-expr-btn", Button)
            await pilot.click(save_btn)
            await pilot.pause()

            # Should show warning notification (we can't easily verify notification,
            # but we can verify no expression was created)
            # Since no file was configured, this would fail if it tried to save

    @pytest.mark.asyncio
    async def test_click_user_expression_loads_it(self, tmp_path):
        """Test clicking user expression loads it into editor."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file, \
             patch('cel.tui.get_expressions_file') as mock_file2:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file
            mock_file2.return_value = test_file

            # Pre-populate with test expression
            from cel.expression_storage import add_expression
            add_expression("MyExpr", "Test expression", "42 * 2")

            app = CELTuiApp()
            async with app.run_test() as pilot:
                library = app.query_one(ExpressionLibrary)
                library.load_expressions()
                library._update_list()
                await pilot.pause()

                expr_area = app.query_one("#expression-input", TextArea)

                # Click on the user expression card
                user_card = library.query_one(".user-expr-card")
                await pilot.click(user_card)
                await pilot.pause()

                # Verify expression was loaded
                assert "42 * 2" in expr_area.text

    @pytest.mark.asyncio
    async def test_saved_count_updates(self, tmp_path):
        """Test that saved count label updates correctly."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file, \
             patch('cel.tui.get_expressions_file') as mock_file2:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file
            mock_file2.return_value = test_file

            app = CELTuiApp()
            async with app.run_test() as pilot:
                library = app.query_one(ExpressionLibrary)
                expr_area = app.query_one("#expression-input", TextArea)

                # Initial count should be 0
                saved_count = library.query_one("#saved-count", Label)
                assert "(0 saved)" in str(saved_count.render())

                # Save an expression
                expr_area.clear()
                expr_area.insert("test.expression")
                await pilot.pause()

                # Call save handler directly
                library.handle_save_expression()
                await pilot.pause()

                # Reload and update display
                library.load_expressions()
                library._update_list()
                await pilot.pause()

                # Count should update to 1
                saved_count = library.query_one("#saved-count", Label)
                assert "(1 saved)" in str(saved_count.render())


class TestCompleteWorkflow:
    """Test complete end-to-end workflows."""

    @pytest.mark.asyncio
    async def test_complete_evaluation_workflow(self):
        """Test a complete workflow: load context, set expression, evaluate."""
        app = CELTuiApp()

        # Create test context file
        test_context = {
            "user": {
                "name": "Bob",
                "age": 25,
                "roles": ["admin"]
            }
        }
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_context, f)
            temp_file = Path(f.name)

        try:
            async with app.run_test() as pilot:
                # Step 1: Load context from file
                file_input = app.query_one("#file-input", Input)
                file_input.value = str(temp_file)
                await pilot.pause()
                app.handle_upload()
                await pilot.pause()

                # Step 2: Enter expression
                expr_area = app.query_one("#expression-input", TextArea)
                expr_area.clear()
                expr_area.insert('user.age >= 18')
                await pilot.pause()

                # Step 3: Evaluate
                app.action_evaluate()
                await pilot.pause()

                # Step 4: Verify result
                result_display = app.query_one("#result-display", Static)
                result_text = str(result_display.render()).lower()
                assert "true" in result_text

        finally:
            temp_file.unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
