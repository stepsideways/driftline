"""driftline: online per-entity anomaly detection.

Score each stream against its own recent baseline rather than a single global
threshold, so a value that is normal for one entity and alarming for another is read
correctly in both.
"""
from __future__ import annotations

from .baseline import Baseline, EwmaBaseline, Reading, WindowBaseline
from .detector import DriftDetector, DriftEvent
from .robust import mad, robust_scale

__version__ = "0.1.0"

__all__ = [
    "Baseline",
    "Reading",
    "WindowBaseline",
    "EwmaBaseline",
    "DriftDetector",
    "DriftEvent",
    "mad",
    "robust_scale",
]
