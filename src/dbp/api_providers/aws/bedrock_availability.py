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
# Provides access to the undocumented AWS Bedrock foundation-model-availability API,
# which allows checking if a user has access to specific Bedrock foundation models.
# Enables more efficient model access verification compared to standard API methods.
###############################################################################
# [Source file design principles]
# - Leverages undocumented but stable API for efficient model access checking
# - Standardized error handling and response parsing
# - Integration with AWSClientFactory for consistent credential management
# - Clear access status classification
###############################################################################
# [Source file constraints]
# - Relies on an undocumented API that may change without notice
# - Must handle all error cases gracefully
# - Must maintain compatibility with Bedrock service changes
# - Should cache results when appropriate to minimize API calls
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# system:boto3
# system:botocore
# system:urllib.parse
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-04T01:27:00Z : Initial implementation by CodeAssistant
# * Created foundation-model-availability API client
# * Implemented check_model_availability function
# * Added response parsing and error handling
# * Documented undocumented API behavior
###############################################################################

import logging
import urllib.parse
from typing import Dict, Any, Optional, List, Union

import boto3
import botocore
from botocore.exceptions import ClientError as BotocoreClientError
from botocore.auth import SigV4Auth
from botocore.awsrequest import AWSRequest
import requests

from .client_factory import AWSClientFactory
from .exceptions import (
    AWSClientError,
    AWSCredentialError,
    AWSRegionError,
    AWSServiceError
)


def check_model_availability(
    model_id: str,
    region: str,
    client_factory: Optional[AWSClientFactory] = None,
    profile_name: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    [Function intent]
    Check a Bedrock foundation model's availability using an undocumented API endpoint.
    This API provides detailed information about model access status.
    
    [Design principles]
    - Direct use of undocumented AWS API for efficiency
    - Proper AWS SigV4 authentication
    - Complete error handling
    - Detailed status reporting
    
    [Implementation details]
    - Uses AWS SigV4 auth for authenticated requests
    - Makes GET request to the foundation-model-availability endpoint
    - Parses JSON response for availability status
    - Handles various error conditions with appropriate exceptions
    - Returns structured response with access details
    
    Args:
        model_id: The Bedrock model ID to check (e.g., "anthropic.claude-3-haiku-20240307-v1:0")
        region: AWS region to check in
        client_factory: Optional AWSClientFactory instance (creates a new one if not provided)
        profile_name: AWS profile name for credentials
        credentials: Explicit AWS credentials (overrides profile_name)
        logger: Optional logger instance
        
    Returns:
        Dict with complete availability status information:
        {
            "agreementAvailability": {
                "errorMessage": None or str,
                "status": "AVAILABLE" or other status
            },
            "authorizationStatus": "AUTHORIZED" or other status,
            "entitlementAvailability": "AVAILABLE" or other status,
            "modelId": str (the model ID without version),
            "regionAvailability": "AVAILABLE" or other status,
            "accessible": bool (True if fully accessible)
        }
        
    Raises:
        AWSCredentialError: For credential-related issues
        AWSRegionError: For region-related issues
        AWSServiceError: For service-specific errors
        AWSClientError: For general client errors
    """
    # Use the provided logger or create a new one
    log = logger or logging.getLogger(__name__)
    
    # Use the provided client factory or create a new one
    factory = client_factory or AWSClientFactory.get_instance()
    
    # Normalize model ID (remove version suffix if present)
    # base_model_id = model_id.split(':')[0] if ':' in model_id else model_id
    url_encoded_model_id = urllib.parse.quote(model_id)
    
    # Construct the API endpoint URL
    endpoint_url = f"https://bedrock.{region}.amazonaws.com/foundation-model-availability/{url_encoded_model_id}"
    
    try:
        # Get a boto3 session with appropriate credentials
        session = factory.get_session(region, profile_name, credentials)
        
        # Get credentials from the session
        aws_credentials = session.get_credentials()
        if aws_credentials is None:
            raise AWSCredentialError(
                "No AWS credentials available",
                region_name=region
            )
        
        # Create a request object for signing
        request = AWSRequest(
            method="GET",
            url=endpoint_url,
            data=None
        )
        
        # Get the frozen credentials
        frozen_credentials = aws_credentials.get_frozen_credentials()
        
        # Create a SigV4 signer
        signer = SigV4Auth(
            frozen_credentials,
            "bedrock",
            region
        )
        
        # Sign the request
        signer.add_auth(request)
        
        # Extract headers for the requests library
        headers = dict(request.headers.items())
        
        # Make the GET request to the AWS API
        log.info(f"Checking foundation model availability for {model_id} in {region} at {endpoint_url}")
        response = requests.get(endpoint_url, headers=headers)
        
        # Handle HTTP errors
        if response.status_code != 200:
            error_message = response.text
            try:
                error_json = response.json()
                if isinstance(error_json, dict) and "Message" in error_json:
                    error_message = error_json["Message"]
            except:
                pass
                
            if response.status_code == 403:
                raise AWSCredentialError(
                    f"Access denied to Bedrock model availability API: {error_message}",
                    service_name="bedrock",
                    region_name=region,
                    error_code="AccessDenied"
                )
            elif response.status_code == 404:
                raise AWSServiceError(
                    f"Model not found or not available in region: {error_message}",
                    service_name="bedrock",
                    region_name=region,
                    error_code="ResourceNotFound"
                )
            else:
                raise AWSServiceError(
                    f"Error checking model availability (HTTP {response.status_code}): {error_message}",
                    service_name="bedrock",
                    region_name=region,
                    error_code=f"HTTP{response.status_code}"
                )
        
        # Parse the JSON response
        availability_data = response.json()
        
        # Add a simple "accessible" flag based on the overall status
        is_accessible = (
            availability_data.get("authorizationStatus") == "AUTHORIZED" and
            availability_data.get("entitlementAvailability") == "AVAILABLE" and
            availability_data.get("regionAvailability") == "AVAILABLE" and
            (availability_data.get("agreementAvailability", {}).get("status") == "AVAILABLE"
             if "agreementAvailability" in availability_data else True)
        )
        availability_data["accessible"] = is_accessible
        
        # Log the result
        access_status = "accessible" if is_accessible else "not accessible"
        log.debug(f"Model {model_id} is {access_status} in region {region}")
        
        return availability_data
        
    except AWSClientError:
        # Re-raise existing AWS exceptions
        raise
    except BotocoreClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        error_message = e.response.get('Error', {}).get('Message', str(e))
        
        if error_code in ('InvalidClientTokenId', 'UnrecognizedClientException', 
                         'AccessDenied', 'AuthFailure'):
            raise AWSCredentialError(
                f"Invalid AWS credentials: {error_message}",
                service_name="bedrock",
                region_name=region,
                error_code=error_code,
                original_error=e
            ) from e
        elif error_code in ('InvalidRegion', 'EndpointConnectionError'):
            raise AWSRegionError(
                f"Invalid or unsupported region: {error_message}",
                service_name="bedrock",
                region_name=region,
                error_code=error_code,
                original_error=e
            ) from e
        else:
            raise AWSServiceError(
                f"Service error: {error_message}",
                service_name="bedrock",
                region_name=region,
                error_code=error_code,
                original_error=e
            ) from e
    except Exception as e:
        # Handle other exceptions
        raise AWSClientError(
            f"Failed to check model availability: {str(e)}",
            service_name="bedrock",
            region_name=region,
            original_error=e
        ) from e


def bulk_check_model_availability(
    model_ids: List[str],
    region: str,
    client_factory: Optional[AWSClientFactory] = None,
    profile_name: Optional[str] = None,
    credentials: Optional[Dict[str, str]] = None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Dict[str, Any]]:
    """
    [Function intent]
    Check multiple Bedrock foundation models' availability in a specific region.
    
    [Design principles]
    - Efficient batch checking
    - Consistent error handling across multiple models
    - Clear result reporting
    
    [Implementation details]
    - Checks each model individually
    - Aggregates results by model ID
    - Continues despite individual model failures
    - Returns comprehensive result dictionary
    
    Args:
        model_ids: List of Bedrock model IDs to check
        region: AWS region to check in
        client_factory: Optional AWSClientFactory instance
        profile_name: AWS profile name for credentials
        credentials: Explicit AWS credentials (overrides profile_name)
        logger: Optional logger instance
        
    Returns:
        Dict mapping model IDs to their availability status information
    """
    # Use the provided logger or create a new one
    log = logger or logging.getLogger(__name__)
    
    # Initialize results dictionary
    results = {}
    
    # Check each model
    for model_id in model_ids:
        try:
            availability = check_model_availability(
                model_id, 
                region,
                client_factory,
                profile_name,
                credentials,
                logger
            )
            results[model_id] = availability
        except Exception as e:
            # Log error but continue with other models
            log.warning(f"Error checking availability for model {model_id}: {str(e)}")
            results[model_id] = {
                "error": str(e),
                "accessible": False
            }
    
    return results


def check_inference_profile_access(
    profile_arn: str,
    client_factory: Optional[AWSClientFactory] = None,
    logger: Optional[logging.Logger] = None
) -> Dict[str, Any]:
    """
    [Function intent]
    Check if the user has access to a specific inference profile.
    
    [Design principles]
    - Leverages direct API check for profile access
    - Returns detailed access information
    - Handles profile ARN parsing
    
    [Implementation details]
    - Extracts region and model ID from profile ARN
    - Uses check_model_availability to verify access
    - Adds profile-specific information to results
    
    Args:
        profile_arn: ARN of the inference profile
        client_factory: Optional AWSClientFactory instance
        logger: Optional logger instance
        
    Returns:
        Dict with profile access information
    """
    # Use the provided logger or create a new one
    log = logger or logging.getLogger(__name__)
    
    # Extract region and model ID from ARN
    # Format: arn:aws:bedrock:REGION:ACCOUNT:inference-profile/PROFILE_ID
    arn_parts = profile_arn.split(':')
    if len(arn_parts) < 6 or not arn_parts[5].startswith('inference-profile/'):
        raise ValueError(f"Invalid inference profile ARN format: {profile_arn}")
    
    region = arn_parts[3]
    profile_id = arn_parts[5].split('/')[-1]
    
    # Extract base model ID from profile ID
    # Profile IDs often follow pattern: REGION.MODEL_ID:VERSION
    profile_id_parts = profile_id.split('.')
    model_id = '.'.join(profile_id_parts[1:]) if len(profile_id_parts) > 1 else profile_id
    
    try:
        # Check if we have access to the underlying model
        availability = check_model_availability(model_id, region, client_factory, logger=logger)
        
        # Add profile-specific information
        availability['profileArn'] = profile_arn
        availability['profileId'] = profile_id
        
        return availability
    except Exception as e:
        log.warning(f"Error checking access for profile {profile_arn}: {str(e)}")
        return {
            "profileArn": profile_arn,
            "profileId": profile_id,
            "error": str(e),
            "accessible": False
        }
