# Scoring and Metrics

This document explains how validators score miners on Subnet 50 (Synth), how those scores translate to TAO rewards, and what the on-chain metrics visible in the dashboard mean.

---

## How Validators Score Miners

### What validators ask for
Validators periodically send requests to each miner asking for 1000 simulated price paths for an asset over a fixed time window (e.g., 1 hour, starting from "now"). Each path has one price point per minute (61 points for a 1-hour window).

### How predictions are scored
Validators use **CRPS (Continuous Ranked Probability Score)** to evaluate predictions once the actual price at the end of the window is known.

CRPS measures how well your predicted distribution covers the actual outcome:
- A tighter distribution centred on the actual price → lower CRPS → higher score
- A wide, spread-out distribution → higher CRPS → lower score
- A distribution that misses the actual price → very high CRPS → penalised

CRPS ranges from 0 (perfect) to ∞ (terrible). The subnet normalises scores across all miners and uses them to set reward weights.

### When scores appear
After a prediction window ends, the validator fetches the actual price and scores all miners that responded to that window. This means:
- There is always a **delay** between submitting predictions and seeing scores
- Scores are updated on-chain roughly every 100–200 blocks (~20–40 minutes)
- After first registration or re-registration, it typically takes **6–24 hours** for incentive/emission to appear

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

## Dashboard Scoring vs Validator Scoring

The dashboard has its own independent accuracy metric for monitoring, which is **separate from validator scoring**:

- **Dashboard MAE** (Mean Absolute Error): compares the **mean predicted end price** against the actual end price from yfinance. Used purely as a local sanity check.
- **Validator CRPS**: evaluates the entire distribution of 1000 paths, not just the mean. This is what actually determines your TAO rewards.

The dashboard MAE is only computed for **BTC, ETH, SOL** because the oracle used by the subnet for XAU and tokenised equities (SPYX, NVDAX, etc.) does not match Yahoo Finance prices. Using yfinance prices to evaluate those assets would give misleadingly high error figures.

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
