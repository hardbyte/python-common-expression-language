"""Test edge cases and error conditions that don't fit in other test categories"""

import datetime

import cel
import pytest
from conftest import evaluate


def test_boolean_edge_cases():
    """Test boolean edge cases"""
    assert not evaluate("true && false", {})
    assert evaluate("true || false", {})
    assert not evaluate("!true", {})
    assert evaluate("!false", {})
