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
# system:boto3
# system:botocore.exceptions
# system:time
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-04T01:34:00Z : Integrated undocumented model availability API by CodeAssistant
# * Added integration with bedrock_availability module
# * Implemented detailed model accessibility checking 
# * Added enhanced error reporting for model access issues
# * Preserved backward compatibility with GetFoundationModel
# 2025-05-03T23:02:36Z : Simplified scan utilities by CodeAssistant
# * Consolidated multiple scan functions into a single unified function
# * Removed direct dependency on external components
# * Simplified parameter lists with sensible defaults
# * Added optional latency tracking callback
# 2025-05-03T17:21:51Z : Initial implementation by CodeAssistant
# * Created scanning functions extracted from discovery classes
# * Implemented combined model and profile scanning
# * Added consistent error handling
###############################################################################

import logging
import time
from typing import Dict, List, Optional, Any, Tuple, Callable

import boto3
import botocore.exceptions

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from ....api_providers.aws.bedrock_availability import check_model_availability


def scan_region(
    region: str,
    client_factory: AWSClientFactory,
    include_models: bool = True,
    include_profiles: bool = True,
    project_models: Optional[List[str]] = None,
    latency_callback: Optional[Callable[[str, float], None]] = None,
    logger: Optional[logging.Logger] = None
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    [Function intent]
    Scan a region for Bedrock models and/or inference profiles in a single operation,
    optimizing API calls while ensuring complete discovery.
    
    [Design principles]
    - Unified scanning interface 
    - Configurable scope (models, profiles, or both)
    - Simple parameter interface with sensible defaults
    - Optional latency tracking
    
    [Implementation details]
    - Creates a single Bedrock client for the region
    - Optionally measures and reports API latency
    - Scans for models and/or profiles based on parameters
    - Prioritizes project-supported models when project_models is provided
    - Returns models and profiles as separate lists
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        include_models: Whether to scan for models
        include_profiles: Whether to scan for profiles
        project_models: Optional list of model IDs supported by the project
        latency_callback: Optional callback function to track latency (takes region and latency in seconds)
        logger: Optional logger instance (creates one if not provided)
        
    Returns:
        Tuple of (models, profiles) lists - empty lists for disabled scan types
    """
    models = []
    profiles = []
    
    # Use provided logger or create one
    log = logger or logging.getLogger(__name__)
    
    try:
        # Verify valid region format
        if not _is_valid_region(region):
            log.warning(f"Invalid region format: {region}")
            return [], []
            
        # 1. Scan for models if requested
        if include_models:
            models = _scan_for_models(
                region, 
                client_factory, 
                project_models or [],
                latency_callback,
                log
            )
            
        # 2. Scan for profiles if requested
        if include_profiles:
            profiles = _scan_for_profiles(
                region,
                client_factory,
                latency_callback,
                log
            )
    
        return models, profiles
        
    except Exception as e:
        log.warning(f"Error scanning region {region}: {str(e)}")
        return [], []


def _scan_for_models(
    region: str,
    client_factory: AWSClientFactory,
    project_models: List[str],
    latency_callback: Optional[Callable[[str, float], None]],
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Internal function to scan a region for Bedrock models.
    
    [Design principles]
    - Single responsibility
    - Complete model discovery
    - Proper error handling
    - Project model prioritization
    
    [Implementation details]
    - Creates regional Bedrock client
    - Measures API latency
    - Extracts complete model data
    - Prioritizes project-supported models
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        project_models: List of model IDs supported by project
        latency_callback: Optional function to track latency
        logger: Logger instance
        
    Returns:
        List of model information dictionaries
    """
    all_models = []
    project_supported_models = []
    
    try:
        # Get Bedrock client for this region
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # Measure latency
        start_time = time.time()
        response = bedrock_client.list_foundation_models()
        latency = time.time() - start_time
        
        # Report latency if callback provided
        if latency_callback:
            latency_callback(region, latency)
        
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
                "requiresInferenceProfile": False,  # Default assumption
                "accessible": True  # Default to true, will verify below
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
            is_supported = any(
                model_id.startswith(supported_id.split(":")[0]) 
                for supported_id in project_models
            )
            
            if is_supported:
                project_supported_models.append(model_info)
        
        # Verify access to models by calling GetFoundationModel API and enrich with detailed model information
        models_to_check = project_supported_models if project_supported_models else all_models
        
        for model_info in models_to_check:
            model_id = model_info["modelId"]
            try:
                # Call GetFoundationModel to verify access and get detailed information
                response = bedrock_client.get_foundation_model(modelIdentifier=model_id)
                
                # Enrich model_info with the detailed model information
                if "modelDetails" in response:
                    model_details = response["modelDetails"]
                    
                    # Store the complete modelDetails in model_info
                    model_info["modelDetails"] = model_details
                    
                    # Update capabilities from the detailed info
                    if "inputModalities" in model_details:
                        model_info["inputModalities"] = model_details["inputModalities"]
                        
                    if "outputModalities" in model_details:
                        model_info["outputModalities"] = model_details["outputModalities"]
                    
                    if "inferenceTypesSupported" in model_details:
                        # Extract inference types supported
                        inference_types = model_details["inferenceTypesSupported"]
                        
                        # Check if model requires an inference profile
                        on_demand_supported = "ON_DEMAND" in inference_types
                        provisioned_supported = "PROVISIONED" in inference_types
                        
                        # If a model supports provisioned but not on-demand, it requires an inference profile
                        if provisioned_supported and not on_demand_supported:
                            model_info["requiresInferenceProfile"] = True
                            logger.debug(f"Model {model_id} requires an inference profile per detailed API")
                    
                    # Add streaming support information
                    if "responseStreamingSupported" in model_details:
                        model_info["responseStreamingSupported"] = model_details["responseStreamingSupported"]

                # Check if the model is accessible using the undocumented API endpoint
                try:
                    # Use our specialized bedrock_availability module to check model access
                    availability_result = check_model_availability(
                        model_id=model_id,
                        region=region,
                        client_factory=client_factory,
                        logger=logger
                    )
                    
                    # Update accessibility flag based on the API response
                    if "accessible" in availability_result:
                        model_info["accessible"] = availability_result["accessible"]
                        
                        # If we're marked as not accessible, log the reason
                        if not availability_result["accessible"]:
                            reasons = []
                            if availability_result.get("authorizationStatus") != "AUTHORIZED":
                                reasons.append(f"Not authorized ({availability_result.get('authorizationStatus')})")
                            if availability_result.get("entitlementAvailability") != "AVAILABLE":
                                reasons.append(f"No entitlement ({availability_result.get('entitlementAvailability')})")
                            if availability_result.get("regionAvailability") != "AVAILABLE":
                                reasons.append(f"Not available in region ({availability_result.get('regionAvailability')})")
                            if "agreementAvailability" in availability_result and availability_result["agreementAvailability"].get("status") != "AVAILABLE":
                                reasons.append(f"Agreement not available ({availability_result['agreementAvailability'].get('status')})")
                            
                            reason_str = ", ".join(reasons) if reasons else "Unknown reason"
                            logger.info(f"Model {model_id} is not accessible: {reason_str}")
                    
                    # Add detailed availability information to the model info
                    model_info["availabilityDetails"] = availability_result
                    
                except Exception as e:
                    # If the availability check fails, fallback to assuming accessible based on GetFoundationModel success
                    logger.warning(f"Error checking model availability via API: {str(e)}")
                    # The model_info["accessible"] flag remains True from GetFoundationModel success
                
            except botocore.exceptions.ClientError as e:
                error_code = e.response['Error']['Code']
                error_message = e.response['Error']['Message']
                
                if error_code == "AccessDeniedException":
                    # No access to this model
                    model_info["accessible"] = False
                    logger.info(f"No access to model {model_id} in region {region}: {error_message}")
                elif error_code == "ResourceNotFoundException":
                    # Model not found - shouldn't happen since we got it from ListFoundationModels
                    logger.warning(f"Model {model_id} not found in region {region} during detailed check")
                else:
                    # Other error, log but assume accessible
                    logger.warning(f"Error checking access to model {model_id}: {error_code} - {error_message}")
            except Exception as e:
                # Log error but don't change accessible flag
                logger.warning(f"Unexpected error checking model {model_id} details: {str(e)}")
        
        # Log discovery results
        total_models = len(all_models)
        project_model_count = len(project_supported_models)
        accessible_count = len([m for m in models_to_check if m.get("accessible", True)])
        logger.info(f"Found {total_models} active models in region {region}, {project_model_count} supported by project, {accessible_count} accessible")
        
        # If we found project models, return only those; otherwise return all models
        return project_supported_models if project_supported_models else all_models
        
    except botocore.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        
        if error_code == "UnrecognizedClientException":
            logger.warning(f"Bedrock is not available in region {region}")
        else:
            logger.warning(f"Error scanning models in region {region}: {error_code} - {error_message}")
        
        return []
    except Exception as e:
        logger.warning(f"Unexpected error scanning models in region {region}: {str(e)}")
        return []


def _scan_for_profiles(
    region: str,
    client_factory: AWSClientFactory,
    latency_callback: Optional[Callable[[str, float], None]],
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Internal function to scan a region for Bedrock inference profiles.
    
    [Design principles]
    - Single responsibility
    - Complete profile discovery
    - Proper error handling
    - Comprehensive metadata collection
    
    [Implementation details]
    - Creates regional Bedrock client
    - Measures API latency
    - Extracts complete profile data
    - Maps model ARNs to profiles
    
    Args:
        region: AWS region to scan
        client_factory: AWSClientFactory instance
        latency_callback: Optional function to track latency
        logger: Logger instance
        
    Returns:
        List of profile information dictionaries
    """
    try:
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # Measure latency
        start_time = time.time()
        response = bedrock_client.list_inference_profiles()
        latency = time.time() - start_time
        
        # Report latency if callback provided
        if latency_callback:
            latency_callback(region, latency)
        
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


def _is_valid_region(region: str) -> bool:
    """
    [Function intent]
    Check if a region name appears to be a valid AWS region format.
    
    [Design principles]
    - Simple validation without API calls
    - Basic format checking
    
    [Implementation details]
    - Checks string format
    - Validates region parts
    
    Args:
        region: Region name to check
        
    Returns:
        Boolean indicating if region format appears valid
    """
    # Basic format check
    if not region or not isinstance(region, str):
        return False
    
    # Check format like "us-west-2"
    parts = region.split('-')
    if len(parts) < 2 or len(parts) > 3:
        return False
        
    # Additional check that second part is a direction
    directions = ["east", "west", "north", "south", "central", "northeast", "northwest", 
                 "southeast", "southwest"]
    if parts[1] not in directions:
        return False
        
    # If third part exists, it should be a number
    if len(parts) == 3:
        try:
            int(parts[2])
        except ValueError:
            return False
    
    return True
