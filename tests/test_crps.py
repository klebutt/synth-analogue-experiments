"""
Tests for CRPS (Continuous Ranked Probability Score) calculation.

This module tests the CRPS calculator which is essential for Synth subnet performance evaluation.
"""

import pytest
import numpy as np
from datetime import datetime, timedelta
from models.crps import CRPSCalculator, calculate_crps, calculate_crps_for_synth, compare_models_crps


class TestCRPSCalculation:
    """Test suite for CRPS calculation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.calculator = CRPSCalculator()
        
        # Create sample predictions (3 simulations, 5 time points)
        self.start_time = datetime.now()
        self.predictions = []
        
        for sim in range(3):
            simulation = []
            for i in range(5):
                time_point = self.start_time + timedelta(minutes=i*5)
                # Create some realistic price variations
                base_price = 50000.0
                noise = np.random.normal(0, 1000)  # $1000 standard deviation
                price = base_price + noise + i * 100  # Slight upward trend
                
                simulation.append({
                    'time': time_point.isoformat(),
                    'price': max(price, 1000.0)  # Ensure positive prices
                })
            self.predictions.append(simulation)
        
        # Create corresponding actual data
        self.actual_data = []
        for i in range(5):
            time_point = self.start_time + timedelta(minutes=i*5)
            # Actual prices with some deviation from predictions
            base_price = 50000.0
            actual_price = base_price + i * 100 + np.random.normal(0, 500)
            
            self.actual_data.append({
                'time': time_point.isoformat(),
                'price': max(actual_price, 1000.0)
            })
    
    def test_crps_calculator_initialization(self):
        """Test CRPS calculator initialization."""
        assert self.calculator.name == "CRPS Calculator"
        assert hasattr(self.calculator, 'calculate_crps')
        assert hasattr(self.calculator, 'calculate_crps_for_synth')
    
    def test_crps_basic_calculation(self):
        """Test basic CRPS calculation."""
        # Extract actual prices and times
        actual_prices = [point['price'] for point in self.actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in self.actual_data]
        
        # Calculate CRPS
        crps_score = self.calculator.calculate_crps(
            self.predictions, actual_prices, actual_times
        )
        
        # CRPS should be a non-negative float
        assert isinstance(crps_score, float)
        assert crps_score >= 0.0
        
        # CRPS should be reasonable (not infinite or extremely large)
        assert crps_score < 1000000.0  # Should be reasonable for price predictions
    
    def test_crps_for_synth_format(self):
        """Test CRPS calculation specifically for Synth subnet format."""
        metrics = self.calculator.calculate_crps_for_synth(
            self.predictions, self.actual_data
        )
        
        # Check required fields
        required_fields = ['crps_score', 'num_simulations', 'num_time_points', 
                          'prediction_horizon', 'timestamp']
        for field in required_fields:
            assert field in metrics, f"Missing required field: {field}"
        
        # Validate values
        assert metrics['num_simulations'] == 3
        assert metrics['num_time_points'] == 5
        assert metrics['prediction_horizon'] == 1200  # 20 minutes in seconds
        assert isinstance(metrics['crps_score'], float)
        assert metrics['crps_score'] >= 0.0
    
    def test_crps_with_perfect_predictions(self):
        """Test CRPS with perfect predictions (should be very low)."""
        # Create perfect predictions (exactly match actual data)
        perfect_predictions = []
        for sim in range(3):
            simulation = []
            for point in self.actual_data:
                simulation.append(point.copy())
            perfect_predictions.append(simulation)
        
        actual_prices = [point['price'] for point in self.actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in self.actual_data]
        
        crps_score = self.calculator.calculate_crps(
            perfect_predictions, actual_prices, actual_times
        )
        
        # Perfect predictions should have very low CRPS
        assert crps_score < 1.0, f"Perfect predictions should have low CRPS, got: {crps_score}"
    
    def test_crps_with_terrible_predictions(self):
        """Test CRPS with terrible predictions (should be high)."""
        # Create terrible predictions (completely wrong)
        terrible_predictions = []
        for sim in range(3):
            simulation = []
            for point in self.actual_data:
                # Predict exactly the opposite of actual
                wrong_price = 100000.0 - point['price']  # Opposite side of 50k
                simulation.append({
                    'time': point['time'],
                    'price': max(wrong_price, 1000.0)
                })
            terrible_predictions.append(simulation)
        
        actual_prices = [point['price'] for point in self.actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in self.actual_data]
        
        crps_score = self.calculator.calculate_crps(
            terrible_predictions, actual_prices, actual_times
        )
        
        # Terrible predictions should have higher CRPS than good predictions
        # The exact threshold depends on the data, so let's compare with good predictions
        good_predictions = []
        for sim in range(3):
            simulation = []
            for point in self.actual_data:
                actual_price = point['price']
                good_price = actual_price + np.random.normal(0, 100)  # Close to actual
                simulation.append({
                    'time': point['time'],
                    'price': max(good_price, 1000.0)
                })
            good_predictions.append(simulation)
        
        good_crps = self.calculator.calculate_crps(good_predictions, actual_prices, actual_times)
        
        # Terrible predictions should have higher CRPS than good predictions
        assert crps_score > good_crps, f"Terrible predictions should have higher CRPS than good: {crps_score} vs {good_crps}"
        
        # CRPS should be reasonable (not extremely low)
        assert crps_score > 50.0, f"Terrible predictions should have reasonable CRPS, got: {crps_score}"
    
    def test_crps_input_validation(self):
        """Test CRPS input validation and error handling."""
        # Test empty predictions
        with pytest.raises(ValueError, match="All inputs must be non-empty"):
            self.calculator.calculate_crps([], [1.0], [datetime.now()])
        
        # Test empty actual prices
        with pytest.raises(ValueError, match="All inputs must be non-empty"):
            self.calculator.calculate_crps(self.predictions, [], [datetime.now()])
        
        # Test mismatched lengths
        with pytest.raises(ValueError, match="actual_prices and actual_times must have same length"):
            self.calculator.calculate_crps(
                self.predictions, 
                [1.0, 2.0],  # 2 prices
                [datetime.now(), datetime.now(), datetime.now()]  # 3 times
            )
        
        # Test predictions not matching actual times
        with pytest.raises(ValueError, match="Number of predictions"):
            self.calculator.calculate_crps(
                self.predictions,  # 5 time points
                [1.0, 2.0, 3.0],  # 3 prices
                [datetime.now(), datetime.now(), datetime.now()]  # 3 times
            )
    
    def test_model_comparison(self):
        """Test comparing multiple models using CRPS."""
        # Create predictions for multiple models
        model_predictions = {
            'random_walk': self.predictions,
            'gbm': self.predictions,  # Using same for simplicity
            'mean_reversion': self.predictions
        }
        
        results = self.calculator.compare_models(model_predictions, self.actual_data)
        
        # Check structure
        assert 'random_walk' in results
        assert 'gbm' in results
        assert 'mean_reversion' in results
        assert 'ranking' in results
        assert 'best_model' in results
        
        # Check ranking
        ranking = results['ranking']
        assert len(ranking) == 3
        assert all(isinstance(item, tuple) and len(item) == 2 for item in ranking)
        
        # Best model should be first in ranking
        best_model_name = results['best_model']
        assert best_model_name == ranking[0][0]
        
        # All models should have CRPS scores
        for model_name in ['random_walk', 'gbm', 'mean_reversion']:
            assert 'crps_score' in results[model_name]
            assert isinstance(results[model_name]['crps_score'], float)
    
    def test_convenience_functions(self):
        """Test the convenience functions work correctly."""
        # Test calculate_crps function
        actual_prices = [point['price'] for point in self.actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in self.actual_data]
        
        crps_score = calculate_crps(self.predictions, actual_prices, actual_times)
        assert isinstance(crps_score, float)
        assert crps_score >= 0.0
        
        # Test calculate_crps_for_synth function
        metrics = calculate_crps_for_synth(self.predictions, self.actual_data)
        assert 'crps_score' in metrics
        
        # The scores might differ slightly due to random sampling in CRPS calculation
        # So we'll just verify they're both reasonable
        assert abs(metrics['crps_score'] - crps_score) < 1000.0, f"CRPS scores should be reasonably close: {metrics['crps_score']} vs {crps_score}"
        
        # Test compare_models_crps function
        model_predictions = {
            'model_a': self.predictions,
            'model_b': self.predictions
        }
        comparison = compare_models_crps(model_predictions, self.actual_data)
        assert 'model_a' in comparison
        assert 'model_b' in comparison
        assert 'ranking' in comparison
    
    def test_crps_mathematical_properties(self):
        """Test that CRPS has expected mathematical properties."""
        # CRPS should be lower for better predictions
        good_predictions = []
        bad_predictions = []
        
        for sim in range(3):
            good_sim = []
            bad_sim = []
            
            for point in self.actual_data:
                actual_price = point['price']
                
                # Good predictions: close to actual
                good_price = actual_price + np.random.normal(0, 100)
                good_sim.append({
                    'time': point['time'],
                    'price': max(good_price, 1000.0)
                })
                
                # Bad predictions: far from actual
                bad_price = actual_price + np.random.normal(0, 5000)
                bad_sim.append({
                    'time': point['time'],
                    'price': max(bad_price, 1000.0)
                })
            
            good_predictions.append(good_sim)
            bad_predictions.append(bad_sim)
        
        actual_prices = [point['price'] for point in self.actual_data]
        actual_times = [datetime.fromisoformat(point['time']) for point in self.actual_data]
        
        good_crps = self.calculator.calculate_crps(good_predictions, actual_prices, actual_times)
        bad_crps = self.calculator.calculate_crps(bad_predictions, actual_prices, actual_times)
        
        # Good predictions should have lower CRPS
        assert good_crps < bad_crps, f"Good predictions should have lower CRPS: {good_crps} vs {bad_crps}"
    
    def test_crps_performance(self):
        """Test CRPS calculation performance with larger datasets."""
        # Create larger dataset
        large_predictions = []
        large_actual_data = []
        
        start_time = datetime.now()
        for sim in range(100):  # 100 simulations
            simulation = []
            for i in range(50):  # 50 time points
                time_point = start_time + timedelta(minutes=i*5)
                price = 50000.0 + np.random.normal(0, 1000)
                
                simulation.append({
                    'time': time_point.isoformat(),
                    'price': max(price, 1000.0)
                })
            large_predictions.append(simulation)
        
        for i in range(50):
            time_point = start_time + timedelta(minutes=i*5)
            price = 50000.0 + np.random.normal(0, 1000)
            
            large_actual_data.append({
                'time': time_point.isoformat(),
                'price': max(price, 1000.0)
            })
        
        # Measure performance
        import time
        start_time = time.time()
        
        metrics = self.calculator.calculate_crps_for_synth(large_predictions, large_actual_data)
        
        calculation_time = time.time() - start_time
        
        # Should complete in reasonable time
        assert calculation_time < 10.0, f"CRPS calculation took too long: {calculation_time:.2f}s"
        
        # Should produce valid results
        assert 'crps_score' in metrics
        assert metrics['num_simulations'] == 100
        assert metrics['num_time_points'] == 50


if __name__ == "__main__":
    pytest.main([__file__])
