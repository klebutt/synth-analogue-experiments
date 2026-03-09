# Scoring and Metrics

This document explains how validators score miners on Subnet 50 (Synth), how those scores translate to TAO rewards, and what the on-chain metrics visible in the dashboard mean.

---

## How Validators Score Miners

*The following matches the [official Synth subnet validator scoring methodology](https://github.com/mode-network/synth-subnet#13-validators-scoring-methodology).*

### What validators ask for
Validators send requests for **1000 simulated price paths** per asset at **5-minute increments** over a **24-hour horizon** (and separately for 1-hour HFT prompts). Parameters: `(start_time, asset, time_increment=300, time_horizon=24h, num_simulations=1000)`. Assets include BTC, ETH, SOL, XAU, SPYX, NVDAX, TSLAX, AAPLX, GOOGLX. Each asset contributes to the final miner weights (see asset weights below).

### CRPS on price change in basis points
Validators do **not** score raw prices. They score **price change in basis points (bp)** so that prompt scores have the same units across all assets.

- **Basis point change** for an interval: `(P_end - P_start) / P_start * 10000`
- **Predicted bp change**: from the 1000 paths, validators compute the ensemble of bp changes over each interval
- **Observed bp change**: from the Pyth oracle at the interval end (validators store prices at each time increment)
- **CRPS** is calculated on the predicted vs observed bp change (ensemble formula: average |y_n - x| minus half the average pairwise |y_n - y_m|)

### Four time increments (5m, 30m, 3h, 24h)
For each checking prompt, CRPS is computed for **four intervals** (with 5-minute steps):

| Interval | Step index | Description |
|----------|------------|-------------|
| 5m  | 1  | t₀ → t₀+5m   |
| 30m | 6  | t₀ → t₀+30m  |
| 3h  | 36 | t₀ → t₀+3h   |
| 24h | 288| t₀ → t₀+24h   |

For each interval: predicted bp changes (from 1000 paths), observed bp change (from Pyth), then CRPS for that interval. **Prompt score = sum of the four CRPS values** (one per interval).

### CRPS transformation (best → 0)
After computing the sum of CRPS per miner per prompt:

1. Order miners by CRPS sum; cap the **worst 10%** of scores to the **90th percentile**
2. Take the **best (lowest)** CRPS sum for that prompt
3. **Subtract the best score from all miners** so the best miner gets **0**
4. Miners who failed to submit or submitted invalidly get the **90th percentile** score

### Rolling average (leaderboard score)
The validator stores historic **per-request** scores. The **leaderboard score** for each miner is a **rolling average** over the past **10 days** of these transformed scores, **weighted by asset**. Recent performance is emphasised; the sum runs over all requests within the 10-day window. Highest-ranking miners have the **lowest** leaderboard scores.

### Final emissions
Emission allocation uses a **softmax** over (negative) leaderboard scores: \( A_i = e^{-\beta L_i} / \sum_j e^{-\beta L_j} \cdot E(t) \) with \(\beta = -0.1\). So lower CRPS → lower transformed score → higher emission.

### Asset weights (24h prompts)
CRPS from each asset contributes to the rolling leaderboard with the following weights (from subnet README): BTC 1.0, ETH ~0.67, XAU ~2.26, SOL ~0.59, SPYX ~2.99, NVDAX ~1.39, TSLAX ~1.42, AAPLX ~1.86, GOOGLX ~1.43.

### When scores appear
After a prediction window ends, the validator fetches actual prices from Pyth and scores all miners. Scores are updated on-chain periodically. After first registration, it typically takes **6–24 hours** for incentive/emission to appear.

---

## On-Chain Metrics (from Bittensor Metagraph)

These are the values visible in the dashboard's "On-Chain Metrics" section and their meanings:

| Metric | Metagraph attr | Description |
|--------|---------------|-------------|
| **Incentive** | `mg.I[uid]` | Your weighted share of the validation reward pool. Proportional to your CRPS rank. Increases as you improve. |
| **Emission (per block)** | `mg.E[uid]` | TAO you earn per blockchain block (~12s). Multiply by 7200 (blocks/day) for daily earnings. |
| **Stake (alpha)** | `mg.S[uid]` | Alpha tokens staked by you in the subnet. ~94.64 ש as of Mar 2026. This is subnet-native alpha, **not raw TAO**. |
| **Consensus** | `mg.C[uid]` | How much validators agree you should be weighted. |
| **Dividends** | `mg.D[uid]` | Staker rewards (for anyone staking on your hotkey). |
| **Validator Trust** | `mg.Tv[uid]` | Trust score assigned by validators. Builds over time. |
| **Pruning Score** | `mg.pruning_score[uid]` | Internal metagraph score used to decide who gets deregistered if the subnet fills up. |

---

## Deregistration Risk

Miners can be removed from the subnet through two mechanisms:

### 1. UID Trimming (competitive pressure)
When all 256 UID slots are full and a new miner tries to register:
- The validator calculates a "pruning score" for every existing miner
- The miner with the **lowest pruning score** is deregistered to make room
- Factors that protect you: high stake, good CRPS performance, long tenure

### 2. Subnet deregistration
The subnet itself could theoretically be removed from the Bittensor root network if it stops attracting stake/validators, but this is rare and unrelated to individual miner performance.

**To protect yourself from UID trimming:**
- Maintain good prediction quality (low CRPS)
- Keep stake above zero
- Ensure the miner is always online and responding to requests

---

## Why Incentive Might Show 0

Common reasons your incentive is 0:
1. **Recently registered** — it takes 6–24h for the first scoring windows to complete
2. **Axon not serving** — if `mg.axons[uid].is_serving = False`, validators can't reach you
3. **Miner crashed** — check `pm2 list` and miner logs
4. **Very low trust** — new miners start with trust 0 and build up gradually
5. **Poor model performance** — if your CRPS is consistently worse than other miners, your weight converges to 0

---

## Dashboard alignment with validator scoring

The dashboard now computes **the same quantity** validators use, so "Validator CRPS" on the dashboard is directly comparable to what drives on-chain scores.

### What the dashboard computes
- **Validator-aligned CRPS**: For each completed prediction (BTC/ETH/SOL only), we compute CRPS on **price change in basis points** for the **four intervals** (5m, 30m, 3h, 24h), then **sum** them — same definition as the subnet.
- **Approximation**: We only have mean, p10, and p90 paths in the log (not the full 1000 paths). We approximate the bp-change distribution per interval with a Gaussian (mean and sigma derived from mean/p10/p90) and use the closed-form Gaussian CRPS formula. So the dashboard value is an **approximation** of the true validator CRPS for that prompt.
- **Actuals**: We use **Yahoo Finance** (yfinance) for actual prices at t₀, t+5m, t+30m, t+3h, t+24h. Validators use **Pyth**. For **BTC, ETH, SOL** the two sources are comparable; for **XAU** and tokenised equities (SPYX, NVDAX, etc.) there can be systematic differences, so we **only score BTC, ETH, SOL** on the dashboard (`SCORING_ASSETS` in `dashboard/app.py`).

### Other dashboard metrics
- **Per-interval CRPS**: Breakdown into CRPS(5m), CRPS(30m), CRPS(3h), CRPS(24h) so you can see which horizon hurts most.
- **Calibration %**: Share of actuals inside the p10–p90 band (target ~80%); supports tuning band width.
- **MAE**: Mean absolute error on endpoint price (secondary; not what validators use).

---

## Known Oracle Mismatch Issue

The subnet's internal oracle for non-crypto assets uses a different pricing source than Yahoo Finance:

| Asset | Issue |
|-------|-------|
| XAU | Subnet oracle uses spot gold pricing; yfinance futures (`GC=F`) diverge by 0.5–2% |
| SPYX, NVDAX, TSLAX, AAPLX, GOOGLX | Tokenised equity prices differ from underlying equity prices due to wrapping/liquidity |

**Impact**: If you include these assets in dashboard MAE calculations, you will see artificially inflated error figures (thousands of percent). The `SCORING_ASSETS = {"BTC", "ETH", "SOL"}` constant in `dashboard/app.py` exists to prevent this.

**This does not affect your actual validator scores** — the validators use the same oracle as the miner when fetching start prices, so predictions are evaluated fairly.

---

## Daily Earnings Estimate

To estimate daily TAO earnings from the metagraph:
```python
emission_per_block = float(mg.E[255])
blocks_per_day = 7200   # ~12s per block
daily_tao = emission_per_block * blocks_per_day
print(f"Estimated daily TAO: {daily_tao:.4f}")
```

As of Mar 2026 the miner was still in the early earning phase with emission ~0.41 per block (raw value, check units in bittensor 10.x as they may be normalised to [0,1]).
