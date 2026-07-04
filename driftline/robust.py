"""Robust scale estimation.

The standard deviation is sensitive to the very outliers an anomaly detector is
trying to find: one large spike inflates the scale and hides the next one. The
median absolute deviation (MAD) is not, which makes it a better ruler for a
baseline that has to stay steady while unusual points arrive.
"""
from __future__ import annotations

from collections.abc import Sequence
from statistics import median

# Scale factor that makes 1.4826 * MAD a consistent estimator of the standard
# deviation for normally distributed data. Standard constant, not tuned.
_MAD_TO_SIGMA = 1.4826


def mad(values: Sequence[float]) -> float:
    """Median absolute deviation from the median."""
    if not values:
        raise ValueError("mad() requires at least one value")
    med = median(values)
    return median([abs(v - med) for v in values])


def robust_scale(values: Sequence[float]) -> float:
    """A standard-deviation-comparable scale that ignores outliers (1.4826 * MAD)."""
    return _MAD_TO_SIGMA * mad(values)
