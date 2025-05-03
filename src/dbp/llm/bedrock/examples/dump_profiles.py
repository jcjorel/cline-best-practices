#!/usr/bin/env python3
"""
Debug script to dump all inference profiles and check what models they're associated with.
This helps to identify how inference profiles are structured and linked to models.
"""

import asyncio
import logging
import json
import os
import sys
import boto3
from datetime import datetime
from typing import Dict, List, Any

# Handle imports for both direct execution and package import
if __name__ == "__main__":
    # Add parent directories to Python path for direct imports
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import directly from the project structure
    from dbp.api_providers.aws.client_factory import AWSClientFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bedrock-profile-dump")

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


def get_bedrock_client(region: str = "us-east-1"):
    """Get a boto3 client for Bedrock in the specified region."""
    try:
        # Create AWS client factory
        client_factory = AWSClientFactory.get_instance()
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        return bedrock_client
    except Exception as e:
        logger.error(f"Error creating Bedrock client: {str(e)}")
        return None


def dump_all_profiles():
    """Dump all inference profiles in us-east-1 region only."""
    # Focus only on us-east-1 region
    region = "us-east-1"
    
    all_profiles = []
    model_to_profiles = {}
    
    print(f"Checking profiles in {region} region...")
    
    # Get Bedrock client for this region
    bedrock_client = get_bedrock_client(region)
    if not bedrock_client:
        print(f"  Could not create client for region {region}")
        return
        
    try:
        # List all inference profiles and dump the raw response
        response = bedrock_client.list_inference_profiles()
        print_json(response, "Raw List Inference Profiles Response")
        profiles = response.get("inferenceProfileSummaries", [])
        
        print(f"  Found {len(profiles)} inference profiles")
        
        # Extract and print Nova and Claude profiles
        nova_profiles = [p for p in profiles if 'nova' in p.get('inferenceProfileId', '').lower()]
        claude_profiles = [p for p in profiles if 'claude' in p.get('inferenceProfileId', '').lower()]
        
        print(f"\n== NOVA PROFILES ({len(nova_profiles)}) ==")
        for profile in nova_profiles:
            print(f"  - {profile.get('inferenceProfileId')}")
        
        print(f"\n== CLAUDE PROFILES ({len(claude_profiles)}) ==")
        for profile in claude_profiles:
            print(f"  - {profile.get('inferenceProfileId')}")
        
        for profile in profiles:
            profile["region"] = region
            all_profiles.append(profile)
            
            # Extract model info and map to profile
            profile_id = profile.get("inferenceProfileId")
            model_arns = []
            
            try:
                # Debug the parameter name
                print(f"  Getting detailed info for profile: {profile_id}")
                
                # Try to get detailed profile info with models - using correct parameter name
                detail_response = bedrock_client.get_inference_profile(
                    inferenceProfileIdentifier=profile_id  # Correct parameter name
                )
                
                # Print raw response for each profile
                if "nova" in profile_id.lower() or "claude" in profile_id.lower():
                    # Only print Nova and Claude responses to avoid overwhelming output
                    print_json(detail_response, f"Raw Profile Response for {profile_id}")
                
                if "inferenceProfile" in detail_response:
                    inference_profile = detail_response["inferenceProfile"]
                    
                    if "models" in inference_profile:
                        for model in inference_profile["models"]:
                            model_arn = model.get("modelArn", "")
                            model_id = model_arn.split("/")[-1] if model_arn else "unknown"
                            model_arns.append(model_arn)
                            
                            # Add to model-to-profile mapping
                            if model_id not in model_to_profiles:
                                model_to_profiles[model_id] = []
                                
                            model_to_profiles[model_id].append({
                                "profile_id": profile_id,
                                "region": region
                            })
                
                profile["modelArns"] = model_arns
                
            except Exception as e:
                print(f"  Error getting details for profile {profile_id}: {str(e)}")
                profile["modelArns"] = []
            
    except Exception as e:
        print(f"  Error listing profiles in region {region}: {str(e)}")
    
    # Display profile summary
    if all_profiles:
        print(f"\n\n== PROFILE SUMMARY ==")
        print(f"Found {len(all_profiles)} total profiles in region {region}")
        
        # Group by type
        profile_types = {}
        for p in all_profiles:
            p_type = p.get("type", "UNKNOWN")
            if p_type not in profile_types:
                profile_types[p_type] = []
            profile_types[p_type].append(p)
            
        for p_type, profiles in profile_types.items():
            print(f"\n== Profile Type: {p_type} ({len(profiles)} profiles) ==")
            for p in profiles[:3]:  # Show sample of profiles
                print(f"  - {p.get('inferenceProfileId')} in {p.get('region')} ({len(p.get('modelArns', []))} models)")
            if len(profiles) > 3:
                print(f"  ... and {len(profiles) - 3} more {p_type} profiles")
                
    # Display model-to-profile mapping
    if model_to_profiles:
        print(f"\n\n== MODEL TO PROFILE MAPPING ==")
        print(f"Found {len(model_to_profiles)} models with associated profiles")
        
        # Sort models by name
        sorted_models = sorted(model_to_profiles.items())
        
        # Group models by type (Nova vs Claude)
        model_groups = {
            "nova": [],
            "claude": [],
            "other": []
        }
        
        for model_id, profiles in sorted_models:
            if "nova" in model_id.lower():
                model_groups["nova"].append((model_id, profiles))
            elif "claude" in model_id.lower():
                model_groups["claude"].append((model_id, profiles))
            else:
                model_groups["other"].append((model_id, profiles))
        
        # Print each group
        for group_name, models in model_groups.items():
            if models:
                print(f"\n== {group_name.upper()} MODELS ({len(models)}) ==")
                for model_id, profiles in models:
                    print(f"\nModel: {model_id}")
                    print(f"Profiles ({len(profiles)}):")
                    for i, profile in enumerate(profiles[:5]):
                        print(f"  {i+1}. {profile['profile_id']} (region: {profile['region']})")
                    if len(profiles) > 5:
                        print(f"  ... and {len(profiles) - 5} more profiles")
        
        # Show example of a profile structure
        if all_profiles:
            first_profile = all_profiles[0]
            print_json(first_profile, "Sample Profile Structure")
            
            # Get detailed structure if available
            try:
                region = first_profile["region"]
                profile_id = first_profile["inferenceProfileId"]
                bedrock_client = get_bedrock_client(region)
                
                if bedrock_client:
                    detail_response = bedrock_client.get_inference_profile(
                        inferenceProfileIdentifier=profile_id
                    )
                    print_json(detail_response, "Detailed Profile Structure")
            except Exception as e:
                print(f"Error getting detailed profile structure: {str(e)}")


if __name__ == "__main__":
    dump_all_profiles()
