"""
Mean Reversion Baseline Model

This model assumes that prices tend to return to a long-term average,
which is common in many financial markets and commodities.
"""

import numpy as np
from typing import List, Dict, Any
from datetime import datetime, timedelta


class MeanReversionModel:
    """
    Mean reversion model for price prediction.
    
    This model assumes that prices are pulled back toward a long-term average
    when they deviate too far from it.
    """
    
    def __init__(self, 
                 mean_price: float = None,
                 reversion_strength: float = None,
                 volatility: float = None):
        """
        Initialize the mean reversion model.
        
        Args:
            mean_price: Long-term average price to revert to
            reversion_strength: How strongly prices are pulled toward the mean (0-1)
            volatility: Random noise in the process
        """
        if mean_price is None:
            self.mean_price = 100000
        else:
            self.mean_price = mean_price
        if reversion_strength is None:
            self.reversion_strength = 0.1
        else:
            self.reversion_strength = reversion_strength
        if volatility is None:
            self.volatility = 0.02
        else:
            self.volatility = volatility
        self.name = "Mean Reversion Baseline"
        
    def predict(self, 
                start_price: float,
                start_time: datetime,
                time_increment: int = 300,  # 5 minutes in seconds
                time_horizon: int = 86400,  # 24 hours in seconds
                num_simulations: int = 100) -> List[List[Dict[str, Any]]]:
        """
        Generate price predictions using mean reversion.
        
        Args:
            start_price: Starting price of the asset
            start_time: When predictions should start
            time_increment: Time between predictions in seconds
            time_horizon: Total prediction horizon in seconds
            num_simulations: Number of simulation paths to generate
            
        Returns:
            List of simulation paths, each containing price predictions
        """
        # TODO: Enhance mean reversion model with:
        # - Time-varying mean (trending mean reversion)
        # - Multiple mean levels (regime switching)
        # - Asymmetric reversion (different speeds up vs down)
        # - Volatility clustering during mean reversion
        
        num_steps = int(time_horizon / time_increment)
        predictions = []
        
        for sim in range(num_simulations):
            path = []
            current_price = start_price
            
            for step in range(num_steps + 1):  # +1 to include start time
                # Calculate time for this step
                current_time = start_time + timedelta(seconds=step * time_increment)
                
                # Mean reversion formula: 
                # dP = α * (μ - P) * dt + σ * dW
                # where α is reversion strength, μ is mean price
                
                # Calculate mean reversion force
                reversion_force = self.reversion_strength * (self.mean_price - current_price)
                
                # Add random noise (using direct 5-minute volatility)
                random_shock = np.random.normal(0, self.volatility * current_price)
                
                # Update price
                price_change = reversion_force + random_shock
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
            "mean_price": self.mean_price,
            "reversion_strength": self.reversion_strength,
            "volatility": self.volatility,
            "description": "Mean reversion with constant parameters"
        }


# TODO: Next steps for baseline models:
# 1. Implement GARCH model for volatility clustering
# 2. Add jump-diffusion for sudden price movements
# 3. Create regime-switching models
# 4. Build ensemble models that combine multiple approaches