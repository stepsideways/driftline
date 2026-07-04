import pytest

from driftline import DriftDetector, EwmaBaseline, WindowBaseline


def _calm_then_spike(det, entity, calm, spike, n_calm=40):
    events = []
    for i in range(n_calm):
        v = calm + (0.5 if i % 2 else -0.5)   # small alternating noise
        e = det.observe(entity, v)
        if e:
            events.append(e)
    return events, det.observe(entity, spike)


def test_detector_fires_on_a_clear_excursion():
    det = DriftDetector(lambda: WindowBaseline(window=30, warmup=10), threshold=3.0)
    warm_events, event = _calm_then_spike(det, "s1", calm=10.0, spike=100.0)
    assert warm_events == []          # nothing fires during the calm run
    assert event is not None
    assert event.entity_id == "s1"
    assert event.direction == "high"
    assert event.z > 3.0


def test_consecutive_requires_sustained_breach():
    # One-sample breach should NOT fire when 3 consecutive are required.
    det = DriftDetector(
        lambda: WindowBaseline(window=30, warmup=10), threshold=3.0, consecutive=3
    )
    for i in range(40):
        det.observe("s1", 0.0 + (0.5 if i % 2 else -0.5))
    assert det.observe("s1", 50.0) is None      # breach 1
    assert det.observe("s1", 50.0) is None      # breach 2
    assert det.observe("s1", 50.0) is not None  # breach 3 confirms


def test_edge_triggered_one_event_per_episode():
    det = DriftDetector(lambda: WindowBaseline(window=15, warmup=8), threshold=3.0)
    for i in range(30):
        det.observe("s1", 0.0 + (0.5 if i % 2 else -0.5))
    first = det.observe("s1", 50.0)
    assert first is not None
    # Still breaching: no repeat events until it clears.
    assert det.observe("s1", 50.0) is None
    assert det.observe("s1", 50.0) is None
    # Clear back to normal for longer than the window, so the spike values age out of
    # the sliding baseline, then breach again -> a new event. (A window baseline needs
    # time to forget a big excursion; that is a real property, exercised here.)
    for i in range(20):
        det.observe("s1", 0.0 + (0.5 if i % 2 else -0.5))
    second = det.observe("s1", 50.0)
    assert second is not None


def test_entities_are_independent():
    det = DriftDetector(lambda: WindowBaseline(window=20, warmup=8), threshold=3.0)
    # Two streams with very different normal levels.
    for i in range(30):
        det.observe("low", 1.0 + (0.2 if i % 2 else -0.2))
        det.observe("high", 1000.0 + (0.2 if i % 2 else -0.2))
    # 1000 is exactly normal for the stream that lives near 1000, and an enormous
    # excursion for the stream that lives near 1. The same value, read correctly in
    # both, which a single global threshold could not do.
    assert det.observe("low", 1000.0) is not None
    assert det.observe("high", 1000.0) is None
    assert det.n_entities == 2


def test_forget_and_reset_release_state():
    det = DriftDetector()
    det.observe("a", 1.0)
    det.observe("b", 1.0)
    assert det.n_entities == 2
    det.forget("a")
    assert det.n_entities == 1
    det.reset()
    assert det.n_entities == 0


def test_detector_accepts_ewma_factory():
    det = DriftDetector(lambda: EwmaBaseline(alpha=0.1, warmup=20), threshold=4.0)
    for i in range(60):
        det.observe("s1", 0.0 + (0.1 if i % 2 else -0.1))
    assert det.observe("s1", 10.0) is not None


@pytest.mark.parametrize("bad", [0.0, -1.0])
def test_rejects_bad_threshold(bad):
    with pytest.raises(ValueError):
        DriftDetector(threshold=bad)


def test_rejects_bad_consecutive():
    with pytest.raises(ValueError):
        DriftDetector(consecutive=0)
