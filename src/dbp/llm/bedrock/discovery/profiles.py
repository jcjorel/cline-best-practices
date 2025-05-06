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
# Provides access to AWS Bedrock inference profiles using data attached to model entries.
# Enables efficient management of provisioned throughput resources by extracting profile 
# information from model data in the simplified BedrockModelDiscovery implementation.
###############################################################################
# [Source file design principles]
# - Clean separation from model discovery
# - Thread-safe operations for concurrent access
# - Model-based profile access pattern
# - Complete metadata extraction
# - Error propagation for better debugging
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must minimize AWS API calls through effective caching
# - Must provide optimal region selection for best performance
# - Must work with the simplified BedrockModelDiscovery implementation
# - Must propagate errors instead of silently handling them
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# codebase:src/dbp/llm/bedrock/discovery/discovery_core.py
# codebase:src/dbp/llm/bedrock/discovery/association.py
# codebase:src/dbp/llm/bedrock/discovery/models_core.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
# system:threading
# system:logging
# system:copy
###############################################################################
# [GenAI tool change history]
# 2025-05-03T23:17:18Z : Updated for compatibility with simplified discovery by CodeAssistant
# * Removed dependencies on removed DiscoveryCache and RegionLatencyTracker
# * Updated to work with the new BedrockModelDiscovery implementation
# * Simplified the class to use the integrated caching in BedrockModelDiscovery
# 2025-05-03T18:48:00Z : Updated for error propagation by CodeAssistant
# * Removed warnings import
# * Updated design principles and constraints
# * Added error propagation to docstrings
# 2025-05-03T18:37:00Z : Removed direct profile caching by CodeAssistant
# * Removed all direct profile caching code
# * Updated to extract profiles from model data only
# * Updated methods to use model cache for profile access
# 2025-05-03T17:27:11Z : Refactored to use shared discovery code by CodeAssistant
# * Updated to inherit from BaseDiscovery
# * Replaced direct scanning with cache-only operations
# * Added deprecation warnings for scanning methods
# * Updated to work with combined model-profile discovery
###############################################################################

import logging
import threading
import copy
from typing import Dict, List, Optional, Any

# External imports
from ....api_providers.aws.client_factory import AWSClientFactory
from .discovery_core import BaseDiscovery
from .association import filter_profiles_by_model, get_model_ids_from_profile


class BedrockProfileDiscovery(BaseDiscovery):
    """
    [Class intent]
    Provides information about AWS Bedrock inference profiles across regions,
    enabling optimal provisioned throughput selection based on region availability and latency.
    Uses profile data attached to model entries. Only instantiated by BedrockModelDiscovery.
    
    [Design principles]
    - Clean separation from model discovery
    - Thread-safe operations for concurrent access
    - Latency-aware region selection
    - Complete metadata extraction
    - Internal usage only (no singleton pattern)
    - Model-based profile access pattern
    - Error propagation for better debugging
    
    [Implementation details]
    - Extracts profile data from model entries 
    - Provides model-to-profile mapping
    - Provides region-specific profile information
    - Maps profile availability by region and model
    - Only instantiated by BedrockModelDiscovery
    - Propagates errors instead of handling them silently
    """
    
    # No singleton pattern - this class is only instantiated by BedrockModelDiscovery
    
    def __init__(self, 
                client_factory: Optional[AWSClientFactory] = None, 
                model_discovery = None,
                logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the profile discovery service.
        
        [Design principles]
        - Component dependency management
        - Thread-safe initialization
        - Internal usage only
        - Proper error propagation
        
        [Implementation details]
        - Sets up dependencies (creating if not provided)
        - Initializes internal state
        - Connects with related discovery services
        - Propagates any initialization errors
        
        Args:
            client_factory: Optional AWSClientFactory instance
            model_discovery: Required BedrockModelDiscovery instance (owner)
            logger: Optional logger instance
        """
            
        # Initialize base class
        super().__init__(client_factory, logger)
        
        # Additional initialization
        self._profile_lock = threading.Lock()
        self._model_to_profiles_map = {}  # {model_id: {region: [profile_ids]}}
        
        # Import model_discovery here to avoid circular imports
        if model_discovery is None:
            from .models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery
            self.model_discovery = BedrockModelDiscovery.get_instance()
        else:
            self.model_discovery = model_discovery
        
    def get_inference_profile_ids(self, model_id: str, region: Optional[str] = None) -> List[str]:
        """
        [Method intent]
        Get all inference profile IDs for a model, optionally in a specific region.
        
        [Design principles]
        - Model-based approach for efficiency
        - Model-specific profile discovery
        - Region-aware operation
        - Model ID variant handling
        - Error propagation
        
        [Implementation details]
        - Gets model data from BedrockModelDiscovery
        - Extracts profile IDs from model data
        - Handles multiple regions if not specified
        - Handles model ID variations (with/without version suffix)
        - Propagates any errors for proper handling
        
        Args:
            model_id: The Bedrock model ID
            region: Optional specific region to check
            
        Returns:
            List of inference profile IDs for the model
            
        Raises:
            Exception: Any error during profile retrieval
        """
        profile_ids = []
        
        # Extract base model ID without version to handle variations
        base_model_id = model_id.split(':')[0]
        self.logger.debug(f"Looking for profiles with base model ID: {base_model_id}")
        
        # If region specified, check only that region
        if region:
            model_data = self.model_discovery.get_model(model_id, region)
            if model_data and "referencedByInstanceProfiles" in model_data:
                for profile in model_data["referencedByInstanceProfiles"]:
                    profile_id = profile.get("inferenceProfileId")
                    if profile_id and profile_id not in profile_ids:
                        profile_ids.append(profile_id)
            return profile_ids
        
        # If no region specified, check all regions where the model is available
        model_regions = self.model_discovery.get_model_regions(model_id)
        
        for region in model_regions:
            model_data = self.model_discovery.get_model(model_id, region)
            if model_data and "referencedByInstanceProfiles" in model_data:
                for profile in model_data["referencedByInstanceProfiles"]:
                    profile_id = profile.get("inferenceProfileId")
                    if profile_id and profile_id not in profile_ids:
                        profile_ids.append(profile_id)
        
        return profile_ids
    
    def get_inference_profile(self, model_id: str, profile_id: str, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get detailed information about a specific inference profile.
        
        [Design principles]
        - Model-based approach for efficiency
        - Direct API access when needed
        - Complete metadata retrieval
        - Error propagation
        
        [Implementation details]
        - Gets model data from BedrockModelDiscovery
        - Extracts profile information from model data
        - Determines best region if not specified
        - Returns complete profile metadata
        - Propagates any errors for proper handling
        
        Args:
            model_id: The Bedrock model ID
            profile_id: The inference profile ID
            region: Optional specific region to check
            
        Returns:
            Dict with profile information or None if not found
            
        Raises:
            Exception: Any error during profile retrieval
        """
        # If region not specified, find a region with this profile
        if not region:
            regions_with_profile = self._find_regions_for_profile(profile_id, model_id)
            
            if not regions_with_profile:
                return None
                
            # Use the first available region (could optimize for latency)
            region = regions_with_profile[0]
        
        # Get model data and extract profile
        model_data = self.model_discovery.get_model(model_id, region)
        if model_data and "referencedByInstanceProfiles" in model_data:
            for profile in model_data["referencedByInstanceProfiles"]:
                if profile.get("inferenceProfileId") == profile_id:
                    return copy.deepcopy(profile)
        
        return None
            
    def _find_regions_for_profile(self, profile_id: str, model_id: Optional[str] = None) -> List[str]:
        """
        [Method intent]
        Find regions where a specific profile is available.
        
        [Design principles]
        - Model-based approach
        - Efficient search algorithm
        - Model-based optimization
        - Error propagation
        
        [Implementation details]
        - Uses model_id to limit search scope when available
        - Gets model data from BedrockModelDiscovery
        - Returns list of regions with profile available
        - Propagates any errors for proper handling
        
        Args:
            profile_id: Inference profile ID to find
            model_id: Optional model ID to narrow search
            
        Returns:
            List of region names where the profile is available
            
        Raises:
            Exception: Any error during region search
        """
        regions_with_profile = []
        
        # If we know the model ID, we can be more efficient by checking only
        # regions where that model is available
        if model_id:
            model_regions = self.model_discovery.get_model_regions(model_id)
            
            for region in model_regions:
                model_data = self.model_discovery.get_model(model_id, region)
                if model_data and "referencedByInstanceProfiles" in model_data:
                    for profile in model_data["referencedByInstanceProfiles"]:
                        if profile.get("inferenceProfileId") == profile_id:
                            regions_with_profile.append(region)
                            break
        else:
            # Without model ID, we need to check all Bedrock regions
            model_mapping = self.model_discovery.get_json_model_mapping()
            
            for region, model_dict in model_mapping.get("models", {}).items():
                for model_info in model_dict.values():
                    if "referencedByInstanceProfiles" in model_info:
                        for profile in model_info["referencedByInstanceProfiles"]:
                            if profile.get("inferenceProfileId") == profile_id:
                                regions_with_profile.append(region)
                                break
        
        # Sort by latency for optimal access
        with self.model_discovery._lock:
            region_latencies = self.model_discovery._memory_cache.get("latency", {})
            
        # Sort by latency if available, otherwise keep current order
        sorted_regions = sorted(
            regions_with_profile,
            key=lambda r: region_latencies.get(r, float('inf'))
        )
        
        return sorted_regions
    
    def get_model_profile_mapping(self, refresh: bool = False) -> Dict[str, Any]:
        """
        [Method intent]
        Get the complete region-based model-profile mapping.
        
        [Design principles]
        - Complete region-based structure
        - Schema versioning for compatibility
        - Comprehensive data for all regions
        - Error propagation for better debugging
        
        [Implementation details]
        - Uses the model_discovery to get the complete mapping
        - Returns properly formatted structure with schema version
        - Propagates any errors for proper handling
        
        Args:
            refresh: Whether to force a refresh of the mapping
            
        Returns:
            Dict containing the complete model-profile mapping across regions
            
        Raises:
            Exception: Any error during mapping creation
        """
        # If refresh requested, force a refresh
        if refresh:
            self.model_discovery.scan_all_regions(force_refresh=True)
            
        # Get the model mapping directly from model_discovery
        mapping = self.model_discovery.get_json_model_mapping()
        
        # Add schema version if not present
        if "schema_version" not in mapping:
            mapping["schema_version"] = "1.0"
        
        return mapping
