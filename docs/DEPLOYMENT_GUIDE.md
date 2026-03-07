# Synth Miner Deployment Guide

This guide documents exactly how the miner works in production, how to verify it, and how to safely update models.

---

## High-Level Architecture

| Component | Path on Server | Notes |
|-----------|---------------|-------|
| PM2 miner process | `/root/synth-subnet/neurons/miner.py` | Official Bittensor entry point |
| PM2 dashboard process | `/root/synth-analogue-experiments/dashboard/app.py` | Flask, port 9090 |
| Bridge (modified) | `/root/synth-subnet/synth/miner/simulations.py` | Delegates to `synth_integration` |
| Custom ensemble model | `/root/synth-analogue-experiments/synth_integration.py` | Your prediction logic |
| Volatility calibration | `/root/synth-analogue-experiments/models/baseline/volatility_calculator.py` | yfinance-based |
| Live price source | `synth-subnet/synth/miner/price_simulation.py` | Pyth/Hermes API |
| Prediction log | `/root/prediction_log.jsonl` | JSONL, one line per prediction batch |

The bridge file (`simulations.py`) was modified once to add:
```python
sys.path.insert(0, '/root/synth-analogue-experiments')
from synth_integration import generate_synth_simulations
```
This is the only modification made to `synth-subnet/`. Everything else is in `synth-analogue-experiments/`.

---

## PM2 Process Config

Located at: `/root/synth-analogue-experiments/miner.official.config.js`

The config defines two PM2 apps:
- **`synth-miner`** — runs the miner via `neurons/miner.py`
- **`synth-dashboard`** — runs `dashboard/app.py` on port 9090

To view running processes:
```bash
pm2 list
pm2 show synth-miner
pm2 show synth-dashboard
```

---

## Verifying the Live Setup

Run these checks on the server to confirm everything is wired correctly:

```bash
# 1. Confirm miner process is running
pm2 describe synth-miner

# 2. Confirm Python resolves synth from the subnet repo
python3.11 -c "import os, synth; print(os.path.dirname(synth.__file__))"
# Expected: /root/synth-subnet/synth

# 3. Confirm bridge delegates to your integration
python3.11 -c "import inspect, synth.miner.simulations as s; print(inspect.getsource(s.generate_simulations))"
# Expected: should see a call to generate_synth_simulations(...)

# 4. Confirm bridge file imports synth_integration
grep -n "synth_integration" /root/synth-subnet/synth/miner/simulations.py

# 5. Confirm your custom code loads
python3.11 -c "
import sys; sys.path.insert(0, '/root/synth-analogue-experiments')
import synth_integration
print('OK:', hasattr(synth_integration, 'generate_synth_simulations'))
"
```

---

## Safe Update Workflow

Use this workflow every time you change model code.

### 1. Test locally (optional but recommended)
```bash
python -c "import synth_integration; print('ok')"
```

### 2. Commit and push
```bash
git add .
git commit -m "describe your change"
git push origin clean
```

### 3. Pull on the server
```bash
ssh root@167.71.143.194
cd /root/synth-analogue-experiments
git pull origin clean
```

### 4. Restart the miner
```bash
pm2 restart synth-miner
pm2 save   # persist the process list across reboots
```

### 5. Verify startup
```bash
pm2 logs synth-miner --lines 50 --nostream
```

Look for clean startup with no ImportErrors or exceptions.

---

## Installing New Dependencies

If you add a new package to `requirements.txt`:
```bash
ssh root@167.71.143.194
cd /root/synth-analogue-experiments
pip install -r requirements.txt
pm2 restart synth-miner
```

---

## Rollback

If a change breaks the miner:
```bash
ssh root@167.71.143.194
cd /root/synth-analogue-experiments
git log --oneline -10          # find the last good commit hash
git reset --hard <COMMIT_HASH>
pm2 restart synth-miner
pm2 logs synth-miner --lines 30
```

---

## On-Chain Status

```bash
python3.11 -c "
import bittensor as bt
sub = bt.Subtensor('finney')
mg = sub.metagraph(50)
uid = 255
print(f'Active:    {bool(mg.active[uid])}')
print(f'Incentive: {float(mg.I[uid]):.6f}')
print(f'Emission:  {float(mg.E[uid]):.6f}')
print(f'Axon:      {mg.axons[uid].is_serving}')
"
```

> **Bittensor 10.x note**: Use `bt.Subtensor` (capital S). Attributes on Metagraph: `mg.I` (incentive), `mg.E` (emission), `mg.C` (consensus), `mg.D` (dividends), `mg.Tv` (validator trust), `mg.S` (stake), `mg.pruning_score`.

---

## Logs and Troubleshooting

| Log | Path |
|-----|------|
| Miner stdout | `~/.pm2/logs/synth-miner-out.log` |
| Miner stderr | `~/.pm2/logs/synth-miner-error.log` |
| Dashboard stdout | `~/.pm2/logs/synth-dashboard-out.log` |
| Prediction log | `/root/prediction_log.jsonl` |

Common issues:
- **`AttributeError: module 'bittensor' has no attribute 'subtensor'`** → Use `bt.Subtensor` (capital S)
- **`ModuleNotFoundError: No module named 'synth_integration'`** → Check bridge file has `sys.path.insert(0, '/root/synth-analogue-experiments')`
- **High memory/CPU** → Normal during active predictions; 1000 simulations × 9 assets is compute-intensive
- **Prediction log stops growing** → Miner may have crashed; `pm2 list` and restart if needed

---

## Server Quick Reference

| Property | Value |
|----------|-------|
| Provider | DigitalOcean |
| IP | 167.71.143.194 |
| OS | Ubuntu 22.04 LTS |
| Python | 3.11 |
| Bittensor | 10.0.1 |
| Wallet | wallet1 / default |
| UID | **255** |
| Subnet | 50 (Synth), finney mainnet |
| Axon port | 8091 |
| Dashboard | http://167.71.143.194:9090 |
