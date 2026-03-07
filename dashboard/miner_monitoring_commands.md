# Miner Monitoring Commands

Essential SSH commands for checking your Synth subnet miner (UID 255, Subnet 50).

> **Tip**: The dashboard at http://167.71.143.194:9090 shows most of this in a UI. Use these commands when you need raw access or the dashboard is unavailable.

---

## Process Status

```bash
# See all PM2 processes (should show synth-miner and synth-dashboard both online)
ssh root@167.71.143.194 "pm2 list"

# Detailed info for the miner
ssh root@167.71.143.194 "pm2 show synth-miner"

# Restart the miner
ssh root@167.71.143.194 "pm2 restart synth-miner"

# Restart the dashboard
ssh root@167.71.143.194 "pm2 restart synth-dashboard"
```

---

## Logs

```bash
# Last 50 lines of miner output
ssh root@167.71.143.194 "pm2 logs synth-miner --lines 50 --nostream"

# Last 50 lines of miner errors
ssh root@167.71.143.194 "pm2 logs synth-miner --err --lines 50 --nostream"

# Follow live logs (Ctrl+C to stop)
ssh root@167.71.143.194 "pm2 logs synth-miner --follow"

# Count prediction requests in the last hour
ssh root@167.71.143.194 "grep 'Received prediction request' ~/.pm2/logs/synth-miner-out.log | tail -200 | wc -l"
```

---

## On-Chain Status

```bash
# Quick metagraph check for UID 255
ssh root@167.71.143.194 "python3.11 -c \"
import bittensor as bt
sub = bt.Subtensor('finney')
mg = sub.metagraph(50)
uid = 255
print(f'Active:    {bool(mg.active[uid])}')
print(f'Incentive: {float(mg.I[uid]):.6f}')
print(f'Emission:  {float(mg.E[uid]):.6f}')
print(f'Stake:     {float(mg.S[uid]):.2f} alpha')
print(f'Axon:      {mg.axons[uid].is_serving}')
\""

# Check coldkey TAO balance
ssh root@167.71.143.194 "python3.11 -c \"
import bittensor as bt
w = bt.wallet(name='wallet1', hotkey='default')
sub = bt.Subtensor('finney')
print('TAO balance:', sub.get_balance(w.coldkeypub.ss58_address))
\""
```

> **API note**: bittensor 10.x uses `bt.Subtensor` (capital S). `mg.trust` and `mg.R` do not exist in 10.x — use `mg.Tv` (validator trust) and `mg.I`, `mg.E`, `mg.C`, `mg.D`, `mg.S` instead.

---

## Integration Verification

```bash
# Confirm the bridge delegates to your model
ssh root@167.71.143.194 "grep -n 'synth_integration' /root/synth-subnet/synth/miner/simulations.py"

# Confirm synth_integration loads
ssh root@167.71.143.194 "python3.11 -c \"
import sys; sys.path.insert(0, '/root/synth-analogue-experiments')
import synth_integration
print('OK — generate_synth_simulations:', hasattr(synth_integration, 'generate_synth_simulations'))
\""

# Run the full diagnostic script
ssh root@167.71.143.194 "python3.11 /root/synth-analogue-experiments/scripts/diagnose_miner_issue.py"
```

---

## Re-registration (if active = False)

```bash
# On the server — run from synth-subnet directory
ssh root@167.71.143.194
cd /root/synth-subnet
btcli subnet register --netuid 50 --wallet.name wallet1 --wallet.hotkey default --subtensor.network finney
```

> Note: Registration costs ~0.8–1.5 TAO depending on subnet demand. The cost fluctuates by interval — if it says "subnet full for this interval, try again in N blocks", wait ~30 minutes (each block ~12s).

---

## Deploy a Code Update

```bash
# 1. On local machine — push changes
git push origin clean

# 2. On server — pull and restart
ssh root@167.71.143.194
cd /root/synth-analogue-experiments
git pull origin clean
pm2 restart synth-miner
pm2 logs synth-miner   # verify clean startup
```

---

## Quick Reference

| Property | Value |
|----------|-------|
| Server | 167.71.143.194 |
| Wallet | wallet1 / default |
| UID | **255** |
| Subnet | 50 (finney mainnet) |
| PM2 miner | `synth-miner` |
| PM2 dashboard | `synth-dashboard` |
| Dashboard URL | http://167.71.143.194:9090 |
| Prediction log | `/root/prediction_log.jsonl` |
| Miner log | `~/.pm2/logs/synth-miner-out.log` |
