"""Per-entity baselines.

A baseline learns what "normal" looks like for one stream and scores each new value
as a standardized deviation from that stream's own recent history. Two estimators are
provided: a sliding window (exact over the last N points) and an exponentially weighted
one (constant memory, no window to size). Both share one deliberate rule: a value is
scored against the baseline of the points that came before it, never including itself,
so an anomaly cannot quietly inflate its own baseline and shrink its own score.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass
from statistics import fmean, median, pstdev
from typing import Protocol, runtime_checkable

from .robust import robust_scale


@dataclass(frozen=True)
class Reading:
    """The result of scoring one value against a baseline.

    Attributes:
        value: the value that was scored.
        mean: the baseline's centre at the time of scoring.
        scale: the baseline's spread (standard deviation, or robust scale).
        z: standardized deviation, (value - mean) / scale. 0.0 while warming up.
        ready: False until the baseline has seen enough points to score.
    """

    value: float
    mean: float
    scale: float
    z: float
    ready: bool


@runtime_checkable
class Baseline(Protocol):
    """A streaming per-entity baseline."""

    def observe(self, value: float) -> Reading:
        """Score `value` against the baseline so far, then fold it in."""
        ...

    @property
    def ready(self) -> bool:
        """True once enough points have been seen to score meaningfully."""
        ...


class WindowBaseline:
    """Baseline over a sliding window of the most recent `window` values.

    Args:
        window: number of recent values to keep.
        warmup: minimum values before scoring begins. Defaults to half the window.
        robust: use 1.4826 * MAD instead of the standard deviation for the scale.
        min_scale: floor on the scale so a momentarily flat stream cannot divide by
            zero and report an infinite deviation.
    """

    def __init__(
        self,
        window: int = 50,
        warmup: int | None = None,
        robust: bool = False,
        min_scale: float = 1e-9,
    ) -> None:
        if window < 2:
            raise ValueError("window must be >= 2")
        if min_scale <= 0:
            raise ValueError("min_scale must be > 0")
        self.window = window
        self.warmup = warmup if warmup is not None else max(2, window // 2)
        if self.warmup < 2:
            raise ValueError("warmup must be >= 2")
        self._robust = robust
        self._min_scale = min_scale
        self._buf: deque[float] = deque(maxlen=window)

    @property
    def ready(self) -> bool:
        return len(self._buf) >= self.warmup

    def observe(self, value: float) -> Reading:
        if self.ready:
            prior = list(self._buf)
            # When robust, use the median AND the MAD-based scale. Robustifying only the
            # scale is not enough: a single outlier still drags the mean, so a normal
            # value scored against that mean looks anomalous. The median resists it too.
            if self._robust:
                mean = median(prior)
                scale = robust_scale(prior)
            else:
                mean = fmean(prior)
                scale = pstdev(prior)
            z = (value - mean) / max(scale, self._min_scale)
            reading = Reading(value, mean, scale, z, True)
        else:
            reading = Reading(value, value, 0.0, 0.0, False)
        self._buf.append(value)
        return reading


class EwmaBaseline:
    """Exponentially weighted baseline. Constant memory, no window to size.

    Recent values weigh more than old ones, controlled by `alpha` (larger forgets
    faster). Uses the standard incremental exponentially weighted mean and variance,
    so it holds only two running numbers regardless of stream length.

    Args:
        alpha: smoothing factor in (0, 1]. Roughly, the baseline reflects the last
            ~1/alpha values.
        warmup: minimum values before scoring begins.
        min_scale: floor on the scale (see WindowBaseline).
    """

    def __init__(
        self, alpha: float = 0.05, warmup: int = 20, min_scale: float = 1e-9
    ) -> None:
        if not 0.0 < alpha <= 1.0:
            raise ValueError("alpha must be in (0, 1]")
        if warmup < 1:
            raise ValueError("warmup must be >= 1")
        if min_scale <= 0:
            raise ValueError("min_scale must be > 0")
        self.alpha = alpha
        self.warmup = warmup
        self._min_scale = min_scale
        self._n = 0
        self._mean = 0.0
        self._var = 0.0

    @property
    def ready(self) -> bool:
        return self._n >= self.warmup

    def observe(self, value: float) -> Reading:
        if self._n == 0:
            self._mean = value
            self._var = 0.0
            self._n = 1
            return Reading(value, value, 0.0, 0.0, False)

        scale = math.sqrt(self._var)
        if self.ready:
            z = (value - self._mean) / max(scale, self._min_scale)
            reading = Reading(value, self._mean, scale, z, True)
        else:
            reading = Reading(value, self._mean, scale, 0.0, False)

        # Incremental exponentially weighted mean and variance (West, 1979).
        diff = value - self._mean
        incr = self.alpha * diff
        self._mean += incr
        self._var = (1.0 - self.alpha) * (self._var + diff * incr)
        self._n += 1
        return reading
