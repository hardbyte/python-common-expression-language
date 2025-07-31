"""Test edge cases and error conditions that don't fit in other test categories"""
import pytest
import datetime
import cel


def test_boolean_edge_cases():
    """Test boolean edge cases"""
    assert cel.evaluate("true && false", {}) == False
    assert cel.evaluate("true || false", {}) == True
    assert cel.evaluate("!true", {}) == False
    assert cel.evaluate("!false", {}) == True