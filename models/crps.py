"""
Continuous Ranked Probability Score (CRPS) Calculation

This module implements CRPS calculation for evaluating forecasting model performance.
CRPS is the primary metric used by Synth subnet to rank miners and allocate rewards.

CRPS measures how well our probability distributions match actual outcomes.
Lower CRPS = better forecasts = more TAO rewards.
"""

import numpy as np
from typing import List, Dict, Any, Union, Tuple
from datetime import datetime


class CRPSCalculator:
    """
    Calculator for Continuous Ranked Probability Score (CRPS).
    
    CRPS is a proper scoring rule that measures the accuracy of probabilistic forecasts.
    It's particularly useful for evaluating ensemble forecasts and probabilistic predictions.
    """
    
    def __init__(self):
        """Initialize the CRPS calculator."""
        self.name = "CRPS Calculator"
    
    def calculate_crps(self, 
                      predictions: List[List[Dict[str, Any]]], 
                      actual_prices: List[float],
                      actual_times: List[datetime]) -> float:
        """
        Calculate CRPS for a set of predictions against actual outcomes.
        
        Args:
            predictions: List of simulation paths, each containing price predictions
                        Format: [[{'time': '2023-01-01T00:00:00', 'price': 100.0}, ...], ...]
            actual_prices: List of actual observed prices
            actual_times: List of actual observation times (must match prediction times)
            
        Returns:
            float: CRPS score (lower is better)
            
        Raises:
            ValueError: If inputs are invalid or don't match
        """
        if not predictions or not actual_prices or not actual_times:
            raise ValueError("All inputs must be non-empty")
        
        if len(actual_prices) != len(actual_times):
            raise ValueError("actual_prices and actual_times must have same length")
        
        # Validate that we have predictions for each actual time
        if len(predictions[0]) != len(actual_times):
            raise ValueError(f"Number of predictions ({len(predictions[0])}) must match number of actual times ({len(actual_times)})")
        
        total_crps = 0.0
        
        # Calculate CRPS for each time point
        for time_idx in range(len(actual_times)):
            # Extract all predicted prices for this time point across simulations
            predicted_prices = [simulation[time_idx]['price'] for simulation in predictions]
            actual_price = actual_prices[time_idx]
            
            # Calculate CRPS for this time point
            time_crps = self._calculate_point_crps(predicted_prices, actual_price)
            total_crps += time_crps
        
        # Return average CRPS across all time points
        return total_crps / len(actual_times)
    
    def _calculate_point_crps(self, predicted_prices: List[float], actual_price: float) -> float:
        """
        Calculate CRPS for a single time point.
        
        Args:
            predicted_prices: List of predicted prices from all simulations
            actual_price: Actual observed price
            
        Returns:
            float: CRPS for this time point
        """
        if not predicted_prices:
            raise ValueError("predicted_prices cannot be empty")
        
        # Convert to numpy array for efficient computation
        pred_array = np.array(predicted_prices)
        actual = float(actual_price)
        
        # CRPS formula: E|X - x| - 0.5 * E|X - X'|
        # where X, X' are independent draws from the predictive distribution
        # and x is the actual observation
        
        # First term: E|X - x| (expected absolute error)
        abs_errors = np.abs(pred_array - actual)
        first_term = np.mean(abs_errors)
        
        # Second term: 0.5 * E|X - X'| (half the expected absolute difference between predictions)
        # We'll approximate this by sampling pairs of predictions
        n_preds = len(pred_array)
        if n_preds > 1:
            # Sample pairs without replacement for efficiency
            n_pairs = min(1000, n_preds * (n_preds - 1) // 2)  # Limit pairs for performance
            pair_diffs = []
            
            for _ in range(n_pairs):
                # Randomly sample two different predictions
                idx1, idx2 = np.random.choice(n_preds, size=2, replace=False)
                pair_diffs.append(abs(pred_array[idx1] - pred_array[idx2]))
            
            second_term = 0.5 * np.mean(pair_diffs)
        else:
            second_term = 0.0
        
        crps = first_term - second_term
        return max(0.0, crps)  # CRPS should be non-negative
    
    def calculate_crps_for_synth(self, 
                                predictions: List[List[Dict[str, Any]]], 
                                actual_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculate CRPS specifically formatted for Synth subnet evaluation.
        
        Args:
            predictions: Model predictions in Synth format
            actual_data: Actual market data in Synth format
            
        Returns:
            Dict containing CRPS score and metadata
        """
        # Extract actual prices and times from Synth format
        actual_prices = [point['price'] for point in actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in actual_data]
        
        # Calculate CRPS
        crps_score = self.calculate_crps(predictions, actual_prices, actual_times)
        
        # Calculate additional metrics for Synth
        metrics = {
            'crps_score': crps_score,
            'num_simulations': len(predictions),
            'num_time_points': len(actual_times),
            'prediction_horizon': self._calculate_horizon(actual_times),
            'timestamp': datetime.now().isoformat()
        }
        
        return metrics
    
    def _calculate_horizon(self, times: List[datetime]) -> int:
        """Calculate prediction horizon in seconds."""
        if len(times) < 2:
            return 0
        return int((times[-1] - times[0]).total_seconds())
    
    def compare_models(self, 
                      model_predictions: Dict[str, List[List[Dict[str, Any]]]], 
                      actual_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Compare multiple models using CRPS scores.
        
        Args:
            model_predictions: Dict mapping model names to their predictions
            actual_data: Actual market data
            
        Returns:
            Dict containing CRPS scores for each model and ranking
        """
        results = {}
        
        for model_name, predictions in model_predictions.items():
            try:
                metrics = self.calculate_crps_for_synth(predictions, actual_data)
                results[model_name] = metrics
            except Exception as e:
                results[model_name] = {
                    'error': str(e),
                    'crps_score': float('inf')  # Worst possible score
                }
        
        # Rank models by CRPS (lower is better)
        ranked_models = sorted(
            [(name, data.get('crps_score', float('inf'))) 
             for name, data in results.items()],
            key=lambda x: x[1]
        )
        
        results['ranking'] = ranked_models
        results['best_model'] = ranked_models[0][0] if ranked_models else None
        
        return results
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the CRPS calculator."""
        return {
            "name": self.name,
            "type": "evaluation",
            "description": "Continuous Ranked Probability Score calculator for Synth subnet",
            "version": "1.0.0"
        }


# Convenience functions for easy use
def calculate_crps(predictions: List[List[Dict[str, Any]]], 
                   actual_prices: List[float],
                   actual_times: List[datetime]) -> float:
    """Calculate CRPS for predictions against actual outcomes."""
    calculator = CRPSCalculator()
    return calculator.calculate_crps(predictions, actual_prices, actual_times)


def calculate_crps_for_synth(predictions: List[List[Dict[str, Any]]], 
                            actual_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Calculate CRPS specifically formatted for Synth subnet evaluation."""
    calculator = CRPSCalculator()
    return calculator.calculate_crps_for_synth(predictions, actual_data)


def compare_models_crps(model_predictions: Dict[str, List[List[Dict[str, Any]]]], 
                        actual_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Compare multiple models using CRPS scores."""
    calculator = CRPSCalculator()
    return calculator.compare_models(model_predictions, actual_data)
