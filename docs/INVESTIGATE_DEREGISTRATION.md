# Investigating Miner Deregistration Issue

## Timeline from Logs

1. **19:29-19:43**: Miner running successfully with UID:233, Stake:94.63685607910156
2. **19:43:45**: Miner stopped (`Stopping miner in background thread`)
3. **19:43:47+**: Multiple restart attempts all fail with "not registered" error

## Possible Causes

### 1. **False Positive - Network/Sync Issue** (Most Likely)
The miner might still be registered, but:
- Metagraph not syncing properly
- Network connection issue to blockchain
- Temporary blockchain node issue

**Check**: Verify actual registration status on-chain

### 2. **Actual Deregistration**
Someone/something deregistered the miner:
- Manual deregistration via `btcli subnet unregister`
- Automatic deregistration (unlikely unless configured)
- Wallet/hotkey was changed

**Check**: Look for deregistration transactions

### 3. **Wallet/Hotkey Path Issue**
The miner might be looking for the wrong wallet:
- Wallet path changed
- Hotkey file moved/deleted
- Permission issues

**Check**: Verify wallet files exist and are accessible

### 4. **Metagraph Sync Issue**
The miner can't see its own registration:
- Blockchain node out of sync
- Network partition
- Stale metagraph cache

**Check**: Force metagraph refresh

## Diagnostic Steps

### Step 1: Check Actual Registration Status

```bash
# Check if you're actually registered on-chain
btcli subnet list --netuid 50 --wallet.name wallet1 --wallet.hotkey default

# Check your UID if registered
btcli subnet list --netuid 50 | grep -i "wallet1\|default" | grep -i "uid\|233"
```

### Step 2: Verify Wallet Files

```bash
# Check wallet exists
ls -la ~/.bittensor/wallets/wallet1/hotkeys/default

# Check wallet can be loaded
btcli wallet show --wallet.name wallet1 --wallet.hotkey default
```

### Step 3: Check Metagraph Sync

```bash
# Try to sync metagraph manually
cd /root/synth-subnet
python3 -c "
import bittensor as bt
wallet = bt.wallet(name='wallet1', hotkey='default')
subtensor = bt.subtensor(network='finney')
metagraph = subtensor.metagraph(netuid=50)
print(f'Metagraph block: {metagraph.block}')
print(f'Number of neurons: {len(metagraph.hotkeys)}')
try:
    uid = metagraph.hotkeys.index(wallet.hotkey.ss58_address)
    print(f'Found UID: {uid}')
    print(f'Stake: {metagraph.S[uid]}')
except ValueError:
    print('Hotkey not found in metagraph')
"
```

### Step 4: Check Recent Transactions

```bash
# Check if there was a deregistration transaction
# (This would require checking blockchain explorer or btcli history)
```

## Most Likely Scenario

Given that:
- Miner was running fine with UID:233
- Error only appears after restart
- No indication of manual deregistration

**Most likely**: Network/sync issue preventing the miner from seeing its registration, NOT an actual deregistration.

## Quick Fix to Try

```bash
# 1. Stop miner
pm2 stop miner

# 2. Clear any cached metagraph data (if exists)
# (Location depends on bittensor version)

# 3. Try starting with explicit network refresh
cd /root/synth-subnet
python3 neurons/miner.py --netuid 50 --logging.debug --wallet.name wallet1 --wallet.hotkey default --axon.port 8091 --blacklist.force_validator_permit true --blacklist.validator_min_stake 1000

# If that works, the issue is with PM2 or cached state
```

## If Actually Deregistered

If the checks above confirm you're actually deregistered:

1. **Re-register immediately**:
   ```bash
   btcli subnet register --netuid 50 --wallet.name wallet1 --wallet.hotkey default
   ```

2. **Investigate why**:
   - Check if someone else has access to your wallet
   - Check wallet transaction history
   - Verify no automated deregistration scripts

## Next Steps

1. **First**: Run Step 1 to verify actual registration status
2. **If registered**: It's a sync issue - try the quick fix
3. **If not registered**: Re-register and investigate cause




