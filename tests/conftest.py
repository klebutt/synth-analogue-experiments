import pytest
import numpy as np
from datetime import datetime, timedelta

# Simple test fixtures for baseline model testing
@pytest.fixture
def sample_price_data():
    """Sample price data for testing."""
    start_time = datetime.now()
    prices = [100.0, 101.0, 99.5, 102.0, 98.0, 103.0, 97.5, 104.0]
    times = [start_time + timedelta(minutes=i*5) for i in range(len(prices))]
    return list(zip(times, prices))

@pytest.fixture
def test_parameters():
    """Common test parameters for models."""
    return {
        'start_price': 100.0,
        'start_time': datetime.now(),
        'time_increment': 300,  # 5 minutes
        'time_horizon': 3600,   # 1 hour
        'num_simulations': 10
    }

@pytest.fixture
def random_seed():
    """Set random seed for reproducible tests."""
    np.random.seed(42)
    return 42
