# Prediction Model Documentation

This document explains how the custom ensemble model works, how it is calibrated, and how to improve it.

---

## Overview

The prediction model is implemented in `synth_integration.py` as `EnsembleGBMWeightedModel`.

It combines three classic financial price simulation models with fixed weights:

| Model | Class | Weight | Description |
|-------|-------|--------|-------------|
| Geometric Brownian Motion | `GeometricBrownianModel` | **50%** | Standard financial model: drift + log-normal random shocks |
| Mean Reversion | `MeanReversionModel` | **30%** | Assumes price gravitates back toward a mean (Ornstein-Uhlenbeck-like) |
| Random Walk | `RandomWalkModel` | **20%** | Pure Gaussian random walk — no drift, no memory |

The final prediction at each time step is a **weighted average** of the outputs of all three models.

---

## Calibration

Every **6 hours per asset**, the model re-calibrates its volatility (σ) and drift (μ) parameters using recent market data:

1. `get_all_volatilities()` is called (from `models/baseline/volatility_calculator.py`)
2. It fetches **2 days of 5-minute OHLCV data** from Yahoo Finance for each asset
3. Volatility is computed as the annualised standard deviation of log returns
4. Drift is computed as the mean log return

If Yahoo Finance is unavailable (rate limit, market closed, network error), the model falls back to hardcoded sigma values in `FALLBACK_SIGMA`:

```python
FALLBACK_SIGMA = {
    "BTC": 0.00472, "ETH": 0.00695, "XAU": 0.00208, "SOL": 0.00782,
    "SPYX": 0.00156, "NVDAX": 0.00342, "TSLAX": 0.00332,
    "AAPLX": 0.00250, "GOOGLX": 0.00332,
}
```

Calibration is cached **in memory per process**. If the miner restarts, calibration runs again on the first request.

---

## Entry Point

The subnet bridge file calls:
```python
generate_synth_simulations(
    asset="BTC",
    start_time="2026-03-06T12:00:00+00:00",
    time_increment=60,     # 1 minute
    time_length=3600,      # 1 hour
    num_simulations=1000,
    sigma=0.01,            # ignored — we use our own volatility
)
```

This function:
1. Fetches the live start price from Pyth/Hermes (`get_asset_price`)
2. Instantiates `EnsembleGBMWeightedModel`
3. Calls `model.predict(...)` to generate 1000 simulation paths
4. Calls `_log_prediction(...)` to append a compressed record to `/root/prediction_log.jsonl`
5. Returns the 1000 paths in Synth subnet format

---

## Output Format

Each call returns a list of 1000 simulations. Each simulation is a list of dicts:
```json
[
  {"time": "2026-03-06T12:00:00+00:00", "price": 68000.00},
  {"time": "2026-03-06T12:01:00+00:00", "price": 68045.21},
  ...
]
```

For a 1-hour window at 1-minute intervals: 61 time points per simulation.

> **Validator requirement**: The first time point's `time` string must exactly match the `start_time` string provided by the validator. The code preserves this string verbatim.

---

## Prediction Log Format

Each prediction is compacted and written to `/root/prediction_log.jsonl`. Instead of storing all 1000 paths (which would be ~50 MB/hour), only summary statistics are stored:

```json
{
  "logged_at": "2026-03-06T12:00:01.123456",
  "asset": "BTC",
  "start_time": "2026-03-06T12:00:00+00:00",
  "end_time": "2026-03-06T13:00:00+00:00",
  "time_increment": 60,
  "time_length": 3600,
  "num_simulations": 1000,
  "price_at_request": 68000.00,
  "mean_path": [68000.00, 68045.21, ...],
  "p10_path": [67800.00, 67820.00, ...],
  "p90_path": [68200.00, 68250.00, ...]
}
```

The dashboard reads this file to display predicted vs actual prices.

---

## Supported Assets

The model generates predictions for all 9 assets the subnet requests:

| Asset | Yahoo Finance ticker (for volatility) |
|-------|--------------------------------------|
| BTC | `BTC-USD` |
| ETH | `ETH-USD` |
| SOL | `SOL-USD` |
| XAU | `GC=F` (gold futures) |
| SPYX | `SPY` |
| NVDAX | `NVDA` |
| TSLAX | `TSLA` |
| AAPLX | `AAPL` |
| GOOGLX | `GOOGL` |

---

## Individual Model Files

### `models/baseline/geometric_brownian.py`
Implements standard GBM:
```
S(t+dt) = S(t) * exp((μ - σ²/2)*dt + σ*√dt*Z)
```
where Z ~ N(0,1).

### `models/baseline/mean_reversion.py`
Implements Ornstein-Uhlenbeck-like mean reversion:
```
S(t+dt) = S(t) + κ*(θ - S(t))*dt + σ*√dt*Z
```
where κ is `reversion_strength`, θ is `mean_price` (set to the current live price each call).

### `models/baseline/random_walk.py`
Implements a simple log-normal random walk:
```
S(t+dt) = S(t) * exp(σ*√dt*Z)
```
No drift term.

### `models/baseline/volatility_calculator.py`
Fetches per-asset σ and μ from Yahoo Finance:
- Downloads 2 days of 5-minute OHLCV data
- Calculates annualised log-return standard deviation (σ)
- Calculates annualised mean log return (μ)
- Returns a dict: `{asset: {"volatility": σ, "drift": μ}}`

---

## How to Improve the Model

The model is intentionally simple. Ways to improve:

1. **Better volatility estimation**: Use GARCH or realised variance instead of simple std dev
2. **Asset-specific calibration windows**: Some assets are more volatile intraday vs overnight
3. **Regime detection**: Different σ/μ during trending vs sideways markets
4. **Correlated simulations**: BTC and ETH are correlated; simulate them jointly
5. **Adjust ensemble weights**: The 50/30/20 split was a starting point — tune based on CRPS feedback from the dashboard

When making changes, always test that `generate_synth_simulations` still runs and returns the correct format before deploying to the server.

---

## Testing

```bash
# Quick import test
python -c "import synth_integration; print('ok')"

# Full integration test (generates 1000 simulations for BTC)
python synth_integration.py

# Run unit tests
pytest tests/test_baseline_models.py -v
pytest tests/test_simulations.py -v
```
