# Miner Status Summary & Next Steps - December 14, 2025

## Current Situation

### Miner Status
- **Registration**: Registered on blockchain (UID 233)
- **Active Status**: 0 (validators marking as inactive)
- **Process Running**: Yes (PID 117198, axon serving=True)
- **Rewards Earned**: 0.44 τ (earned earlier, but currently not receiving requests)
- **Stake**: 198.23 τ

### Process Issues
- **PM2 Status**: "miner" process shows as stopped (51 restarts - kept crashing)
- **Actual Process**: Direct Python process running `custom_synth_miner.py` 
  - File was deleted but process still running from memory
  - Process started Oct 12, running from `/root/synth-analogue-experiments`
  - Working directory: `/root/synth-analogue-experiments`

### Code Issues
- **Deployed Code**: `synth_integration.py` has default `num_simulations=100`
- **Validator Requirement**: Now requests `num_simulations=1000` (upgraded Nov 13, 2025)
- **Code Path**: Should pass parameter correctly, but default mismatch is risky
- **Stale Code**: Running old deleted file code instead of current repo code

## Root Causes Identified

1. **PM2 Process Crashed Repeatedly** (51 restarts) - needs investigation
2. **Miner Running Stale Code** - deleted file still in memory
3. **Default num_simulations Mismatch** - 100 vs 1000 requirement
4. **Server Code Not Aligned** - deployed code doesn't match repo

## Next Steps

### Step 1: Update Code Defaults
**Action**: Update `synth_integration.py` to change default `num_simulations` from 100 to 1000
- File: `synth_integration.py` line 166
- Change: `num_simulations=100` → `num_simulations=1000`
- Update comment to reflect current requirement

### Step 2: Align Server with Repo
**Action**: Deploy updated code to server
- Ensure server `/root/synth-analogue-experiments/synth_integration.py` matches repo
- Verify all dependencies are up to date

### Step 3: Restart Miner Properly
**Action**: Stop old process and restart with current code
- Stop process PID 117198 (running deleted file)
- Fix PM2 configuration
- Start miner via PM2 with current code

### Step 4: Fix PM2 Issues
**Action**: Investigate and fix why PM2 was crashing
- Check PM2 error logs for crash reason
- Fix PM2 config/startup issues
- Ensure auto-restart works properly
- Enable PM2 auto-start on boot

## Technical Details

### Code Flow (Current)
1. Validator requests with `num_simulations=1000`
2. `miner.py` → `simulations.py` → `generate_synth_simulations()`
3. Parameter should be passed: `num_simulations=simulation_input.num_simulations`
4. Default in function is 100 (should be overridden, but risky)

### Files Involved
- `/root/synth-subnet/neurons/miner.py` - Main miner entry point
- `/root/synth-subnet/synth/miner/simulations.py` - Delegates to custom code
- `/root/synth-analogue-experiments/synth_integration.py` - Our custom model (needs update)
- `/root/synth-analogue-experiments/custom_synth_miner.py.backup` - Old deleted file

### PM2 Configuration
- PM2 process name: "miner"
- Should run: `/root/synth-subnet/neurons/miner.py`
- Currently: Stopped (51 restarts)
- Direct process: Running `custom_synth_miner.py` (deleted file)

## Verification Commands

After fixes, verify with:
```bash
# Check registration
ssh root@167.71.143.194 "python3 -c \"import bittensor as bt; sub=bt.subtensor('finney'); mg=sub.metagraph(50); uid=233; print(f'Active: {mg.active[uid]}, Axon: {mg.axons[uid].is_serving}')\""

# Check PM2 status
ssh root@167.71.143.194 "pm2 list"

# Check process
ssh root@167.71.143.194 "ps aux | grep miner | grep -v grep"

# Check logs
ssh root@167.71.143.194 "pm2 logs miner --lines 50"
```

## Goal
Align server deployed miner with repo code and get PM2 process running correctly.


