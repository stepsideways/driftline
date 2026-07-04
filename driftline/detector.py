"""Multi-entity drift detector.

Manages one baseline per entity (a sensor, a server, an account, any stream with its
own idea of normal) and emits an event when a stream deviates from its own baseline.
Two pieces of real-world discipline are built in:

  1. Consecutive-sample confirmation, so a single noisy reading does not fire an alarm.
  2. Edge triggering, so one sustained excursion produces one event, not a storm of
     them every sample until it clears.

Per-entity state can be released with `forget`, so a long-running detector over a
changing population of entities does not grow without bound.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from .baseline import Baseline, WindowBaseline

BaselineFactory = Callable[[], Baseline]


@dataclass(frozen=True)
class DriftEvent:
    """A confirmed deviation of one entity from its own baseline."""

    entity_id: str
    value: float
    z: float
    direction: str  # "high" or "low"
    mean: float
    scale: float


class DriftDetector:
    """Detect per-entity drift across many streams.

    Args:
        baseline_factory: builds a fresh baseline for each new entity. Defaults to a
            WindowBaseline. Pass a lambda to configure it, e.g.
            `lambda: EwmaBaseline(alpha=0.1)`.
        threshold: absolute standardized deviation at or above which a sample counts
            as a breach.
        consecutive: number of consecutive breaches required to confirm an event.
    """

    def __init__(
        self,
        baseline_factory: BaselineFactory | None = None,
        threshold: float = 3.0,
        consecutive: int = 1,
    ) -> None:
        if threshold <= 0:
            raise ValueError("threshold must be > 0")
        if consecutive < 1:
            raise ValueError("consecutive must be >= 1")
        self._factory: BaselineFactory = baseline_factory or (lambda: WindowBaseline())
        self.threshold = threshold
        self.consecutive = consecutive
        self._baselines: dict[str, Baseline] = {}
        self._streak: dict[str, int] = {}
        self._firing: dict[str, bool] = {}

    def observe(self, entity_id: str, value: float) -> DriftEvent | None:
        """Feed one value for one entity. Returns a DriftEvent only when a fresh,
        confirmed excursion begins; otherwise None."""
        baseline = self._baselines.get(entity_id)
        if baseline is None:
            baseline = self._factory()
            self._baselines[entity_id] = baseline
            self._streak[entity_id] = 0
            self._firing[entity_id] = False

        reading = baseline.observe(value)

        if not reading.ready or abs(reading.z) < self.threshold:
            # Below threshold (or still warming up): the episode, if any, has cleared.
            self._streak[entity_id] = 0
            self._firing[entity_id] = False
            return None

        self._streak[entity_id] += 1
        if self._firing[entity_id]:
            return None  # already reported this ongoing episode
        if self._streak[entity_id] >= self.consecutive:
            self._firing[entity_id] = True
            return DriftEvent(
                entity_id=entity_id,
                value=value,
                z=reading.z,
                direction="high" if reading.z > 0 else "low",
                mean=reading.mean,
                scale=reading.scale,
            )
        return None

    def forget(self, entity_id: str) -> None:
        """Release all state for one entity."""
        self._baselines.pop(entity_id, None)
        self._streak.pop(entity_id, None)
        self._firing.pop(entity_id, None)

    def reset(self) -> None:
        """Release all state for every entity."""
        self._baselines.clear()
        self._streak.clear()
        self._firing.clear()

    @property
    def n_entities(self) -> int:
        return len(self._baselines)
