import pytest

import cel


def test_custom_function():
    def custom_function(a, b):
        return a + b

    assert cel.evaluate("custom_function(1, 2)", {"custom_function": custom_function}) == 3


def test_readme_custom_function_example():
    def is_adult(age):
        return age > 21

    assert cel.evaluate("is_adult(age)", {"is_adult": is_adult, "age": 18}) == False
    assert cel.evaluate("is_adult(age)", {"is_adult": is_adult, "age": 32}) == True
