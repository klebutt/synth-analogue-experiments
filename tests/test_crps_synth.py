"""Tests for validator-style CRPS on basis point changes (models/crps_synth.py)."""

import pytest
import numpy as np
from models.crps_synth import validator_crps_basis_points, VALIDATOR_INTERVAL_NAMES


def test_validator_crps_perfect_predictions():
    """When predicted bp changes match actual, CRPS should be 0."""
    # 10 paths, all with same 5 prices; actual = same prices -> bp changes match exactly
    p0, p5m, p30m, p3h, p24h = 100000.0, 100050.0, 100200.0, 101000.0, 102000.0
    path_5 = np.array([[p0, p5m, p30m, p3h, p24h]] * 10)
    actual = [p0, p5m, p30m, p3h, p24h]
    score, per = validator_crps_basis_points(path_5, actual)
    assert score == 0.0
    assert per["5m"] == 0.0 and per["30m"] == 0.0 and per["3h"] == 0.0 and per["24h"] == 0.0


def test_validator_crps_four_intervals():
    """Returns prompt_score (sum) and per_interval with keys 5m, 30m, 3h, 24h."""
    np.random.seed(42)
    n = 100
    p0 = 50000.0
    path_5 = np.zeros((n, 5))
    path_5[:, 0] = p0
    path_5[:, 1] = p0 + np.random.normal(0, 200, n)
    path_5[:, 2] = p0 + np.random.normal(0, 400, n)
    path_5[:, 3] = p0 + np.random.normal(0, 800, n)
    path_5[:, 4] = p0 + np.random.normal(0, 1500, n)
    path_5 = np.maximum(path_5, 1000.0)
    actual = [p0, p0 + 100, p0 + 200, p0 + 500, p0 + 1000]
    score, per = validator_crps_basis_points(path_5, actual)
    assert score >= 0
    assert set(per.keys()) == set(VALIDATOR_INTERVAL_NAMES)
    assert abs(score - (per["5m"] + per["30m"] + per["3h"] + per["24h"])) < 1e-6


def test_validator_crps_full_289_paths():
    """Accepts full 289-step paths and uses indices 0, 1, 6, 36, 288."""
    n = 20
    paths_289 = np.random.uniform(49000, 51000, (n, 289))
    paths_289[:, 0] = 50000.0
    actual_5 = [50000.0, 50100.0, 50200.0, 50500.0, 51000.0]
    score, per = validator_crps_basis_points(paths_289, actual_5)
    assert np.isfinite(score)
    assert set(per.keys()) == set(VALIDATOR_INTERVAL_NAMES)


def test_validator_crps_bad_actual_length_raises():
    """Requires 5 actual prices."""
    path_5 = np.random.uniform(1000, 10000, (10, 5))
    with pytest.raises(ValueError, match="actual_prices must be 5"):
        validator_crps_basis_points(path_5, [1.0, 2.0, 3.0])
