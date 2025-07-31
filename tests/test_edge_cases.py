"""Test edge cases and error conditions that don't fit in other test categories"""

import datetime

import cel
import pytest


def test_boolean_edge_cases():
    """Test boolean edge cases"""
    assert not cel.evaluate("true && false", {})
    assert cel.evaluate("true || false", {})
    assert not cel.evaluate("!true", {})
    assert cel.evaluate("!false", {})
