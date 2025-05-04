#!/usr/bin/env python3
"""
Example demonstrating prompt caching with Amazon Bedrock models.

This script shows:
1. How to check if a model supports prompt caching
2. How to enable prompt caching for a model
3. How to mark cache points in conversations
4. How to use the marked messages in API calls
5. How to use model discovery to find the best region for a model
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional

from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
from dbp.llm.bedrock.enhanced_base import ModelCapability
from dbp.llm.bedrock.client_factory import BedrockClientFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("prompt_caching_example")

def get_best_region_for_model(model_id: str) -> Optional[str]:
    """Find the best region for a specific model using BedrockModelDiscovery."""
    discovery = BedrockModelDiscovery.get_instance()
    best_regions = discovery.get_best_regions_for_model(model_id)
    
    if not best_regions:
        logger.warning(f"No regions found for model {model_id}")
        return None
        
    best_region = best_regions[0]
    logger.info(f"Best region for model {model_id}: {best_region}")
    return best_region


async def run_without_caching(model_id: str) -> float:
    """Run a sample conversation without caching and measure time."""
    # Find the best region for this model
    region = get_best_region_for_model(model_id)
    
    # Create client using factory - add debug info to trace modelId issue
    client = BedrockClientFactory.create_client(
        model_id=model_id, 
        region_name=region, 
        logger=logger
    )
    
    # Debug output to check if inference profile is being used
    if hasattr(client, 'inference_profile_arn') and client.inference_profile_arn:
        logger.info(f"DEBUG: Client has inference profile ARN: {client.inference_profile_arn}")
    await client.initialize()
    
    # Disable caching explicitly
    client.enable_prompt_caching(False)
    
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in AWS services."},
        {"role": "user", "content": "What is Amazon Bedrock prompt caching?"}
    ]
    
    start_time = time.time()
    
    # Process the conversation
    result = ""
    async for chunk in client.stream_chat(messages):
        if "delta" in chunk and "text" in chunk["delta"]:
            result += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"Without caching - Response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(result)} characters")
    
    return elapsed_time

async def run_with_caching(model_id: str) -> float:
    """Run a sample conversation with caching and measure time."""
    # Find the best region for this model
    region = get_best_region_for_model(model_id)
    
    # Create client using factory
    client = BedrockClientFactory.create_client(
        model_id=model_id, 
        region_name=region, 
        logger=logger
    )
    await client.initialize()
    
    # Check if model supports caching
    supports_caching = client.has_capability(ModelCapability.PROMPT_CACHING)
    logger.info(f"Model {model_id} supports prompt caching: {supports_caching}")
    
    # Enable caching if supported
    caching_enabled = client.enable_prompt_caching(True)
    logger.info(f"Prompt caching enabled: {caching_enabled}")
    
    # Create messages with static content at the beginning for better caching
    messages = [
        {"role": "system", "content": "You are a helpful assistant specializing in AWS services."},
        {"role": "user", "content": "What is Amazon Bedrock prompt caching?"}
    ]
    
    # Mark a cache point
    result = client.mark_cache_point(messages)
    logger.info(f"Cache point status: {result['status']}")
    logger.info(f"Cache ID: {result['cache_id']}")
    
    start_time = time.time()
    
    # Process the conversation with cache-enabled messages
    response = ""
    async for chunk in client.stream_chat(result["messages"]):
        if "delta" in chunk and "text" in chunk["delta"]:
            response += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"With caching - First run response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(response)} characters")
    
    # Run second time with same messages to see caching effect
    logger.info("Running second time with same messages...")
    start_time = time.time()
    
    second_response = ""
    async for chunk in client.stream_chat(result["messages"]):
        if "delta" in chunk and "text" in chunk["delta"]:
            second_response += chunk["delta"]["text"]
    
    elapsed_time = time.time() - start_time
    logger.info(f"With caching - Second run response time: {elapsed_time:.2f} seconds")
    logger.info(f"Response length: {len(second_response)} characters")
    
    return elapsed_time

async def compare_performance(model_id: str) -> Dict[str, float]:
    """Compare performance with and without caching."""
    logger.info(f"Testing prompt caching performance with model {model_id}")
    
    # Run without caching first
    time_without_caching = await run_without_caching(model_id)
    
    # Wait a moment
    await asyncio.sleep(1)
    
    # Run with caching
    time_with_caching_first = await run_with_caching(model_id)
    
    return {
        "without_caching": time_without_caching,
        "with_caching_first": time_with_caching_first
    }

def find_best_caching_model() -> Optional[str]:
    """Find a model that supports prompt caching and is available."""
    discovery = BedrockModelDiscovery.get_instance()
    
    # Get models that support caching
    caching_status = discovery.get_prompt_caching_support_status()
    caching_models = [model for model, supported in caching_status.items() if supported]
    
    if not caching_models:
        logger.warning("No models with prompt caching support found")
        return None
    
    # Check which models are available in their best regions
    for model in caching_models:
        best_regions = discovery.get_best_regions_for_model(model)
        if best_regions:
            logger.info(f"Selected model {model} in region {best_regions[0]}")
            return model
    
    logger.warning("No available models with prompt caching support found")
    return None

async def main():
    """Main entry point."""
    try:
        # Find the best model with prompt caching support
        model_id = find_best_caching_model()
        if not model_id:
            logger.error("No suitable model found for prompt caching demonstration")
            return
            
        # Get the best region for this model
        region = get_best_region_for_model(model_id)
        
        # Create client using factory
        client = BedrockClientFactory.create_client(
            model_id=model_id, 
            region_name=region, 
            logger=logger
        )
        await client.initialize()
        
        # Show models that support prompt caching
        discovery = client._model_discovery
        if discovery:
            status = discovery.get_prompt_caching_support_status()
            logger.info("Models with prompt caching support:")
            for model, supported in status.items():
                if supported:
                    logger.info(f"- {model}")
        
        # Compare performance
        results = await compare_performance(model_id)
        
        logger.info("\nPerformance Summary:")
        logger.info(f"Without caching: {results['without_caching']:.2f} seconds")
        logger.info(f"With caching (first run): {results['with_caching_first']:.2f} seconds")
        
    except Exception as e:
        logger.error(f"Error: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
