#!/usr/bin/env python3
"""
Diagnostic script to identify why miner is getting -1 scores with v1.5.0 format.
Run this on the server to check what's actually happening.
"""

import sys
import os
from datetime import datetime, timedelta
import time
import traceback

# Add paths
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, 'synth-subnet'))
sys.path.insert(0, project_root)

def test_with_1000_simulations():
    """Test if code can handle 1000 simulations."""
    print("=" * 60)
    print("TEST 1: Can generate 1000 simulations?")
    print("=" * 60)
    
    try:
        from synth_integration import generate_synth_simulations
        
        start_time = (datetime.now() + timedelta(minutes=1)).isoformat()
        print(f"Start time: {start_time}")
        print("Generating 1000 simulations...")
        
        start = time.time()
        result = generate_synth_simulations(
            asset='BTC',
            start_time=start_time,
            time_increment=300,
            time_length=86400,
            num_simulations=1000
        )
        elapsed = time.time() - start
        
        print(f"✅ SUCCESS: Generated {len(result)} simulations in {elapsed:.2f} seconds")
        print(f"✅ Each simulation has {len(result[0])} time points")
        
        if elapsed > 50:
            print(f"⚠️  WARNING: Takes {elapsed:.2f}s - may timeout!")
        
        return True, result
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False, None

def test_format_validation():
    """Test if output format matches validator requirements."""
    print("\n" + "=" * 60)
    print("TEST 2: Format validation")
    print("=" * 60)
    
    try:
        from synth_integration import generate_synth_simulations
        from synth.validator.response_validation import validate_responses
        from synth.simulation_input import SimulationInput
        
        start_time = (datetime.now() + timedelta(minutes=1)).isoformat()
        result = generate_synth_simulations(
            asset='BTC',
            start_time=start_time,
            time_increment=300,
            time_length=86400,
            num_simulations=1000
        )
        
        simulation_input = SimulationInput(
            asset="BTC",
            time_increment=300,
            time_length=86400,
            num_simulations=1000,
            start_time=start_time
        )
        
        request_time = datetime.now()
        validation_result = validate_responses(
            result,
            simulation_input,
            request_time,
            "0.5"  # process_time_str
        )
        
        if validation_result == "CORRECT":
            print("✅ Format validation PASSED")
            return True
        else:
            print(f"❌ Format validation FAILED: {validation_result}")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def test_through_miner_path():
    """Test the exact code path the miner uses."""
    print("\n" + "=" * 60)
    print("TEST 3: Testing through miner code path")
    print("=" * 60)
    
    try:
        from synth.miner.simulations import generate_simulations
        
        start_time = (datetime.now() + timedelta(minutes=1)).isoformat()
        print(f"Start time: {start_time}")
        print("Generating through miner path...")
        
        start = time.time()
        result = generate_simulations(
            asset='BTC',
            start_time=start_time,
            time_increment=300,
            time_length=86400,
            num_simulations=1000
        )
        elapsed = time.time() - start
        
        print(f"✅ SUCCESS: Generated {len(result)} simulations in {elapsed:.2f} seconds")
        print(f"✅ Each simulation has {len(result[0])} time points")
        
        # Check format
        first_time = result[0][0].get("time", "")
        if first_time == start_time:
            print(f"✅ Start time matches: {first_time}")
        else:
            print(f"❌ Start time mismatch!")
            print(f"   Expected: {start_time}")
            print(f"   Got:      {first_time}")
        
        return True
    except Exception as e:
        print(f"❌ FAILED: {e}")
        traceback.print_exc()
        return False

def check_start_time_format():
    """Check if start_time format matches exactly."""
    print("\n" + "=" * 60)
    print("TEST 4: Start time format check")
    print("=" * 60)
    
    # Test different formats
    test_times = [
        (datetime.now() + timedelta(minutes=1)).isoformat(),
        (datetime.now() + timedelta(minutes=1)).replace(microsecond=0).isoformat(),
        (datetime.now(timezone.utc) + timedelta(minutes=1)).isoformat(),
    ]
    
    for test_time in test_times:
        print(f"\nTesting format: {test_time}")
        try:
            from synth_integration import generate_synth_simulations
            result = generate_synth_simulations(
                asset='BTC',
                start_time=test_time,
                time_increment=300,
                time_length=86400,
                num_simulations=10  # Small number for speed
            )
            first_time = result[0][0].get("time", "")
            print(f"  Generated first time: {first_time}")
            if first_time == test_time:
                print(f"  ✅ Matches!")
            else:
                print(f"  ❌ Mismatch!")
        except Exception as e:
            print(f"  ❌ Error: {e}")

def main():
    print("Miner Diagnostic Script for v1.5.0 Format Issues")
    print("=" * 60)
    print()
    
    results = []
    
    # Test 1: Can generate 1000?
    success, result = test_with_1000_simulations()
    results.append(("Generate 1000 simulations", success))
    
    # Test 2: Format validation
    if success:
        results.append(("Format validation", test_format_validation()))
    
    # Test 3: Miner path
    results.append(("Miner code path", test_through_miner_path()))
    
    # Test 4: Start time format
    check_start_time_format()
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    all_passed = all(r[1] for r in results)
    if all_passed:
        print("\n✅ All tests passed! Code should work with v1.5.0 format.")
        print("   If miner still gets -1, check:")
        print("   1. Miner is using latest code (restart with: pm2 restart miner)")
        print("   2. Check logs for actual errors: pm2 logs miner --lines 500")
        print("   3. Verify num_simulations in requests: pm2 logs miner | grep num_simulations")
    else:
        print("\n❌ Some tests failed. Fix issues above before deploying.")

if __name__ == "__main__":
    from datetime import timezone
    main()




