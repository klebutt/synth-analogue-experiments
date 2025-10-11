#!/usr/bin/env python3
"""
Custom Synth Miner using our Ensemble (GBM-weighted) model
This replaces the default generate_simulations with our superior analog-inspired forecasting model.
"""

import time
import typing
import bittensor as bt
import sys
import os

# Add project root to path for our custom models
project_root = os.path.abspath(os.path.dirname(__file__))
sys.path.insert(0, project_root)

# Import our custom model integration
from synth_integration import generate_synth_simulations

# Import base miner class and protocol from synth-subnet
sys.path.insert(0, os.path.join(project_root, 'synth-subnet'))
from synth.base.miner import BaseMinerNeuron
from synth.protocol import Simulation


class CustomMiner(BaseMinerNeuron):
    """
    Custom miner neuron class that uses our Ensemble (GBM-weighted) model.
    This replaces the default generate_simulations with our superior analog-inspired forecasting model.
    """

    def __init__(self, config=None):
        super(CustomMiner, self).__init__(config=config)
        bt.logging.info("Custom Miner initialized with Ensemble (GBM-weighted) model")
        bt.logging.info("Expected CRPS: 547.30")
        bt.logging.info("Ready to earn TAO rewards with superior predictions!")

    async def forward_miner(self, synapse: Simulation) -> Simulation:
        simulation_input = synapse.simulation_input
        bt.logging.info(
            f"Received prediction request from: {synapse.dendrite.hotkey} for timestamp: {simulation_input.start_time}"
        )
        bt.logging.info(f"Asset: {simulation_input.asset}")
        bt.logging.info(f"Time increment: {simulation_input.time_increment}s")
        bt.logging.info(f"Time length: {simulation_input.time_length}s")
        bt.logging.info(f"Simulations: {simulation_input.num_simulations}")

        try:
            # Use our custom Ensemble model instead of the default generate_simulations
            bt.logging.info("Generating predictions with Ensemble (GBM-weighted) model...")
            
            synapse.simulation_output = generate_synth_simulations(
                asset=simulation_input.asset,
                start_time=simulation_input.start_time,
                time_increment=simulation_input.time_increment,
                time_length=simulation_input.time_length,
                num_simulations=simulation_input.num_simulations,
                sigma=self.config.simulation.sigma,  # Standard deviation of the simulated price path
            )
            
            bt.logging.success("Predictions generated successfully with custom model!")
            bt.logging.info(f"Generated {len(synapse.simulation_output)} simulations")
            
            # Log some statistics about the predictions
            if synapse.simulation_output:
                first_sim = synapse.simulation_output[0]
                if first_sim:
                    prices = [point['price'] for point in first_sim]
                    if prices:
                        min_price = min(prices)
                        max_price = max(prices)
                        bt.logging.info(f"Price range: ${min_price:.2f} - ${max_price:.2f}")
            
        except Exception as e:
            bt.logging.error(f"Error generating predictions: {str(e)}")
            # Fallback to default behavior if our model fails
            bt.logging.warning("Falling back to default generate_simulations...")
            from synth.miner.simulations import generate_simulations
            synapse.simulation_output = generate_simulations(
                asset=simulation_input.asset,
                start_time=simulation_input.start_time,
                time_increment=simulation_input.time_increment,
                time_length=simulation_input.time_length,
                num_simulations=simulation_input.num_simulations,
                sigma=self.config.simulation.sigma,
            )

        return synapse

    async def blacklist(self, synapse: Simulation) -> typing.Tuple[bool, str]:
        """
        Determines whether an incoming request should be blacklisted and thus ignored.
        """
        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning("Received a request without a dendrite or hotkey.")
            return True, "Missing dendrite or hotkey"

        if (
            not self.config.blacklist.allow_non_registered
            and synapse.dendrite.hotkey not in self.metagraph.hotkeys
        ):
            bt.logging.trace(f"Blacklisting un-registered hotkey {synapse.dendrite.hotkey}")
            return True, "Unrecognized hotkey"

        uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        stake = self.metagraph.S[uid]
        bt.logging.info(f"Requesting UID: {uid} | Stake at UID: {stake}")

        if uid in self.config.blacklist.validator_exceptions:
            bt.logging.info(f"Requesting UID: {uid} whitelisted as a validator")
        else:
            if stake <= self.config.blacklist.validator_min_stake:
                bt.logging.info(
                    f"Hotkey: {synapse.dendrite.hotkey}: stake below minimum threshold of {self.config.blacklist.validator_min_stake}"
                )
                return True, "Stake below minimum threshold"

        if self.config.blacklist.force_validator_permit:
            if not self.metagraph.validator_permit[uid]:
                bt.logging.warning(f"Blacklisting a request from non-validator hotkey {synapse.dendrite.hotkey}")
                return True, "Non-validator hotkey"

        bt.logging.trace(f"Not Blacklisting recognized hotkey {synapse.dendrite.hotkey}")
        return False, "Hotkey recognized!"

    async def priority(self, synapse: Simulation) -> float:
        """
        The priority function determines the order in which requests are handled.
        """
        if synapse.dendrite is None or synapse.dendrite.hotkey is None:
            bt.logging.warning("Received a request without a dendrite or hotkey.")
            return 0.0

        caller_uid = self.metagraph.hotkeys.index(synapse.dendrite.hotkey)
        priority = float(self.metagraph.S[caller_uid])
        bt.logging.trace(f"Prioritizing {synapse.dendrite.hotkey} with value: {priority}")
        return priority

    def save_state(self):
        pass

    def load_state(self):
        pass

    def set_weights(self):
        pass

    async def forward_validator(self):
        pass

    def print_info(self):
        metagraph = self.metagraph
        self.uid = self.metagraph.hotkeys.index(self.wallet.hotkey.ss58_address)

        log = (
            "Custom Miner | "
            f"Step:{self.step} | "
            f"UID:{self.uid} | "
            f"Stake:{metagraph.S[self.uid]} | "
            f"Trust:{metagraph.T[self.uid]:.4f} | "
            f"Incentive:{metagraph.I[self.uid]:.4f} | "
            f"Emission:{metagraph.E[self.uid]:.4f} | "
            f"Model:Ensemble(GBM-weighted)"
        )
        bt.logging.info(log)


# This is the main function, which runs the miner.
if __name__ == "__main__":
    with CustomMiner() as miner:
        while True:
            miner.print_info()
            time.sleep(20)
