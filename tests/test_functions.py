import datetime
import time
from typing import Any, Dict, List, Optional

import cel
import pytest


def test_custom_function():
    def custom_function(a, b):
        return a + b

    assert cel.evaluate("custom_function(1, 2)", {"custom_function": custom_function}) == 3


def test_readme_custom_function_example():
    def is_adult(age):
        return age > 21

    assert not cel.evaluate("is_adult(age)", {"is_adult": is_adult, "age": 18})
    assert cel.evaluate("is_adult(age)", {"is_adult": is_adult, "age": 32})


class TestPythonExceptionPropagation:
    """Test that Python exceptions from custom functions are properly propagated."""

    def test_value_error_propagation(self):
        """Test ValueError from custom function is propagated as RuntimeError."""

        def raise_value_error(x):
            if x < 0:
                raise ValueError("Value must be non-negative")
            return x * 2

        # Should work normally
        assert cel.evaluate("double_positive(5)", {"double_positive": raise_value_error}) == 10

        # Should propagate ValueError as RuntimeError
        with pytest.raises(RuntimeError, match="Value must be non-negative"):
            cel.evaluate("double_positive(-1)", {"double_positive": raise_value_error})

    def test_type_error_propagation(self):
        """Test TypeError from custom function is propagated as RuntimeError."""

        def strict_math(a, b):
            if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
                raise TypeError("Arguments must be numeric")
            return a + b

        # Should work normally
        assert cel.evaluate("math(1, 2.5)", {"math": strict_math}) == 3.5

        # Should propagate TypeError as RuntimeError
        with pytest.raises(RuntimeError, match="Arguments must be numeric"):
            cel.evaluate(
                "math('hello', 'world')", {"math": strict_math, "str1": "hello", "str2": "world"}
            )

    def test_custom_exception_propagation(self):
        """Test custom exceptions from functions are propagated as RuntimeError."""

        class ValidationError(Exception):
            pass

        def validate_email(email):
            if "@" not in email:
                raise ValidationError("Invalid email format")
            return email.lower()

        # Should work normally
        assert (
            cel.evaluate("validate('test@example.com')", {"validate": validate_email})
            == "test@example.com"
        )

        # Should propagate custom exception as RuntimeError
        with pytest.raises(RuntimeError, match="Invalid email format"):
            cel.evaluate("validate('invalid-email')", {"validate": validate_email})

    def test_zero_division_error_propagation(self):
        """Test ZeroDivisionError from custom function is propagated."""

        def safe_divide(a, b):
            if b == 0:
                raise ZeroDivisionError("Cannot divide by zero")
            return a / b

        # Should work normally
        assert cel.evaluate("divide(10, 2)", {"divide": safe_divide}) == 5.0

        # Should propagate ZeroDivisionError as RuntimeError
        with pytest.raises(RuntimeError, match="Cannot divide by zero"):
            cel.evaluate("divide(10, 0)", {"divide": safe_divide})


class TestFunctionSignatures:
    """Test functions with different argument signatures."""

    def test_no_arguments_function(self):
        """Test function with no arguments."""

        def get_current_time():
            return "2024-01-01T00:00:00Z"

        assert (
            cel.evaluate("current_time()", {"current_time": get_current_time})
            == "2024-01-01T00:00:00Z"
        )

    def test_single_argument_function(self):
        """Test function with single argument."""

        def square(x):
            return x * x

        assert cel.evaluate("square(5)", {"square": square}) == 25
        assert cel.evaluate("square(2.5)", {"square": square}) == 6.25

    def test_multiple_arguments_function(self):
        """Test function with multiple arguments."""

        def calculate_area(length, width, height=1):
            return length * width * height

        # Test with required arguments
        assert cel.evaluate("area(5, 3)", {"area": calculate_area}) == 15

        # Note: CEL doesn't support default arguments directly,
        # so we test the Python function behavior when called from CEL
        def area_with_default(length, width):
            return calculate_area(length, width)  # Uses default height=1

        assert cel.evaluate("area_2d(4, 6)", {"area_2d": area_with_default}) == 24

    def test_variadic_arguments_simulation(self):
        """Test function that handles variable number of arguments via list."""

        def sum_all(numbers):
            """Sum all numbers in a list - simulates *args functionality."""
            if not isinstance(numbers, list):
                return numbers  # Single number
            return sum(numbers)

        # Single number
        assert cel.evaluate("sum_numbers(42)", {"sum_numbers": sum_all}) == 42

        # List of numbers
        assert cel.evaluate("sum_numbers([1, 2, 3, 4, 5])", {"sum_numbers": sum_all}) == 15

    def test_keyword_arguments_simulation(self):
        """Test function that handles keyword-like arguments via dict."""

        def format_person(person_dict):
            """Format person info - simulates **kwargs functionality."""
            name = person_dict.get("name", "Unknown")
            age = person_dict.get("age", 0)
            title = person_dict.get("title", "")

            if title:
                return f"{title} {name} (age {age})"
            return f"{name} (age {age})"

        # Test with different combinations
        basic_context = {"format": format_person, "person": {"name": "Alice", "age": 30}}
        assert cel.evaluate("format(person)", basic_context) == "Alice (age 30)"

        title_context = {
            "format": format_person,
            "person": {"name": "Bob", "age": 45, "title": "Dr."},
        }
        assert cel.evaluate("format(person)", title_context) == "Dr. Bob (age 45)"


class TestComplexTypeHandling:
    """Test functions that receive and return complex types."""

    def test_list_input_and_output(self):
        """Test functions that work with lists."""

        def filter_even_numbers(numbers):
            """Return only even numbers from a list."""
            return [n for n in numbers if n % 2 == 0]

        def list_stats(numbers):
            """Return statistics about a list."""
            if not numbers:
                return {"count": 0, "sum": 0, "avg": 0}
            return {"count": len(numbers), "sum": sum(numbers), "avg": sum(numbers) / len(numbers)}

        # Test list filtering
        context = {"filter_even": filter_even_numbers, "numbers": [1, 2, 3, 4, 5, 6]}
        result = cel.evaluate("filter_even(numbers)", context)
        assert result == [2, 4, 6]

        # Test list statistics
        stats_context = {"stats": list_stats, "data": [1, 2, 3, 4, 5]}
        result = cel.evaluate("stats(data)", stats_context)
        assert result == {"count": 5, "sum": 15, "avg": 3.0}

    def test_dict_input_and_output(self):
        """Test functions that work with dictionaries."""

        def merge_dicts(dict1, dict2):
            """Merge two dictionaries."""
            result = dict1.copy()
            result.update(dict2)
            return result

        def extract_keys(dictionary):
            """Extract all keys from a dictionary as a list."""
            return list(dictionary.keys())

        # Test dictionary merging
        merge_context = {"merge": merge_dicts, "dict1": {"a": 1, "b": 2}, "dict2": {"c": 3, "d": 4}}
        result = cel.evaluate("merge(dict1, dict2)", merge_context)
        assert result == {"a": 1, "b": 2, "c": 3, "d": 4}

        # Test key extraction
        keys_context = {
            "get_keys": extract_keys,
            "data": {"name": "Alice", "age": 30, "city": "NYC"},
        }
        result = cel.evaluate("get_keys(data)", keys_context)
        assert set(result) == {"name", "age", "city"}  # Order may vary

    def test_nested_data_structures(self):
        """Test functions with deeply nested data structures."""

        def find_user_by_id(users, user_id):
            """Find user in nested data structure."""
            for user in users:
                if user.get("id") == user_id:
                    return user
            return None

        def count_nested_items(data):
            """Count items in nested structure."""
            total = 0
            for category in data.values():
                if isinstance(category, dict) and "items" in category:
                    total += len(category["items"])
            return total

        # Test user finding
        users_data = [
            {"id": 1, "name": "Alice", "role": "admin"},
            {"id": 2, "name": "Bob", "role": "user"},
            {"id": 3, "name": "Charlie", "role": "moderator"},
        ]
        find_context = {"find_user": find_user_by_id, "users": users_data}
        result = cel.evaluate("find_user(users, 2)", find_context)
        assert result == {"id": 2, "name": "Bob", "role": "user"}

        # Test nested counting
        nested_data = {
            "electronics": {"items": ["phone", "laptop", "tablet"]},
            "books": {"items": ["novel", "textbook"]},
            "clothes": {"items": ["shirt", "pants", "shoes", "hat"]},
        }
        count_context = {"count_items": count_nested_items, "inventory": nested_data}
        result = cel.evaluate("count_items(inventory)", count_context)
        assert result == 9

    def test_datetime_handling(self):
        """Test functions that work with datetime objects."""

        def format_datetime(dt):
            """Format datetime object to string."""
            if isinstance(dt, datetime.datetime):
                return dt.strftime("%Y-%m-%d %H:%M:%S")
            return str(dt)

        def datetime_diff_days(dt1, dt2):
            """Calculate difference in days between two datetime objects."""
            if isinstance(dt1, datetime.datetime) and isinstance(dt2, datetime.datetime):
                return abs((dt2 - dt1).days)
            return 0

        def create_datetime_from_string(date_string):
            """Create datetime from string."""
            try:
                return datetime.datetime.fromisoformat(date_string.replace("Z", "+00:00"))
            except ValueError:
                return None

        # Test datetime formatting
        test_dt = datetime.datetime(2024, 1, 15, 14, 30, 0)
        format_context = {"format_dt": format_datetime, "dt": test_dt}
        result = cel.evaluate("format_dt(dt)", format_context)
        assert result == "2024-01-15 14:30:00"

        # Test datetime difference
        dt1 = datetime.datetime(2024, 1, 1)
        dt2 = datetime.datetime(2024, 1, 15)
        diff_context = {"days_between": datetime_diff_days, "start": dt1, "end": dt2}
        result = cel.evaluate("days_between(start, end)", diff_context)
        assert result == 14

        # Test datetime creation
        create_context = {"parse_dt": create_datetime_from_string}
        result = cel.evaluate("parse_dt('2024-01-01T12:00:00Z')", create_context)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2024
        assert result.month == 1
        assert result.day == 1

    def test_bytes_handling(self):
        """Test functions that work with bytes objects."""

        def encode_string(text):
            """Encode string to bytes."""
            return text.encode("utf-8")

        def decode_bytes(data):
            """Decode bytes to string."""
            if isinstance(data, bytes):
                return data.decode("utf-8")
            return str(data)

        def bytes_length(data):
            """Get length of bytes object."""
            if isinstance(data, bytes):
                return len(data)
            return 0

        # Test string encoding
        encode_context = {"encode": encode_string}
        result = cel.evaluate("encode('hello world')", encode_context)
        assert result == b"hello world"

        # Test bytes decoding
        decode_context = {"decode": decode_bytes, "data": b"hello world"}
        result = cel.evaluate("decode(data)", decode_context)
        assert result == "hello world"

        # Test bytes length
        length_context = {"byte_len": bytes_length, "data": b"hello"}
        result = cel.evaluate("byte_len(data)", length_context)
        assert result == 5


class TestFunctionPerformance:
    """Test performance characteristics of calling Python functions from CEL."""

    def test_simple_function_call_performance(self):
        """Test performance of simple function calls."""

        def simple_add(a, b):
            return a + b

        context = {"add": simple_add}
        expression = "add(1, 2)"

        # Warm up
        for _ in range(100):
            cel.evaluate(expression, context)

        # Measure performance
        start_time = time.perf_counter()
        iterations = 10000

        for _ in range(iterations):
            result = cel.evaluate(expression, context)
            assert result == 3

        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations

        # Should be reasonably fast (under 200 microseconds per call)
        # Adjusted threshold for realistic hardware performance
        assert avg_time < 0.0002, f"Function call too slow: {avg_time * 1000000:.1f} μs per call"

    def test_complex_function_call_performance(self):
        """Test performance of more complex function calls."""

        def complex_calculation(data):
            """Perform complex calculation on data."""
            if not isinstance(data, list):
                return 0

            # Simulate some computation
            result = 0
            for item in data:
                if isinstance(item, dict) and "value" in item:
                    result += item["value"] * 2
            return result

        # Create test data
        test_data = [{"value": i} for i in range(100)]
        context = {"calculate": complex_calculation, "data": test_data}
        expression = "calculate(data)"

        # Warm up
        for _ in range(10):
            cel.evaluate(expression, context)

        # Measure performance
        start_time = time.perf_counter()
        iterations = 1000

        for _ in range(iterations):
            result = cel.evaluate(expression, context)
            assert result == 9900  # Sum of 0*2 + 1*2 + ... + 99*2

        end_time = time.perf_counter()
        avg_time = (end_time - start_time) / iterations

        # Should complete within reasonable time (under 1ms per call)
        assert avg_time < 0.001, (
            f"Complex function call too slow: {avg_time * 1000:.1f} ms per call"
        )

    def test_function_call_with_large_data(self):
        """Test performance with large data structures."""

        def process_large_list(items):
            """Process a large list of items."""
            return len([item for item in items if item % 2 == 0])

        # Create large test data
        large_data = list(range(10000))
        context = {"process": process_large_list, "data": large_data}
        expression = "process(data)"

        # Measure performance
        start_time = time.perf_counter()
        result = cel.evaluate(expression, context)
        end_time = time.perf_counter()

        # Verify correctness
        assert result == 5000  # Half the numbers are even

        # Should complete within reasonable time (under 10ms)
        execution_time = end_time - start_time
        assert execution_time < 0.01, (
            f"Large data processing too slow: {execution_time * 1000:.1f} ms"
        )


class TestFunctionEdgeCases:
    """Test edge cases and boundary conditions for custom functions."""

    def test_function_returning_none(self):
        """Test function that returns None."""

        def maybe_return_value(condition):
            if condition:
                return "value"
            return None

        # Test None return
        assert cel.evaluate("get_value(false)", {"get_value": maybe_return_value}) is None

        # Test non-None return
        assert cel.evaluate("get_value(true)", {"get_value": maybe_return_value}) == "value"

    def test_function_with_empty_collections(self):
        """Test function behavior with empty collections."""

        def process_collection(items):
            if not items:
                return {"empty": True}
            return {"count": len(items), "first": items[0]}

        # Test empty list
        assert cel.evaluate("process([])", {"process": process_collection}) == {"empty": True}

        # Test non-empty list
        result = cel.evaluate("process([1, 2, 3])", {"process": process_collection})
        assert result == {"count": 3, "first": 1}

    def test_function_with_recursive_data(self):
        """Test function with recursive/circular data structures."""

        def safe_traverse(data, max_depth=5):
            """Safely traverse data structure with depth limit."""

            def _traverse(obj, depth):
                if depth > max_depth:
                    return "MAX_DEPTH_REACHED"

                if isinstance(obj, dict):
                    return {k: _traverse(v, depth + 1) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [_traverse(item, depth + 1) for item in obj]
                else:
                    return obj

            return _traverse(data, 0)

        # Test normal nested structure
        nested_data = {"level1": {"level2": {"level3": "value"}}}
        context = {"traverse": safe_traverse, "data": nested_data}
        result = cel.evaluate("traverse(data)", context)
        assert result == {"level1": {"level2": {"level3": "value"}}}

        # Test very deep structure (would hit depth limit)
        very_deep = {"a": {"b": {"c": {"d": {"e": {"f": {"g": "too_deep"}}}}}}}
        deep_context = {"traverse": safe_traverse, "data": very_deep}
        result = cel.evaluate("traverse(data)", deep_context)
        # Should contain MAX_DEPTH_REACHED somewhere in the result
        assert "MAX_DEPTH_REACHED" in str(result)

    def test_function_with_special_values(self):
        """Test function handling special Python values."""

        def handle_special_values(value):
            """Handle special Python values."""
            if value is None:
                return "null"
            elif value == float("inf"):
                return "infinity"
            elif value == float("-inf"):
                return "negative_infinity"
            elif str(value) == "nan":
                return "not_a_number"
            else:
                return f"normal:{value}"

        # Test None
        assert cel.evaluate("handle(null)", {"handle": handle_special_values}) == "null"

        # Test normal values
        assert cel.evaluate("handle(42)", {"handle": handle_special_values}) == "normal:42"
        assert cel.evaluate("handle('test')", {"handle": handle_special_values}) == "normal:test"


class TestFunctionIntegrationWithCELFeatures:
    """Test how custom functions integrate with CEL language features."""

    def test_function_in_conditional_expressions(self):
        """Test custom functions in conditional expressions."""

        def is_valid_email(email):
            return "@" in email and "." in email

        def get_domain(email):
            return email.split("@")[1] if "@" in email else ""

        context = {"is_valid": is_valid_email, "domain": get_domain, "email": "user@example.com"}

        # Use function in conditional
        result = cel.evaluate("is_valid(email) ? domain(email) : 'invalid'", context)
        assert result == "example.com"

        # Test with invalid email
        invalid_context = context.copy()
        invalid_context["email"] = "invalid-email"
        result = cel.evaluate("is_valid(email) ? domain(email) : 'invalid'", invalid_context)
        assert result == "invalid"

    def test_function_with_list_operations(self):
        """Test custom functions with CEL list operations."""

        def multiply_by_two(x):
            return x * 2

        def is_even(x):
            return x % 2 == 0

        context = {"double": multiply_by_two, "even": is_even, "numbers": [1, 2, 3, 4, 5]}

        # Note: CEL's map() might not work directly with custom functions
        # due to type system limitations, but we can test other combinations

        # Test function with list filtering (conceptual - may need adaptation)
        # This tests the function itself, integration with CEL macros may vary
        assert cel.evaluate("double(5)", context) == 10
        assert cel.evaluate("even(4)", context)
        assert not cel.evaluate("even(3)", context)

    def test_function_with_map_operations(self):
        """Test custom functions with CEL map operations."""

        def get_nested_value(obj, key):
            """Get nested value from object."""
            if isinstance(obj, dict) and key in obj:
                return obj[key]
            return None

        def has_property(obj, prop):
            """Check if object has property."""
            return isinstance(obj, dict) and prop in obj

        context = {
            "get": get_nested_value,
            "has_prop": has_property,
            "user": {"name": "Alice", "profile": {"age": 30, "city": "NYC"}},
        }

        # Test nested access
        assert cel.evaluate("get(user, 'name')", context) == "Alice"
        assert cel.evaluate("has_prop(user, 'profile')", context)
        assert not cel.evaluate("has_prop(user, 'missing')", context)

    def test_function_chaining(self):
        """Test chaining multiple custom functions."""

        def string_upper(s):
            return s.upper()

        def string_replace(s, old, new):
            return s.replace(old, new)

        def string_length(s):
            return len(s)

        context = {
            "upper": string_upper,
            "replace": string_replace,
            "length": string_length,
            "text": "hello world",
        }

        # Test function chaining
        result = cel.evaluate("length(upper(replace(text, 'world', 'CEL')))", context)
        assert result == len("HELLO CEL")


class TestContextIntegration:
    """Test how custom functions integrate with CEL Context class."""

    def test_context_class_function_registration(self):
        """Test registering functions using Context class."""

        def multiply(a, b):
            return a * b

        def greet(name):
            return f"Hello, {name}!"

        context = cel.Context()
        context.add_variable("x", 5)
        context.add_variable("y", 3)
        context.add_function("multiply", multiply)
        context.add_function("greet", greet)
        context.add_variable("name", "Alice")

        # Test function calls with Context class
        assert cel.evaluate("multiply(x, y)", context) == 15
        assert cel.evaluate("greet(name)", context) == "Hello, Alice!"

    def test_mixed_context_and_functions(self):
        """Test mixing variables and functions in context."""

        def calculate_tax(amount, rate):
            return amount * rate

        def format_currency(amount):
            return f"${amount:.2f}"

        context = cel.Context()
        context.add_variable("price", 100.0)
        context.add_variable("tax_rate", 0.08)
        context.add_function("calc_tax", calculate_tax)
        context.add_function("format", format_currency)

        # Test complex expression with functions and variables
        result = cel.evaluate("format(price + calc_tax(price, tax_rate))", context)
        assert result == "$108.00"
