import math
from dataclasses import FrozenInstanceError

import pytest

from driftline import EwmaBaseline, Reading, WindowBaseline


def test_window_warms_up_before_scoring():
    b = WindowBaseline(window=10, warmup=5)
    readings = [b.observe(1.0) for _ in range(4)]
    assert all(not r.ready for r in readings)
    assert all(r.z == 0.0 for r in readings)
    # 5th observation reaches warmup -> the NEXT observe scores.
    b.observe(1.0)
    assert b.ready
    r = b.observe(1.0)
    assert r.ready


def test_window_scores_against_prior_points_not_itself():
    # A steady stream at 0 with sd 1-ish, then one large spike. The spike must be
    # scored against the calm history, not a history that already contains it.
    b = WindowBaseline(window=50, warmup=10)
    for v in (0.0, 1.0, -1.0, 0.5, -0.5, 1.0, -1.0, 0.0, 0.5, -0.5, 0.2, -0.2):
        b.observe(v)
    spike = b.observe(20.0)
    assert spike.ready
    assert spike.z > 5.0                 # clearly anomalous
    # The spike did not collapse its own score by joining its own baseline.
    assert abs(spike.value - 20.0) < 1e-9


def test_window_z_matches_hand_computation():
    b = WindowBaseline(window=4, warmup=4)
    for v in (10.0, 12.0, 14.0, 16.0):   # mean 13, pstdev = sqrt(5)
        b.observe(v)
    r = b.observe(20.0)
    expected = (20.0 - 13.0) / math.sqrt(5.0)
    assert r.z == pytest.approx(expected, rel=1e-9)


def test_min_scale_prevents_divide_by_zero_on_flat_stream():
    b = WindowBaseline(window=5, warmup=3, min_scale=1e-9)
    for _ in range(5):
        b.observe(7.0)                   # perfectly flat -> scale 0
    r = b.observe(7.5)
    assert math.isfinite(r.z)            # no ZeroDivisionError / inf


def test_robust_scale_resists_a_contaminating_outlier():
    plain = WindowBaseline(window=30, warmup=10, robust=False)
    rob = WindowBaseline(window=30, warmup=10, robust=True)
    seq = [0.0, 1.0, -1.0, 0.5, -0.5, 0.2, -0.2, 0.3, -0.3, 0.1, 100.0]  # one huge outlier
    for v in seq:
        plain.observe(v)
        rob.observe(v)
    # A genuine deviation right after a contaminated window: the plain baseline has its
    # mean dragged up and its scale inflated by the outlier, so 3.0 looks unremarkable.
    # The robust baseline (median centre, MAD scale) ignored the outlier, so it scores
    # 3.0 as the clear deviation it is.
    rp = plain.observe(3.0)
    rr = rob.observe(3.0)
    assert abs(rr.z) > abs(rp.z)
    assert rr.z > 3.0            # robust: 3.0 is well above the clean baseline near 0


def test_ewma_converges_and_scores():
    b = EwmaBaseline(alpha=0.1, warmup=30)
    for _ in range(200):
        b.observe(5.0)
    assert b.ready
    r = b.observe(5.0)
    assert r.mean == pytest.approx(5.0, abs=1e-6)
    assert abs(r.z) < 1.0


def test_ewma_flags_a_shift():
    b = EwmaBaseline(alpha=0.05, warmup=30)
    for _ in range(100):
        b.observe(0.0)
    # inject a little noise so variance is non-zero, then shift far away
    for v in (0.1, -0.1, 0.05, -0.05, 0.1, -0.1):
        b.observe(v)
    r = b.observe(5.0)
    assert r.z > 5.0


@pytest.mark.parametrize("bad", [0, 1])
def test_window_rejects_tiny_window(bad):
    with pytest.raises(ValueError):
        WindowBaseline(window=bad)


@pytest.mark.parametrize("bad", [0.0, -0.1, 1.5])
def test_ewma_rejects_bad_alpha(bad):
    with pytest.raises(ValueError):
        EwmaBaseline(alpha=bad)


def test_reading_is_immutable():
    r = Reading(1.0, 0.0, 1.0, 1.0, True)
    with pytest.raises(FrozenInstanceError):
        r.value = 2.0  # type: ignore[misc]
