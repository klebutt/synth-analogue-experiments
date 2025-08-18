"""
Random Walk Baseline Model

This is a simple random walk model that serves as a basic baseline.
It generates price predictions by adding random noise to the current price.
"""

import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta


class RandomWalkModel:
    """
    Simple random walk model for price prediction.
    
    This model assumes that price changes are random and independent.
    It's included as a baseline to compare against more sophisticated approaches.
    """
    
    def __init__(self, volatility: float = 0.02):
        """
        Initialize the random walk model.
        
        Args:
            volatility: Standard deviation of price changes (as a fraction)
        """
        self.volatility = volatility
        self.name = "Random Walk Baseline"
        
    def predict(self, 
                start_price: float,
                start_time: datetime,
                time_increment: int = 300,  # 5 minutes in seconds
                time_horizon: int = 86400,  # 24 hours in seconds
                num_simulations: int = 100) -> List[List[Dict[str, Any]]]:
        """
        Generate price predictions using random walk.
        
        Args:
            start_price: Starting price of the asset
            start_time: When predictions should start
            time_increment: Time between predictions in seconds
            time_horizon: Total prediction horizon in seconds
            num_simulations: Number of simulation paths to generate
            
        Returns:
            List of simulation paths, each containing price predictions
        """
        # TODO: Add more sophisticated random walk variants
        # - Consider adding drift terms
        # - Implement different noise distributions (normal, student-t, etc.)
        # - Add mean reversion components
        
        num_steps = int(time_horizon / time_increment)
        predictions = []
        
        for sim in range(num_simulations):
            path = []
            current_price = start_price
            
            for step in range(num_steps + 1):  # +1 to include start time
                # Calculate time for this step
                current_time = start_time + timedelta(seconds=step * time_increment)
                
                # Generate random price change
                price_change = np.random.normal(0, self.volatility * current_price)
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
            "volatility": self.volatility,
            "description": "Simple random walk with normal noise"
        }


# TODO: Add more baseline models here:
# 1. Geometric Brownian Motion (GBM) - accounts for percentage changes
# 2. Mean Reversion - prices tend to return to long-term average
# 3. GARCH models - capture volatility clustering
# 4. Jump-diffusion models - handle sudden price movements
