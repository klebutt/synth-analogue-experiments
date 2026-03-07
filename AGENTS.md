# AGENTS.md — AI Agent Context

**Read this file first** before making any changes to this repo.

This document gives you everything you need to work effectively in this codebase without causing damage to the live production miner.

---

## What This Repo Is

A **Bittensor Subnet 50 (Synth) miner** running on DigitalOcean. It generates probabilistic price forecasts for 9 assets and earns TAO rewards from validators.

The repo contains:
1. A custom **ensemble prediction model** (`synth_integration.py` + `models/baseline/`)
2. A **Flask monitoring dashboard** (`dashboard/app.py`) served on port 9090
3. A **PM2 process config** (`miner.official.config.js`) that manages both on the server

---

## Critical Facts You Must Know

### 1. UID is 255, NOT 233
Previous versions of docs and some log files referenced UID 233. **The current UID is 255.** Always use 255 when querying the metagraph.

### 2. Bittensor 10.x API differences
The server runs bittensor **10.0.1**. The API is different from 9.x:
```python
# CORRECT
sub = bt.Subtensor('finney')        # capital S
mg = sub.metagraph(50)
mg.I[uid]   # incentive
mg.E[uid]   # emission
mg.C[uid]   # consensus
mg.D[uid]   # dividends
mg.Tv[uid]  # validator trust
mg.S[uid]   # stake (alpha tokens, NOT TAO)
mg.pruning_score[uid]

# WRONG (will throw AttributeError)
sub = bt.subtensor('finney')        # lowercase s
mg.R[uid]   # no such attribute
mg.T[uid]   # no such attribute (use mg.Tv)
mg.trust[uid]  # may exist but is miner trust, not validator trust
```

### 3. Stake shown in dashboard is Alpha, not TAO
`mg.S[uid]` returns the alpha token stake in the subnet (~94.64 ש as of Mar 2026). This is not raw TAO. The dashboard labels it "Alpha Stake (ש)" for clarity.

### 4. There are two separate repos on the server
- `/root/synth-subnet/` — the official Synth subnet code (managed by the subnet team). **Do not modify any file here except `synth/miner/simulations.py`**, which was modified once to delegate to our model.
- `/root/synth-analogue-experiments/` — this repo (our custom model + dashboard).

### 5. The bridge file (`simulations.py`) must not be overwritten by `git pull`
The file `/root/synth-subnet/synth/miner/simulations.py` was manually patched on the server to add:
```python
sys.path.insert(0, '/root/synth-analogue-experiments')
from synth_integration import generate_synth_simulations
```
If you ever run `git pull` inside `/root/synth-subnet`, check that this patch survived.

### 6. The prediction log is the source of truth for the dashboard
The miner appends every batch of predictions to `/root/prediction_log.jsonl` on the server. The dashboard reads this file directly. The format is one JSON object per line.

### 7. Oracle mismatch for XAU and equity assets
The subnet uses an internal oracle for XAU, SPYX, NVDAX, TSLAX, AAPLX, GOOGLX pricing that does not match Yahoo Finance. **Dashboard MAE scoring is only reliable for BTC, ETH, SOL.** The `SCORING_ASSETS` constant in `dashboard/app.py` restricts scoring to these three.

### 8. yfinance is rate-limited
`dashboard/app.py` uses batched yfinance downloads (one download per asset per scoring window) to avoid hitting rate limits. Do not add sequential per-record yfinance calls — this was the original bug that caused 8000%+ MAE values.

---

## Repo Structure

```
synth-analogue-experiments/
│
├── AGENTS.md                        ← You are here
├── README.md                        ← Project overview
├── synth_integration.py             ← MAIN MODEL — ensemble prediction logic
├── miner.official.config.js         ← PM2 config (both processes)
├── requirements.txt                 ← Runtime dependencies
│
├── models/baseline/
│   ├── geometric_brownian.py        ← GBM (50% weight)
│   ├── mean_reversion.py            ← Mean reversion (30% weight)
│   ├── random_walk.py               ← Random walk (20% weight)
│   └── volatility_calculator.py     ← Fetches σ and drift from yfinance
│
├── dashboard/
│   ├── app.py                       ← Flask server, all API endpoints
│   ├── templates/index.html         ← Frontend UI (Chart.js, vanilla JS)
│   └── miner_monitoring_commands.md ← SSH command reference
│
├── scripts/
│   └── diagnose_miner_issue.py     ← Runs a quick prediction test
│
├── tests/
│   ├── test_baseline_models.py     ← Unit tests for models
│   ├── test_crps.py                ← CRPS scoring tests
│   └── test_simulations.py         ← Integration test for the bridge
│
└── docs/
    ├── ARCHITECTURE.md             ← System diagrams and flow
    ├── DEPLOYMENT_GUIDE.md         ← Safe update workflow
    ├── MINER_HEALTH_CHECK.md       ← Health verification commands
    ├── MODEL.md                    ← Prediction model detail
    ├── DASHBOARD.md                ← Dashboard API reference
    └── SCORING_AND_METRICS.md      ← How validators score miners
```

---

## Where NOT to Make Changes

| File / Directory | Reason |
|-----------------|--------|
| `/root/synth-subnet/**` (except `simulations.py`) | Official subnet code — changes will be overwritten by `git pull` |
| `synth_integration.py` — `generate_synth_simulations` signature | Validators call this via the bridge; changing the signature breaks the miner |
| `dashboard/app.py` — `MINER_UID = 255` | Hardcoded; must stay in sync with actual UID |

---

## How to Deploy Changes Safely

```bash
# 1. Local: edit, test import
python -c "import synth_integration; print('ok')"

# 2. Push
git add . && git commit -m "your description"
git push origin clean

# 3. Server: pull and restart
ssh root@167.71.143.194
cd /root/synth-analogue-experiments && git pull origin clean
pm2 restart synth-miner
pm2 logs synth-miner   # verify no errors
```

Always verify with `pm2 logs` after restarting — an ImportError or syntax error will crash the miner immediately.

---

## Key Constants in the Codebase

| Constant | File | Value | Meaning |
|----------|------|-------|---------|
| `MINER_UID` | `dashboard/app.py` | `255` | Our UID on subnet 50 |
| `NETUID` | `dashboard/app.py` | `50` | Synth subnet ID |
| `SCORING_ASSETS` | `dashboard/app.py` | `{"BTC", "ETH", "SOL"}` | Assets with reliable oracle data for MAE |
| `MAX_RECORDS` | `dashboard/app.py` | `200` | Records loaded for the predictions table |
| `MAX_RECORDS_STATS` | `dashboard/app.py` | `2000` | Records loaded for statistics computation |
| `CHART_CACHE_TTL` | `dashboard/app.py` | `300s` | Cache TTL for /api/charts |
| `CHAIN_CACHE_TTL` | `dashboard/app.py` | `600s` | Cache TTL for /api/chain |
| `STATS_CACHE_TTL` | `dashboard/app.py` | `300s` | Cache TTL for /api/predictions stats |
| `FALLBACK_SIGMA` | `synth_integration.py` | dict | Per-asset fallback volatility if yfinance fails |
| Simulation count | `synth_integration.py` | `1000` | Number of price paths per prediction |
| Model weights | `synth_integration.py` | GBM=0.5, MR=0.3, RW=0.2 | Ensemble blending weights |

---

## Supported Assets

| Asset | Type | yfinance ticker | Oracle reliable? |
|-------|------|----------------|-----------------|
| BTC | Crypto | `BTC-USD` | ✅ Yes |
| ETH | Crypto | `ETH-USD` | ✅ Yes |
| SOL | Crypto | `SOL-USD` | ✅ Yes |
| XAU | Gold | `GC=F` | ⚠️ Oracle mismatch |
| SPYX | Tokenised equity | `SPY` | ⚠️ Oracle mismatch |
| NVDAX | Tokenised equity | `NVDA` | ⚠️ Oracle mismatch |
| TSLAX | Tokenised equity | `TSLA` | ⚠️ Oracle mismatch |
| AAPLX | Tokenised equity | `AAPL` | ⚠️ Oracle mismatch |
| GOOGLX | Tokenised equity | `GOOGL` | ⚠️ Oracle mismatch |

---

## Further Reading

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Full system diagrams
- [docs/MODEL.md](docs/MODEL.md) — How the ensemble model works
- [docs/DASHBOARD.md](docs/DASHBOARD.md) — Dashboard API endpoints
- [docs/SCORING_AND_METRICS.md](docs/SCORING_AND_METRICS.md) — How validators score and reward miners
- [docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md) — Safe update workflow
- [docs/MINER_HEALTH_CHECK.md](docs/MINER_HEALTH_CHECK.md) — Step-by-step health checks
