###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Provides scanning utilities for AWS Bedrock models and inference profiles.
# Centralizes scanning functionality to enable combined discovery operations
# and reduce code duplication between model and profile discovery.
###############################################################################
# [Source file design principles]
# - Single responsibility for each function
# - Consistent error handling across scanning operations
# - Thread safety for concurrent operations
# - Latency measurement and optimization
# - Cache-first approach for performance
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must minimize AWS API calls through effective caching
# - Must handle AWS credential management securely
# - Must be backward compatible with existing discovery behavior
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# codebase:src/dbp/llm/bedrock/discovery/cache.py
# codebase:src/dbp/llm/bedrock/discovery/latency.py
# system:boto3
# system:botocore.exceptions
# system:time
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-03T17:21:51Z : Initial implementation by CodeAssistant
# * Created scanning functions extracted from discovery classes
# * Implemented combined model and profile scanning
# * Added consistent error handling
###############################################################################

import logging
import time
from typing import Dict, List, Optional, Any, Tuple

import boto3
import botocore.exceptions

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker


def scan_region_for_models(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    project_supported_models: List[str],
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Scan a specific region for available Bedrock models, measuring API latency.
    Prioritizes project-supported models for caching and metadata retention.
    
    [Design principles]
    - Complete model discovery
    - Latency measurement for region optimization
    - Robust error handling
    - Full metadata extraction
    - Project-focused model prioritization
    
    [Implementation details]
    - Creates regional Bedrock client using factory
    - Measures API response time
    - Records latency metrics
    - Extracts complete model attributes
    - Filters for active models only
    - Prioritizes project-supported models for caching
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        latency_tracker: RegionLatencyTracker instance
        project_supported_models: List of model IDs supported by project
        logger: Logger instance
        
    Returns:
        List of dicts with model information in the region
    """
    models = []
    all_models = []
    project_models = []
    start_time = time.time()
    
    try:
        # Get Bedrock client for this region
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # List available foundation models
        response = bedrock_client.list_foundation_models()
        
        # Calculate and record latency
        latency = time.time() - start_time
        latency_tracker.update_latency(region, latency)
        
        # Extract model information
        for model_summary in response.get("modelSummaries", []):
            # Check if model is active
            model_status = model_summary.get("modelLifecycle", {}).get("status")
            if model_status != "ACTIVE":
                continue
            
            # Extract model attributes
            model_id = model_summary["modelId"]
            
            # Create basic model info dictionary
            model_info = {
                "modelId": model_id,
                "modelName": model_summary.get("modelName", ""),
                "provider": model_summary.get("providerName", ""),
                "capabilities": [],
                "status": model_status,
                "requiresInferenceProfile": False  # Default assumption
            }
            
            # Extract capabilities if available
            if "outputModalities" in model_summary:
                model_info["capabilities"].extend(model_summary["outputModalities"])
            
            # Extract inference types and determine if profile is required
            on_demand_supported = False
            provisioned_supported = False
            
            if "inferenceTypes" in model_summary:
                for inference_type in model_summary["inferenceTypes"]:
                    if inference_type == "ON_DEMAND":
                        on_demand_supported = True
                        model_info["capabilities"].append("on-demand")
                    elif inference_type == "PROVISIONED":
                        provisioned_supported = True
                        model_info["capabilities"].append("provisioned")
            
            # If a model supports provisioned but not on-demand, it requires an inference profile
            if provisioned_supported and not on_demand_supported:
                model_info["requiresInferenceProfile"] = True
                logger.debug(f"Model {model_id} requires an inference profile")
            
            all_models.append(model_info)
            
            # Check if this is a project-supported model
            model_base_id = model_id.split(":")[0]
            is_supported = any(
                model_id.startswith(supported_id.split(":")[0]) 
                for supported_id in project_supported_models
            )
            
            if is_supported:
                project_models.append(model_info)
        
        total_models = len(all_models)
        project_model_count = len(project_models)
        
        logger.info(f"Found {total_models} active models in region {region}, {project_model_count} supported by project")
        
        # If we found project models, return only those for caching
        # Otherwise return all models (for discovery purposes)
        models = project_models if project_models else all_models
        
        return models
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == "UnrecognizedClientException":
            logger.warning(f"Bedrock is not available in region {region}")
        else:
            logger.warning(f"Error scanning region {region}: {error_code} - {error_message}")
        
        return []
    except Exception as e:
        logger.warning(f"Unexpected error scanning region {region}: {str(e)}")
        return []


def scan_region_for_profiles(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Scan a region for all available Bedrock inference profiles, measuring API latency.
    Collects comprehensive profile metadata for each profile found.
    
    [Design principles]
    - Complete profile discovery
    - Latency measurement
    - Robust error handling
    - Complete metadata extraction
    - Model-to-profile mapping
    
    [Implementation details]
    - Creates regional Bedrock client using factory
    - Measures API response time
    - Records latency metrics
    - Extracts complete profile attributes
    - Maps model ARNs to profiles
    - Returns fully populated profile information
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        latency_tracker: RegionLatencyTracker instance
        logger: Logger instance
        
    Returns:
        List of dicts with profile information in the region
    """
    try:
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # Measure latency
        start_time = time.time()
        response = bedrock_client.list_inference_profiles()
        latency = time.time() - start_time
        latency_tracker.update_latency(region, latency)
        
        profiles = []
        model_arn_to_profiles = {}  # Map model ARNs to profiles
        
        # Process all profile summaries
        for profile_summary in response.get("inferenceProfileSummaries", []):
            profile_info = {
                "inferenceProfileId": profile_summary.get("inferenceProfileId"),
                "inferenceProfileName": profile_summary.get("inferenceProfileName", ""),
                "inferenceProfileArn": profile_summary.get("inferenceProfileArn"),
                "description": profile_summary.get("description", ""),
                "status": profile_summary.get("status", ""),
                "type": profile_summary.get("type", ""),
                "region": region,
                "models": profile_summary.get("models", [])
            }
            
            # Add profile to list
            profiles.append(profile_info)
            
            # Map models to this profile
            model_arns = []
            for model_ref in profile_summary.get("models", []):
                model_arn = model_ref.get("modelArn")
                if model_arn:
                    model_arns.append(model_arn)
                    
                    # Extract model ID from ARN
                    model_id_from_arn = model_arn.split("/")[-1] if model_arn else None
                    
                    if model_id_from_arn:
                        # Add this profile to the model ARN mapping
                        if model_id_from_arn not in model_arn_to_profiles:
                            model_arn_to_profiles[model_id_from_arn] = []
                        
                        model_arn_to_profiles[model_id_from_arn].append({
                            "profileId": profile_info["inferenceProfileId"],
                            "profileArn": profile_info["inferenceProfileArn"],
                            "region": region
                        })
            
            # Save model ARNs as part of the profile info
            profile_info["modelArns"] = model_arns
        
        logger.info(f"Found {len(profiles)} inference profiles in region {region}")
        
        return profiles
        
    except Exception as e:
        logger.warning(f"Error scanning profiles in region {region}: {str(e)}")
        return []


def scan_region_combined(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    project_supported_models: List[str],
    cache: DiscoveryCache,
    logger: logging.Logger
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    [Function intent]
    Scan a region for both Bedrock models and inference profiles in a single operation,
    optimizing API calls and thread usage while ensuring complete discovery.
    
    [Design principles]
    - Efficient combined scanning
    - Conditional profile scanning
    - Complete error handling
    - Comprehensive caching
    - Thread-efficient operation
    
    [Implementation details]
    - Creates a single Bedrock client for the region
    - Measures and records API latency
    - Scans for models first
    - Only scans for profiles if needed based on model requirements
    - Updates cache for both models and profiles
    - Returns tuple of (models, profiles)
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        latency_tracker: RegionLatencyTracker instance
        project_supported_models: List of model IDs supported by project
        cache: DiscoveryCache instance
        logger: Logger instance
        
    Returns:
        Tuple of (models, profiles) lists
    """
    models = []
    profiles = []
    
    try:
        # Get Bedrock client for this region
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # 1. Scan for models
        models = scan_region_for_models(region, client_factory, latency_tracker, project_supported_models, logger)
        
        # 2. Scan for profiles
        try:
            profiles = scan_region_for_profiles(region, client_factory, latency_tracker, logger)
        except Exception as e:
            logger.warning(f"Error scanning profiles in region {region}: {str(e)}")
    
        # Return models and profiles
        return models, profiles
        
    except Exception as e:
        logger.warning(f"Error scanning region {region}: {str(e)}")
        return [], []
