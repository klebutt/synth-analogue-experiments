# Miner Monitoring Commands

Essential terminal commands for checking on your Synth subnet miner.

## 🔍 Essential Miner Monitoring Commands

### 1. Check Miner Status
```bash
ssh root@167.71.143.194 "pm2 status"
```
- Shows if your miner is running, stopped, or errored
- Displays uptime, memory usage, and restart count

### 2. View Miner Logs
```bash
ssh root@167.71.143.194 "pm2 logs miner --lines 50"
```
- Shows recent miner activity
- Look for "Received prediction request" to see validator requests
- Check for errors or warnings

### 3. Check Stake & Balance
```bash
ssh root@167.71.143.194 "btcli stake list --wallet.name wallet1 --wallet.hotkey default"
```
- Shows your current stake amount
- Displays stake across different subnets

### 4. Check Wallet Balance
```bash
ssh root@167.71.143.194 "btcli wallet overview --wallet.name wallet1 --wallet.hotkey default"
```
- Shows available TAO balance
- Displays staked vs free balance

### 5. Check Network Status
```bash
ssh root@167.71.143.194 "btcli subnet metagraph --netuid 50 --no_prompt"
```
- Shows all miners in the subnet
- Displays your UID (233) and position
- Shows trust scores and emissions

### 5.1. Check Active Status (Quick)
```bash
ssh root@167.71.143.194 "python3 -c \"
import bittensor as bt
sub = bt.subtensor(network='finney')
mg = sub.metagraph(netuid=50)
uid = 233
print(f'UID {uid}: Active={mg.active[uid]}, Stake={mg.S[uid]:.2f}, Trust={mg.trust[uid]:.4f}')
print(f'Axon serving: {mg.axons[uid].is_serving}')
if mg.active[uid] == 0:
    print('❌ MINER IS INACTIVE')
else:
    print('✅ MINER IS ACTIVE')
\""
```
- Quick check of active status, stake, trust, and axon serving
- Shows if miner is active or inactive

### 6. Check Validator Requests
```bash
ssh root@167.71.143.194 "pm2 logs miner --lines 100 | grep -c 'Received prediction'"
```
- Counts total validator requests received
- Shows if you're getting work from validators

### 7. Check System Resources
```bash
ssh root@167.71.143.194 "pm2 show miner"
```
- Shows detailed process information
- Displays CPU and memory usage
- Shows restart count and uptime

### 8. Restart Miner (if needed)
```bash
ssh root@167.71.143.194 "pm2 restart miner"
```
- Restarts the miner if it's stuck or errored
- Use if you see issues in the logs

### 9. Check Recent Activity
```bash
ssh root@167.71.143.194 "pm2 logs miner --lines 20 | tail -20"
```
- Shows the last 20 log entries
- Quick check for recent activity

### 10. Monitor Live Logs
```bash
ssh root@167.71.143.194 "pm2 logs miner --follow"
```
- Shows live, real-time logs
- Press Ctrl+C to stop monitoring

## 🚀 Quick Health Check

Run these 4 commands for a quick status check:
```bash
ssh root@167.71.143.194 "pm2 status | grep miner"
ssh root@167.71.143.194 "btcli stake list --wallet.name wallet1 --wallet.hotkey default | grep 50"
ssh root@167.71.143.194 "pm2 logs miner --lines 10 | grep -E 'Received prediction|Error|Warning'"
ssh root@167.71.143.194 "python3 -c \"import bittensor as bt; sub=bt.subtensor('finney'); mg=sub.metagraph(50); print(f'Active: {mg.active[233]}, Trust: {mg.trust[233]:.4f}, Axon: {mg.axons[233].is_serving}')\""
```

These commands will tell you if your miner is running, how much stake you have, if you're receiving validator requests, and your active status!

## 🎯 Check Active Status

### Simple Active Check
```bash
ssh root@167.71.143.194 "python3 -c \"import bittensor as bt; sub=bt.subtensor('finney'); mg=sub.metagraph(50); print(f'Active: {mg.active[233]}, Trust: {mg.trust[233]:.4f}, Axon: {mg.axons[233].is_serving}')\""
```

### Detailed Status Check
```bash
ssh root@167.71.143.194 "python3 -c \"
import bittensor as bt
sub = bt.subtensor(network='finney')
mg = sub.metagraph(netuid=50)
uid = 233
print(f'=== MINER STATUS ===')
print(f'UID: {uid}')
print(f'Active: {mg.active[uid]}')
print(f'Stake: {mg.S[uid]:.2f} τ')
print(f'Trust: {mg.trust[uid]:.4f}')
print(f'Incentive: {mg.incentive[uid]:.4f}')
print(f'Emission: {mg.emission[uid]}')
print(f'Axon serving: {mg.axons[uid].is_serving}')
print(f'Total active miners: {mg.active.sum()}')
print(f'Active validators: {sum(mg.validator_permit)}')
if mg.active[uid] == 0:
    print('❌ MINER IS INACTIVE')
else:
    print('✅ MINER IS ACTIVE')
\""
```

### Check if Miner is Receiving Requests
```bash
ssh root@167.71.143.194 "pm2 logs miner --lines 50 | grep -E 'Received prediction|request|validator' | tail -10"
```

## 📊 Dashboard Alternative

For a visual interface, use the web dashboard:
- **URL**: http://localhost:5000
- **Features**: Real-time monitoring, stake tracking, validator requests
- **Auto-refresh**: Every 30 seconds

## 🔧 Troubleshooting

### Miner Not Running
```bash
ssh root@167.71.143.194 "pm2 start miner"
```

### Check for Errors
```bash
ssh root@167.71.143.194 "pm2 logs miner --err"
```

### View All PM2 Processes
```bash
ssh root@167.71.143.194 "pm2 list"
```

---

**Server**: 167.71.143.194  
**Wallet**: wallet1  
**Hotkey**: default  
**UID**: 233  
**Subnet**: 50 (Synth)
