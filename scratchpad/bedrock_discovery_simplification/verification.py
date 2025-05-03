#!/usr/bin/env python3
"""
Verification script for the simplified Bedrock Model Discovery implementation.
This script demonstrates the key features of the simplified implementation:

1. Simplified initialization with BaseDiscovery
2. Integrated caching directly in BedrockModelDiscovery
3. Simplified scanning API
4. Thread-safe operations 
5. Profile association with models

Run this script to verify that all core functionality is working correctly.
"""

import sys
import os
import asyncio
import json
import threading
import logging
from typing import Dict, List, Any

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
sys.path.insert(0, project_root)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bedrock-discovery-verification")

# Import the simplified implementation
from src.dbp.llm.bedrock.discovery.models import BedrockModelDiscovery


def set_up():
    """Set up the test environment."""
    logger.info("Setting up test environment...")
    # Ensure any existing cache is cleared
    model_discovery = BedrockModelDiscovery.get_instance()
    model_discovery.clear_cache()
    logger.info("Cache cleared for clean test")


def verify_singleton_pattern():
    """Verify that the singleton pattern works correctly."""
    logger.info("Verifying singleton pattern...")
    
    # Create two instances and verify they're the same object
    discovery1 = BedrockModelDiscovery.get_instance()
    discovery2 = BedrockModelDiscovery.get_instance()
    
    assert discovery1 is discovery2, "Singleton pattern is broken - got different instances"
    logger.info("✅ Singleton pattern verified")
    
    # Verify that scan_on_init parameter works
    discovery3 = BedrockModelDiscovery.get_instance(scan_on_init=True)
    assert discovery1 is discovery3, "Singleton pattern is broken with scan_on_init parameter"
    logger.info("✅ Singleton scan_on_init parameter verified")


def verify_scanning():
    """Verify that model scanning works correctly."""
    logger.info("Verifying model scanning functionality...")
    
    # Get the model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Test with a small set of regions
    test_regions = ["us-east-1", "us-west-2"]
    
    # Scan with force_refresh to ensure we get fresh data
    result = model_discovery.scan_all_regions(regions=test_regions, force_refresh=True)
    
    # Verify the structure of the result
    assert "models" in result, "Result should contain 'models' key"
    assert isinstance(result["models"], dict), "Models should be a dictionary"
    
    # Verify each region has model data
    for region in test_regions:
        assert region in result["models"], f"Missing data for region {region}"
    
    logger.info("✅ Model scanning functionality verified")


def verify_caching():
    """Verify that integrated caching works correctly."""
    logger.info("Verifying integrated caching functionality...")
    
    # Get the model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Clear cache
    model_discovery.clear_cache()
    
    # Scan regions to populate cache
    test_regions = ["us-east-1"]
    model_discovery.scan_all_regions(regions=test_regions, force_refresh=True)
    
    # Save cache to file
    cache_file = os.path.join(os.path.dirname(__file__), "test_cache.json")
    model_discovery.save_cache_to_file(cache_file)
    
    # Verify the cache file exists
    assert os.path.exists(cache_file), "Cache file was not created"
    
    # Clear memory cache
    model_discovery.clear_cache()
    
    # Load from file
    success = model_discovery.load_cache_from_file(cache_file)
    assert success, "Failed to load cache from file"
    
    # Verify data is loaded
    result = model_discovery.scan_all_regions(regions=test_regions)
    assert test_regions[0] in result["models"], "Cache loading failed - no data for region"
    
    # Clean up
    if os.path.exists(cache_file):
        os.remove(cache_file)
    
    logger.info("✅ Integrated caching functionality verified")


def verify_thread_safety():
    """Verify that thread safety mechanisms work correctly."""
    logger.info("Verifying thread safety...")
    
    # Get the model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Create a function to update latency data concurrently
    def update_latency(region, value):
        for i in range(10):  # Do multiple updates
            model_discovery.update_latency(region, value + i * 0.01)
    
    # Create threads that update latency concurrently
    threads = []
    for i in range(5):
        region = f"region-{i}"
        t = threading.Thread(target=update_latency, args=(region, 0.1 * i))
        threads.append(t)
    
    # Start all threads
    for t in threads:
        t.start()
    
    # Wait for all threads to complete
    for t in threads:
        t.join()
    
    # Verify all regions have latency data without errors
    with model_discovery._lock:
        latency_data = model_discovery._memory_cache.get("latency", {})
    
    for i in range(5):
        region = f"region-{i}"
        assert region in latency_data, f"Missing latency data for {region}"
    
    logger.info("✅ Thread safety verified")


def verify_profile_association():
    """Verify that profile association works correctly."""
    logger.info("Verifying profile association...")
    
    # Get the model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Scan US regions to find models with profiles
    test_regions = ["us-east-1", "us-west-2"]
    model_discovery.scan_all_regions(regions=test_regions, force_refresh=True)
    
    # Get all models
    all_models = model_discovery.get_all_models()
    
    # Find a model with profiles
    model_with_profiles = None
    for model in all_models:
        if "referencedByInstanceProfiles" in model and model["referencedByInstanceProfiles"]:
            model_with_profiles = model
            break
    
    if model_with_profiles:
        model_id = model_with_profiles["modelId"]
        profiles = model_with_profiles["referencedByInstanceProfiles"]
        logger.info(f"Found model {model_id} with {len(profiles)} profiles")
        
        # Verify profile structure
        assert "inferenceProfileId" in profiles[0], "Profile should have inferenceProfileId"
        assert "inferenceProfileArn" in profiles[0], "Profile should have inferenceProfileArn"
        
        logger.info("✅ Profile association verified")
    else:
        logger.warning("⚠️ No models with profiles found - profile association test skipped")


def verify_region_selection():
    """Verify that region selection and sorting works correctly."""
    logger.info("Verifying region selection functionality...")
    
    # Get the model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Add some test latency data
    for i, region in enumerate(["us-east-1", "us-west-2", "eu-west-1"]):
        model_discovery.update_latency(region, 0.1 * (i + 1))  # us-east-1 fastest, eu-west-1 slowest
    
    # Get the best regions for a model (assume a model is available in all regions)
    preferred_regions = ["eu-west-1"]  # This should come first despite slower latency
    
    # Mock a model being available in all regions to test region sorting
    with model_discovery._lock:
        if "models" not in model_discovery._memory_cache:
            model_discovery._memory_cache["models"] = {}
        
        # Add test model to all regions
        for region in ["us-east-1", "us-west-2", "eu-west-1"]:
            if region not in model_discovery._memory_cache["models"]:
                model_discovery._memory_cache["models"][region] = {}
            model_discovery._memory_cache["models"][region]["test-model"] = {"modelId": "test-model"}
    
    best_regions = model_discovery.get_best_regions_for_model(
        "test-model", 
        preferred_regions=preferred_regions
    )
    
    # Verify preferred region is first
    assert best_regions[0] == "eu-west-1", f"Preferred region should be first, got {best_regions[0]}"
    
    # Verify remaining regions are sorted by latency (us-east-1 before us-west-2)
    assert best_regions[1] == "us-east-1", f"Expected us-east-1 as second region, got {best_regions[1]}"
    assert best_regions[2] == "us-west-2", f"Expected us-west-2 as third region, got {best_regions[2]}"
    
    logger.info("✅ Region selection functionality verified")


async def main():
    """Run all verification tests."""
    logger.info("=== Starting Bedrock Model Discovery Verification ===")
    
    # Set up the test environment
    set_up()
    
    # Run verification tests
    verify_singleton_pattern()
    verify_scanning()
    verify_caching()
    verify_thread_safety()
    verify_profile_association()
    verify_region_selection()
    
    logger.info("=== All verification tests completed successfully! ===")


if __name__ == "__main__":
    asyncio.run(main())
