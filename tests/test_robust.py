import math

import pytest

from driftline.robust import mad, robust_scale


def test_mad_of_symmetric_values():
    # values 1..9, median 5, absolute deviations 0,1,1,2,2,3,3,4,4 -> median 2
    assert mad([1, 2, 3, 4, 5, 6, 7, 8, 9]) == 2


def test_mad_ignores_a_single_extreme_value():
    base = [10, 11, 9, 10, 12, 8, 10]
    contaminated = base + [10_000]
    # One wild point moves the standard deviation enormously but the MAD barely.
    assert mad(contaminated) < 3 * mad(base)


def test_robust_scale_matches_std_for_normal_like_data():
    # For a roughly normal sample, 1.4826 * MAD approximates the standard deviation.
    data = [-2, -1, -1, 0, 0, 0, 1, 1, 2]
    rs = robust_scale(data)
    sd = math.sqrt(sum(x * x for x in data) / len(data))
    assert rs == pytest.approx(sd, rel=0.5)


def test_mad_requires_values():
    with pytest.raises(ValueError):
        mad([])
