# Troubleshooting -1 Score Issue

## What -1 Score Means

A -1 score indicates a **format validation failure**. According to the validator code, -1 is returned when:

1. **No prediction received** (`miner_prediction is None`)
2. **Format validation failed** (`format_validation != CORRECT`)
3. **No real prices available** (`len(real_prices) == 0`)
4. **CRPS calculation exception**
5. **CRPS score is NaN**

## Critical Format Requirements

Based on `synth/validator/response_validation.py`, your response must pass ALL these checks:

### 1. Number of Simulations
- **Expected**: Must match `simulation_input.num_simulations` exactly
- **Current code**: Generates 100 simulations
- **⚠️ POTENTIAL ISSUE**: Release v1.5.0 mentions "1k Paths" - validators may now request **1000 simulations** instead of 100

### 2. Number of Time Points
- **Expected**: `(time_length / time_increment) + 1`
- **For 24h @ 5min**: `(86400 / 300) + 1 = 289` time points per path
- **Your code**: Should generate 289 points per simulation

### 3. Start Time Match
- **Expected**: First time point of ALL paths must exactly match `simulation_input.start_time`
- **Format**: ISO 8601, e.g., `"2025-10-30T17:02:00+00:00"`
- **⚠️ CRITICAL**: Must match character-for-character

### 4. Time Increments
- **Expected**: Exactly `time_increment` seconds between consecutive points
- **For 5min**: Exactly 300 seconds (5 * 60)
- **Validation**: `actual_delta == timedelta(seconds=300)`

### 5. Price Format
- **Expected**: `int` or `float` (not string!)
- **Your code**: Uses `max(0.01, weighted_price)` which should be fine

### 6. Response Timing
- **Must arrive**: Before `start_time` (you have ~1 minute buffer)
- **Timeout**: If `process_time_str is None`, you get -1

## Diagnostic Steps (Run on Server)

### Step 1: Check What Validators Are Actually Requesting

```bash
# Check recent validator requests in logs
pm2 logs miner --lines 500 | grep -i "num_simulations\|simulation_input" | tail -20
```

### Step 2: Verify Your Response Format

```bash
# Test locally what your code generates
cd /root/synth-analogue-experiments
python3 -c "
from synth_integration import generate_synth_simulations
from datetime import datetime, timedelta
import json

start_time = (datetime.now() + timedelta(minutes=1)).isoformat()
result = generate_synth_simulations(
    asset='BTC',
    start_time=start_time,
    time_increment=300,
    time_length=86400,
    num_simulations=100  # Try 100 first
)

print(f'Number of simulations: {len(result)}')
print(f'Number of time points per sim: {len(result[0])}')
print(f'First time point: {result[0][0][\"time\"]}')
print(f'First price type: {type(result[0][0][\"price\"])}')
print(f'Time increment check:')
for i in range(1, min(5, len(result[0]))):
    from datetime import datetime
    t1 = datetime.fromisoformat(result[0][i-1]['time'])
    t2 = datetime.fromisoformat(result[0][i]['time'])
    delta = (t2 - t1).total_seconds()
    print(f'  Step {i}: {delta} seconds (expected 300)')
"
```

### Step 3: Check for Format Validation Errors

```bash
# Look for validation error messages in logs
pm2 logs miner --lines 1000 | grep -i "incorrect\|validation\|format\|error" | tail -30
```

### Step 4: Test with 1000 Simulations (If Validators Updated)

The release note "v1.5.0 New Format and 1k Paths" suggests validators may now request 1000 simulations. Test if your code can handle this:

```bash
python3 -c "
from synth_integration import generate_synth_simulations
from datetime import datetime, timedelta

start_time = (datetime.now() + timedelta(minutes=1)).isoformat()
try:
    result = generate_synth_simulations(
        asset='BTC',
        start_time=start_time,
        time_increment=300,
        time_length=86400,
        num_simulations=1000  # Test with 1000
    )
    print(f'SUCCESS: Generated {len(result)} simulations')
    print(f'Each has {len(result[0])} time points')
except Exception as e:
    print(f'ERROR: {e}')
    import traceback
    traceback.print_exc()
"
```

## ✅ CONFIRMED ISSUE: v1.5.0 Changed to 1000 Simulations

**Release**: [v1.5.0 "New Format and 1k Paths"](https://github.com/mode-network/synth-subnet/releases/tag/v1.5.0) (Nov 10, 2025)

**What Changed**:
- Validators now request **1000 simulations** instead of 100
- Your miner is still generating 100 simulations
- This causes format validation failure: `"Number of paths is incorrect: expected 1000, got 100"` → **-1 score**

**Good News**: Your code already accepts `num_simulations` as a parameter, so it should work! The issue is that your deployed code may have a hardcoded default of 100.

**Solution**: Ensure your miner uses the `num_simulations` value from the validator request (not a hardcoded 100)

### Issue 2: Start Time Format Mismatch
**Solution**: Ensure your `start_time` matches exactly what validators send. Check for timezone issues (`+00:00` vs `Z`).

### Issue 3: Time Increment Precision
**Solution**: Ensure timestamps are exactly 300 seconds apart. Floating point issues can cause validation failures.

### Issue 4: Response Too Slow
**Solution**: Check if your miner is responding before `start_time`. Look for timeout errors in logs.

## Immediate Action Items

1. **Check server logs** for actual `num_simulations` being requested
2. **Verify your code generates exactly** what validators expect
3. **Test with 1000 simulations** to see if that's the new requirement
4. **Check for timezone/format issues** in start_time matching

## References

- Validator validation code: `synth-subnet/synth/validator/response_validation.py`
- Reward calculation: `synth-subnet/synth/validator/reward.py` (lines 54-59 show -1 conditions)
- Release notes: v1.5.0 mentions "New Format and 1k Paths"
- README: https://github.com/mode-network/synth-subnet#12-task-presented-to-the-miners

