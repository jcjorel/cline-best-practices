#!/usr/bin/env python3
"""
Optimized example demonstrating the AWS Bedrock model discovery mechanism integrated with BedrockBase.

This example shows:
1. Initializing BedrockBase with model discovery enabled
2. Finding optimal regions for a model
3. Automatic region fallback when a model is not available
4. Specifying preferred regions for model selection
5. Working with inference profiles

IMPORTANT OPTIMIZATION NOTES:
This version is optimized to avoid redundant AWS API calls by:
- Performing a single region scan and reusing the cached data
- Sharing data between functions to avoid duplicate lookups
- Reusing client instances where possible
- Minimizing force_refresh operations

Usage:
    python model_discovery_example_optimized.py
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any, Optional

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.base import BedrockBase
    from dbp.llm.bedrock.enhanced_base import EnhancedBedrockBase
    from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
else:
    # Relative imports when used as part of the package
    from ..base import BedrockBase
    from ..discovery.models import BedrockModelDiscovery


# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Set to INFO for less verbose output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bedrock-model-discovery-optimized")

# Set boto3 and urllib3 loggers to WARNING level to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Set discovery logger to INFO level (use DEBUG only when troubleshooting)
logging.getLogger('dbp.llm.bedrock.discovery.models').setLevel(logging.INFO)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def print_model_availability(model_id: str, shared_state: Dict[str, Any]):
    """Print availability information about a specific Bedrock model."""
    print(f"\n=== Model Availability for {model_id} ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Find regions where the model is available (uses cache, no API calls)
    available_regions = model_discovery.get_model_regions(model_id)
    print(f"Model is available in {len(available_regions)} regions: {', '.join(available_regions)}")
    
    # Check availability with preferred regions (uses cache, no API calls)
    preferred_regions = ["us-east-1", "eu-west-1", "ap-southeast-2"]
    print(f"\nChecking best regions with preferences: {preferred_regions}")
    best_regions = model_discovery.get_best_regions_for_model(
        model_id,
        preferred_regions=preferred_regions
    )
    print(f"Best regions (in order): {', '.join(best_regions)}")
    
    # Check for inference profiles
    print("\n=== Inference Profiles ===")
    
    # Get the model with profile information (uses cache, no API calls)
    if best_regions:
        model_data = model_discovery.get_model(model_id)
        if model_data:
            profiles = model_data.get("referencedByInstanceProfiles", [])
            
            if profiles:
                profile_ids = [p.get("inferenceProfileId") for p in profiles if "inferenceProfileId" in p]
                print(f"Model has {len(profile_ids)} inference profiles: {', '.join(profile_ids)}")
                
                # Get details for the first profile
                if profiles:
                    first_profile = profiles[0]
                    print(f"\nDetails for profile {first_profile.get('inferenceProfileId')}:")
                    print(json.dumps(first_profile, indent=2, cls=DateTimeJSONEncoder))
            else:
                print(f"Model {model_id} does not have any inference profiles")
        else:
            print(f"Could not retrieve model data for {model_id}")
    else:
        print(f"Model {model_id} is not available in any region")


async def client_with_discovery(shared_state: Dict[str, Any]):
    """Demonstrate using BedrockBase with model discovery for all project supported models."""
    print("\n=== Testing All Project Supported Models with 3-Shot Conversation ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    print(f"Found {len(project_models)} project-supported models to test")
    
    # Define conversation prompts for 3-shot conversation
    prompts = [
        "What is Amazon Bedrock?",
        "What are its key features?",
        "How does it compare to other AWS AI services?"
    ]
    
    # Non-preferred region where models might not be available
    initial_region = "ap-south-1"  # Mumbai
    preferred_regions = ["us-east-1", "us-west-2"]
    
    # For performance optimization, group models by provider/type to potentially reuse clients
    # This is a simplified approach; in a real app, you'd use more sophisticated grouping
    model_clients = {}
    
    # Test each project model with a 3-shot conversation
    for model_id in sorted(project_models):
        print(f"\n{'='*80}")
        print(f"TESTING MODEL: {model_id}")
        print(f"{'='*80}")
        
        try:
            # Get models and profiles from cache (no API calls)
            print(f"Getting models and profiles for {model_id} from cache...")
            
            # Get cached data from shared state
            region_models = shared_state.get("region_data", {})
            
            # Check each region for the model and its profiles
            profiles_found = False
            for region, region_model_dict in region_models.get("models", {}).items():
                # Find our model in the returned models
                if model_id in region_model_dict:
                    model = region_model_dict[model_id]
                    # Check if this model has associated profiles
                    profiles = model.get("referencedByInstanceProfiles", [])
                    if profiles:
                        profiles_found = True
                        print(f"  Region {region}: Found {len(profiles)} profiles for {model_id}")
                        
                        # Print profile details
                        for p in profiles:
                            print(f"    - {p.get('inferenceProfileId')}: {p.get('inferenceProfileName', 'No name')}")
            
            if not profiles_found:
                print(f"  No profiles found for {model_id} in any region")
            
            # Now try to get specific model data (uses cache, no API calls)
            print(f"Getting complete model data for {model_id} from cache...")
            model_data = model_discovery.get_model(model_id)
            
            # Check if model requires an inference profile
            requires_profile = model_data and model_data.get("requiresInferenceProfile", False)
            
            if requires_profile:
                print(f"Skipping model {model_id} as it requires an inference profile")
                # Skip models that require inference profiles for this example
                continue
                
            # Extract profiles from model data (for informational purposes only)
            inference_profile_arn = None
            if model_data and "referencedByInstanceProfiles" in model_data:
                profiles = model_data["referencedByInstanceProfiles"]
                profile_arns = []
                if profiles:
                    for p in profiles:
                        if "inferenceProfileArn" in p:
                            profile_arns.append(p["inferenceProfileArn"])
                    
                    if profile_arns:
                        print(f"Found profile ARNs: {', '.join(profile_arns)}")
                        inference_profile_arn = profile_arns[0]
                        print(f"Model requires an inference profile, using ARN: {inference_profile_arn}")
            
            # Check if we already have a suitable client we can reuse
            client_key = f"{model_id}:{inference_profile_arn}"
            client = model_clients.get(client_key)
            
            if not client:
                # Create client with model discovery enabled
                print(f"Creating new client in initial region {initial_region}")
                print(f"Model discovery is enabled with preferred regions: {', '.join(preferred_regions)}")
                
                client = EnhancedBedrockBase(
                model_id=model_id,
                region_name=initial_region,
                logger=logger,
                use_model_discovery=True,
                preferred_regions=preferred_regions,
                inference_profile_arn=inference_profile_arn
                )
                
                # Initialize client - this will trigger model discovery if needed
                print("Initializing client (will use model discovery with cached data)...")
                await client.initialize()
                
                # Store client for potential reuse
                model_clients[client_key] = client
                
                print(f"Client initialized successfully in region: {client.region_name}")
                
                # Get best regions information (from cache)
                best_regions = client.get_best_regions_for_model()
                print(f"Best regions for {model_id}: {', '.join(best_regions)}")
            else:
                print(f"Reusing existing client for {model_id}")
                # Ensure model id is set correctly
                client.model_id = model_id
        except Exception as e:
            print(f"Error initializing client for model {model_id}: {str(e)}")
            print(f"Skipping model {model_id}")
            continue
        
        # Initialize conversation context - will be built up across turns
        conversation = []
        
        # Conduct 3-shot conversation
        for turn, prompt in enumerate(prompts):
            print(f"\nTURN {turn+1} - Sending prompt: {prompt}")
            
            # Add user message to conversation
            conversation.append({"role": "user", "content": prompt})
            
            # Send prompt to model with conversation context
            print("\nSTREAMING RESPONSE:")
            print("-------------------------------------------")
            
            response_text = ""
            chunk_count = 0
            
            try:
                # Stream chat with conversation context
                async for chunk in client.stream_chat(conversation):
                    if chunk["type"] == "content_block_delta" and "delta" in chunk:
                        if "text" in chunk["delta"]:
                            text = chunk["delta"]["text"]
                            response_text += text
                            # Print each chunk immediately to show streaming behavior
                            print(text, end="", flush=True)
                            chunk_count += 1
                
                print("\n-------------------------------------------")
                print(f"Received {len(response_text)} characters in {chunk_count} chunks")
            except Exception as e:
                print("\n-------------------------------------------")
                print(f"ERROR: {str(e)}")
                print("Skipping this model due to access or configuration issues.")
                break  # Skip remaining turns for this model
            
            # Add assistant response to conversation for next turn
            conversation.append({"role": "assistant", "content": response_text})
        
        # Don't shut down the client here if we might reuse it
    
    # Clean up all clients at the end
    print("\nShutting down all clients...")
    for client_key, client in model_clients.items():
        await client.shutdown()
    print("All clients shut down successfully")


async def check_inference_profiles(shared_state: Dict[str, Any]):
    """Demonstrate discovery and retrieval of inference profiles."""
    print("\n=== Inference Profile Discovery ===")
    
    # Get model discovery instance from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get models and profiles from cache
    print("Getting models and profiles from cache...")
    region_models = shared_state.get("region_data", {})
    
    # Find a model with inference profiles
    model_with_profiles = None
    profile_count = 0
    profile_region = None
    
    # Check each region for profiles using cached data
    model_with_profiles_map = {}
    
    for region, models in region_models.get("models", {}).items():
        # Check for models with profiles in this region
        for model_id, model in models.items():
            profiles = model.get("referencedByInstanceProfiles", [])
            
            if profiles:
                # Count profiles per model
                if model_id not in model_with_profiles_map:
                    model_with_profiles_map[model_id] = {}
                
                model_with_profiles_map[model_id][region] = profiles
                
                # Update if this is the model with the most profiles
                if len(profiles) > profile_count:
                    model_with_profiles = model_id
                    profile_count = len(profiles)
                    profile_region = region
    
    if model_with_profiles:
        print(f"\nFound model {model_with_profiles} with {profile_count} inference profiles in {profile_region}")
        
        # Get the full model data (from cache, no API calls)
        model_data = model_discovery.get_model(model_with_profiles, region=profile_region)
        
        if model_data and "referencedByInstanceProfiles" in model_data:
            profiles = model_data["referencedByInstanceProfiles"]
            profile_ids = [p.get("inferenceProfileId") for p in profiles if "inferenceProfileId" in p]
            print(f"Profile IDs in {profile_region}: {', '.join(profile_ids)}")
            
            # Get details for first profile
            if profiles:
                first_profile = profiles[0]
                
                # Display profile information
                print(f"\nProfile information for {first_profile.get('inferenceProfileId')}:")
                print(json.dumps({
                    "inferenceProfileId": first_profile.get("inferenceProfileId"),
                    "inferenceProfileName": first_profile.get("inferenceProfileName", "N/A"),
                    "status": first_profile.get("status", "N/A"),
                    "provisionedThroughput": first_profile.get("provisionedThroughput", {})
                }, indent=2, cls=DateTimeJSONEncoder))
        else:
            print(f"Could not retrieve profile information for model {model_with_profiles}")
    else:
        print("No models with inference profiles found in any region")


async def display_project_supported_models(shared_state: Dict[str, Any]):
    """Display the availability of all project-supported models across regions."""
    print("\n=== Project-Supported Models Availability ===")
    
    # Get model discovery from shared state
    model_discovery = shared_state.get("model_discovery")
    
    # Get project-supported models from shared state
    project_models = shared_state.get("project_models")
    if not project_models:
        print("No project-supported models found!")
        return
    
    print(f"Found {len(project_models)} project-supported models:")
    for model_id in sorted(project_models):
        print(f"  - {model_id}")
    
    print("\nChecking availability across regions (using cached data)...")
    
    # Get cached region data from shared state
    region_data = shared_state.get("region_data", {})
    region_models = region_data.get("models", {})
    
    # For each project model, check availability and best regions
    print("\nAvailability Summary:")
    print("-" * 50)
    print(f"{'Model ID':<40} | {'Available Regions':<30} | {'Best Region'}")
    print("-" * 100)
    
    for model_id in sorted(project_models):
        # Get regions where this model is available (from cache)
        available_regions = model_discovery.get_model_regions(model_id)
        
        # Get best region (from cache)
        best_regions = model_discovery.get_best_regions_for_model(model_id)
        best_region = best_regions[0] if best_regions else "N/A"
        
        # Format for display
        short_model_id = model_id.split(":")[0]
        regions_str = ", ".join(available_regions[:3])
        if len(available_regions) > 3:
            regions_str += f" +{len(available_regions)-3} more"
            
        print(f"{short_model_id:<40} | {regions_str:<30} | {best_region}")
    
    print("-" * 100)


async def display_region_model_availability(shared_state: Dict[str, Any]):
    """Display which models are available in each region."""
    print("\n=== Model Availability by Region ===")
    
    # Get cached region data from shared state
    print("Retrieving model availability from cache...")
    region_data = shared_state.get("region_data", {})
    region_models = region_data.get("models", {})
    
    # Display models by region
    for region, models_dict in sorted(region_models.items()):
        print(f"\nRegion: {region} - {len(models_dict)} models available:")
        
        # Group by provider for better organization
        providers = {}
        for model_id, model in models_dict.items():
            provider = model.get("provider", "Unknown")
            if provider not in providers:
                providers[provider] = []
            providers[provider].append(model)
        
        # Display grouped by provider
        for provider, provider_models in sorted(providers.items()):
            print(f"  Provider: {provider}")
            # Sort models by name
            for model in sorted(provider_models, key=lambda x: x.get("modelName", "")):
                model_name = model.get("modelName", model.get("modelId", "Unknown"))
                print(f"    - {model_name}")


async def main():
    """Run all examples with optimized performance."""
    print("===== Bedrock Model Discovery Examples (OPTIMIZED) =====")
    
    # Create discovery and get project-supported models
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Check if we need to perform an initial scan (clear cache and rescan)
    print("Checking if cache is populated...")
    region_data = model_discovery.scan_all_regions()
    
    if not region_data.get("models", {}):
        print("Cache is empty or invalid. Performing a full region scan...")
        region_data = model_discovery.scan_all_regions(force_refresh=True)
        print(f"Scan complete. Found models in {len(region_data.get('models', {}))} regions")
    else:
        print(f"Using cached data. Found models in {len(region_data.get('models', {}))} regions")
    
    # Get project-supported models
    project_models = model_discovery.project_supported_models
    if not project_models:
        print("No project-supported models found!")
        return
    
    # Create shared state to pass between functions
    shared_state = {
        "model_discovery": model_discovery,
        "region_data": region_data,
        "project_models": project_models
    }
    
    # Run all examples with shared state to avoid redundant API calls
    await display_project_supported_models(shared_state)
    await client_with_discovery(shared_state)
    await display_region_model_availability(shared_state)
    
    # Use the first project model for detailed availability example
    example_model_id = sorted(project_models)[0]
    await print_model_availability(example_model_id, shared_state)
    
    # Check inference profiles using shared state
    await check_inference_profiles(shared_state)
    
    print("\nAll examples completed successfully using optimized approach.")
    print("Compare execution time with the original example to see performance improvement.")


if __name__ == "__main__":
    asyncio.run(main())
