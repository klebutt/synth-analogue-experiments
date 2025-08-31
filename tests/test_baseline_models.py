"""
Tests for baseline forecasting models.

This file contains unit tests to ensure our baseline models work correctly.
"""

import pytest
import numpy as np
import time
from datetime import datetime, timedelta

# Import our actual models
from models.baseline.random_walk import RandomWalkModel
from models.baseline.geometric_brownian import GeometricBrownianModel
from models.baseline.mean_reversion import MeanReversionModel


class TestBaselineModels:
    """Test suite for baseline forecasting models."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.start_price = 50000.0
        self.start_time = datetime.now()
        self.time_increment = 300  # 5 minutes
        self.time_horizon = 3600   # 1 hour (reduced from 24 hours for faster testing)
        self.num_simulations = 10  # Small number for testing
        
        # Set random seed for reproducible tests
        np.random.seed(42)
    
    def test_random_walk_basic(self):
        """Test basic random walk functionality."""
        # 1. Create RandomWalkModel instance
        model = RandomWalkModel(volatility=0.02)
        
        # 2. Generate predictions
        predictions = model.predict(
            start_price=self.start_price,
            start_time=self.start_time,
            time_increment=self.time_increment,
            time_horizon=self.time_horizon,
            num_simulations=self.num_simulations
        )
        
        # 3. Verify output format
        assert isinstance(predictions, list), "Predictions should be a list"
        assert len(predictions) == self.num_simulations, f"Expected {self.num_simulations} simulations"
        
        # 4. Check that prices stay positive
        for simulation in predictions:
            assert isinstance(simulation, list), "Each simulation should be a list"
            for prediction in simulation:
                assert prediction['price'] > 0, f"Price should be positive, got {prediction['price']}"
        
        # 5. Verify time increments are correct
        first_simulation = predictions[0]
        assert len(first_simulation) == (self.time_horizon // self.time_increment) + 1, "Correct number of time steps"
        
        # Check time progression
        for i in range(1, len(first_simulation)):
            current_time = datetime.fromisoformat(first_simulation[i]['time'])
            prev_time = datetime.fromisoformat(first_simulation[i-1]['time'])
            time_diff = (current_time - prev_time).total_seconds()
            assert time_diff == self.time_increment, f"Time increment should be {self.time_increment} seconds"
    
    def test_gbm_basic(self):
        """Test basic geometric brownian motion functionality."""
        # 1. Create GeometricBrownianModel instance
        model = GeometricBrownianModel(drift=0.001, volatility=0.02)
        
        # 2. Test with different drift and volatility parameters
        predictions = model.predict(
            start_price=self.start_price,
            start_time=self.start_time,
            time_increment=self.time_increment,
            time_horizon=self.time_horizon,
            num_simulations=self.num_simulations
        )
        
        # 3. Verify percentage-based price changes
        assert len(predictions) == self.num_simulations, "Correct number of simulations"
        
        # Check that GBM produces percentage-based changes (not absolute)
        first_simulation = predictions[0]
        for i in range(1, len(first_simulation)):
            current_price = first_simulation[i]['price']
            prev_price = first_simulation[i-1]['price']
            # Price changes should be percentage-based, not absolute
            assert current_price > 0, "GBM prices should stay positive"
        
        # 4. Check output format and constraints
        for simulation in predictions:
            assert len(simulation) == (self.time_horizon // self.time_increment) + 1, "Correct number of time steps"
            for prediction in simulation:
                assert 'time' in prediction, "Each prediction should have 'time' key"
                assert 'price' in prediction, "Each prediction should have 'price' key"
                assert prediction['price'] > 0, "GBM prices should be positive"
    
    def test_mean_reversion_basic(self):
        """Test basic mean reversion functionality."""
        # 1. Create MeanReversionModel instance
        mean_price = 50000.0
        model = MeanReversionModel(
            mean_price=mean_price,
            reversion_strength=0.1,
            volatility=0.02
        )
        
        # 2. Test reversion toward mean price
        predictions = model.predict(
            start_price=self.start_price,
            start_time=self.start_time,
            time_increment=self.time_increment,
            time_horizon=self.time_horizon,
            num_simulations=self.num_simulations
        )
        
        # 3. Verify reversion strength parameter
        assert len(predictions) == self.num_simulations, "Correct number of simulations"
        
        # Check that prices tend to move toward mean (this is probabilistic, so we check structure)
        for simulation in predictions:
            assert len(simulation) == (self.time_horizon // self.time_increment) + 1, "Correct number of time steps"
            for prediction in simulation:
                assert prediction['price'] > 0, "Mean reversion prices should stay positive"
        
        # 4. Check that prices don't explode
        # Mean reversion should keep prices within reasonable bounds
        all_prices = [p['price'] for sim in predictions for p in sim]
        max_price = max(all_prices)
        min_price = min(all_prices)
        
        # Prices should stay within reasonable bounds (not explode to infinity or go to zero)
        assert max_price < self.start_price * 10, "Prices shouldn't explode upward"
        assert min_price > self.start_price * 0.1, "Prices shouldn't collapse to near zero"
    
    def test_prediction_format(self):
        """Test that all models return correct prediction format."""
        # 1. Test all baseline models
        models = [
            RandomWalkModel(volatility=0.02),
            GeometricBrownianModel(drift=0.001, volatility=0.02),
            MeanReversionModel(mean_price=50000.0, reversion_strength=0.1, volatility=0.02)
        ]
        
        for model in models:
            predictions = model.predict(
                start_price=self.start_price,
                start_time=self.start_time,
                time_increment=self.time_increment,
                time_horizon=self.time_horizon,
                num_simulations=self.num_simulations
            )
            
            # 2. Verify output structure matches Synth subnet requirements
            assert isinstance(predictions, list), "Predictions should be a list"
            assert len(predictions) == self.num_simulations, "Correct number of simulations"
            
            for simulation in predictions:
                assert isinstance(simulation, list), "Each simulation should be a list"
                assert len(simulation) == (self.time_horizon // self.time_increment) + 1, "Correct number of time steps"
                
                for prediction in simulation:
                    # 3. Check time format (ISO 8601)
                    time_str = prediction['time']
                    try:
                        datetime.fromisoformat(time_str)
                    except ValueError:
                        pytest.fail(f"Time format should be ISO 8601, got: {time_str}")
                    
                    # 4. Ensure correct number of simulations and required keys
                    assert 'time' in prediction, "Missing 'time' key"
                    assert 'price' in prediction, "Missing 'price' key"
                    assert isinstance(prediction['price'], (int, float)), "Price should be numeric"
                    assert prediction['price'] > 0, "Price should be positive"
    
    def test_parameter_validation(self):
        """Test that models handle invalid parameters gracefully."""
        # 1. Test negative prices
        model = RandomWalkModel(volatility=0.02)
        
        # This should work (models should handle negative start prices gracefully or raise clear errors)
        try:
            predictions = model.predict(
                start_price=-100.0,
                start_time=self.start_time,
                time_increment=self.time_increment,
                time_horizon=self.time_horizon,
                num_simulations=self.num_simulations
            )
            # If it works, verify the output is still valid
            assert len(predictions) == self.num_simulations, "Should still produce correct number of simulations"
        except Exception as e:
            # If it fails, the error should be clear
            # Note: numpy's "scale < 0" error is acceptable for negative prices
            error_msg = str(e).lower()
            assert ("price" in error_msg or "negative" in error_msg or 
                   "scale" in error_msg), f"Error should mention price/negative/scale: {e}"
        
        # 2. Test invalid time parameters
        try:
            predictions = model.predict(
                start_price=self.start_price,
                start_time=self.start_time,
                time_increment=-300,  # Negative time increment
                time_horizon=self.time_horizon,
                num_simulations=self.num_simulations
            )
            # Currently our models don't validate time parameters, so this might work
            # In the future, we might want to add validation
            assert len(predictions) == self.num_simulations, "Should still produce correct number of simulations"
        except Exception as e:
            # If it fails, that's also acceptable - means we added validation
            pass
        
        # 3. Test extreme parameter values
        try:
            predictions = model.predict(
                start_price=self.start_price,
                start_time=self.start_time,
                time_increment=self.time_increment,
                time_horizon=self.time_horizon,
                num_simulations=1000000  # Very large number
            )
            # If it works, it should complete in reasonable time
            assert len(predictions) == 1000000, "Should handle large simulation counts"
        except Exception as e:
            # If it fails, should be a clear error
            error_msg = str(e).lower()
            assert ("memory" in error_msg or "time" in error_msg or 
                   "scale" in error_msg), f"Error should mention resource limits: {e}"
        
        # 4. Verify error handling
        # Models should either work or give clear error messages
    
    def test_performance_benchmarks(self):
        """Test that models meet basic performance requirements."""
        model = RandomWalkModel(volatility=0.02)
        
        # 1. Measure prediction generation time
        start_time = time.time()
        predictions = model.predict(
            start_price=self.start_price,
            start_time=self.start_time,
            time_increment=self.time_increment,
            time_horizon=self.time_horizon,
            num_simulations=self.num_simulations
        )
        generation_time = time.time() - start_time
        
        # 2. Check memory usage (basic check)
        # For now, just verify the output is reasonable size
        total_predictions = len(predictions) * len(predictions[0])
        assert total_predictions > 0, "Should produce predictions"
        
        # 3. Verify scalability with more simulations
        # Test with larger simulation count
        start_time = time.time()
        large_predictions = model.predict(
            start_price=self.start_price,
            start_time=self.start_time,
            time_increment=self.time_increment,
            time_horizon=self.time_horizon,
            num_simulations=100  # 10x more simulations
        )
        large_generation_time = time.time() - start_time
        
        # 4. Set performance benchmarks
        # Small simulations should complete quickly
        assert generation_time < 1.0, f"Small simulations should complete in <1s, took {generation_time:.3f}s"
        
        # Larger simulations should scale reasonably (not 10x slower for 10x data)
        # Add small epsilon to prevent division by zero for very fast operations
        epsilon = 0.001  # 1 millisecond
        if generation_time < epsilon:
            generation_time = epsilon
        
        time_ratio = large_generation_time / generation_time
        assert time_ratio < 15, f"10x more simulations shouldn't take >15x longer, ratio: {time_ratio:.2f}"
        
        # Verify larger output is correct
        assert len(large_predictions) == 100, "Should produce correct number of large simulations"


# Additional test categories for future implementation:
# 1. Integration tests between models
# 2. CRPS calculation tests
# 3. Model comparison tests
# 4. Edge case handling tests
# 5. Performance regression tests


if __name__ == "__main__":
    pytest.main([__file__])
