#!/usr/bin/env python3
"""
Example demonstrating the AWS Bedrock model discovery mechanism integrated with BedrockBase.

This example shows:
1. Initializing BedrockBase with model discovery enabled
2. Finding optimal regions for a model
3. Automatic region fallback when a model is not available
4. Specifying preferred regions for model selection
5. Working with inference profiles

Usage:
    python model_discovery_example.py
"""

import asyncio
import logging
import json
import os
import sys
from datetime import datetime
from typing import List, Dict, Any

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.llm.bedrock.base import BedrockBase
    from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
    from dbp.llm.bedrock.discovery.cache import DiscoveryCache
    from dbp.llm.bedrock.discovery.latency import RegionLatencyTracker
else:
    # Relative imports when used as part of the package
    from ..base import BedrockBase
    from ..discovery.models import BedrockModelDiscovery
    from ..discovery.cache import DiscoveryCache
    from ..discovery.latency import RegionLatencyTracker


# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG for detailed output including cache and model discovery operations
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("bedrock-model-discovery-example")

# Set boto3 and urllib3 loggers to WARNING level to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

# Ensure cache and model discovery loggers are set to DEBUG level
logging.getLogger('dbp.llm.bedrock.discovery.cache').setLevel(logging.DEBUG)
logging.getLogger('dbp.llm.bedrock.discovery.models').setLevel(logging.DEBUG)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""
    
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


async def print_model_availability(model_id: str):
    """Print availability information about a specific Bedrock model."""
    print(f"\n=== Model Availability for {model_id} ===")
    
    # Get model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Find regions where the model is available
    available_regions = model_discovery.get_model_regions(model_id)
    print(f"Model is available in {len(available_regions)} regions: {', '.join(available_regions)}")
    
    # Check availability with preferred regions
    preferred_regions = ["us-east-1", "eu-west-1", "ap-southeast-2"]
    print(f"\nChecking best regions with preferences: {preferred_regions}")
    best_regions = model_discovery.get_best_regions_for_model(
        model_id,
        preferred_regions=preferred_regions
    )
    print(f"Best regions (in order): {', '.join(best_regions)}")
    
    # Check for inference profiles
    print("\n=== Inference Profiles ===")
    
    # Get the model with profile information
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


async def client_with_discovery():
    """Demonstrate using BedrockBase with model discovery for all project supported models."""
    print("\n=== Testing All Project Supported Models with 3-Shot Conversation ===")
    
    # Get model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Get project-supported models
    project_models = model_discovery.project_supported_models
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
    
    # Test each project model with a 3-shot conversation
    for model_id in sorted(project_models):
        print(f"\n{'='*80}")
        print(f"TESTING MODEL: {model_id}")
        print(f"{'='*80}")
        
        try:
            # Get models and profiles from cache
            print(f"Getting models and profiles for {model_id} from cache...")
            
            # Use model_discovery to get models and profiles (cache-only)
            region_models = model_discovery.scan_all_regions()
            
            # Check each region for the model and its profiles
            for bedrock_region, models in region_models.items():
                # Find our model in the returned models
                for model in models:
                    if model.get("modelId") == model_id:
                        # Check if this model has associated profiles
                        profiles = model.get("referencedByInstanceProfiles", [])
                        print(f"  Region {bedrock_region}: Found {len(profiles)} profiles for {model_id}")
                        
                        # Print profile details
                        for p in profiles:
                            print(f"    - {p.get('inferenceProfileId')}: {p.get('inferenceProfileName', 'No name')}")
            
            # Now try to get specific model data with the new get_model method
            print(f"Getting complete model data for {model_id}...")
            model_data = model_discovery.get_model(model_id)
            
            # Extract profiles from model data
            inference_profile_id = None
            if model_data and "referencedByInstanceProfiles" in model_data:
                profiles = model_data["referencedByInstanceProfiles"]
                if profiles:
                    profile_ids = [p.get("inferenceProfileId") for p in profiles if "inferenceProfileId" in p]
                    print(f"Found profiles: {', '.join(profile_ids)}")
                    inference_profile_id = profile_ids[0] if profile_ids else None
                    
                    if inference_profile_id:
                        print(f"Model requires an inference profile, using: {inference_profile_id}")
            
            # Create client with model discovery enabled
            print(f"Creating client in initial region {initial_region}")
            print(f"Model discovery is enabled with preferred regions: {', '.join(preferred_regions)}")
            
            client = BedrockBase(
                model_id=model_id,
                region_name=initial_region,
                logger=logger,
                use_model_discovery=True,
                preferred_regions=preferred_regions,
                inference_profile_id=inference_profile_id
            )
            
            # Initialize client - this will trigger model discovery if needed
            print("Initializing client (will use model discovery)...")
            await client.initialize()
            
            print(f"Client initialized successfully in region: {client.region_name}")
            
            # Get best regions information
            best_regions = client.get_best_regions_for_model()
            print(f"Best regions for {model_id}: {', '.join(best_regions)}")
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
            
            # Add assistant response to conversation for next turn
            conversation.append({"role": "assistant", "content": response_text})
        
        # Shutdown client
        await client.shutdown()
        print(f"\nFinished testing model: {model_id}")


async def check_inference_profiles():
    """Demonstrate discovery and retrieval of inference profiles."""
    print("\n=== Inference Profile Discovery ===")
    
    # Get model discovery instance
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Get models and profiles from cache
    print("Getting models and profiles from cache...")
    region_models = model_discovery.scan_all_regions()
    
    # Find a model with inference profiles
    model_with_profiles = None
    profile_count = 0
    profile_region = None
    
    # Check each region for profiles using the model_discovery scan
    model_with_profiles_map = {}
    
    for region, models in region_models.items():
        # Check for models with profiles in this region
        for model in models:
            model_id = model.get("modelId")
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
        
        # Get the full model data
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


async def display_project_supported_models():
    """Display the availability of all project-supported models across regions."""
    print("\n=== Project-Supported Models Availability ===")
    
    # Create discovery components
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Get project-supported models
    project_models = model_discovery.project_supported_models
    if not project_models:
        print("No project-supported models found!")
        return
    
    print(f"Found {len(project_models)} project-supported models:")
    for model_id in sorted(project_models):
        print(f"  - {model_id}")
    
    print("\nChecking availability across regions...")
    
    # Scan all regions once to populate cache
    region_models = model_discovery.scan_all_regions()

    # Print model details for debugging
    print("\nModel Requirements Analysis:")
    print("-" * 100)
    print(f"{'Model ID':<40} | {'On-Demand':<10} | {'Provisioned':<12} | {'Requires Profile':<16}")
    print("-" * 100)
    
    # Check all models in all regions
    for region, models in region_models.items():
        for model in models:
            model_id = model.get("modelId", "Unknown")
            # Check if this is a project-supported model
            for project_model_id in project_models:
                if model_id == project_model_id or model_id.startswith(project_model_id.split(":")[0]):
                    capabilities = model.get("capabilities", [])
                    on_demand = "on-demand" in capabilities
                    provisioned = "provisioned" in capabilities
                    requires_profile = model.get("requiresInferenceProfile", False)
                    
                    print(f"{model_id:<40} | {str(on_demand):<10} | {str(provisioned):<12} | {str(requires_profile):<16}")
                    break
    
    print("-" * 100)
    
    # For each project model, check availability and best regions
    print("\nAvailability Summary:")
    print("-" * 50)
    print(f"{'Model ID':<40} | {'Available Regions':<30} | {'Best Region'}")
    print("-" * 100)
    
    for model_id in sorted(project_models):
        # Get regions where this model is available
        available_regions = model_discovery.get_model_regions(model_id)
        
        # Get best region (taking into account latency)
        best_regions = model_discovery.get_best_regions_for_model(model_id)
        best_region = best_regions[0] if best_regions else "N/A"
        
        # Format for display
        short_model_id = model_id.split(":")[0]
        regions_str = ", ".join(available_regions[:3])
        if len(available_regions) > 3:
            regions_str += f" +{len(available_regions)-3} more"
            
        print(f"{short_model_id:<40} | {regions_str:<30} | {best_region}")
    
    print("-" * 100)

async def display_region_model_availability():
    """Display which models are available in each region."""
    print("\n=== Model Availability by Region ===")
    
    # Create discovery components
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Get all models across regions
    print("Retrieving model availability across all regions...")
    region_models = model_discovery.scan_all_regions()
    
    # Display models by region
    for region, models in sorted(region_models.items()):
        print(f"\nRegion: {region} - {len(models)} models available:")
        
        # Group by provider for better organization
        providers = {}
        for model in models:
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
    """Run all examples."""
    print("===== Bedrock Model Discovery Examples =====")
    
    # Create discovery to get project-supported models
    model_discovery = BedrockModelDiscovery.get_instance()
    
    # Force a rescan to ensure we get fresh data
    print("Forcing a complete model rescan to ensure fresh results...")
    # Use force_rescan parameter to clear cache and perform a fresh scan
    region_models = model_discovery.scan_all_regions(force_rescan=True)
    print(f"Rescan complete. Found models in {len(region_models)} regions")
    
    # Get project-supported models
    project_models = model_discovery.project_supported_models
    if not project_models:
        print("No project-supported models found!")
        return
        
    # Display project-supported models availability first
    await display_project_supported_models()
    
    # Test all project-supported models with 3-shot conversation
    await client_with_discovery()
    
    # Additional examples
    print("\n\n===== Additional Examples =====")
    
    # Display model availability by region
    await display_region_model_availability()
    
    # Use the first project model for detailed availability example
    example_model_id = sorted(project_models)[0]
    
    # Print model availability
    await print_model_availability(example_model_id)
    
    # Check inference profiles
    await check_inference_profiles()


if __name__ == "__main__":
    asyncio.run(main())
