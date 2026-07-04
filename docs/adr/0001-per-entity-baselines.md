# ADR 0001: Score each stream against its own baseline

- Status: accepted
- Date: 2026-07-03

## Context

driftline monitors many streams at once: sensors in a fleet, servers in a cluster,
accounts on a platform. The job is to flag when a stream departs from normal. The
question this decision settles is: normal according to what.

The simplest thing to build is one global threshold. Learn a mean and a spread across
all streams, draw one band, and flag any value outside it. It is one number to store and
one comparison per sample.

It is also wrong whenever streams differ in their normal range, which is most of the
time. A global band is dominated by the wide-ranging and high-baseline streams. It cries
wolf on streams that are naturally high and it misses real shifts on streams that are
naturally low, because a shift that is large for a quiet stream is still inside a band
sized for the loud ones. The synthetic benchmark in `benchmarks/per_entity_vs_global.py`
shows the extreme version: on heterogeneous streams the global band never fires at all,
catching zero injected episodes, while a per-entity baseline catches almost every one.

## Decision

Keep one baseline per entity. Each stream is scored as a standardized deviation from its
own recent history, so the same numeric value can be routine for one entity and a clear
excursion for another, and both are read correctly.

Three rules travel with this decision because per-entity baselines fail in specific ways
without them:

1. **Causal scoring.** A value is scored against the points before it, then folded in,
   never against a baseline that already contains it. Otherwise a large anomaly inflates
   its own baseline and shrinks its own score, and the detector misses the spike it
   exists to catch.

2. **Warmup.** A baseline does not score until it has seen enough points to have an
   opinion, so cold-start noise on a new entity does not fire alarms.

3. **A robust option.** Centering on the median and scaling by the MAD, rather than the
   mean and standard deviation, means a single contaminating outlier does not mask the
   next genuine deviation. Offered as an option rather than the default because it costs
   a sort per score and is not always needed.

## Consequences

Good:
- A value is judged on terms that fit the entity it came from, which is the entire point.
- The API stays small. A caller feeds `(entity_id, value)` and gets events.
- The estimators sit behind a `Baseline` protocol, so the sliding-window and
  exponentially weighted implementations are interchangeable and a new one is a drop-in.

Costs, stated plainly:
- Memory grows with the number of live entities. `forget` and `reset` exist so a
  long-running detector over a changing population can release state.
- Each per-entity window is a smaller sample than one pooled global estimate, so on
  genuinely homogeneous streams, where every entity shares a range, the per-entity
  approach is slightly noisier and a global monitor does a little better. The benchmark
  reports this case rather than hiding it. Per-entity is the right default when normal
  differs by entity, not a universal improvement.

## Alternatives considered

- **Single global threshold.** Rejected as the primary mode for the reasons above. It
  remains the honest choice when streams are known to be homogeneous, and the benchmark
  keeps it as the comparison so the tradeoff is visible.
- **Clustering entities and one baseline per cluster.** A reasonable middle ground when
  entities fall into a few natural groups. Deferred: it adds a clustering step and its
  own tuning, and the per-entity baseline already covers the general case. It can be
  layered on later by mapping an entity id to a cluster id before `observe`.
