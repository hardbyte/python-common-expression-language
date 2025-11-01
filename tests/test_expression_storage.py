"""
Tests for expression storage functionality.

Tests the OS-specific configuration directory and user expression persistence.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from cel.expression_storage import (
    add_expression,
    delete_expression,
    get_config_dir,
    get_expressions_file,
    load_user_expressions,
    save_user_expressions,
    update_expression,
)


class TestConfigDir:
    """Test configuration directory location."""

    def test_get_config_dir_creates_directory(self):
        """Test that get_config_dir creates the directory if it doesn't exist."""
        config_dir = get_config_dir()
        assert config_dir.exists()
        assert config_dir.is_dir()

    def test_config_dir_in_home(self):
        """Test that config dir is within user's home directory."""
        config_dir = get_config_dir()
        home = Path.home()
        assert str(config_dir).startswith(str(home))

    def test_expressions_file_path(self):
        """Test that expressions file path is correct."""
        expressions_file = get_expressions_file()
        assert expressions_file.name == "expressions.json"
        assert expressions_file.parent == get_config_dir()


class TestSaveLoad:
    """Test saving and loading expressions."""

    def test_save_and_load_empty_list(self, tmp_path):
        """Test saving and loading an empty expression list."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Save empty list
            save_user_expressions([])

            # Load and verify
            expressions = load_user_expressions()
            assert expressions == []

    def test_save_and_load_single_expression(self, tmp_path):
        """Test saving and loading a single expression."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Save expression
            test_expr = ("Test Expr", "A test expression", "1 + 1")
            save_user_expressions([test_expr])

            # Load and verify
            expressions = load_user_expressions()
            assert len(expressions) == 1
            assert expressions[0] == test_expr

    def test_save_and_load_multiple_expressions(self, tmp_path):
        """Test saving and loading multiple expressions."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Save expressions
            test_exprs = [
                ("Expr 1", "First expression", "1 + 1"),
                ("Expr 2", "Second expression", "2 * 3"),
                ("Expr 3", "Third expression", '"hello"'),
            ]
            save_user_expressions(test_exprs)

            # Load and verify
            expressions = load_user_expressions()
            assert len(expressions) == 3
            assert expressions == test_exprs

    def test_load_nonexistent_file(self, tmp_path):
        """Test loading from non-existent file returns empty list."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "nonexistent.json"
            mock_file.return_value = test_file

            expressions = load_user_expressions()
            assert expressions == []

    def test_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON returns empty list."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "invalid.json"
            mock_file.return_value = test_file

            # Write invalid JSON
            test_file.write_text("{ invalid json }")

            expressions = load_user_expressions()
            assert expressions == []

    def test_load_wrong_format(self, tmp_path):
        """Test loading wrong format returns empty list."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "wrong_format.json"
            mock_file.return_value = test_file

            # Write wrong format (not a list)
            test_file.write_text('{"key": "value"}')

            expressions = load_user_expressions()
            assert expressions == []

    def test_save_preserves_json_structure(self, tmp_path):
        """Test that saved JSON has correct structure."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Save expression
            test_expr = ("Test", "Description", "expression")
            save_user_expressions([test_expr])

            # Read and verify JSON structure
            with test_file.open() as f:
                data = json.load(f)

            assert isinstance(data, list)
            assert len(data) == 1
            assert data[0]["name"] == "Test"
            assert data[0]["description"] == "Description"
            assert data[0]["expression"] == "expression"


class TestAddExpression:
    """Test adding expressions."""

    def test_add_expression_to_empty_file(self, tmp_path):
        """Test adding first expression to empty file."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            add_expression("Test", "A test", "1 + 1")

            expressions = load_user_expressions()
            assert len(expressions) == 1
            assert expressions[0] == ("Test", "A test", "1 + 1")

    def test_add_multiple_expressions(self, tmp_path):
        """Test adding multiple expressions sequentially."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            add_expression("First", "First expr", "1")
            add_expression("Second", "Second expr", "2")
            add_expression("Third", "Third expr", "3")

            expressions = load_user_expressions()
            assert len(expressions) == 3

    def test_add_duplicate_name_raises_error(self, tmp_path):
        """Test that adding duplicate name raises ValueError."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            add_expression("Test", "First", "1")

            with pytest.raises(ValueError, match="already exists"):
                add_expression("Test", "Duplicate", "2")


class TestDeleteExpression:
    """Test deleting expressions."""

    def test_delete_existing_expression(self, tmp_path):
        """Test deleting an existing expression."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Add expression
            add_expression("Test", "A test", "1 + 1")
            assert len(load_user_expressions()) == 1

            # Delete it
            result = delete_expression("Test")
            assert result is True
            assert len(load_user_expressions()) == 0

    def test_delete_nonexistent_expression(self, tmp_path):
        """Test deleting non-existent expression returns False."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            result = delete_expression("Nonexistent")
            assert result is False

    def test_delete_one_of_many(self, tmp_path):
        """Test deleting one expression from many."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Add multiple
            add_expression("First", "A", "1")
            add_expression("Second", "B", "2")
            add_expression("Third", "C", "3")

            # Delete middle one
            result = delete_expression("Second")
            assert result is True

            expressions = load_user_expressions()
            assert len(expressions) == 2
            assert expressions[0][0] == "First"
            assert expressions[1][0] == "Third"


class TestUpdateExpression:
    """Test updating expressions."""

    def test_update_expression_name_only(self, tmp_path):
        """Test updating just the name of an expression."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Add expression
            add_expression("Old Name", "Description", "expression")

            # Update name
            update_expression("Old Name", "New Name", "Description", "expression")

            expressions = load_user_expressions()
            assert len(expressions) == 1
            assert expressions[0][0] == "New Name"

    def test_update_all_fields(self, tmp_path):
        """Test updating all fields of an expression."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Add expression
            add_expression("Name", "Old desc", "old expr")

            # Update all fields
            update_expression("Name", "New Name", "New desc", "new expr")

            expressions = load_user_expressions()
            assert len(expressions) == 1
            assert expressions[0] == ("New Name", "New desc", "new expr")

    def test_update_nonexistent_raises_error(self, tmp_path):
        """Test updating non-existent expression raises ValueError."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            with pytest.raises(ValueError, match="not found"):
                update_expression("Nonexistent", "New", "desc", "expr")

    def test_update_to_duplicate_name_raises_error(self, tmp_path):
        """Test updating to a duplicate name raises ValueError."""
        with patch('cel.expression_storage.get_expressions_file') as mock_file:
            test_file = tmp_path / "test_expressions.json"
            mock_file.return_value = test_file

            # Add two expressions
            add_expression("First", "A", "1")
            add_expression("Second", "B", "2")

            # Try to rename Second to First
            with pytest.raises(ValueError, match="already exists"):
                update_expression("Second", "First", "B", "2")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
