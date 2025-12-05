"""Tests for the compile() function and Program class.

The compile() function pre-compiles a CEL expression into a Program object
that can be executed multiple times with different contexts, providing
significant performance benefits for repeated evaluation of the same expression.
"""

import datetime

import cel
from cel import Context
import pytest


class TestCompileBasics:
    """Basic compilation and execution tests."""

    def test_compile_simple_expression(self):
        """Test compiling a simple arithmetic expression."""
        program = cel.compile("1 + 2")
        result = program.execute()
        assert result == 3

    def test_compile_returns_program(self):
        """Test that compile() returns a Program object."""
        program = cel.compile("true")
        assert hasattr(program, "execute")

    def test_program_repr(self):
        """Test Program __repr__ method."""
        program = cel.compile("x + y")
        repr_str = repr(program)
        assert "Program" in repr_str
        assert "x + y" in repr_str

    def test_execute_without_context(self):
        """Test executing a program without context."""
        program = cel.compile("42")
        assert program.execute() == 42

    def test_execute_with_none_context(self):
        """Test executing with explicit None context."""
        program = cel.compile("true && false")
        assert program.execute(None) is False


class TestCompileWithContext:
    """Tests for compile/execute with various context types."""

    def test_execute_with_dict_context(self):
        """Test executing with a dictionary context."""
        program = cel.compile("x + y")
        result = program.execute({"x": 10, "y": 20})
        assert result == 30

    def test_execute_with_context_object(self):
        """Test executing with a Context object."""
        program = cel.compile("name + ' is ' + string(age)")
        ctx = Context()
        ctx.add_variable("name", "Alice")
        ctx.add_variable("age", 30)
        result = program.execute(ctx)
        assert result == "Alice is 30"

    def test_execute_same_program_different_contexts(self):
        """Test executing the same program with different contexts."""
        program = cel.compile("price * quantity")
        
        result1 = program.execute({"price": 10, "quantity": 5})
        assert result1 == 50
        
        result2 = program.execute({"price": 25, "quantity": 4})
        assert result2 == 100
        
        result3 = program.execute({"price": 100, "quantity": 1})
        assert result3 == 100

    def test_execute_with_nested_context(self):
        """Test executing with nested dictionary context."""
        program = cel.compile("user.name + ' (' + user.role + ')'")
        result = program.execute({
            "user": {"name": "Bob", "role": "admin"}
        })
        assert result == "Bob (admin)"

    def test_execute_with_list_context(self):
        """Test executing with list in context."""
        program = cel.compile("items[0] + items[1]")
        result = program.execute({"items": [10, 20, 30]})
        assert result == 30


class TestCompileWithFunctions:
    """Tests for compile/execute with custom functions."""

    def test_execute_with_custom_function(self):
        """Test executing with a custom Python function."""
        program = cel.compile("double(x)")
        ctx = Context()
        ctx.add_function("double", lambda x: x * 2)
        ctx.add_variable("x", 21)
        result = program.execute(ctx)
        assert result == 42

    def test_execute_with_multiple_custom_functions(self):
        """Test executing with multiple custom functions."""
        program = cel.compile("add(x, y) + multiply(x, y)")
        ctx = Context()
        ctx.add_function("add", lambda a, b: a + b)
        ctx.add_function("multiply", lambda a, b: a * b)
        ctx.add_variable("x", 3)
        ctx.add_variable("y", 4)
        result = program.execute(ctx)
        assert result == 19  # (3+4) + (3*4) = 7 + 12 = 19


class TestCompileTypes:
    """Tests for various CEL types with compile/execute."""

    def test_compile_boolean(self):
        """Test compiling boolean expressions."""
        program = cel.compile("a > b && c")
        result = program.execute({"a": 10, "b": 5, "c": True})
        assert result is True

    def test_compile_string(self):
        """Test compiling string expressions."""
        program = cel.compile("greeting + ' ' + name")
        result = program.execute({"greeting": "Hello", "name": "World"})
        assert result == "Hello World"

    def test_compile_list(self):
        """Test compiling list expressions."""
        program = cel.compile("[a, b, c]")
        result = program.execute({"a": 1, "b": 2, "c": 3})
        assert result == [1, 2, 3]

    def test_compile_map(self):
        """Test compiling map expressions."""
        program = cel.compile("{'name': name, 'age': age}")
        result = program.execute({"name": "Alice", "age": 30})
        assert result == {"name": "Alice", "age": 30}

    def test_compile_null(self):
        """Test compiling null expressions."""
        program = cel.compile("null")
        result = program.execute()
        assert result is None

    def test_compile_bytes(self):
        """Test compiling bytes expressions."""
        program = cel.compile("b'hello'")
        result = program.execute()
        assert result == b"hello"

    def test_compile_timestamp(self):
        """Test compiling timestamp expressions."""
        program = cel.compile("timestamp('2024-01-01T00:00:00Z')")
        result = program.execute()
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024

    def test_compile_duration(self):
        """Test compiling duration expressions."""
        program = cel.compile("duration('1h30m')")
        result = program.execute()
        assert isinstance(result, datetime.timedelta)
        assert result.total_seconds() == 5400


class TestCompileErrors:
    """Tests for error handling in compile/execute."""

    def test_compile_invalid_syntax(self):
        """Test that invalid syntax raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse"):
            cel.compile("1 + + 2")

    def test_compile_empty_expression(self):
        """Test that empty expression raises ValueError."""
        with pytest.raises(ValueError, match="Failed to parse"):
            cel.compile("")

    def test_execute_undefined_variable(self):
        """Test that undefined variable raises RuntimeError."""
        program = cel.compile("undefined_var + 1")
        with pytest.raises(RuntimeError):
            program.execute({})

    def test_execute_type_error(self):
        """Test that type errors are properly raised."""
        program = cel.compile("x + y")
        with pytest.raises(TypeError):
            # String + int should fail
            program.execute({"x": "hello", "y": 42})

    def test_execute_invalid_context_type(self):
        """Test that invalid context type raises ValueError."""
        program = cel.compile("x + 1")
        with pytest.raises(ValueError, match="must be a Context object or a dict"):
            program.execute("invalid context")


class TestCompileRealWorldExamples:
    """Real-world usage examples for compile/execute."""

    def test_access_control_policy(self):
        """Test access control policy evaluation."""
        policy = cel.compile(
            'user.role == "admin" || (resource.owner == user.id && action == "read")'
        )
        
        # Admin can do anything
        assert policy.execute({
            "user": {"id": "alice", "role": "admin"},
            "resource": {"owner": "bob"},
            "action": "delete"
        }) is True
        
        # Owner can read their own resource
        assert policy.execute({
            "user": {"id": "bob", "role": "user"},
            "resource": {"owner": "bob"},
            "action": "read"
        }) is True
        
        # Non-owner cannot read others' resources
        assert policy.execute({
            "user": {"id": "charlie", "role": "user"},
            "resource": {"owner": "bob"},
            "action": "read"
        }) is False

    def test_pricing_calculation(self):
        """Test pricing calculation with discounts."""
        pricing = cel.compile(
            "price * quantity * (1.0 - discount)"
        )
        
        # No discount
        assert pricing.execute({
            "price": 100.0, "quantity": 2.0, "discount": 0.0
        }) == 200.0
        
        # 10% discount
        result = pricing.execute({
            "price": 100.0, "quantity": 2.0, "discount": 0.1
        })
        assert abs(result - 180.0) < 0.001

    def test_validation_rules(self):
        """Test validation rules."""
        age_check = cel.compile("age >= 18 && age <= 120")
        
        assert age_check.execute({"age": 25}) is True
        assert age_check.execute({"age": 17}) is False
        assert age_check.execute({"age": 121}) is False

    def test_data_filtering(self):
        """Test data filtering expression."""
        filter_expr = cel.compile(
            'status == "active" && score >= min_score'
        )
        
        items = [
            {"status": "active", "score": 85},
            {"status": "inactive", "score": 90},
            {"status": "active", "score": 70},
            {"status": "active", "score": 95},
        ]
        
        filtered = [
            item for item in items
            if filter_expr.execute({**item, "min_score": 80})
        ]
        
        assert len(filtered) == 2
        assert filtered[0]["score"] == 85
        assert filtered[1]["score"] == 95


class TestCompilePerformancePattern:
    """Tests demonstrating the performance benefit pattern."""

    def test_compile_once_execute_many(self):
        """Demonstrate compile-once-execute-many pattern."""
        # Compile the expression once
        expr = cel.compile("x * x + y * y")
        
        # Execute many times with different values
        results = []
        for i in range(100):
            result = expr.execute({"x": i, "y": i + 1})
            results.append(result)
        
        # Verify some results
        assert results[0] == 0 * 0 + 1 * 1  # 1
        assert results[1] == 1 * 1 + 2 * 2  # 5
        assert results[10] == 10 * 10 + 11 * 11  # 221

    def test_reuse_compiled_program(self):
        """Test that compiled programs can be reused safely."""
        program = cel.compile("value > threshold")
        
        # Multiple sequential executions
        assert program.execute({"value": 10, "threshold": 5}) is True
        assert program.execute({"value": 3, "threshold": 5}) is False
        assert program.execute({"value": 100, "threshold": 50}) is True
        assert program.execute({"value": 0, "threshold": 0}) is False
