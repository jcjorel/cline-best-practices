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
# Provides utilities for associating AWS Bedrock inference profiles with models.
# Handles the extraction of model identifiers from profile data and embeds profile
# information into model objects for convenient access.
###############################################################################
# [Source file design principles]
# - Pure ARN-based model ID extraction
# - Complete profile-to-model mapping
# - Prevention of duplicate associations
# - Clean function-based implementation
# - Consistent error handling
###############################################################################
# [Source file constraints]
# - Must handle inconsistent profile data
# - Must be thread-safe for concurrent access
# - Must handle missing or malformed ARNs
# - Must be backward compatible with existing implementations
###############################################################################
# [Dependencies]
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-03T17:23:21Z : Initial implementation by CodeAssistant
# * Created association utilities extracted from discovery classes
# * Implemented profile filtering functionality
# * Added complete documentation
###############################################################################

import logging
from typing import Dict, List, Optional, Any


def associate_profiles_with_models(
    models: List[Dict[str, Any]], 
    profiles: List[Dict[str, Any]],
    logger: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Associate profiles with models using ARN-based extraction from profiles,
    embedding profile information directly in the model objects.
    
    [Design principles]
    - Pure ARN-based model ID extraction
    - Complete profile embedding
    - Duplicate prevention
    - Profile requirement detection
    
    [Implementation details]
    - Extracts model IDs directly from ARNs in profile model references
    - Embeds complete profile objects in matching models
    - Prevents duplicate profile entries
    - Detects models requiring inference profiles
    
    Args:
        models: List of model information dictionaries
        profiles: List of profile information dictionaries
        logger: Optional logger
        
    Returns:
        The updated models list with embedded profile information
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    # Process each profile
    for profile in profiles:
        profile_id = profile.get("inferenceProfileId")
        if not profile_id:
            continue
            
        # Examine each model ARN in this profile
        for model_ref in profile.get("models", []):
            model_arn = model_ref.get("modelArn", "")
            if not model_arn or "/" not in model_arn:
                continue
                
            # Extract model ID directly from ARN
            # ARN format: arn:aws:bedrock:{region}::foundation-model/{model_id}
            arn_parts = model_arn.split("/")
            if len(arn_parts) >= 2:
                referenced_model_id = arn_parts[-1]
                
                # Find matching model
                for model in models:
                    if model.get("modelId") == referenced_model_id:
                        # Initialize referencedByInstanceProfiles if needed
                        if "referencedByInstanceProfiles" not in model:
                            model["referencedByInstanceProfiles"] = []
                        
                        # Avoid duplicates
                        profile_already_added = any(
                            p.get("inferenceProfileId") == profile_id 
                            for p in model["referencedByInstanceProfiles"]
                        )
                        
                        if not profile_already_added:
                            # Add the complete profile data to the model
                            logger.debug(f"Adding profile {profile_id} to model {referenced_model_id}")
                            model["referencedByInstanceProfiles"].append(profile)
    
    return models


def filter_profiles_by_model(
    profiles: List[Dict[str, Any]],
    model_id: str,
    logger: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Filter profiles to return only those associated with a specific model ID.
    
    [Design principles]
    - ARN-based model ID extraction
    - Base model ID matching for variants
    - Efficient filtering
    
    [Implementation details]
    - Extracts model IDs from ARNs in profile references
    - Handles both exact matches and base model ID matches
    - Returns filtered list of matching profiles
    
    Args:
        profiles: List of profile information dictionaries
        model_id: The model ID to filter by
        logger: Optional logger
        
    Returns:
        List of profiles associated with the specified model
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    # Extract base model ID without version to handle variations
    base_model_id = model_id.split(':')[0]
    logger.debug(f"Filtering profiles for model ID: {model_id} (base: {base_model_id})")
    
    matching_profiles = []
    
    for profile in profiles:
        is_match = False
        
        # Check direct model ID match
        if profile.get("modelId") == model_id or profile.get("modelId") == base_model_id:
            is_match = True
        else:
            # Check model references in the profile
            for model_ref in profile.get("models", []):
                model_arn = model_ref.get("modelArn", "")
                if not model_arn or "/" not in model_arn:
                    continue
                    
                # Extract model ID from ARN
                arn_parts = model_arn.split("/")
                if len(arn_parts) >= 2:
                    referenced_model_id = arn_parts[-1]
                    
                    # Check for exact match or base ID match
                    if (referenced_model_id == model_id or 
                        referenced_model_id.split(':')[0] == base_model_id):
                        is_match = True
                        break
        
        if is_match:
            matching_profiles.append(profile)
    
    logger.debug(f"Found {len(matching_profiles)} matching profiles for model {model_id}")
    return matching_profiles


def get_model_ids_from_profile(
    profile: Dict[str, Any],
    logger: Optional[logging.Logger] = None
) -> List[str]:
    """
    [Function intent]
    Extract all model IDs referenced by a profile.
    
    [Design principles]
    - Complete ARN parsing
    - Robust error handling
    - Consistent model ID extraction
    
    [Implementation details]
    - Extracts model IDs from ARNs in profile model references
    - Handles missing or malformed ARNs
    - Returns unique list of model IDs
    
    Args:
        profile: Profile information dictionary
        logger: Optional logger
        
    Returns:
        List of model IDs referenced by the profile
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    model_ids = []
    
    # Check direct model ID if available
    if "modelId" in profile and profile["modelId"]:
        model_ids.append(profile["modelId"])
    
    # Extract from model references
    for model_ref in profile.get("models", []):
        model_arn = model_ref.get("modelArn", "")
        if not model_arn or "/" not in model_arn:
            continue
            
        # Extract model ID from ARN
        try:
            referenced_model_id = model_arn.split("/")[-1]
            if referenced_model_id and referenced_model_id not in model_ids:
                model_ids.append(referenced_model_id)
        except Exception as e:
            if logger:
                logger.warning(f"Error extracting model ID from ARN {model_arn}: {str(e)}")
    
    return model_ids
