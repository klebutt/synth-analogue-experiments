# Miner Health Check Guide — UID 255

This guide provides a systematic approach to verify your live miner (UID 255) is operating correctly on the Synth subnet (netuid 50).

> **Quick alternative**: The dashboard at http://167.71.143.194:9090 shows all key metrics in real time.

---

## Quick Status Check (30 seconds)

```bash
# 1. Check all PM2 processes
ssh root@167.71.143.194 "pm2 list"

# 2. Check blockchain metagraph status
ssh root@167.71.143.194 "python3.11 -c \"
import bittensor as bt
sub = bt.Subtensor('finney')
mg = sub.metagraph(50)
uid = 255
print(f'Active: {mg.active[uid]}, Incentive: {mg.I[uid]:.6f}, Emission: {mg.E[uid]:.6f}')
print(f'Axon serving: {mg.axons[uid].is_serving}')
\""

# 3. Check recent prediction requests
ssh root@167.71.143.194 "pm2 logs synth-miner --lines 20 --nostream | grep -E 'Received prediction|Error'"
```

**Understanding the status:**
- `pm2 list` should show `synth-miner` and `synth-dashboard` both as **online**
- `Active = True` means your miner is registered on-chain
- `Incentive > 0` means validators are weighting you (this takes time after re-registration)
- `Axon serving = True` means validators can reach you

---

## Comprehensive Health Check (5 minutes)

### Step 1: Process Status
```bash
ssh root@167.71.143.194 "pm2 list"
ssh root@167.71.143.194 "pm2 show synth-miner"
```

**Expected:**
- `synth-miner`: status `online`, low restart count
- `synth-dashboard`: status `online`
- Memory: ~700–900 MB for the miner (1000 simulations are CPU/memory intensive)
- CPU: high during predictions (~90–100%), low when idle

---

### Step 2: Blockchain Registration Status
```bash
ssh root@167.71.143.194 "python3.11 -c \"
import bittensor as bt
sub = bt.Subtensor('finney')
mg = sub.metagraph(50)
uid = 255
print(f'=== MINER STATUS (UID {uid}) ===')
print(f'Active:          {bool(mg.active[uid])}')
print(f'Stake (alpha):   {float(mg.S[uid]):.2f} ש')
print(f'Incentive:       {float(mg.I[uid]):.6f}')
print(f'Emission:        {float(mg.E[uid]):.6f}')
print(f'Validator trust: {float(mg.Tv[uid]):.6f}')
print(f'Consensus:       {float(mg.C[uid]):.6f}')
print(f'Axon serving:    {mg.axons[uid].is_serving}')
\""
```

> **Note**: `bt.Subtensor` (capital S) is required in bittensor 10.x. `bt.subtensor` will throw AttributeError.

**What to check:**
- ✅ `Active = True` — critical; if False, miner is deregistered
- ✅ `Axon serving = True` — if False, validators can't reach you
- ✅ `Stake > 0` — your alpha token stake in the subnet
- ⚠️ `Incentive = 0` — expected for first ~24–48h after re-registration while scoring windows complete

---

### Step 3: Recent Activity & Logs
```bash
# Count recent requests (last 24h)
ssh root@167.71.143.194 "grep -c 'Received prediction request' ~/.pm2/logs/synth-miner-out.log"

# View recent log entries
ssh root@167.71.143.194 "pm2 logs synth-miner --lines 30 --nostream"

# Check for errors
ssh root@167.71.143.194 "pm2 logs synth-miner --err --lines 30 --nostream"
```

**What to look for:**
- ✅ "Received prediction request" messages appearing regularly (~172/hour across all assets)
- ✅ No repeated Python exceptions
- ✅ Recent timestamps (activity within last few minutes)

---

### Step 4: Integration Verification
Verify your custom models are being used:

```bash
# Check bridge file imports your code
ssh root@167.71.143.194 "grep -n 'synth_integration' /root/synth-subnet/synth/miner/simulations.py"

# Verify synth_integration imports correctly
ssh root@167.71.143.194 "python3.11 -c \"
import sys
sys.path.insert(0, '/root/synth-analogue-experiments')
import synth_integration
print('✅ synth_integration loaded')
print(f'   Has generate_synth_simulations: {hasattr(synth_integration, \"generate_synth_simulations\")}')
\""
```

---

### Step 5: Quick Prediction Test
```bash
ssh root@167.71.143.194 "python3.11 /root/synth-analogue-experiments/scripts/diagnose_miner_issue.py"
```

---

### Step 6: Wallet Balance
```bash
ssh root@167.71.143.194 "python3.11 -c \"
import bittensor as bt
wallet = bt.wallet(name='wallet1', hotkey='default')
sub = bt.Subtensor('finney')
balance = sub.get_balance(wallet.coldkeypub.ss58_address)
print(f'Coldkey TAO balance: {balance}')
\""
```

As of March 2026: ~τ0.397 free TAO in coldkey.

---

## Red Flags (Immediate Action Required)

1. **`active = False`** → Miner deregistered; re-register via `btcli subnet register --netuid 50 --wallet.name wallet1 --wallet.hotkey default --subtensor.network finney` on the server
2. **`axon serving = False`** → Network/firewall issue; check the miner is running and port 8091 is open
3. **No prediction requests in 1+ hours** → Check `pm2 list` — miner may have crashed; `pm2 restart synth-miner`
4. **High restart count** → Miner is crash-looping; check error logs
5. **`synth_integration` import error** → Check git pull completed; check `simulations.py` bridge

---

## Healthy Miner Checklist

- [ ] `pm2 list` shows `synth-miner` and `synth-dashboard` both **online**
- [ ] `active = True` (on-chain registration valid)
- [ ] `axon serving = True`
- [ ] Prediction requests appearing in logs
- [ ] No repeated Python exceptions in error log
- [ ] `synth_integration` module loads correctly
- [ ] Dashboard at http://167.71.143.194:9090 accessible

---

## Quick Reference

| Property | Value |
|----------|-------|
| Server | 167.71.143.194 |
| Wallet | wallet1 / default |
| UID | **255** |
| Subnet | 50 (Synth), finney mainnet |
| PM2 miner process | `synth-miner` |
| PM2 dashboard process | `synth-dashboard` |
| Miner log | `~/.pm2/logs/synth-miner-out.log` |
| Prediction log | `/root/prediction_log.jsonl` |
| Dashboard | http://167.71.143.194:9090 |

---

## Related Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) — How the two-layer system works
- [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) — How to safely update the miner
- [SCORING_AND_METRICS.md](SCORING_AND_METRICS.md) — Understanding incentive and emission
- [dashboard/miner_monitoring_commands.md](../dashboard/miner_monitoring_commands.md) — Quick SSH command reference
