"""Analytics utilities for simple telemetry calculations.

Provides `calculate_growth_rate(initial_value, final_value)` which returns the
percentage growth from `initial_value` to `final_value`.
"""
from __future__ import annotations

from typing import Union


Number = Union[int, float]


def calculate_growth_rate(initial_value: Number, final_value: Number) -> float:
    """Calculate percentage growth from `initial_value` to `final_value`.

    Formula: ((final_value - initial_value) / initial_value) * 100

    Edge cases:
    - If `initial_value` is 0, return 0.0 to avoid ZeroDivisionError and provide
      a safe, explicit result used by the tests.
    - Accepts ints and floats and returns a float.
    """
    try:
        init = float(initial_value)
        final = float(final_value)
    except (TypeError, ValueError):
        raise TypeError("initial_value and final_value must be numbers")

    if init == 0.0:
        return 0.0

    growth = ((final - init) / init) * 100.0
    return growth
"""Analytics utilities for simple telemetry calculations.

Provides `calculate_growth_rate(initial_value, final_value)` which returns the
percentage growth from `initial_value` to `final_value`.
"""
from __future__ import annotations

from typing import Union


Number = Union[int, float]


def calculate_growth_rate(initial_value: Number, final_value: Number) -> float:
    """Calculate percentage growth from `initial_value` to `final_value`.

    Formula: ((final_value - initial_value) / initial_value) * 100

    Edge cases:
    - If `initial_value` is 0, return 0.0 to avoid ZeroDivisionError and provide
      a safe, explicit result used by the tests.
    - Accepts ints and floats and returns a float.
    """
    try:
        init = float(initial_value)
        final = float(final_value)
    except (TypeError, ValueError):
        raise TypeError("initial_value and final_value must be numbers")

    if init == 0.0:
        return 0.0

    growth = ((final - init) / init) * 100.0
    return growth
