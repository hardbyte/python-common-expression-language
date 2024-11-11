import pytest

import cel

@pytest.mark.xfail()
def test_custom_function():
    def custom_function(a, b):
        return a + b

    assert cel.evaluate("custom_function(1, 2)", {'custom_function': custom_function}) == 3

