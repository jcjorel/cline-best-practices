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
# Provides access to AWS Bedrock inference profiles using cached data collected by
# BedrockModelDiscovery. Enables efficient management of provisioned throughput resources
# by providing profile information without duplicating API calls.
###############################################################################
# [Source file design principles]
# - Clean separation from model discovery
# - Thread-safe operations for concurrent access
# - Cache-first approach for performance
# - Complete metadata extraction
# - Singleton pattern for project-wide reuse
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must minimize AWS API calls through effective caching
# - Must provide optimal region selection for best performance
# - Must be backward compatible with existing Bedrock client implementations
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/cache.py
# codebase:src/dbp/llm/bedrock/discovery/latency.py
# codebase:src/dbp/llm/bedrock/discovery/models.py
# codebase:src/dbp/llm/bedrock/discovery/discovery_core.py
# system:threading
# system:logging
# system:warnings
###############################################################################
# [GenAI tool change history]
# 2025-05-03T15:13:00Z : Implementation by CodeAssistant
# * Created cache-only version of BedrockProfileDiscovery
# * Added deprecation warnings for scanning methods
# * Updated to inherit from BaseDiscovery
###############################################################################

import logging
import threading
import time
import warnings
import copy
from typing import Dict, List, Optional, Any, Set

# Local imports
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from .discovery_core import BaseDiscovery
from .association import associate_profiles_with_models, filter_profiles_by_model

# External imports
from ....api_providers.aws.client_factory import AWSClientFactory


class BedrockProfileDiscovery(BaseDiscovery):
    """
    [Class intent]
    Provides information about AWS Bedrock inference profiles across regions,
    enabling optimal provisioned throughput selection based on region availability and latency.
    Uses cached data gathered by BedrockModelDiscovery.
    
    [Design principles]
    - Clean separation from model discovery
    - Thread-safe operations for concurrent access
    - Latency-aware region selection
    - Complete metadata extraction
    - Singleton pattern for project-wide reuse
    - Cache-first approach for performance
    
    [Implementation details]
    - Accesses cache populated by BedrockModelDiscovery
    - Provides model-to-profile mapping
    - Uses cached data with configurable TTL
    - Provides region-specific profile information
    - Maps profile availability by region and model
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, 
                    cache: Optional[DiscoveryCache] = None, 
                    client_factory: Optional[AWSClientFactory] = None, 
                    latency_tracker: Optional[RegionLatencyTracker] = None, 
                    model_discovery = None,
                    logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Get the singleton instance of BedrockProfileDiscovery, creating it if needed.
        
        [Design principles]
        - Thread-safe singleton access
        - Lazy initialization
        - Component dependency injection
        
        [Implementation details]
        - Double-checked locking pattern
        - Creates instance only when first needed
        - Returns same instance for all callers
        - Allows dependency injection for testing
        
        Args:
            cache: Optional DiscoveryCache instance
            client_factory: Optional AWSClientFactory instance
            latency_tracker: Optional RegionLatencyTracker instance
            model_discovery: Optional BedrockModelDiscovery instance
            logger: Optional logger instance
            
        Returns:
            BedrockProfileDiscovery: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        cache=cache,
                        client_factory=client_factory,
                        latency_tracker=latency_tracker,
                        model_discovery=model_discovery,
                        logger=logger
                    )
        return cls._instance
    
    def __init__(self, 
                cache: Optional[DiscoveryCache] = None, 
                client_factory: Optional[AWSClientFactory] = None, 
                latency_tracker: Optional[RegionLatencyTracker] = None,
                model_discovery = None,
                logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the profile discovery service.
        
        [Design principles]
        - Protected constructor for singleton pattern
        - Component dependency management
        - Thread-safe initialization
        
        [Implementation details]
        - Sets up dependencies (creating if not provided)
        - Initializes internal state
        - Connects with related discovery services
        
        Args:
            cache: Optional DiscoveryCache instance
            client_factory: Optional AWSClientFactory instance
            latency_tracker: Optional RegionLatencyTracker instance
            model_discovery: Optional BedrockModelDiscovery instance
            logger: Optional logger instance
        """
        # Initialize base class
        super().__init__(cache, client_factory, latency_tracker, logger)
        
        # Additional initialization
        self._profile_lock = threading.Lock()
        self._model_to_profiles_map = {}  # {model_id: {region: [profile_ids]}}
        
        # Import model_discovery here to avoid circular imports
        if model_discovery is None:
            from .models import BedrockModelDiscovery
            self.model_discovery = BedrockModelDiscovery.get_instance(
                cache=self.cache,
                client_factory=self.client_factory,
                latency_tracker=self.latency_tracker
            )
        else:
            self.model_discovery = model_discovery
    
    def scan_profiles_in_region(self, region: str, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        [DEPRECATED] Scan a region for all available inference profiles, optionally filtered by model.
        
        This method is deprecated and will be removed in a future version.
        The profile scanning is now automatically performed by BedrockModelDiscovery.scan_all_regions().
        
        [Design principles]
        - Complete profile discovery
        - Latency measurement
        - Optional model filtering
        - Cache integration
        
        [Implementation details]
        - Delegates scanning to BedrockModelDiscovery
        - Returns data from cache
        
        Args:
            region: AWS region to scan
            model_id: Optional model ID to filter profiles
            
        Returns:
            List of profile information dictionaries
        """
        warnings.warn(
            "scan_profiles_in_region is deprecated. Profile scanning is now automatically "
            "performed by BedrockModelDiscovery.scan_all_regions()",
            DeprecationWarning, 
            stacklevel=2
        )
        
        # Force a rescan of the region to get latest profiles
        self.model_discovery.scan_all_regions([region], refresh_cache=True)
        
        # Return profiles from cache
        return self.cache.get_profile_cache(region, model_id)
    
    def get_inference_profile_ids(self, model_id: str, region: Optional[str] = None) -> List[str]:
        """
        [Method intent]
        Get all inference profile IDs for a model, optionally in a specific region.
        
        [Design principles]
        - Cache-first approach for efficiency
        - Model-specific profile discovery
        - Region-aware operation
        - Model ID variant handling
        
        [Implementation details]
        - Checks cache for profile information
        - Returns profile IDs mapped to the model
        - Handles multiple regions if not specified
        - Handles model ID variations (with/without version suffix)
        
        Args:
            model_id: The Bedrock model ID
            region: Optional specific region to check
            
        Returns:
            List of inference profile IDs for the model
        """
        profile_ids = []
        
        # Extract base model ID without version to handle variations
        base_model_id = model_id.split(':')[0]
        self.logger.debug(f"Looking for profiles with base model ID: {base_model_id}")
        
        # If region specified, check only that region
        if region:
            profiles = self._get_profiles_in_region(region)
            if profiles:
                for profile in profiles:
                    # Check for exact match or base model ID match
                    profile_model_id = profile.get("modelId", "")
                    if profile_model_id == model_id or profile_model_id == base_model_id:
                        profile_ids.append(profile["inferenceProfileId"])
            return profile_ids
        
        # If no region specified, check all regions where the model is available
        model_regions = self.model_discovery.get_model_regions(model_id)
        
        for region in model_regions:
            region_profiles = self._get_profiles_in_region(region)
            if region_profiles:
                for profile in region_profiles:
                    # Check for exact match or base model ID match
                    profile_model_id = profile.get("modelId", "")
                    if profile_model_id == model_id or profile_model_id == base_model_id:
                        profile_id = profile["inferenceProfileId"]
                        if profile_id not in profile_ids:
                            profile_ids.append(profile_id)
        
        return profile_ids
    
    def get_inference_profile(self, model_id: str, profile_id: str, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get detailed information about a specific inference profile.
        
        [Design principles]
        - Cache-first approach for efficiency
        - Direct API access when needed
        - Complete metadata retrieval
        
        [Implementation details]
        - Checks cache for profile information
        - Determines best region if not specified
        - Returns complete profile metadata
        
        Args:
            model_id: The Bedrock model ID
            profile_id: The inference profile ID
            region: Optional specific region to check
            
        Returns:
            Dict with profile information or None if not found
        """
        # If region not specified, find a region with this profile
        if not region:
            regions_with_profile = self._find_regions_for_profile(profile_id, model_id)
            
            if not regions_with_profile:
                return None
                
            # Use the first available region (could optimize for latency)
            region = regions_with_profile[0]
        
        # Check cache first
        cached_profiles = self.cache.get_profile_cache(region)
        if cached_profiles:
            for profile in cached_profiles:
                if profile.get("inferenceProfileId") == profile_id:
                    return copy.deepcopy(profile)
        
        return None
    
    def _get_profiles_in_region(self, region: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get all inference profiles in a specific region, using cache only.
        
        [Design principles]
        - Cache-only approach
        - Error handling
        
        [Implementation details]
        - Checks cache for region profiles
        - Returns all profile data for the region
        
        Args:
            region: AWS region to get profiles for
            
        Returns:
            List of profile information dictionaries
        """
        # Get from cache
        cached_profiles = self.cache.get_profile_cache(region)
        return cached_profiles or []
            
    def _find_regions_for_profile(self, profile_id: str, model_id: Optional[str] = None) -> List[str]:
        """
        [Method intent]
        Find regions where a specific profile is available.
        
        [Design principles]
        - Cache-only approach
        - Efficient search algorithm
        - Model-based optimization
        
        [Implementation details]
        - Uses model_id to limit search scope when available
        - Checks cache before making API calls
        - Returns list of regions with profile available
        
        Args:
            profile_id: Inference profile ID to find
            model_id: Optional model ID to narrow search
            
        Returns:
            List of region names where the profile is available
        """
        regions_with_profile = []
        
        # If we know the model ID, we can be more efficient by checking only
        # regions where that model is available
        if model_id:
            model_regions = self.model_discovery.get_model_regions(model_id)
            
            for region in model_regions:
                profiles = self._get_profiles_in_region(region)
                for profile in profiles:
                    if profile.get("inferenceProfileId") == profile_id:
                        regions_with_profile.append(region)
                        break
        else:
            # Without model ID, we need to check all Bedrock regions
            for region in self.INITIAL_BEDROCK_REGIONS:
                profiles = self._get_profiles_in_region(region)
                for profile in profiles:
                    if profile.get("inferenceProfileId") == profile_id:
                        regions_with_profile.append(region)
                        break
        
        # Sort by latency for optimal access
        return self.get_sorted_regions(regions_with_profile)
    
    def get_model_id_for_profile(self, profile_id: str, region: Optional[str] = None) -> Optional[str]:
        """
        [Method intent]
        Get the model ID associated with a specific inference profile.
        
        [Design principles]
        - Efficient resolution
        - Region-specific lookup
        - Cache-only approach
        
        [Implementation details]
        - Checks internal mapping first
        - Falls back to cache
        - Returns the associated model ID
        
        Args:
            profile_id: The inference profile ID
            region: Optional specific region for lookup
            
        Returns:
            str: The associated model ID, or None if not found
        """
        # First check the internal mapping if we have it
        with self._profile_lock:
            for model_id, regions in self._model_to_profiles_map.items():
                if region:
                    # If region specified, check only that region
                    if region in regions and profile_id in regions[region]:
                        return model_id
                else:
                    # Otherwise check all regions
                    for r, profiles in regions.items():
                        if profile_id in profiles:
                            return model_id
        
        # If not found in mapping, try to get the profile directly
        # If region provided, check only that region
        if region:
            profile = self._get_profile_by_id(profile_id, region)
            if profile and "modelId" in profile:
                return profile["modelId"]
                
        # Otherwise we need to search across regions
        for region in self.INITIAL_BEDROCK_REGIONS:
            profile = self._get_profile_by_id(profile_id, region)
            if profile and "modelId" in profile:
                return profile["modelId"]
                
        return None
    
    def _get_profile_by_id(self, profile_id: str, region: str) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get a profile by ID from a specific region using the cache.
        
        [Design principles]
        - Cache-only approach
        - Error handling
        
        [Implementation details]
        - Checks cache for the profile
        - Returns complete profile information
        
        Args:
            profile_id: Inference profile ID
            region: AWS region to check
            
        Returns:
            Dict with profile information or None if not found
        """
        # Check cache
        cached_profiles = self.cache.get_profile_cache(region)
        if cached_profiles:
            for profile in cached_profiles:
                if profile.get("inferenceProfileId") == profile_id:
                    return profile
        
        return None
        
    def get_model_profile_mapping(self, refresh: bool = False) -> Dict[str, Any]:
        """
        [Method intent]
        Get the complete region-based model-profile mapping.
        
        [Design principles]
        - Cache-first approach for efficiency
        - Complete region-based structure
        - Schema versioning for compatibility
        - Comprehensive data for all regions
        
        [Implementation details]
        - Checks cache first if not refreshing
        - Uses model discovery to refresh data if needed
        - Returns properly formatted structure with schema version
        
        Args:
            refresh: Whether to force a refresh of the mapping
            
        Returns:
            Dict containing the complete model-profile mapping across regions
        """
        cache_key = "bedrock_model_profile_mapping"
        
        # Check cache first unless refresh is requested
        if not refresh:
            cached_mapping = self.cache.get(cache_key)
            if cached_mapping:
                self.logger.info("Using cached model-profile mapping")
                return cached_mapping
        
        # If refresh requested or not in cache, force full scan via model discovery
        if refresh:
            self.model_discovery.scan_all_regions(refresh_cache=True)
            
        # Build mapping from cached data
        all_regions = self.model_discovery.INITIAL_BEDROCK_REGIONS
        all_regions_data = {}
        
        for region in all_regions:
            models = self.model_discovery.cache.get_model_cache(region)
            profiles = self.cache.get_profile_cache(region)
            
            if models:
                if profiles:
                    # Ensure profiles are associated with models
                    models = associate_profiles_with_models(models, profiles, self.logger)
                
                # Add to region data structure
                all_regions_data[region] = {model["modelId"]: model for model in models}
        
        # Create the final structure
        merged_data = {
            "schema_version": "1.0",
            "models": all_regions_data
        }
        
        # Cache the results
        self.cache.set(cache_key, merged_data)
        self.logger.info("Built and cached new model-profile mapping")
        
        return merged_data
    
    def clear_cache(self) -> None:
        """
        [Method intent]
        Clear all cached profile data.
        
        [Design principles]
        - Complete cache clearing
        - Thread safety
        - State management
        
        [Implementation details]
        - Invalidates all profile cache entries
        - Clears internal mapping
        - Logs clearing operations
        
        Returns:
            None
        """
        try:
            # Find all profile cache entries and invalidate them
            for region in self.INITIAL_BEDROCK_REGIONS:
                cache_key = f"bedrock_profiles:{region}"
                self.cache.invalidate(cache_key)
            
            # Also invalidate the model-profile mapping
            self.cache.invalidate("bedrock_model_profile_mapping")
            
            # Clear internal mapping
            with self._profile_lock:
                self._model_to_profiles_map.clear()
                
            self.logger.info("Profile discovery cache cleared")
        except Exception as e:
            self.logger.warning(f"Error clearing profile cache: {str(e)}")
