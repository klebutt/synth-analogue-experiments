"""
Configuration file for Synth Analog Experiments.

This file contains all the configuration parameters for models, testing, and deployment.
"""

import os
from typing import Dict, Any

# TODO: Add environment variable support
# TODO: Add configuration validation
# TODO: Add different config profiles (dev, test, prod)


class Config:
    """Main configuration class."""
    
    # Project settings
    PROJECT_NAME = "Synth Analog Experiments"
    VERSION = "0.1.0"
    DEBUG = True
    
    # Model parameters
    MODELS = {
        "random_walk": {
            "volatility": 0.02,
            "description": "Basic random walk model"
        },
        "geometric_brownian": {
            "drift": 0.0,
            "volatility": 0.02,
            "description": "GBM with constant parameters"
        },
        "mean_reversion": {
            "mean_price": 50000.0,
            "reversion_strength": 0.1,
            "volatility": 0.02,
            "description": "Mean reversion model"
        },
        "fluid_dynamics": {
            "viscosity": 0.1,
            "pressure_gradient": 0.0,
            "turbulence_strength": 0.05,
            "description": "Fluid dynamics analog model"
        }
    }
    
    # Synth subnet parameters
    SYNTH_CONFIG = {
        "time_increment": 300,      # 5 minutes in seconds
        "time_horizon": 86400,      # 24 hours in seconds
        "num_simulations": 100,     # Required by Synth
        "assets": ["BTC", "ETH"],   # Supported assets
        "max_response_time": 60     # Maximum time to respond (seconds)
    }
    
    # Testing parameters
    TEST_CONFIG = {
        "num_simulations": 10,      # Smaller for testing
        "time_horizon": 3600,       # 1 hour for testing
        "random_seed": 42           # For reproducible tests
    }
    
    # Performance settings
    PERFORMANCE = {
        "max_prediction_time": 30,  # Maximum seconds to generate predictions
        "memory_limit_mb": 1024,    # Memory usage limit
        "parallel_workers": 4       # Number of parallel workers
    }
    
    # Logging configuration
    LOGGING = {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "synth_analog.log"
    }
    
    @classmethod
    def get_model_config(cls, model_name: str) -> Dict[str, Any]:
        """Get configuration for a specific model."""
        return cls.MODELS.get(model_name, {})
    
    @classmethod
    def get_synth_config(cls) -> Dict[str, Any]:
        """Get Synth subnet configuration."""
        return cls.SYNTH_CONFIG.copy()
    
    @classmethod
    def get_test_config(cls) -> Dict[str, Any]:
        """Get testing configuration."""
        return cls.TEST_CONFIG.copy()
    
    @classmethod
    def validate_config(cls) -> bool:
        """Validate configuration parameters."""
        # TODO: Implement configuration validation
        # 1. Check that all required parameters are present
        # 2. Validate parameter ranges and types
        # 3. Ensure consistency between related parameters
        # 4. Log any validation issues
        
        return True


# TODO: Add configuration loading from files
# TODO: Add environment-specific configurations
# TODO: Add configuration hot-reloading
# TODO: Add configuration encryption for sensitive data

if __name__ == "__main__":
    # Test configuration
    config = Config()
    print(f"Configuration loaded: {config.PROJECT_NAME} v{config.VERSION}")
    
    # Test model config retrieval
    rw_config = config.get_model_config("random_walk")
    print(f"Random Walk config: {rw_config}")
    
    # Validate configuration
    if config.validate_config():
        print("✅ Configuration is valid")
    else:
        print("❌ Configuration validation failed")
