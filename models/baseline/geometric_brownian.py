"""
Geometric Brownian Motion (GBM) Baseline Model

This model assumes that percentage price changes follow a random walk,
which is more realistic than absolute price changes for financial assets.
"""

import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta


class GeometricBrownianModel:
    """
    Geometric Brownian Motion model for price prediction.
    
    This model assumes that the logarithm of price changes follows a random walk,
    which means percentage changes are normally distributed.
    """
    
    def __init__(self, drift: float = None, volatility: float = None):
        """
        Initialize the GBM model.
        
        Args:
            drift: Expected annual return rate (default: 0 = no trend)
            volatility: Annual volatility (standard deviation of returns)
        """
        if drift is None:
            self.drift = 0.0
        else:
            self.drift = drift
        if volatility is None:
            self.volatility = 0.02
        else:
            self.volatility = volatility
        self.name = "Geometric Brownian Motion Baseline"
        
    def predict(self, 
                start_price: float,
                start_time: datetime,
                time_increment: int = 300,  # 5 minutes in seconds
                time_horizon: int = 86400,  # 24 hours in seconds
                num_simulations: int = 100) -> List[List[Dict[str, Any]]]:
        """
        Generate price predictions using GBM.
        
        Args:
            start_price: Starting price of the asset
            start_time: When predictions should start
            time_increment: Time between predictions in seconds
            time_horizon: Total prediction horizon in seconds
            num_simulations: Number of simulation paths to generate
            
        Returns:
            List of simulation paths, each containing price predictions
        """
        # TODO: Enhance GBM model with:
        # - Time-varying volatility (stochastic volatility)
        # - Regime switching (bull/bear markets)
        # - Correlation with other assets
        # - Fat-tailed distributions (student-t, etc.)
        
        num_steps = int(time_horizon / time_increment)
        predictions = []
        
        # Use direct 5-minute volatility (no time scaling needed)
        # For 5-minute predictions, volatility should be per-5-minute interval
        mu = self.drift  # Drift per 5-minute interval
        sigma = self.volatility  # Volatility per 5-minute interval
        
        for sim in range(num_simulations):
            path = []
            current_price = start_price
            
            for step in range(num_steps + 1):  # +1 to include start time
                # Calculate time for this step
                current_time = start_time + timedelta(seconds=step * time_increment)
                
                # GBM formula: dS = S * (μ*dt + σ*dW)
                # where dW is a random normal variable
                random_shock = np.random.normal(0, 1)
                price_change = current_price * (mu + sigma * random_shock)
                current_price += price_change
                
                # Ensure price stays positive
                current_price = max(current_price, 0.01)
                
                path.append({
                    "time": current_time.isoformat(),
                    "price": current_price
                })
            
            predictions.append(path)
        
        return predictions
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the model."""
        return {
            "name": self.name,
            "type": "baseline",
            "drift": self.drift,
            "volatility": self.volatility,
            "description": "GBM with constant drift and volatility"
        }


# TODO: Next baseline models to implement:
# 1. Mean Reversion Model - prices return to long-term average
# 2. GARCH Model - captures volatility clustering
# 3. Jump-Diffusion Model - handles sudden price movements
# 4. Regime-Switching Model - different behavior in different market conditions