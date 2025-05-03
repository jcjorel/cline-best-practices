#!/usr/bin/env python3
"""
Test script for the new Bedrock profile discovery algorithm.

This script tests the new ARN-based profile association algorithm implemented
in the BedrockProfileDiscovery class by comparing its output with the expected
format from raw_api_profile_test.py.
"""

import json
import logging
import os
import sys
import time
from datetime import datetime

# Add parent directories to Python path for direct imports when running directly
if __name__ == "__main__":
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)

from dbp.llm.bedrock.discovery.profiles import BedrockProfileDiscovery

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bedrock-profile-algorithm-test")

# Custom JSON encoder for datetime objects
class DateTimeJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def print_json(data, title=None):
    """Print formatted JSON data with an optional title."""
    if title:
        print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, cls=DateTimeJsonEncoder))
    print("\n" + "="*80 + "\n")

def main():
    """Main execution function."""
    logger.info("Starting test of the new profile algorithm implementation")
    
    # Get the BedrockProfileDiscovery instance
    profile_discovery = BedrockProfileDiscovery.get_instance()
    
    # Run the new algorithm to get the model-profile mapping
    start_time = time.time()
    mapping = profile_discovery.get_model_profile_mapping(refresh=True)  # Force refresh to test algorithm
    elapsed_time = time.time() - start_time
    
    logger.info(f"Profile algorithm completed in {elapsed_time:.2f} seconds")
    
    # Get statistics
    all_regions_data = mapping.get("models", {})
    total_regions = len(all_regions_data)
    total_models = 0
    total_profiles = 0
    models_with_profiles = 0
    
    # Calculate statistics
    for region, models in all_regions_data.items():
        region_model_count = len(models)
        total_models += region_model_count
        
        # Count models with profiles
        for model_id, model in models.items():
            if "referencedByInstanceProfiles" in model and model["referencedByInstanceProfiles"]:
                models_with_profiles += 1
                profile_count = len(model["referencedByInstanceProfiles"])
                total_profiles += profile_count
                logger.debug(f"Model {model_id} in {region} has {profile_count} profiles")
    
    # Print statistics
    logger.info(f"Total regions: {total_regions}")
    logger.info(f"Total models: {total_models}")
    logger.info(f"Total models with profiles: {models_with_profiles}")
    logger.info(f"Total profiles linked to models: {total_profiles}")
    
    # Save results to file for comparison
    output_file = "new_algorithm_profile_mapping.json"
    with open(output_file, 'w') as f:
        json.dump(mapping, f, indent=2, cls=DateTimeJsonEncoder)
    
    logger.info(f"Results saved to {output_file}")
    
    # Print sample of the mapping for quick verification
    if all_regions_data:
        sample_region = next(iter(all_regions_data))
        region_data = all_regions_data[sample_region]
        
        # Find a model with profiles to show
        sample_model = None
        for model_id, model in region_data.items():
            if "referencedByInstanceProfiles" in model and model["referencedByInstanceProfiles"]:
                sample_model = model
                break
        
        # Print sample model with profiles
        if sample_model:
            print_json({
                "sampleModel": sample_model
            }, f"Sample model with profiles from {sample_region}")
    
    logger.info("Test completed! Compare results with bedrock_model_profile_mapping.json from raw_api_profile_test.py")

if __name__ == "__main__":
    main()
