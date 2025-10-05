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
                start_price: float,
                start_time: datetime,
                time_increment: int = 300,  # 5 minutes
                time_horizon: int = 86400,  # 24 hours
                num_simulations: int = 100) -> List[List[Dict[str, Any]]]:
        """
        Generate predictions using our ensemble model.
        Returns format compatible with Synth subnet.
        """
        
        # Update mean reversion model with current price
        self.models['MeanReversion'].mean_price = start_price
        
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
                    # Future time steps - get predictions from each model
                    model_predictions = []
                    
                    for model_name, model in self.models.items():
                        # Get prediction for this specific time step
                        pred = model.predict(start_price, start_time, 
                                          time_increment, time_horizon, 1)
                        if pred and pred[0] and len(pred[0]) > step:
                            model_predictions.append(pred[0][step]['price'])
                    
                    if model_predictions:
                        # Weighted average of predictions
                        weighted_price = sum(p * w for p, w in zip(model_predictions, self.weights[:len(model_predictions)]))
                        
                        simulation_predictions.append({
                            'time': current_time.isoformat(),
                            'price': max(0.01, weighted_price)  # Ensure positive price
                        })
            
            if simulation_predictions:
                all_predictions.append(simulation_predictions)
        
        return all_predictions


def generate_synth_simulations(
    asset="BTC",
    start_time: str = "",
    time_increment=300,
    time_length=86400,
    num_simulations=100,
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
    
    # Convert start_time string to datetime
    start_datetime = datetime.fromisoformat(start_time)
    
    # Generate predictions using our ensemble model
    predictions = model.predict(
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
    print("🧪 Testing our Ensemble (GBM-weighted) model integration...")
    print("=" * 60)
    
    # Test parameters (matching Synth subnet defaults)
    asset = "BTC"
    time_increment = 300  # 5 minutes
    time_length = 86400   # 24 hours
    num_simulations = 100
    
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
            print("❌ No predictions generated")
            return False
            
        if len(predictions) != num_simulations:
            print(f"❌ Expected {num_simulations} simulations, got {len(predictions)}")
            return False
            
        # Check first simulation format
        first_sim = predictions[0]
        if not isinstance(first_sim, list):
            print("❌ Each simulation should be a list")
            return False
            
        # Check time points (should be 25 for 24 hours with 5-minute increments)
        expected_steps = int(time_length / time_increment) + 1
        if len(first_sim) != expected_steps:
            print(f"❌ Expected {expected_steps} time points, got {len(first_sim)}")
            return False
            
        # Check format of first prediction
        first_pred = first_sim[0]
        if not isinstance(first_pred, dict) or 'time' not in first_pred or 'price' not in first_pred:
            print("❌ Each prediction should be a dict with 'time' and 'price' keys")
            return False
            
        print(f"✅ Generated {len(predictions)} simulations")
        print(f"✅ Each simulation has {len(first_sim)} time points")
        print(f"✅ Format validation passed")
        print(f"✅ Start time: {first_sim[0]['time']}")
        print(f"✅ End time: {first_sim[-1]['time']}")
        print(f"✅ Price range: ${min(p['price'] for p in first_sim):.2f} - ${max(p['price'] for p in first_sim):.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        return False


if __name__ == "__main__":
    print("🚀 Synth Subnet Integration - Analog Experiments")
    print("=" * 60)
    print("🎯 Using our best model: Ensemble (GBM-weighted)")
    print("📊 Expected CRPS Score: 547.30")
    print("💰 Ready to earn TAO rewards!")
    print()
    
    # Test our integration
    success = test_our_model()
    
    if success:
        print("\n🎉 Integration test PASSED!")
        print("✅ Our model is ready for Synth subnet deployment")
    else:
        print("\n❌ Integration test FAILED!")
        print("🔧 Need to fix issues before deployment")
