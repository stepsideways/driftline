# driftline: runbook

Run every feature without Claude. Read `REVIEW_GUIDE.md` first for orientation, and
`README.md` for the quickstart in prose.

Legend: **[verified]** = run and confirmed on 2026-07-21 (Windows dev host, Python
3.12.10). **[from-source]** = the command is read from the code and correct as written,
but was not executed in this pass.

## 1. Prerequisites

- Python 3.10 or later. Confirmed on 3.12.10. Check: `python --version`.
- No compiler, no system libraries, no GPU. The library is pure Python standard library
  with zero runtime dependencies.
- OS: any. Nothing platform-specific. Commands below use a POSIX shell; on Windows use the
  PowerShell activate script noted inline.
- Development extras (pytest, ruff) are optional and only needed to run the tests and the
  linter. They install with the `[dev]` extra.
- No token, no private sibling repo, no network access is required to install or run
  anything here.

## 2. Install

From a fresh clone:

```bash
git clone https://github.com/stepsideways/driftline.git
cd driftline
python -m venv .venv
source .venv/bin/activate        # Windows PowerShell: .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .                 # library only  [from-source]
pip install -e ".[dev]"          # with pytest + ruff  [from-source]
```

There is no lockfile; the runtime dependency set is empty, so a lockfile would pin only
the dev tools. The `[dev]` extra pins `pytest>=8` and `ruff>=0.5` (see `pyproject.toml`).

Note: because the package directory `driftline/` sits at the repo root, `import driftline`
also works from the repo root without installing. A proper `pip install -e .` is what makes
it importable from anywhere. **[verified: import from repo root]**

```bash
python -c "import driftline; print(driftline.__version__, driftline.__all__)"
# -> 0.1.0 ['Baseline', 'Reading', 'WindowBaseline', 'EwmaBaseline', 'DriftDetector', 'DriftEvent', 'mad', 'robust_scale']
```

## 3. Features

This is a library plus a benchmark. There is no server and no CLI. The runnable surfaces
are the import API, the benchmark script, the test suite, and the linter.

### Library API: detect per-entity drift **[verified: import + smoke]**

The primary use. One detector, many entities; each entity gets its own baseline the first
time it is seen. `observe` returns a `DriftEvent` only when a fresh, confirmed excursion
begins, not once per sample while it lasts.

```python
from driftline import DriftDetector, WindowBaseline, EwmaBaseline

det = DriftDetector(threshold=3.0, consecutive=2)     # default WindowBaseline per entity
for entity_id, value in stream:                        # your stream of (id, number)
    event = det.observe(entity_id, value)
    if event:
        print(f"{event.entity_id}: {event.value} is {event.z:.1f} sigma {event.direction}")

det.forget("sensor-42")   # release state for an entity you will not see again
```

Choose the baseline that fits the stream:

```python
# Exact over the last 200 points, robust to the odd contaminating outlier.
det = DriftDetector(lambda: WindowBaseline(window=200, robust=True), threshold=3.5)
# Constant memory, no window to size, forgets old behavior at a fixed rate.
det = DriftDetector(lambda: EwmaBaseline(alpha=0.02), threshold=3.5)
```

Verify it works with a one-line smoke check (a calm run, then a spike, must produce exactly
one event):

```bash
python -c "from driftline import DriftDetector, WindowBaseline; \
d=DriftDetector(lambda: WindowBaseline(window=30, warmup=10), threshold=3.0); \
[d.observe('s', 10.0+(0.5 if i%2 else -0.5)) for i in range(40)]; \
e=d.observe('s', 100.0); print('event:', e is not None, 'z=%.1f' % e.z, e.direction)"
# -> event: True z=... high
```

### Reproducible benchmark: per-entity vs global **[verified]**

```bash
python benchmarks/per_entity_vs_global.py
```

Builds a synthetic population of 200 streams, injects sustained shifts, and scores
per-entity detection against a single global band at the episode level. Deterministic given
the fixed seed. Observed output (2026-07-21):

```
Heterogeneous streams (different normal ranges):
  per-entity   precision= 0.28  recall= 0.93  f1= 0.43  (detections=26, false alarms=67)
  global       precision= 0.00  recall= 0.00  f1= 0.00  (detections=0, false alarms=0)

Homogeneous streams (same normal range):
  per-entity   precision= 0.32  recall= 0.97  f1= 0.48  (detections=32, false alarms=68)
  global       precision= 0.49  recall= 1.00  f1= 0.65  (detections=33, false alarms=35)
```

This matches the table in `README.md`. Read the heterogeneous block: the global band never
fires when streams have different normal ranges. The homogeneous block is the honest
caveat where a pooled global estimate does a little better. Runs in well under a second, no
network, no files written.

## 4. Tests

```bash
pytest -q                        # from the repo root, after pip install -e ".[dev]"
python -m pytest -q              # equivalent without relying on the console script
```

**[verified: 26 passed in 0.07s]**. Collection count is stable:

```bash
python -m pytest --collect-only -q      # -> 26 tests collected   [verified]
```

The suite covers the causal-scoring rule, the hand-checked z arithmetic, the robust path
under contamination, warmup, the divide-by-zero floor, per-entity independence, consecutive
confirmation, edge triggering, and state release. No external dependencies, no network, no
fixtures on disk.

Lint (the same check CI runs):

```bash
ruff check .                     # -> All checks passed!   [verified: ruff 0.15.20]
```

CI runs lint, the test suite, and a benchmark smoke run across Python 3.10, 3.11, and 3.12
on every push to `main` and every pull request (`.github/workflows/ci.yml`).

## 5. Deploy and packaging

There is nothing to deploy. driftline is an importable library, not a service; it binds no
port and opens no socket. Distribution is a normal Python package build:

```bash
python -m build                  # produces dist/*.whl and dist/*.tar.gz   [from-source]
```

The build backend is hatchling; the wheel packages the `driftline` directory (see
`[tool.hatch.build.targets.wheel]` in `pyproject.toml`). Consumers install the wheel and
`import driftline`.

## 6. Troubleshooting

- **`ModuleNotFoundError: No module named 'driftline'`**: you are running from outside the
  repo root and have not installed the package. Either `pip install -e .`, or run from the
  repo root. The benchmark script sidesteps this by inserting the repo root on `sys.path`,
  so `python benchmarks/per_entity_vs_global.py` works from a fresh clone with no install.
- **`python -m driftline` fails with "cannot be directly executed"**: expected. There is
  no CLI; use the import API (section 3) or the benchmark script. This is a library.
- **`pytest: command not found`**: install the dev extra: `pip install -e ".[dev]"`, or
  invoke as `python -m pytest`.
- **A flat stream does not raise a divide-by-zero**: that is `min_scale` working as
  designed. A momentarily constant stream has zero spread; the scale is floored (default
  `1e-9`) so `z` stays finite instead of reporting an infinite deviation.
- **No events fire during a calm warmup run**: expected. A baseline reports `ready=False`
  and returns `z=0.0` until it has seen `warmup` points (default: half the window for
  `WindowBaseline`, 20 for `EwmaBaseline`), so cold-start noise does not alarm.
