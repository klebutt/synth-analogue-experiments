# synth-analogue-experiments

A custom miner for [Bittensor Subnet 50 (Synth)](https://github.com/synth-subnet), deployed on DigitalOcean and earning TAO rewards by generating probabilistic price forecasts for crypto and tokenised equity assets.

---

## What This Is

The Synth subnet asks miners to predict price distributions (1000 simulated paths) for assets including BTC, ETH, SOL, XAU, and five tokenised equities (SPYX, NVDAX, TSLAX, AAPLX, GOOGLX). Validators score submissions using CRPS — the closer your distribution is to the actual price, the higher your reward.

This repo contains:
- A custom **Ensemble GBM-Weighted** prediction model
- A **monitoring dashboard** served directly from the miner server
- All supporting infrastructure (PM2 config, volatility calibration, etc.)

---

## Current Status

| Property | Value |
|----------|-------|
| Server | DigitalOcean — `167.71.143.194` |
| UID | **255** on Subnet 50 |
| Wallet | `wallet1 / default` |
| Dashboard | http://167.71.143.194:9090 |
| Git branch | `clean` |
| Bittensor version | 10.0.1 |

---

## Repo Structure

```
synth-analogue-experiments/
│
├── AGENTS.md                     ← START HERE if you are an AI agent
├── synth_integration.py          ← Custom ensemble model (core prediction logic)
├── miner.official.config.js      ← PM2 process manifest (miner + dashboard)
├── requirements.txt              ← Runtime dependencies
│
├── models/
│   └── baseline/
│       ├── geometric_brownian.py ← GBM model (50% weight)
│       ├── mean_reversion.py     ← Mean reversion model (30% weight)
│       ├── random_walk.py        ← Random walk model (20% weight)
│       └── volatility_calculator.py ← Fetches σ and drift from yfinance
│
├── dashboard/
│   ├── app.py                    ← Flask server (runs ON the miner server, port 9090)
│   └── templates/index.html     ← Dashboard UI
│
├── scripts/
│   └── diagnose_miner_issue.py  ← Diagnostic script for debugging prediction issues
│
├── tests/
│   ├── test_baseline_models.py  ← Tests for custom models
│   ├── test_crps.py             ← Tests for CRPS scoring util
│   └── test_simulations.py     ← Integration test for the bridge
│
├── docs/
│   ├── ARCHITECTURE.md          ← System diagrams + request flow
│   ├── DEPLOYMENT_GUIDE.md      ← Safe update workflow
│   ├── MINER_HEALTH_CHECK.md    ← Step-by-step health verification
│   ├── MODEL.md                 ← How the prediction model works
│   ├── DASHBOARD.md             ← Dashboard architecture and API reference
│   └── SCORING_AND_METRICS.md  ← How scoring works, known oracle issues
│
└── synth-subnet/                ← Git submodule — official subnet code (do not modify
                                    except synth/miner/simulations.py)
```

---

## Quick Start

### View the Dashboard
```
http://167.71.143.194:9090
```
Auto-refreshes every 60 seconds. Shows PM2 status, on-chain metrics, predictions, and per-asset price charts.

### Check Miner Health (SSH)
```bash
ssh root@167.71.143.194 "pm2 list"
```

### Deploy a Code Change
```bash
# 1. Edit files locally, then:
git add . && git commit -m "your message"
git push origin clean

# 2. On the server:
ssh root@167.71.143.194
cd /root/synth-analogue-experiments && git pull origin clean
pm2 restart synth-miner
pm2 logs synth-miner   # verify clean startup
```

---

## Key Docs

- **[AGENTS.md](AGENTS.md)** — Full context for AI agents working in this repo
- **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)** — How the two-layer system works
- **[docs/MODEL.md](docs/MODEL.md)** — The prediction model in detail
- **[docs/DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** — Safe update procedure
- **[docs/DASHBOARD.md](docs/DASHBOARD.md)** — Dashboard API and scoring
- **[docs/SCORING_AND_METRICS.md](docs/SCORING_AND_METRICS.md)** — Scoring mechanics and known issues
