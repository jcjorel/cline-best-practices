#!/usr/bin/env python3
"""
Direct AWS Bedrock API testing script for models and inference profiles.

This script directly uses boto3 to:
1. Fetch all models in us-east-1
2. Fetch all inference profiles in us-east-1
3. Filter for Nova and Claude models/profiles
4. Map inference profiles to models based on modelArns
5. Output the merged data structure

This helps understand how AWS Bedrock APIs work without any custom discovery classes.
"""

import boto3
import json
import logging
from datetime import datetime
import os
import sys

# Add parent directories to Python path for direct imports when running directly
if __name__ == "__main__":
    parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
    sys.path.insert(0, parent_dir)
    
    # Import client factory for AWS credentials
    from dbp.api_providers.aws.client_factory import AWSClientFactory

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bedrock-raw-api-test")

# Set boto3 loggers to WARNING to reduce verbosity
logging.getLogger('boto3').setLevel(logging.WARNING)
logging.getLogger('botocore').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)

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

def get_bedrock_client(service_name='bedrock', region='us-east-1'):
    """Get a boto3 client for Bedrock services."""
    # Use AWSClientFactory for credentials
    client_factory = AWSClientFactory.get_instance()
    client = client_factory.get_client(service_name, region_name=region)
    return client

def get_all_models(region='us-east-1'):
    """Get all foundation models in the specified region."""
    logger.info(f"Fetching all foundation models in {region}")
    
    bedrock_client = get_bedrock_client('bedrock', region)
    
    try:
        # Call ListFoundationModels API
        response = bedrock_client.list_foundation_models()
        models = response.get("modelSummaries", [])
        logger.info(f"Found {len(models)} models in {region}")
        return models
    except Exception as e:
        logger.error(f"Error fetching models: {str(e)}")
        return []

def get_model_details(model_id, region='us-east-1'):
    """Get detailed information about a specific model."""
    logger.info(f"Fetching details for model {model_id} in {region}")
    
    bedrock_client = get_bedrock_client('bedrock', region)
    
    try:
        # Call GetFoundationModel API
        response = bedrock_client.get_foundation_model(
            modelIdentifier=model_id
        )
        return response
    except Exception as e:
        logger.error(f"Error fetching model details: {str(e)}")
        return {}

def get_all_inference_profiles(region='us-east-1'):
    """Get all inference profiles in the specified region."""
    logger.info(f"Fetching all inference profiles in {region}")
    
    bedrock_client = get_bedrock_client('bedrock', region)
    
    try:
        # Call ListInferenceProfiles API
        response = bedrock_client.list_inference_profiles()
        profiles = response.get("inferenceProfileSummaries", [])
        logger.info(f"Found {len(profiles)} inference profiles in {region}")
        return profiles
    except Exception as e:
        logger.error(f"Error fetching inference profiles: {str(e)}")
        return []

def get_inference_profile_details(profile_id, region='us-east-1'):
    """Get detailed information about a specific inference profile."""
    logger.info(f"Fetching details for profile {profile_id} in {region}")
    
    bedrock_client = get_bedrock_client('bedrock', region)
    
    try:
        # Call GetInferenceProfile API (using the correct parameter name)
        response = bedrock_client.get_inference_profile(
            inferenceProfileIdentifier=profile_id
        )
        return response
    except Exception as e:
        logger.error(f"Error fetching profile details: {str(e)}")
        return {}

def get_all_aws_regions():
    """Get all available AWS regions using describe_regions API."""
    logger.info("Discovering all available AWS regions")
    
    # Create an EC2 client in us-east-1 to discover all regions
    client_factory = AWSClientFactory.get_instance()
    ec2_client = client_factory.get_client('ec2', region_name='us-east-1')
    
    # Call describe_regions API - will raise exception on error
    response = ec2_client.describe_regions()
    
    # Extract region names from response
    regions = [region['RegionName'] for region in response['Regions']]
    logger.info(f"Discovered {len(regions)} AWS regions")
    return regions

# Project supported models (from model client classes)
# These are the models officially supported by the project
PROJECT_SUPPORTED_MODELS = [
    # Claude models
    "anthropic.claude-3-5-haiku-20241022-v1:0",
    "anthropic.claude-3-5-sonnet-20240620-v1:0", 
    "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "anthropic.claude-3-7-sonnet-20250219-v1:0",
    
    # Nova models
    "amazon.nova-lite-v1:0",
    "amazon.nova-micro-v1:0", 
    "amazon.nova-pro-v1:0",
    "amazon.nova-premier-v1:0",
    "amazon.nova-reel-v1:0"
]

def filter_project_supported_items(items, item_type="model"):
    """
    Filter items to include only those officially supported by the project.
    Uses exact model ID matching for models and profiles that reference those models.
    """
    result = []
    
    # For models, directly match against supported model IDs
    if item_type == "model":
        for item in items:
            model_id = item.get("modelId", "")
            base_model_id = model_id.split(":")[0]  # Extract base model ID without version
            
            # Check if this exact model ID is in our supported models list
            is_supported = model_id in PROJECT_SUPPORTED_MODELS or any(
                model_id.startswith(supported_id.split(":")[0]) 
                for supported_id in PROJECT_SUPPORTED_MODELS
            )
            
            if is_supported:
                result.append(item)
    
    # For profiles, check if they reference our supported models
    else:  # item_type == "profile"
        for profile in items:
            # Extract all model ARNs referenced by this profile
            referenced_models = []
            for model_ref in profile.get("models", []):
                model_arn = model_ref.get("modelArn", "")
                if "/" in model_arn:
                    # Extract model ID from ARN (format: arn:aws:bedrock:region::foundation-model/model_id)
                    model_id = model_arn.split("/")[-1]
                    referenced_models.append(model_id)
            
            # Check if any referenced model is in our supported models list
            is_supported = any(
                model_id in PROJECT_SUPPORTED_MODELS or any(
                    model_id.startswith(supported_id.split(":")[0])
                    for supported_id in PROJECT_SUPPORTED_MODELS
                )
                for model_id in referenced_models
            )
            
            if is_supported:
                result.append(profile)
    
    return result

def map_profiles_to_models(models, profiles):
    """Map inference profiles to models based on modelArns - PURE ARN-BASED MATCHING ALGORITHM."""
    # Step 1: Create mapping of model IDs to model objects
    model_dict = {model.get("modelId"): model for model in models if model.get("modelId")}
    # Also create profile lookup dictionary
    profile_dict = {profile.get("inferenceProfileId"): profile for profile in profiles if profile.get("inferenceProfileId")}
    
    # Step 2: Extract all model IDs for quick matching later
    model_ids = set(model_dict.keys())
    
    # Print which models require inference profiles (based on metadata)
    requires_profile_models = set()
    for model_id, model in model_dict.items():
        inference_types = model.get("inferenceTypesSupported", [])
        if "INFERENCE_PROFILE" in inference_types:
            requires_profile_models.add(model_id)
    
    print(f"Found {len(requires_profile_models)} models that require inference profiles:")
    for model_id in requires_profile_models:
        print(f"  - {model_id}")
    
    # Process each profile
    profile_count = 0
    for profile in profiles:
        profile_id = profile.get("inferenceProfileId")
        if not profile_id:
            continue
            
        profile_count += 1
        print(f"\nProcessing profile {profile_count}/{len(profiles)}: {profile_id}")
        
        # Examine each model ARN in this profile
        for model_ref in profile.get("models", []):
            model_arn = model_ref.get("modelArn", "")
            if not model_arn:
                continue
                
            # Extract model ID directly from ARN
            # ARN format: arn:aws:bedrock:{region}::foundation-model/{model_id}
            arn_parts = model_arn.split("/")
            if len(arn_parts) >= 2:
                referenced_model_id = arn_parts[-1]
                
                # Debug
                print(f"  Profile references model: {referenced_model_id}")
                
                # Check if we have this model in our list
                if referenced_model_id in model_dict:
                    # Initialize referencedByInstanceProfiles array if it doesn't exist
                    if "referencedByInstanceProfiles" not in model_dict[referenced_model_id]:
                        model_dict[referenced_model_id]["referencedByInstanceProfiles"] = []
                    
                    # Only add if not already there
                    profile_already_added = any(
                        p.get("inferenceProfileId") == profile_id 
                        for p in model_dict[referenced_model_id]["referencedByInstanceProfiles"]
                    )
                    
                    if not profile_already_added:
                        # Add the complete profile data to the model
                        model_dict[referenced_model_id]["referencedByInstanceProfiles"].append(profile)
                        print(f"  → Added {profile_id} to model {referenced_model_id}")
    
    # Cross-check that all models requiring profiles have profiles
    for model_id in requires_profile_models:
        model = model_dict[model_id]
        if "referencedByInstanceProfiles" not in model or not model["referencedByInstanceProfiles"]:
            print(f"\nWARNING: Model {model_id} requires inference profile but no profile was found!")
        else:
            profiles = model["referencedByInstanceProfiles"]
            profile_ids = [p.get("inferenceProfileId") for p in profiles]
            print(f"Model {model_id} requires inference profile and has {len(profiles)} profiles: {', '.join(profile_ids)}")
    
    # Count matches and models
    models_with_profiles = sum(1 for model in model_dict.values() if "referencedByInstanceProfiles" in model and model["referencedByInstanceProfiles"])
    total_associations = sum(len(model.get("referencedByInstanceProfiles", [])) for model in model_dict.values())
    print(f"\nFound {total_associations} total profile-to-model associations")
    print(f"Found profiles for {models_with_profiles} out of {len(model_dict)} models")
    
    # For backward compatibility, also create the old mapping format
    model_to_profiles = {}
    profile_to_models = {}
    
    for model_id, model in model_dict.items():
        if "referencedByInstanceProfiles" in model and model["referencedByInstanceProfiles"]:
            model_to_profiles[model_id] = [p.get("inferenceProfileId") for p in model["referencedByInstanceProfiles"]]
            
            for profile in model["referencedByInstanceProfiles"]:
                profile_id = profile.get("inferenceProfileId")
                if profile_id:
                    if profile_id not in profile_to_models:
                        profile_to_models[profile_id] = []
                    if model_id not in profile_to_models[profile_id]:
                        profile_to_models[profile_id].append(model_id)
    
    # Return both formats
    return {
        "modelToProfiles": model_to_profiles,
        "profileToModels": profile_to_models,
        "modelsWithProfiles": [m for m in models if "referencedByInstanceProfiles" in m]
    }

def main():
    """Main execution function."""
    # Get all AWS regions
    all_regions = get_all_aws_regions()
    logger.info(f"Starting Bedrock API test across {len(all_regions)} AWS regions")
    
    # Store model data by region
    all_regions_data = {}
    processed_regions = 0
    
    # Process each AWS region
    for region in all_regions:
        try:
            logger.info(f"Processing region {region} ({processed_regions + 1}/{len(all_regions)})")
            
            # Get all models in this region
            all_models = get_all_models(region)
            if not all_models:
                logger.info(f"No Bedrock models found in {region}, skipping...")
                continue
                
            print(f"Found {len(all_models)} total models in {region}")
            
            # Filter for project supported models
            filtered_models = filter_project_supported_items(all_models, "model")
            print(f"Filtered to {len(filtered_models)} project supported models in {region}")
            
            if not filtered_models:
                logger.info(f"No project-supported models found in {region}, skipping...")
                continue
            
            # Get all inference profiles in this region
            all_profiles = get_all_inference_profiles(region)
            print(f"Found {len(all_profiles)} total inference profiles in {region}")
            
            # Filter for profiles that reference project supported models
            filtered_profiles = filter_project_supported_items(all_profiles, "profile")
            print(f"Filtered to {len(filtered_profiles)} profiles for project supported models in {region}")
            
            # Print filtered models and profiles (first region only to avoid too much output)
            if processed_regions == 0:
                print_json(filtered_models, f"Filtered Models in {region}")
                print_json(filtered_profiles, f"Filtered Profiles in {region}")
            
            # Map profiles to models
            mapping = map_profiles_to_models(filtered_models, filtered_profiles)
            if processed_regions == 0:
                print_json(mapping, f"Profile-Model Mapping in {region}")
            
            # Store this region's models in the result dictionary
            all_regions_data[region] = {model["modelId"]: model for model in filtered_models}
            
            print(f"Added {len(filtered_models)} models from {region} to output")
            print("=" * 60)
            processed_regions += 1
            
        except Exception as e:
            logger.error(f"Error processing region {region}: {str(e)}")
            print(f"Error processing region {region}: {str(e)}")
    
    # Create final structure with regions at the top level as requested
    merged_data = {
        "models": all_regions_data
    }
    
    # Write to file for easier analysis
    output_file = "bedrock_model_profile_mapping.json"
    with open(output_file, 'w') as f:
        json.dump(merged_data, f, indent=2, cls=DateTimeJsonEncoder)
    
    # Summarize the results
    total_regions = len(all_regions_data)
    total_models = sum(len(models) for models in all_regions_data.values())
    
    logger.info(f"Wrote merged data to {output_file} with {total_models} total models across {total_regions} regions")
    print(f"\nComplete merged data written to {output_file} with {total_models} total models across {total_regions} regions")

if __name__ == "__main__":
    main()
