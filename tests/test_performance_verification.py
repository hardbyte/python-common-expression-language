"""
Performance verification tests to ensure optimizations are working correctly.
These tests verify that our PyO3 0.25.0 optimizations maintain functionality
while potentially improving performance.
"""

import datetime
import time

import cel


def test_large_list_conversion_performance():
    """Test performance with large lists to verify optimized list conversion"""
    # Create a large list to test conversion performance
    large_list = list(range(1000))

    start_time = time.time()
    result = cel.evaluate("size(items)", {"items": large_list})
    end_time = time.time()

    # Verify correctness
    assert result == 1000

    # Test should complete reasonably quickly (under 1 second even on slow systems)
    assert end_time - start_time < 1.0


def test_large_dict_conversion_performance():
    """Test performance with large dictionaries to verify optimized dict conversion"""
    # Create a large dictionary
    large_dict = {f"key_{i}": i for i in range(100)}

    start_time = time.time()
    result = cel.evaluate("size(data)", {"data": large_dict})
    end_time = time.time()

    # Verify correctness
    assert result == 100

    # Test should complete reasonably quickly
    assert end_time - start_time < 1.0


def test_nested_structure_conversion_performance():
    """Test performance with deeply nested structures"""
    nested_data = {
        "level1": {
            "level2": {
                "level3": {
                    "numbers": [1, 2, 3, 4, 5] * 20,  # 100 items
                    "datetime": datetime.datetime.now(datetime.timezone.utc),
                    "boolean": True,
                    "string": "test_string" * 10,
                }
            }
        }
    }

    start_time = time.time()
    result = cel.evaluate("size(data.level1.level2.level3.numbers)", {"data": nested_data})
    end_time = time.time()

    # Verify correctness
    assert result == 100

    # Test should complete reasonably quickly
    assert end_time - start_time < 1.0


def test_function_call_performance():
    """Test performance of Python function calls with multiple arguments"""

    def test_function(a, b, c, d, e):
        return a + b + c + d + e

    context = cel.Context()
    context.add_function("test_func", test_function)

    # Test with multiple function calls
    start_time = time.time()
    for _i in range(50):  # 50 function calls
        result = cel.evaluate("test_func(1, 2, 3, 4, 5)", context)
        assert result == 15
    end_time = time.time()

    # Multiple function calls should still be reasonably fast
    assert end_time - start_time < 2.0


def test_mixed_type_conversion_performance():
    """Test performance with mixed data types"""
    mixed_data = {
        "integers": [1, 2, 3, 4, 5] * 20,
        "floats": [1.1, 2.2, 3.3, 4.4, 5.5] * 20,
        "strings": ["hello", "world"] * 50,
        "booleans": [True, False] * 50,
        "dates": [datetime.datetime.now(datetime.timezone.utc)] * 10,
        "bytes": [b"test"] * 10,
    }

    start_time = time.time()
    # Test various operations on mixed data
    result1 = cel.evaluate("size(data.integers)", {"data": mixed_data})
    result2 = cel.evaluate("size(data.floats)", {"data": mixed_data})
    result3 = cel.evaluate("size(data.strings)", {"data": mixed_data})
    result4 = cel.evaluate("size(data.booleans)", {"data": mixed_data})
    result5 = cel.evaluate("size(data.dates)", {"data": mixed_data})
    result6 = cel.evaluate("size(data.bytes)", {"data": mixed_data})
    end_time = time.time()

    # Verify correctness
    assert result1 == 100
    assert result2 == 100
    assert result3 == 100
    assert result4 == 100
    assert result5 == 10
    assert result6 == 10

    # All operations should complete reasonably quickly
    assert end_time - start_time < 1.0


def test_string_processing_performance():
    """Test optimized string processing without unnecessary allocations"""
    # Test with various string operations
    long_string = "hello world " * 100

    start_time = time.time()
    result = cel.evaluate("text + ' suffix'", {"text": long_string})
    end_time = time.time()

    # Verify correctness
    assert result == long_string + " suffix"

    # Should be fast
    assert end_time - start_time < 0.5
