#!/usr/bin/env python3
"""
Debug script to dump the raw AWS Bedrock model and profile responses.
This helps identify exactly what fields indicate that a model requires an inference profile.
"""

import asyncio
import logging
import json
import os
import sys
import boto3
from datetime import datetime
from typing import Dict, Any

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.api_providers.aws.client_factory import AWSClientFactory
    from dbp.llm.bedrock.discovery.models import BedrockModelDiscovery
    from dbp.llm.bedrock.discovery.profiles import BedrockProfileDiscovery
    from dbp.llm.bedrock.discovery.cache import DiscoveryCache
    from dbp.llm.bedrock.discovery.latency import RegionLatencyTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bedrock-debug-script")

# Set boto3 and urllib3 loggers to WARNING level to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)


class DateTimeJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for handling datetime objects."""
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def print_json(data, title=None):
    """Pretty print JSON data with an optional title."""
    if title:
        print(f"\n=== {title} ===")
    print(json.dumps(data, indent=2, cls=DateTimeJSONEncoder))
    print("\n" + "="*80 + "\n")


async def dump_raw_model_data(region: str = "us-east-1"):
    """Dump raw AWS Bedrock model response data for a specific region."""
    print(f"Dumping raw Bedrock model data for region {region}...")
    
    # Create AWS client factory
    client_factory = AWSClientFactory.get_instance()
    
    try:
        # Get raw response from Bedrock API
        print("Getting Bedrock client...")
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        print("Calling list_foundation_models API...")
        response = bedrock_client.list_foundation_models()
        
        # Extract all model summaries
        models = response.get("modelSummaries", [])
        print(f"Found {len(models)} models in region {region}")
        
        # Filter for project supported models
        model_discovery = BedrockModelDiscovery.get_instance(
            client_factory=client_factory,
            logger=logger
        )
        project_models = model_discovery.project_supported_models
        print(f"Project supported models: {project_models}")
        
        # Filter for Nova models and one Claude model for comparison
        nova_models = []
        claude_models = []
        
        for model in models:
            model_id = model.get("modelId", "")
            
            if "amazon.nova" in model_id:
                nova_models.append(model)
            elif "anthropic.claude" in model_id and len(claude_models) < 1:
                claude_models.append(model)
        
        # Print raw model data
        print_json(nova_models[:1], f"Nova Model Raw Data (showing 1 of {len(nova_models)})")
        print_json(claude_models, "Claude Model Raw Data (for comparison)")
        
    except Exception as e:
        print(f"Error dumping model data: {str(e)}")


async def dump_raw_profile_data(regions=None):
    """Dump raw AWS Bedrock inference profile response data across multiple regions."""
    if regions is None:
        regions = ["us-east-1", "us-west-2", "eu-west-1"]
        
    print(f"Dumping raw Bedrock profile data across regions: {regions}")
    
    # Create AWS client factory
    client_factory = AWSClientFactory.get_instance()
    
    all_profiles = []
    model_profile_mapping = {}
    
    for region in regions:
        try:
            # Get raw response from Bedrock API
            print(f"\nChecking region {region}...")
            bedrock_client = client_factory.get_client("bedrock", region_name=region)
            
            response = bedrock_client.list_inference_profiles()
            
            # Extract all profile summaries
            profiles = response.get("inferenceProfileSummaries", [])
            print(f"Found {len(profiles)} profiles in region {region}")
            
            if profiles:
                # Collect model -> profile mapping
                for profile in profiles:
                    model_id = profile.get("modelId", "")
                    profile_id = profile.get("inferenceProfileId", "")
                    
                    if model_id:
                        if model_id not in model_profile_mapping:
                            model_profile_mapping[model_id] = []
                        model_profile_mapping[model_id].append({
                            "profile_id": profile_id,
                            "region": region
                        })
                
                # Save for combined reporting
                all_profiles.extend([{**p, "region": region} for p in profiles])
                
                # Show first profile only
                print_json(profiles[0], f"Sample Profile from {region}")
                
                # Get detailed information for one profile
                profile_id = profiles[0].get("inferenceProfileId")
                print(f"Getting detailed information for profile {profile_id}...")
                
                try:
                    profile_detail = bedrock_client.get_inference_profile(
                        inferenceProfileId=profile_id
                    )
                    
                    print_json(profile_detail, f"Detailed Profile Information ({region})")
                except Exception as e:
                    print(f"Error getting profile details: {str(e)}")
            
        except Exception as e:
            print(f"Error dumping profile data for {region}: {str(e)}")
    
    # Print aggregated model to profile mappings
    print("\n=== Model to Profile Mapping ===")
    print(f"Found {len(model_profile_mapping)} models with profiles")
    
    # Sort by number of profiles (descending)
    sorted_models = sorted(
        model_profile_mapping.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )
    
    for model_id, profiles in sorted_models[:5]:  # Show top 5 models by profile count
        print(f"\nModel: {model_id}")
        print(f"  Profiles: {len(profiles)}")
        for idx, profile in enumerate(profiles[:3]):  # Show first 3 profiles
            print(f"  {idx+1}. {profile['profile_id']} (region: {profile['region']})")
        if len(profiles) > 3:
            print(f"  ... and {len(profiles) - 3} more profiles")


async def dump_debugged_model_scan(region: str = "us-east-1"):
    """Dump the BedrockModelDiscovery._scan_region result with debugging."""
    print(f"Debugging BedrockModelDiscovery._scan_region for region {region}...")
    
    # Create core components
    cache = DiscoveryCache()
    latency_tracker = RegionLatencyTracker(cache=cache)
    client_factory = AWSClientFactory.get_instance()
    
    # Create model discovery with debug logging
    model_discovery = BedrockModelDiscovery.get_instance(
        cache=cache,
        latency_tracker=latency_tracker, 
        client_factory=client_factory,
        logger=logger
    )
    
    # Call _scan_region directly
    print(f"Calling _scan_region for {region}...")
    models = model_discovery._scan_region(region)
    
    # Filter for Nova and Claude models
    nova_models = [m for m in models if "amazon.nova" in m.get("modelId", "")]
    claude_models = [m for m in models if "anthropic.claude" in m.get("modelId", "")][:1]
    
    # Print results
    print_json(nova_models[:2], f"Nova Models After Scanning (showing 2 of {len(nova_models)})")
    print_json(claude_models, "Claude Model After Scanning (for comparison)")


async def main():
    """Run all debug functions."""
    print("===== Bedrock Debug Script =====")
    
    region = "us-east-1"
    
    # First dump raw model data
    await dump_raw_model_data(region)
    
    # Then dump raw profile data across multiple regions
    await dump_raw_profile_data(["us-east-1", "us-west-2"])
    
    # Finally debug model scanning
    await dump_debugged_model_scan(region)


if __name__ == "__main__":
    asyncio.run(main())
