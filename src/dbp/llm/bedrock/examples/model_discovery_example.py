#!/usr/bin/env python3
"""
Example demonstrating the AWS Bedrock model discovery mechanism integrated with BedrockBase.

This example shows:
1. Initializing BedrockBase with model discovery enabled
2. Finding optimal regions for a model
3. Automatic region fallback when a model is not available
4. Specifying preferred regions for model selection

Usage:
    python model_discovery_example.py
"""

import asyncio
import logging
import json
import os
import sys
from typing import List, Dict, Any

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.base import BedrockBase
    from dbp.llm.bedrock.model_discovery import BedrockModelDiscovery
else:
    # Relative imports when used as part of the package
    from ..base import BedrockBase
    from ..model_discovery import BedrockModelDiscovery


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bedrock-model-discovery-example")


async def print_model_availability(model_id: str):
    """Print availability information about a specific Bedrock model."""
    print(f"\n=== Model Availability for {model_id} ===")
    
    # Create discovery instance
    discovery = BedrockModelDiscovery(logger=logger)
    
    # Scan all regions for available models
    print("Scanning all AWS regions for Bedrock models...")
    region_models = discovery.scan_all_regions()
    
    # Find regions where the model is available
    available_regions = discovery.get_model_regions(model_id)
    print(f"Model is available in {len(available_regions)} regions: {', '.join(available_regions)}")
    
    # Check availability with preferred regions
    preferred_regions = ["us-east-1", "eu-west-1", "ap-southeast-2"]
    print(f"\nChecking best regions with preferences: {preferred_regions}")
    best_regions = discovery.get_best_regions_for_model(
        model_id,
        preferred_regions=preferred_regions
    )
    print(f"Best regions (in order): {', '.join(best_regions)}")


async def client_with_discovery():
    """Demonstrate using BedrockBase with model discovery enabled."""
    print("\n=== BedrockBase with Model Discovery ===")
    
    # Claude 3 Haiku model ID
    model_id = "anthropic.claude-3-haiku-20240307-v1:0"
    
    # Non-preferred region where model might not be available
    initial_region = "ap-south-1"  # Mumbai
    
    # Create client with model discovery enabled
    print(f"Creating client for {model_id} in initial region {initial_region}")
    print("Model discovery is enabled with preferred regions: us-east-1, us-west-2")
    
    client = BedrockBase(
        model_id=model_id,
        region_name=initial_region,
        logger=logger,
        use_model_discovery=True,
        preferred_regions=["us-east-1", "us-west-2"]
    )
    
    try:
        # Initialize client - this will trigger model discovery if needed
        print("Initializing client (will use model discovery)...")
        await client.initialize()
        
        print(f"Client initialized successfully in region: {client.region_name}")
        
        # Get best regions information
        best_regions = client.get_best_regions_for_model()
        print(f"Best regions for {model_id}: {', '.join(best_regions)}")
        
        # Define the test prompt
        test_prompt = "What is Amazon Bedrock?"
        
        # Send the test prompt to the model
        print("\nSending test prompt to model...")
        print(f"PROMPT: {test_prompt}")
        print("\nSTREAMING RESPONSE:")
        print("-------------------------------------------")
        
        response_text = ""
        chunk_count = 0
        
        # Use streaming API to demonstrate the model works, displaying each chunk as it arrives
        async for chunk in client.stream_generate(test_prompt):
            if chunk["type"] == "content_block_delta" and "delta" in chunk:
                if "text" in chunk["delta"]:
                    text = chunk["delta"]["text"]
                    response_text += text
                    # Print each chunk immediately to show streaming behavior
                    print(text, end="", flush=True)
                    chunk_count += 1
        
        print("\n-------------------------------------------")
        print(f"\nReceived {len(response_text)} characters in {chunk_count} chunks")
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        # Shutdown client
        await client.shutdown()


async def main():
    """Run all examples."""
    print("===== Bedrock Model Discovery Examples =====")
    
    # Standard models to check
    claude_model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    
    # Print model availability
    await print_model_availability(claude_model_id)
    
    # Demonstrate client with discovery
    await client_with_discovery()


if __name__ == "__main__":
    asyncio.run(main())
