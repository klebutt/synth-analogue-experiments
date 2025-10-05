"""
Deployment-Ready Synth Subnet Miner
Uses our best-performing Ensemble (GBM-weighted) model
Ready for production deployment and TAO rewards
"""

import sys
import os
import time
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Add paths
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'synth-subnet'))

# Import our integration
from synth_integration import generate_synth_simulations

# Import Synth components
from synth.simulation_input import SimulationInput
from synth.utils.helpers import get_current_time, round_time_to_minutes
from synth.validator.response_validation import validate_responses


class AnalogExperimentsMiner:
    """
    Production-ready miner using our best-performing model.
    Ensemble (GBM-weighted) with CRPS: 547.30
    """
    
    def __init__(self):
        self.name = "Analog Experiments Miner"
        self.model_name = "Ensemble (GBM-weighted)"
        self.expected_crps = 547.30
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        
    def generate_predictions(self, 
                           asset: str = "BTC",
                           time_increment: int = 300,
                           time_length: int = 86400,
                           num_simulations: int = 100) -> Dict[str, Any]:
        """
        Generate predictions using our best model.
        Returns both predictions and metadata.
        """
        try:
            # Set start time (1-2 hours in future, like Synth subnet)
            current_time = get_current_time()
            start_time = round_time_to_minutes(current_time, 60, 120)
            
            # Generate predictions
            predictions = generate_synth_simulations(
                asset=asset,
                start_time=start_time.isoformat(),
                time_increment=time_increment,
                time_length=time_length,
                num_simulations=num_simulations
            )
            
            # Validate predictions
            simulation_input = SimulationInput(
                asset=asset,
                time_increment=time_increment,
                time_length=time_length,
                num_simulations=num_simulations,
                start_time=start_time.isoformat()
            )
            
            validation_result = validate_responses(
                predictions,
                simulation_input,
                start_time,
                "0"  # miner_uid
            )
            
            return {
                'predictions': predictions,
                'validation': validation_result,
                'metadata': {
                    'model': self.model_name,
                    'expected_crps': self.expected_crps,
                    'asset': asset,
                    'start_time': start_time.isoformat(),
                    'num_simulations': num_simulations,
                    'time_points': len(predictions[0]) if predictions else 0
                }
            }
            
        except Exception as e:
            return {
                'predictions': None,
                'validation': 'ERROR',
                'error': str(e),
                'metadata': {
                    'model': self.model_name,
                    'asset': asset,
                    'error_time': datetime.now().isoformat()
                }
            }
    
    def process_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single prediction request.
        """
        self.total_requests += 1
        
        print(f"\n📨 Processing request #{self.total_requests}")
        print(f"🎯 Asset: {request_data.get('asset', 'BTC')}")
        print(f"⏱️  Time increment: {request_data.get('time_increment', 300)}s")
        print(f"📏 Time length: {request_data.get('time_length', 86400)}s")
        print(f"🔄 Simulations: {request_data.get('num_simulations', 100)}")
        
        start_time = time.time()
        result = self.generate_predictions(**request_data)
        processing_time = time.time() - start_time
        
        if result['validation'] == 'CORRECT':
            self.successful_requests += 1
            print(f"✅ SUCCESS - Validation: {result['validation']}")
            print(f"⏱️  Processing time: {processing_time:.2f}s")
            print(f"📊 Generated {len(result['predictions'])} simulations")
            print(f"📈 Price range: ${min(p['price'] for p in result['predictions'][0]):.2f} - ${max(p['price'] for p in result['predictions'][0]):.2f}")
        else:
            self.failed_requests += 1
            print(f"❌ FAILED - Validation: {result['validation']}")
            if 'error' in result:
                print(f"🔧 Error: {result['error']}")
        
        result['processing_time'] = processing_time
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get miner performance statistics.
        """
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests > 0 else 0
        
        return {
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': success_rate,
            'model': self.model_name,
            'expected_crps': self.expected_crps
        }
    
    def run_benchmark(self, num_tests: int = 10):
        """
        Run performance benchmark tests.
        """
        print(f"🏃 Running benchmark with {num_tests} tests...")
        print("=" * 60)
        
        processing_times = []
        success_count = 0
        
        for i in range(num_tests):
            print(f"\n🧪 Test {i+1}/{num_tests}")
            
            # Test with different assets
            assets = ["BTC", "ETH", "XAU", "SOL"]
            asset = assets[i % len(assets)]
            
            request_data = {
                'asset': asset,
                'time_increment': 300,
                'time_length': 86400,
                'num_simulations': 100
            }
            
            result = self.process_request(request_data)
            
            if result['validation'] == 'CORRECT':
                success_count += 1
                processing_times.append(result['processing_time'])
        
        # Calculate benchmark results
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        benchmark_success_rate = (success_count / num_tests) * 100
        
        print(f"\n📊 BENCHMARK RESULTS")
        print("=" * 60)
        print(f"✅ Successful tests: {success_count}/{num_tests}")
        print(f"📈 Success rate: {benchmark_success_rate:.1f}%")
        print(f"⏱️  Average processing time: {avg_processing_time:.2f}s")
        print(f"🎯 Model: {self.model_name}")
        print(f"📊 Expected CRPS: {self.expected_crps}")
        
        if benchmark_success_rate >= 90:
            print(f"\n🎉 BENCHMARK PASSED!")
            print(f"✅ Ready for production deployment")
            print(f"💰 Should earn TAO rewards with high reliability")
        else:
            print(f"\n⚠️  BENCHMARK NEEDS IMPROVEMENT")
            print(f"🔧 Success rate below 90% - investigate issues")
        
        return {
            'success_rate': benchmark_success_rate,
            'avg_processing_time': avg_processing_time,
            'total_tests': num_tests,
            'successful_tests': success_count
        }


def main():
    """
    Main function to run the deployment miner.
    """
    print("🚀 Analog Experiments Miner - Production Ready")
    print("=" * 60)
    print("🎯 Model: Ensemble (GBM-weighted)")
    print("📊 Expected CRPS: 547.30")
    print("💰 Ready to earn TAO rewards!")
    print()
    
    # Initialize miner
    miner = AnalogExperimentsMiner()
    
    # Run benchmark
    benchmark_results = miner.run_benchmark(num_tests=5)
    
    # Show final stats
    print(f"\n📋 FINAL STATISTICS")
    print("=" * 60)
    stats = miner.get_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    print(f"\n🎯 DEPLOYMENT STATUS")
    print("=" * 60)
    if benchmark_results['success_rate'] >= 90:
        print("✅ READY FOR DEPLOYMENT")
        print("🚀 Can be deployed to Synth subnet")
        print("💰 Should earn TAO rewards consistently")
    else:
        print("⚠️  NEEDS MORE TESTING")
        print("🔧 Fix issues before deployment")


if __name__ == "__main__":
    main()
