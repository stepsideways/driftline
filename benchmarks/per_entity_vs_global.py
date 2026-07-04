"""Per-entity baseline versus a single global threshold.

A reproducible, synthetic benchmark. It builds a population of streams, injects a
sustained shift into some of them, and asks two detectors to find the shifts:

  1. driftline: each stream scored against its own recent baseline.
  2. global: one mean and one spread learned across all streams, one fixed band.

Scoring is at the episode level, the honest measure for a sustained shift against an
adaptive baseline: an episode counts as detected if the method flags at least one sample
inside the injected window, and a false alarm is a run of flagged samples outside every
injected window.

The point it makes, and the caveat it is honest about:

  - When streams have different normal ranges, the global band is dominated by the
    wide-ranging streams and never fires, so it catches nothing. The per-entity baseline
    reads each stream on its own terms and catches almost every episode.
  - When every stream shares the same range, the result flips: one pooled estimate is
    steadier than many short per-entity windows, so the global monitor is a little
    better. Per-entity is the right tool when normal differs from entity to entity, not
    a free win everywhere.

Pure standard library. Deterministic given the seed. Run: python benchmarks/per_entity_vs_global.py
"""
from __future__ import annotations

import os
import random
import sys
from dataclasses import dataclass
from statistics import fmean, pstdev

# Make the package importable when this file is run directly (python benchmarks/...).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from driftline import WindowBaseline  # noqa: E402


@dataclass(frozen=True)
class Scores:
    precision: float
    recall: float
    f1: float
    detections: int
    false_alarms: int


def _make_dataset(rng: random.Random, n_entities: int, T: int, warmup: int,
                  window: int, anomaly_frac: float, shift_sigmas: float,
                  heterogeneous: bool) -> tuple[dict[str, list[float]], dict[str, list[bool]]]:
    data: dict[str, list[float]] = {}
    truth: dict[str, list[bool]] = {}
    for i in range(n_entities):
        eid = f"e{i}"
        level = rng.uniform(0.0, 100.0) if heterogeneous else 50.0
        sd = rng.uniform(0.5, 3.0) if heterogeneous else 1.5
        window_anom: tuple[int, int] | None = None
        if rng.random() < anomaly_frac:
            start = rng.randint(warmup + window, T - 40)
            window_anom = (start, start + rng.randint(15, 30))
        series: list[float] = []
        flags: list[bool] = []
        for t in range(T):
            v = rng.gauss(level, sd)
            anom = window_anom is not None and window_anom[0] <= t < window_anom[1]
            if anom:
                v += shift_sigmas * sd
            series.append(v)
            flags.append(anom)
        data[eid] = series
        truth[eid] = flags
    return data, truth


def _flags_per_entity(data, warmup, window, threshold) -> dict[str, list[bool]]:
    flags: dict[str, list[bool]] = {}
    for eid, series in data.items():
        b = WindowBaseline(window=window, warmup=warmup)
        f: list[bool] = []
        for v in series:
            r = b.observe(v)
            f.append(r.ready and abs(r.z) >= threshold)
        flags[eid] = f
    return flags


def _flags_global(data, warmup, threshold) -> dict[str, list[bool]]:
    # Learn one mean and spread from a clean-ish training slice (the first `warmup`
    # samples of every stream), exactly as a single global monitor would be calibrated,
    # then apply one fixed band to every stream.
    train: list[float] = []
    for series in data.values():
        train.extend(series[:warmup])
    gmean = fmean(train)
    band = threshold * pstdev(train)
    return {eid: [abs(v - gmean) >= band for v in s] for eid, s in data.items()}


def _episode_scores(flags, truth, warmup) -> Scores:
    # Event-level scoring, which is what matters for a sustained shift: an episode is
    # DETECTED if the method flags at least one sample inside the injected window; a
    # false alarm is a maximal run of flagged samples (past warmup) that overlaps no
    # injected window.
    detected = total = false_alarm_runs = 0
    for eid, f in flags.items():
        tr = truth[eid]
        injected = [i for i, x in enumerate(tr) if x]
        if injected:
            total += 1
            if any(f[t] for t in range(injected[0], injected[-1] + 1)):
                detected += 1
        in_run = run_is_false = False
        for t in range(len(f)):
            if t < warmup:
                continue
            if f[t]:
                if not in_run:
                    in_run, run_is_false = True, True
                if tr[t]:
                    run_is_false = False
            else:
                false_alarm_runs += in_run and run_is_false
                in_run = False
        false_alarm_runs += in_run and run_is_false

    recall = detected / total if total else 0.0
    precision = detected / (detected + false_alarm_runs) if (detected + false_alarm_runs) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0
    return Scores(precision, recall, f1, detected, false_alarm_runs)


def run(heterogeneous: bool, seed: int = 7) -> tuple[Scores, Scores]:
    rng = random.Random(seed)
    warmup, window, threshold = 60, 60, 3.5
    data, truth = _make_dataset(
        rng, n_entities=200, T=400, warmup=warmup, window=window,
        anomaly_frac=0.15, shift_sigmas=4.0, heterogeneous=heterogeneous)
    per_entity = _episode_scores(_flags_per_entity(data, warmup, window, threshold), truth, warmup)
    global_ = _episode_scores(_flags_global(data, warmup, threshold), truth, warmup)
    return per_entity, global_


def _row(name: str, s: Scores) -> str:
    return (f"  {name:<12} precision={s.precision:5.2f}  recall={s.recall:5.2f}  "
            f"f1={s.f1:5.2f}  (detections={s.detections}, false alarms={s.false_alarms})")


def main() -> None:
    print("Heterogeneous streams (different normal ranges):")
    pe, gl = run(heterogeneous=True)
    print(_row("per-entity", pe))
    print(_row("global", gl))
    print()
    print("Homogeneous streams (same normal range):")
    pe2, gl2 = run(heterogeneous=False)
    print(_row("per-entity", pe2))
    print(_row("global", gl2))
    print()
    print("Read the heterogeneous block: when normal differs by stream, the global band is")
    print("dominated by the wide-ranging streams and never fires, so it catches nothing,")
    print("while per-entity catches almost every episode. On homogeneous streams the honest")
    print("result flips: one pooled estimate is steadier than 200 short per-entity windows,")
    print("so the global monitor is a little better there. Per-entity is the right tool when")
    print("normal differs from entity to entity, not a free win everywhere.")


if __name__ == "__main__":
    main()
