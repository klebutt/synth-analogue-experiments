#!/usr/bin/env python3
import bittensor as bt

def check_miner_status():
    try:
        sub = bt.subtensor(network='finney')
        mg = sub.metagraph(netuid=50)
        uid = 233
        
        print("=== MINER STATUS ===")
        print(f"UID: {uid}")
        print(f"Active: {mg.active[uid]}")
        print(f"Stake: {mg.S[uid]:.2f} τ")
        print(f"Trust: {mg.trust[uid]:.4f}")
        print(f"Incentive: {mg.incentive[uid]:.4f}")
        print(f"Emission: {mg.emission[uid]}")
        print(f"Axon serving: {mg.axons[uid].is_serving}")
        print(f"Total active miners: {mg.active.sum()}")
        print(f"Active validators: {sum(mg.validator_permit)}")
        
        if mg.active[uid] == 0:
            print("❌ MINER IS INACTIVE")
        else:
            print("✅ MINER IS ACTIVE")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_miner_status()
