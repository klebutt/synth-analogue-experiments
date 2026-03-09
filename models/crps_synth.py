"""
Validator-style CRPS on basis point changes for Synth subnet.

Validators score CRPS on price change in basis points over four intervals:
5m, 30m, 3h, 24h. Prompt score = sum of the four interval CRPS values.

This module provides a function to compute that exact quantity from full
ensemble paths and actual prices at t0, 5m, 30m, 3h, 24h. For use in
local experiments, scripts, and tests — not used by the miner at runtime.
See docs/SCORING_AND_METRICS.md and the Synth subnet README.
"""

from __future__ import annotations

import numpy as np
from typing import List, Sequence, Tuple, Union

# Step indices for 5-minute increments: 0, 1, 6, 36, 288 = t0, 5m, 30m, 3h, 24h
VALIDATOR_INTERVAL_STEPS = (0, 1, 6, 36, 288)
VALIDATOR_INTERVAL_NAMES = ("5m", "30m", "3h", "24h")


def _crps_ensemble(predicted_values: np.ndarray, actual: float) -> float:
    """
    CRPS for one interval from an ensemble of predicted values and one actual.
    Formula: (1/N) sum_n |y_n - x| - (1/(2N^2)) sum_n sum_m |y_n - y_m|
    """
    pred = np.asarray(predicted_values, dtype=float).ravel()
    n = pred.size
    if n == 0:
        return float("nan")
    term1 = np.mean(np.abs(pred - actual))
    if n == 1:
        return max(0.0, term1)
    # Full pairwise |y_n - y_m| for exact CRPS (no sampling)
    diff = np.abs(pred[:, np.newaxis] - pred[np.newaxis, :])
    term2 = 0.5 * np.mean(diff)
    crps = term1 - term2
    return max(0.0, crps)


def validator_crps_basis_points(
    paths: Union[List[List[float]], np.ndarray],
    actual_prices: Union[Sequence[float], Sequence[Tuple[int, float]]],
) -> Tuple[float, dict]:
    """
    Compute validator-style CRPS on price change in basis points over 5m, 30m, 3h, 24h.

    Args:
        paths: Either:
          - List of paths, each path a list of 5 prices [P0, P_5m, P_30m, P_3h, P_24h], or
          - 2D array of shape (n_paths, 289) with 5-min steps (indices 0, 1, 6, 36, 288 used).
        actual_prices: Either:
          - List of 5 floats [P0, P_5m, P_30m, P_3h, P_24h], or
          - List of (step_index, price) for the five steps.

    Returns:
        (prompt_score, per_interval_crps):
        - prompt_score: sum of CRPS over the four intervals (same as validators).
        - per_interval_crps: {"5m": float, "30m": float, "3h": float, "24h": float}.
    """
    paths_arr = np.asarray(paths, dtype=float)
    if paths_arr.ndim == 1:
        paths_arr = paths_arr[np.newaxis, :]
    n_paths = paths_arr.shape[0]

    # Normalise to (n_paths, 5) for the five step indices
    if paths_arr.shape[1] >= 289:
        # Full paths: extract steps 0, 1, 6, 36, 288
        path_5 = paths_arr[:, [0, 1, 6, 36, 288]]
    elif paths_arr.shape[1] == 5:
        path_5 = paths_arr
    else:
        raise ValueError("paths must have 5 prices per path or full 289-step paths")

    # Actual prices: list of 5 or list of (step, price)
    if actual_prices and isinstance(actual_prices[0], (list, tuple)) and len(actual_prices[0]) == 2:
        step_to_price = dict(actual_prices)
        actual_5 = np.array([
            step_to_price[0], step_to_price[1], step_to_price[6],
            step_to_price[36], step_to_price[288]
        ], dtype=float)
    else:
        actual_5 = np.asarray(actual_prices, dtype=float)
        if actual_5.size != 5:
            raise ValueError("actual_prices must be 5 prices [P0, P_5m, P_30m, P_3h, P_24h]")
        actual_5 = actual_5.ravel()

    p0_path = path_5[:, 0]
    actual_p0 = actual_5[0]
    if actual_p0 <= 0 or np.any(p0_path <= 0):
        return float("nan"), {k: float("nan") for k in VALIDATOR_INTERVAL_NAMES}

    per_interval = {}
    # Intervals: 5m (col 1), 30m (col 2), 3h (col 3), 24h (col 4) — col 0 is t0
    for i, name in enumerate(VALIDATOR_INTERVAL_NAMES):
        k = i + 1  # end step index in path_5 (1, 2, 3, 4)
        pred_bp = (path_5[:, k] - p0_path) / p0_path * 10000.0
        actual_bp = (actual_5[k] - actual_p0) / actual_p0 * 10000.0
        crps = _crps_ensemble(pred_bp, actual_bp)
        per_interval[name] = crps

    prompt_score = sum(per_interval.values())
    return prompt_score, per_interval
