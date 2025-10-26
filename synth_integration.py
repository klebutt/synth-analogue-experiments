"""
Synth Subnet Integration for Analog Experiments
Integrates our best-performing Ensemble (GBM-weighted) model with Synth subnet
"""

import sys
import os
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add our project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import our best models
from models.baseline.random_walk import RandomWalkModel
from models.baseline.geometric_brownian import GeometricBrownianModel
from models.baseline.mean_reversion import MeanReversionModel
from models.crps import CRPSCalculator
from models.baseline.volatility_calculator import get_all_volatilities

# Import Synth utilities
sys.path.insert(0, os.path.join(project_root, 'synth-subnet'))
from synth.miner.price_simulation import get_asset_price
from synth.utils.helpers import convert_prices_to_time_format


class EnsembleGBMWeightedModel:
    """
    Our best-performing ensemble model with GBM weighting.
    CRPS Score: 547.30 (from notebook results)
    """
    
    def __init__(self):
        self.name = "Ensemble (GBM-weighted)"
        self.last_calibration = {}
        self.cached_params = {}
        
        # Initialize individual models with optimized parameters
        self.models = {
            'RandomWalk': RandomWalkModel(volatility=0.02),
            'GBM': GeometricBrownianModel(drift=0.0001, volatility=0.015),
            'MeanReversion': MeanReversionModel(
                mean_price=50000,  # Will be updated with current price
                reversion_strength=0.1,
                volatility=0.02
            )
        }
        
        # GBM-weighted ensemble (best performing configuration)
        self.weights = [0.2, 0.5, 0.3]  # [RW, GBM, MR]
        
    def predict(self,
                asset: str, 
                start_price: float,
                start_time: datetime,
                time_increment: int = 300,  # 5 minutes
                time_horizon: int = 86400,  # 24 hours
                num_simulations: int = 100) -> List[List[Dict[str, Any]]]:
        """
        Generate predictions using our ensemble model.
        Returns format compatible with Synth subnet.
        """
        
        # check if we need to calibrate
        current_time = datetime.now()
        needs_calibration = False
        if asset not in self.last_calibration:
            needs_calibration = True
        else:
            time_since_calibration = current_time - self.last_calibration[asset]
            if time_since_calibration.total_seconds() > 6 * 3600:
                needs_calibration = True

        if needs_calibration:
            volatilities = get_all_volatilities()
            self.cached_params[asset] = {
                'volatility': volatilities[asset]['volatility'],
                'drift': volatilities[asset]['drift']
            }
            self.last_calibration[asset] = current_time

            self.models['RandomWalk'].volatility = self.cached_params[asset]['volatility']
            self.models['GBM'].drift = self.cached_params[asset]['drift']
            self.models['GBM'].volatility = self.cached_params[asset]['volatility']
            self.models['MeanReversion'].reversion_strength = 0.1
            self.models['MeanReversion'].volatility = self.cached_params[asset]['volatility']

        # Update mean reversion model with current price
        self.models['MeanReversion'].mean_price = start_price
        
        # Get predictions from each individual model
        model_predictions = {}
        for model_name, model in self.models.items():
            try:
                pred = model.predict(start_price, start_time, 
                                   time_increment, time_horizon, num_simulations)
                if pred and len(pred) > 0:
                    model_predictions[model_name] = pred
            except Exception as e:
                print(f"Warning: {model_name} model failed: {e}")
                continue
        
        if not model_predictions:
            raise ValueError("All models failed to generate predictions")
        
        # Calculate number of time steps
        num_steps = int(time_horizon / time_increment) + 1  # +1 for start time
        
        all_predictions = []
        
        for sim in range(num_simulations):
            simulation_predictions = []
            
            for step in range(num_steps):
                current_time = start_time + timedelta(seconds=step * time_increment)
                
                if step == 0:
                    # Start time - use current price
                    simulation_predictions.append({
                        'time': current_time.isoformat(),
                        'price': start_price
                    })
                else:
                    # Future time steps - ensemble predictions
                    step_predictions = []
                    weights_used = []
                    
                    for i, (model_name, model_preds) in enumerate(model_predictions.items()):
                        if sim < len(model_preds) and step < len(model_preds[sim]):
                            step_predictions.append(model_preds[sim][step]['price'])
                            weights_used.append(self.weights[i])
                    
                    if step_predictions:
                        # Weighted average of predictions
                        weighted_price = sum(p * w for p, w in zip(step_predictions, weights_used))
                        
                        simulation_predictions.append({
                            'time': current_time.isoformat(),
                            'price': max(0.01, weighted_price)  # Ensure positive price
                        })
                    else:
                        # Fallback to previous price if no predictions available
                        prev_price = simulation_predictions[step-1]['price']
                        simulation_predictions.append({
                            'time': current_time.isoformat(),
                            'price': prev_price
                        })
            
            if simulation_predictions:
                all_predictions.append(simulation_predictions)
        
        return all_predictions


def generate_synth_simulations(
    asset="BTC",
    start_time="",
    time_increment=300,
    time_length=86400,
    num_simulations=100,  # Official Synth subnet requirement
    sigma=0.01,  # Ignored - we use our own model
):
    """
    Generate simulated price paths using our best ensemble model.
    Compatible with Synth subnet interface.
    
    Parameters:
        asset (str): The asset to simulate. Default is 'BTC'.
        start_time (str): The start time of the simulation. Defaults to current time.
        time_increment (int): Time increment in seconds.
        time_length (int): Total time length in seconds.
        num_simulations (int): Number of simulation runs.
        sigma (float): Standard deviation (ignored - we use our own model).
    
    Returns:
        List[List[Dict]]: Simulated price paths in Synth format.
    """
    if start_time == "":
        raise ValueError("Start time must be provided.")
    
    # Get current price from Synth's price feed
    current_price = get_asset_price(asset)
    if current_price is None:
        raise ValueError(f"Failed to fetch current price for asset: {asset}")
    
    # Initialize our best model
    model = EnsembleGBMWeightedModel()
    
    # Convert start_time to datetime (handle both string and datetime inputs)
    if isinstance(start_time, str):
        start_datetime = datetime.fromisoformat(start_time)
    else:
        start_datetime = start_time
    
    # Generate predictions using our ensemble model
    predictions = model.predict(
        asset=asset,
        start_price=current_price,
        start_time=start_datetime,
        time_increment=time_increment,
        time_horizon=time_length,
        num_simulations=num_simulations
    )
    
    return predictions


def test_our_model():
    """
    Test our model integration with Synth subnet format.
    """
    print("Testing our Ensemble (GBM-weighted) model integration...")
    print("=" * 60)
    
    # Test parameters (matching Synth subnet defaults)
    asset = "BTC"
    time_increment = 300  # 5 minutes
    time_length = 86400   # 24 hours
    num_simulations = 100   # Official Synth subnet requirement
    
    # Set start time to 1 hour from now (Synth subnet format)
    start_time = (datetime.now() + timedelta(hours=1)).isoformat()
    
    try:
        # Generate predictions
        predictions = generate_synth_simulations(
            asset=asset,
            start_time=start_time,
            time_increment=time_increment,
            time_length=time_length,
            num_simulations=num_simulations
        )
        
        # Validate output format
        if not predictions:
            print("ERROR: No predictions generated")
            return False
            
        if len(predictions) != num_simulations:
            print(f"ERROR: Expected {num_simulations} simulations, got {len(predictions)}")
            return False
            
        # Check first simulation format
        first_sim = predictions[0]
        if not isinstance(first_sim, list):
            print("ERROR: Each simulation should be a list")
            return False
            
        # Check time points (should be 25 for 24 hours with 5-minute increments)
        expected_steps = int(time_length / time_increment) + 1
        if len(first_sim) != expected_steps:
            print(f"ERROR: Expected {expected_steps} time points, got {len(first_sim)}")
            return False
            
        # Check format of first prediction
        first_pred = first_sim[0]
        if not isinstance(first_pred, dict) or 'time' not in first_pred or 'price' not in first_pred:
            print("ERROR: Each prediction should be a dict with 'time' and 'price' keys")
            return False
            
        print(f"SUCCESS: Generated {len(predictions)} simulations")
        print(f"SUCCESS: Each simulation has {len(first_sim)} time points")
        print(f"SUCCESS: Format validation passed")
        print(f"SUCCESS: Start time: {first_sim[0]['time']}")
        print(f"SUCCESS: End time: {first_sim[-1]['time']}")
        print(f"SUCCESS: Price range: ${min(p['price'] for p in first_sim):.2f} - ${max(p['price'] for p in first_sim):.2f}")
        
        return True
        
    except Exception as e:
        print(f"ERROR: Error during testing: {e}")
        return False


if __name__ == "__main__":
    print("Synth Subnet Integration - Analog Experiments")
    print("=" * 60)
    print("Using our best model: Ensemble (GBM-weighted)")
    print("Expected CRPS Score: 547.30")
    print("Ready to earn TAO rewards!")
    print()
    
    # Test our integration
    success = test_our_model()
    
    if success:
        print("\nIntegration test PASSED!")
        print("Our model is ready for Synth subnet deployment")
    else:
        print("\nIntegration test FAILED!")
        print("Need to fix issues before deployment")