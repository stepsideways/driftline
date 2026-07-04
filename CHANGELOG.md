# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to
[Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2026-07-03

First release.

### Added
- `WindowBaseline`: sliding-window per-entity baseline with causal scoring, warmup, a
  robust (median + MAD) option, and a floor on scale.
- `EwmaBaseline`: exponentially weighted baseline with constant memory, using the
  incremental West (1979) mean and variance.
- `DriftDetector`: one baseline per entity, consecutive-sample confirmation, edge
  triggering (one event per sustained episode), and per-entity state release via
  `forget` and `reset`.
- `robust_scale` and `mad` helpers.
- `benchmarks/per_entity_vs_global.py`: reproducible episode-level benchmark comparing
  per-entity baselines against a single global threshold, with an honest homogeneous
  case where the global monitor wins.
- Full type hints, a `py.typed` marker, and a test suite covering the causal-scoring
  rule, robust contamination handling, warmup, debouncing, and state release.
