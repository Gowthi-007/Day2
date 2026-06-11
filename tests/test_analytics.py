# tests/test_analytics.py
import pytest
from src.analytics import calculate_growth_rate


def test_standard_growth():
    # Initial 50 to Final 75 is a 50% increase
    # (75 - 50) / 50 * 100 = 50%
    assert calculate_growth_rate(50, 75) == 50.0


def test_zero_division_safety():
    # Edge case: If initial_value is 0, it should gracefully return 0.0 instead of crashing
    assert calculate_growth_rate(0, 100) == 0.0
