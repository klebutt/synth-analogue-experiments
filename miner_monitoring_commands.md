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
ssh root@167.71.143.194 "pm2 logs custom-miner --lines 50"
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

### 6. Check Validator Requests
```bash
ssh root@167.71.143.194 "pm2 logs custom-miner --lines 100 | grep -c 'Received prediction'"
```
- Counts total validator requests received
- Shows if you're getting work from validators

### 7. Check System Resources
```bash
ssh root@167.71.143.194 "pm2 show custom-miner"
```
- Shows detailed process information
- Displays CPU and memory usage
- Shows restart count and uptime

### 8. Restart Miner (if needed)
```bash
ssh root@167.71.143.194 "pm2 restart custom-miner"
```
- Restarts the miner if it's stuck or errored
- Use if you see issues in the logs

### 9. Check Recent Activity
```bash
ssh root@167.71.143.194 "pm2 logs custom-miner --lines 20 | tail -20"
```
- Shows the last 20 log entries
- Quick check for recent activity

### 10. Monitor Live Logs
```bash
ssh root@167.71.143.194 "pm2 logs custom-miner --follow"
```
- Shows live, real-time logs
- Press Ctrl+C to stop monitoring

## 🚀 Quick Health Check

Run these 3 commands for a quick status check:
```bash
ssh root@167.71.143.194 "pm2 status | grep custom-miner"
ssh root@167.71.143.194 "btcli stake list --wallet.name wallet1 --wallet.hotkey default | grep 50"
ssh root@167.71.143.194 "pm2 logs custom-miner --lines 10 | grep -E 'Received prediction|Error|Warning'"
```

These commands will tell you if your miner is running, how much stake you have, and if you're receiving validator requests!

## 📊 Dashboard Alternative

For a visual interface, use the web dashboard:
- **URL**: http://localhost:5000
- **Features**: Real-time monitoring, stake tracking, validator requests
- **Auto-refresh**: Every 30 seconds

## 🔧 Troubleshooting

### Miner Not Running
```bash
ssh root@167.71.143.194 "pm2 start custom-miner"
```

### Check for Errors
```bash
ssh root@167.71.143.194 "pm2 logs custom-miner --err"
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
