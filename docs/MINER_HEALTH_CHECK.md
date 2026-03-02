# Miner Health Check Guide - UID 233

This guide provides a systematic approach to verify your live miner (UID 233) is operating correctly on the Synth subnet (netuid 50).

## 🎯 Quick Status Check (30 seconds)

Run these commands to get an immediate overview:

```bash
# 1. Check ALL PM2 processes (important - miner might have different name)
ssh root@167.71.143.194 "pm2 list"

# 2. Check blockchain active status (this is what the tracker shows)
ssh root@167.71.143.194 "python3 -c \"import bittensor as bt; sub=bt.subtensor('finney'); mg=sub.metagraph(50); print(f'Active: {mg.active[233]}, Trust: {mg.trust[233]:.4f}, Axon: {mg.axons[233].is_serving}')\""

# 3. Check if any Python miner process is running
ssh root@167.71.143.194 "ps aux | grep -E 'miner.py|neurons/miner' | grep -v grep"

# 4. Check recent activity (if earning rewards, you're running)
ssh root@167.71.143.194 "pm2 logs miner --lines 50 --nostream 2>/dev/null | grep -E 'Received prediction|Error|score' | tail -10"
```

**Understanding the status:**
- **Blockchain "Active" status** = Miner is registered (what tracker shows)
- **PM2 "stopped"** = Process might not be running (or might have different name)
- **Reward weights** = If you're earning rewards (even low), the miner WAS running
- **Low reward weights** = Poor model performance (bad CRPS scores), not necessarily that it's stopped

**What to look for:**
- ✅ PM2 shows miner as "online" OR Python process is running
- ✅ Active status = 1 (blockchain registration)
- ✅ Axon serving = True (process is actually running)
- ✅ Recent "Received prediction request" in logs (getting validator queries)
- ⚠️ Low reward weights = Model quality issue, not deployment issue

---

## 📊 Comprehensive Health Check (5 minutes)

### Step 1: Process Status
Verify the miner process is running correctly:

```bash
# First, check ALL PM2 processes (miner might be named differently)
ssh root@167.71.143.194 "pm2 list"

# Check if miner is running as a Python process directly (outside PM2)
ssh root@167.71.143.194 "ps aux | grep -E 'miner.py|custom_synth_miner|neurons/miner' | grep -v grep"

# Then check the specific miner process in PM2 (try both common names)
ssh root@167.71.143.194 "pm2 describe miner 2>/dev/null || pm2 describe synth-miner 2>/dev/null || echo 'No miner process found in PM2'"
```

**Expected output:**
- Either PM2 shows a process with status `online` OR a Python process is running directly
- If PM2 shows "stopped" but a Python process exists, the miner is running outside PM2
- Restart count: Should be low (high restart count = crashing repeatedly)

**Understanding Your Setup:**
Based on your output, you have:
- **PM2 "miner"**: Stopped (51 restarts = kept crashing)
- **Direct Python process**: Running `custom_synth_miner.py` (this is what's actually working!)

**If PM2 shows "stopped" but a direct process is running:**
Your miner IS working, just not managed by PM2. This is fine, but:
- ✅ Miner is operational
- ⚠️ No PM2 auto-restart if it crashes
- ⚠️ Harder to monitor via PM2 logs

**To fix PM2 (optional):**
```bash
# Check why PM2 kept crashing
ssh root@167.71.143.194 "pm2 logs miner --err --lines 100 --nostream | grep -E 'Error|Exception|ImportError' | head -20"

# If you want to use PM2, stop the direct process first, then fix PM2
ssh root@167.71.143.194 "kill \$(ps aux | grep custom_synth_miner | grep -v grep | awk '{print \$2}')"
ssh root@167.71.143.194 "cd /root/synth-subnet && pm2 restart miner"
```

---

### Step 2: Blockchain Registration Status
Check if you're registered and active on-chain:

**Bash (Linux/macOS):**
```bash
ssh root@167.71.143.194 "python3 -c \"
import bittensor as bt
sub = bt.subtensor(network='finney')
mg = sub.metagraph(netuid=50)
uid = 233
print(f'=== MINER STATUS (UID {uid}) ===')
print(f'Active: {mg.active[uid]} (1=active, 0=inactive)')
print(f'Stake: {mg.S[uid]:.2f} τ')
print(f'Trust: {mg.trust[uid]:.4f}')
print(f'Incentive: {mg.incentive[uid]:.4f}')
print(f'Emission: {mg.emission[uid]:.6f}')
print(f'Axon serving: {mg.axons[uid].is_serving}')
print(f'Hotkey: {mg.hotkeys[uid][:16]}...')
if mg.active[uid] == 0:
    print('❌ MINER IS INACTIVE - Check registration!')
else:
    print('✅ MINER IS ACTIVE')
\""
```

**PowerShell (Windows):** Use a one-liner so PowerShell doesn't parse Python's `if`:
```powershell
ssh root@167.71.143.194 "python3 -c `"import bittensor as bt; sub=bt.subtensor('finney'); mg=sub.metagraph(50); uid=233; print('=== MINER STATUS (UID', uid, ') ==='); print('Active:', mg.active[uid], '(1=active, 0=inactive)'); print('Stake:', mg.S[uid], 'tau'); print('Trust:', mg.trust[uid]); print('Incentive:', mg.incentive[uid]); print('Emission:', mg.emission[uid]); print('Axon serving:', mg.axons[uid].is_serving); print('INACTIVE - Check registration!' if mg.active[uid]==0 else 'ACTIVE')`"
```

**What to check:**
- ✅ `Active = 1` (critical - if 0, miner is deregistered)
- ✅ `Axon serving = True` (if False, validators can't reach you)
- ✅ `Stake > 0` (you need stake to participate)
- ✅ `Trust > 0` (indicates validators are rating you)

---

### Step 3: Recent Activity & Logs
Check if you're receiving validator requests:

```bash
# Count recent requests
ssh root@167.71.143.194 "pm2 logs miner --lines 100 | grep -c 'Received prediction request'"

# View recent log entries
ssh root@167.71.143.194 "pm2 logs miner --lines 50 | tail -30"
```

**What to look for:**
- ✅ "Received prediction request" messages (shows validators are querying you)
- ✅ No repeated errors or exceptions
- ✅ Recent timestamps (activity within last hour)

**Common log patterns:**
- `Received prediction request for asset: BTC` - ✅ Good, receiving work
- `Error generating simulations` - ❌ Problem with your model code
- `Timeout` - ❌ Taking too long to respond
- `Not registered` - ❌ Registration issue

---

### Step 4: System Resources
Check if the server has adequate resources:

```bash
ssh root@167.71.143.194 "pm2 show miner"
```

**Check:**
- CPU usage: Should be reasonable (< 100% sustained)
- Memory: Should not be maxed out
- Restart count: Should be stable (not constantly restarting)

---

### Step 5: Integration Verification
Verify your custom models are being used correctly:

```bash
# Check that synth_integration is being called
ssh root@167.71.143.194 "grep -n 'synth_integration' /root/synth-subnet/synth/miner/simulations.py"

# Verify the integration path exists
ssh root@167.71.143.194 "python3 -c \"
import sys
sys.path.insert(0, '/root/synth-analogue-experiments')
try:
    import synth_integration
    print('✅ synth_integration module found')
    print(f'   Location: {synth_integration.__file__}')
    print(f'   Has generate_synth_simulations: {hasattr(synth_integration, \"generate_synth_simulations\")}')
except Exception as e:
    print(f'❌ Error importing synth_integration: {e}')
\""
```

**Expected:**
- ✅ `synth_integration` import found in simulations.py
- ✅ Module can be imported successfully
- ✅ `generate_synth_simulations` function exists

---

### Step 6: Stake & Wallet Status
Verify your stake and wallet balance:

```bash
# Check stake on subnet 50
ssh root@167.71.143.194 "btcli stake list --wallet.name wallet1 --wallet.hotkey default | grep 50"

# Check wallet balance
ssh root@167.71.143.194 "btcli wallet overview --wallet.name wallet1 --wallet.hotkey default"
```

**What to check:**
- ✅ You have stake on subnet 50 (required to participate)
- ✅ Wallet has some balance (for transaction fees)

---

## 🔍 Detailed Diagnostics (if issues found)

### If Miner is Inactive (Active = 0)

1. **Check registration:**
```bash
ssh root@167.71.143.194 "btcli subnet list --netuid 50 --wallet.name wallet1 --wallet.hotkey default"
```

2. **Check wallet files:**
```bash
ssh root@167.71.143.194 "ls -la ~/.bittensor/wallets/wallet1/hotkeys/default"
```

3. **Re-register if needed:**
```bash
ssh root@167.71.143.194 "cd /root/synth-subnet && btcli subnet register --netuid 50 --wallet.name wallet1 --wallet.hotkey default"
```

---

### If Not Receiving Requests

1. **Check if validators are active:**
```bash
ssh root@167.71.143.194 "python3 -c \"
import bittensor as bt
sub = bt.subtensor('finney')
mg = sub.metagraph(50)
active_validators = sum(mg.validator_permit)
print(f'Active validators: {active_validators}')
\""
```

2. **Check your trust score:**
- Low trust = validators may skip you
- Check recent emissions to see if you're earning rewards

3. **Verify axon is serving:**
- If `is_serving = False`, validators can't reach you
- Check firewall/network settings

---

### If Getting Errors in Logs

1. **View error logs:**
```bash
ssh root@167.71.143.194 "pm2 logs miner --err --lines 100"
```

2. **Test model generation:**
```bash
ssh root@167.71.143.194 "cd /root/synth-analogue-experiments && python3 scripts/diagnose_miner_issue.py"
```

3. **Check dependencies:**
```bash
ssh root@167.71.143.194 "cd /root/synth-analogue-experiments && python3 -m pip list | grep -E 'bittensor|synth|numpy|pandas'"
```

---

## 📈 Monitoring Dashboard

For continuous monitoring, use the web dashboard:

1. **Start dashboard (local):**
```bash
cd dashboard
python3 -m pip install -r dashboard_requirements.txt
python3 simple_miner_api.py
```

2. **Access:** http://localhost:5000
   - Auto-refreshes every 30 seconds
   - Shows real-time status, stake, requests, etc.

---

## 🚨 Red Flags (Immediate Action Required)

Watch for these warning signs:

1. **Active = 0** → Miner deregistered, re-register immediately
2. **Axon serving = False** → Network/firewall issue, check connectivity
3. **No requests in 24+ hours** → Check trust score, validator activity
4. **Constant restarts** → Check logs for errors, resource issues
5. **Repeated errors in logs** → Model code issue, test locally first

---

## ✅ Healthy Miner Checklist

Your miner is healthy if:

- [ ] PM2 shows status: `online`
- [ ] Active status: `1`
- [ ] Axon serving: `True`
- [ ] Receiving validator requests (check logs)
- [ ] Trust score > 0
- [ ] No errors in recent logs
- [ ] Stable uptime (not constantly restarting)
- [ ] Stake > 0 on subnet 50
- [ ] `synth_integration` module loads correctly

---

## 📝 Quick Reference

**Server:** 167.71.143.194  
**Wallet:** wallet1  
**Hotkey:** default  
**UID:** 233  
**Subnet:** 50 (Synth)  
**Network:** finney (mainnet)

**Key Directories:**
- Miner code: `/root/synth-subnet`
- Custom models: `/root/synth-analogue-experiments`
- PM2 logs: `~/.pm2/logs/miner-out.log`, `~/.pm2/logs/miner-error.log`

---

## 🔗 Related Documentation

- [Deployment Guide](DEPLOYMENT_GUIDE.md) - How your miner is set up
- [Miner Monitoring Commands](../dashboard/miner_monitoring_commands.md) - All available commands
- [Troubleshooting Guide](TROUBLESHOOTING_MINUS_ONE_SCORE.md) - Common issues and fixes

