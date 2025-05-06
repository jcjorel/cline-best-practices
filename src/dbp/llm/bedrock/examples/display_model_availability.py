#!/usr/bin/env python3
"""
Example demonstrating how to display the availability summary for AWS Bedrock models.

This script shows how to use the display_availability_summary method of BedrockModelDiscovery
to generate a formatted table showing model availability across regions.

Usage:
    python display_model_availability.py
"""

import os
import sys
import logging

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
else:
    # Relative imports when used as part of the package
    from ..discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bedrock-model-availability")

# Set discovery logger to INFO level
logging.getLogger('dbp.llm.bedrock.discovery.models_capabilities').setLevel(logging.INFO)
# Set boto3 loggers to WARNING to reduce noise
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)


def main():
    """
    Display availability summary for all supported Bedrock models.
    """
    print("Getting Bedrock model discovery instance...")
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Check if cache is populated, refresh if needed
    print("Checking model cache...")
    region_data = model_discovery.scan_all_regions()
    
    if not region_data.get("models", {}):
        print("Cache is empty. Performing a full region scan (this may take a minute)...")
        region_data = model_discovery.scan_all_regions(force_refresh=True)
    else:
        print("Using cached model data.")
    
    # Display the availability summary
    print("\n" + model_discovery.display_availability_summary())


if __name__ == "__main__":
    main()
