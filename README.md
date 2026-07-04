# driftline

Online per-entity anomaly detection. Score each stream against its own recent
baseline instead of one global threshold, so a value that is normal for one entity
and alarming for another is read correctly in both.

The idea is old and simple: a fixed cutoff that works for the average stream is wrong
for the streams that are naturally high or naturally low. If you monitor a fleet of
sensors, a population of servers, or many accounts, "normal" is per-entity, and the
detector should be too. driftline is a small, dependency-free, typed implementation of
that idea, with the parts that make it survive contact with real data: causal scoring,
a robust option, warmup, and alarm debouncing.

Pure Python standard library. No numpy, no pandas, no config file. Python 3.10+.

## Install

```bash
pip install -e .          # from a clone
pip install -e ".[dev]"   # with pytest + ruff
```

## Quickstart

```python
from driftline import DriftDetector

# One detector, many entities. Each entity gets its own baseline the first time it is seen.
det = DriftDetector(threshold=3.0, consecutive=2)

for reading in stream:                       # reading = (entity_id, value)
    event = det.observe(reading.entity_id, reading.value)
    if event:
        print(f"{event.entity_id}: {event.value} is {event.z:.1f} sigma {event.direction}")
```

`observe` returns a `DriftEvent` only when a fresh, confirmed excursion begins, not once
per sample while it lasts. A sustained shift produces one event, not a storm.

Pick the baseline that fits the stream:

```python
from driftline import DriftDetector, WindowBaseline, EwmaBaseline

# Exact over the last 200 points, robust to the odd contaminating outlier.
det = DriftDetector(lambda: WindowBaseline(window=200, robust=True), threshold=3.5)

# Constant memory, no window to size, forgets old behavior at a fixed rate.
det = DriftDetector(lambda: EwmaBaseline(alpha=0.02), threshold=3.5)
```

Release state for entities you will not see again, so a long-running detector over a
changing population does not grow without bound:

```python
det.forget("sensor-42")
```

## Why per-entity

`benchmarks/per_entity_vs_global.py` is a reproducible synthetic benchmark. It builds a
population of streams, injects a sustained shift into some of them, and asks two
detectors to find the shifts: driftline (each stream against its own baseline) versus a
single global band learned across all streams. Scoring is at the episode level, which is
the honest measure for a sustained shift against an adaptive baseline: did the detector
catch the event, and how many spurious alert-runs did it raise.

```
Heterogeneous streams (different normal ranges):
  per-entity   precision= 0.28  recall= 0.93  f1= 0.43  (detections=26, false alarms=67)
  global       precision= 0.00  recall= 0.00  f1= 0.00  (detections=0,  false alarms=0)

Homogeneous streams (same normal range):
  per-entity   precision= 0.32  recall= 0.97  f1= 0.48  (detections=32, false alarms=68)
  global       precision= 0.49  recall= 1.00  f1= 0.65  (detections=33, false alarms=35)
```

Read the heterogeneous block. When normal differs by stream, the global band is
dominated by the wide-ranging streams and never fires, so it catches nothing, while
per-entity catches almost every episode.

The homogeneous block is the honest caveat, and it does not flatter this library. When
every stream shares one range, a single pooled estimate is steadier than 200 short
per-entity windows, so the global monitor is a little better there. Per-entity is the
right tool when normal differs from entity to entity, which in the real world it usually
does. It is not a free win everywhere.

Run it yourself:

```bash
python benchmarks/per_entity_vs_global.py
```

## Design notes

A few decisions are load-bearing and worth calling out. The reasoning behind the central
one is in [docs/adr/0001-per-entity-baselines.md](docs/adr/0001-per-entity-baselines.md).

**Causal scoring.** A value is scored against the baseline of the points that came
before it, never a baseline that already contains it. Fold-then-score lets a large
anomaly quietly inflate its own baseline and shrink its own score, which is the classic
way a streaming detector misses the very spike it exists to catch. driftline scores
first, then folds the value in.

**Robust option.** `WindowBaseline(robust=True)` centers on the median and scales by
1.4826 times the median absolute deviation instead of the mean and standard deviation.
One contaminating outlier drags the mean and inflates the standard deviation enough to
mask the next genuine deviation. The median and MAD ignore it. Robustifying only the
scale is not enough, because the mean is still pulled, so both the center and the scale
switch together.

**Warmup.** A baseline reports `ready = False` and does not score until it has seen
enough points to have an opinion. Cold-start noise does not fire alarms.

**Debouncing.** `consecutive=N` requires N consecutive breaches before confirming, which
filters single-sample noise. Edge triggering then emits one event per sustained episode
and re-arms only after the stream returns to normal.

**A floor on scale.** A momentarily flat stream has zero spread, which would divide by
zero and report an infinite deviation. `min_scale` floors it.

## Tests

```bash
pytest -q
```

The suite covers the causal-scoring rule, the hand-checked z arithmetic, the robust path
under contamination, warmup, the divide-by-zero floor, per-entity independence,
consecutive confirmation, edge triggering, and state release. It runs in well under a
second with no external dependencies.

## Scope

driftline detects univariate drift: one number per entity per step. It is not a
forecaster, not a classifier, and not multivariate. It does one thing, which is to tell
you when a stream has departed from its own normal, and it tries to do that honestly.

## About

Written by Matthew Lashomb. I am a registered nurse who writes software. Watching the
same monitor alarm identically for two patients whose normal heart rates are forty beats
apart is what made per-entity baselines feel obvious to me, and the habits in this
library (score before you fold, prefer the honest benchmark to the flattering one, say
what the tool is not) come from a setting where the difference between signal and noise
is not academic. This repository is a small, self-contained demonstration of how I build.

## License

MIT. See [LICENSE](LICENSE).
