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
# Discovers and provides information about available AWS Bedrock models across regions.
# Optimizes model discovery through parallel scanning, caching, and latency-based 
# region prioritization to provide efficient access to Bedrock foundation models.
# Also handles inference profile association with models for provisioned throughput support.
###############################################################################
# [Source file design principles]
# - Efficient parallel scanning using ThreadPoolExecutor
# - Thread-safe operations for concurrent access
# - Latency-optimized region selection
# - Comprehensive model metadata extraction
# - Singleton pattern for project-wide reuse
# - Cache-first approach for performance
# - Combined model and profile discovery
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must minimize AWS API calls through effective caching
# - Must provide optimal region selection for best performance
# - Must handle AWS credential management securely
# - Must be backward compatible with existing Bedrock client implementations
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# codebase:src/dbp/llm/bedrock/discovery/cache.py
# codebase:src/dbp/llm/bedrock/discovery/latency.py
# codebase:src/dbp/llm/bedrock/discovery/discovery_core.py
# codebase:src/dbp/llm/bedrock/discovery/scan_utils.py
# codebase:src/dbp/llm/bedrock/discovery/association.py
# system:boto3
# system:botocore.exceptions
# system:concurrent.futures
# system:threading
# system:time
# system:logging
# system:copy
###############################################################################
# [GenAI tool change history]
# 2025-05-03T20:58:00Z : Updated cache structure to match JSON format by CodeAssistant
# * Modified cache structure to match bedrock_model_profile_mapping.json
# * Updated model discovery to work with the new structure
# * Implemented ARN-based profile mapping for inference profiles
# * Improved region handling and model lookup
# 2025-05-03T17:24:26Z : Refactored to use shared discovery code by CodeAssistant
# * Updated to inherit from BaseDiscovery
# * Replaced scanning code with scan_utils
# * Added combined model and profile discovery
# * Added get_model method with profile association
# 2025-05-03T11:38:23Z : Initial implementation by CodeAssistant
# * Created BedrockModelDiscovery singleton class
# * Implemented parallel region scanning with ThreadPoolExecutor
# * Added integration with cache and latency tracking components
# * Implemented latency-based region sorting and selection
###############################################################################

import logging
import threading
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Set, Union

import boto3
import botocore.exceptions

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from .discovery_core import BaseDiscovery
from .scan_utils import scan_region_for_models, scan_region_combined
from .association import associate_profiles_with_models


class BedrockModelDiscovery(BaseDiscovery):
    """
    [Class intent]
    Discovers and provides information about available AWS Bedrock models across regions,
    with optimized region selection based on latency measurements and user preferences.
    
    [Design principles]
    - Efficient parallel scanning using ThreadPoolExecutor
    - Thread-safe operations for concurrent access
    - Latency-optimized region selection
    - Comprehensive model metadata extraction
    - Singleton pattern for project-wide reuse
    
    [Implementation details]
    - Uses AWSClientFactory for client access
    - Implements parallel region scanning with latency measurement
    - Caches discovery results with configurable TTL
    - Provides latency-based sorting of regions
    - Maps model availability by region
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    # Bedrock is not available in all AWS regions
    # This list can be dynamically updated through discovery
    INITIAL_BEDROCK_REGIONS = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", 
        "ap-southeast-1", "ap-southeast-2", "eu-central-1"
    ]
    
    @classmethod
    def get_instance(cls):
        """
        [Method intent]
        Get the singleton instance of BedrockModelDiscovery, creating it if needed.
        
        [Design principles]
        - Thread-safe singleton access
        - Lazy initialization
        - Simple parameter-free access
        
        [Implementation details]
        - Double-checked locking pattern
        - Creates instance only when first needed
        - Returns same instance for all callers
        - Uses default components (creates cache, etc.)
        - Attempts to load cache when created
        
        Returns:
            BedrockModelDiscovery: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create default components
                    client_factory = AWSClientFactory.get_instance()
                    cache = DiscoveryCache()
                    latency_tracker = RegionLatencyTracker(cache=cache)
                    logger = logging.getLogger(cls.__name__)
                    
                    cls._instance = cls(
                        cache=cache,
                        client_factory=client_factory,
                        latency_tracker=latency_tracker,
                        logger=logger
                    )
                    
                    # Try to load cache, scan all regions if loading fails
                    try:
                        cls._instance.initialize_cache()
                    except Exception as e:
                        logger.warning(f"Failed to initialize cache: {str(e)}, will scan regions when needed")
        
        return cls._instance
    
    def __init__(self, 
                cache: Optional[DiscoveryCache] = None, 
                client_factory: Optional[AWSClientFactory] = None, 
                latency_tracker: Optional[RegionLatencyTracker] = None, 
                logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the Bedrock model discovery service.
        
        [Design principles]
        - Protected constructor for singleton pattern
        - Component dependency management
        - Thread-safe initialization
        
        [Implementation details]
        - Sets up dependencies (creating if not provided)
        - Initializes internal state
        - Loads supported models from project model classes
        - No automatic scanning - call initialize_cache() after creation
        
        Args:
            cache: Optional DiscoveryCache instance
            client_factory: Optional AWSClientFactory instance
            latency_tracker: Optional RegionLatencyTracker instance
            logger: Optional logger instance
            
        Raises:
            RuntimeError: If attempting to create instance directly instead of using get_instance()
        """
        # Enforce singleton pattern
        if self.__class__._instance is not None:
            raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
            
        # Initialize components and dependencies
        self.client_factory = client_factory or AWSClientFactory.get_instance()
        self.cache = cache or DiscoveryCache()
        self.latency_tracker = latency_tracker or RegionLatencyTracker(cache=self.cache)
        self.logger = logger or logging.getLogger(__name__)
        self._region_lock = threading.Lock()
        
        # Get project supported models from model classes
        self.project_supported_models = self._get_project_supported_models()
        self.logger.info(f"Loaded {len(self.project_supported_models)} project-supported models")
    
    def initialize_cache(self) -> None:
        """
        [Method intent]
        Initialize cache by loading from disk or scanning if necessary.
        
        [Design principles]
        - Explicit cache initialization
        - Fallback to scanning if loading fails
        - Error propagation for transparency
        
        [Implementation details]
        - Attempts to load cache from disk using the load() method
        - If loading fails, triggers a full scan to populate cache
        - Propagates errors for handling by callers
        
        Raises:
            Exception: If loading fails and scanning also fails
        """
        try:
            # Try to load cache from disk
            self.logger.info("Loading model discovery cache from disk")
            self.cache.load()
            self.logger.info("Cache loaded successfully")
        except Exception as e:
            self.logger.warning(f"Cache loading failed: {str(e)}")
            self.logger.info("Performing full region scan to rebuild cache")
            
            # Perform a full scan to rebuild cache
            self._scan_all_regions()
            
            # Save the cache to disk
            try:
                self.cache.save()
                self.logger.info("Cache saved successfully after rebuilding")
            except Exception as save_err:
                self.logger.warning(f"Failed to save cache after rebuilding: {str(save_err)}")
    
    def scan_all_regions(self, regions: Optional[List[str]] = None, force_rescan: bool = False) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Get Bedrock models across regions, either from cache or by forcing a fresh scan.
        
        [Design principles]
        - Cache-first approach by default
        - Option to force fresh data with cache cleanup 
        - Complete model information
        - User control over cache behavior
        
        [Implementation details]
        - By default, uses only cached data with no API calls
        - With force_rescan=True, clears cache and performs fresh scan
        - Returns empty dicts for regions with no data
        - Saves results to cache after scanning
        
        Args:
            regions: Optional list of regions to get models for (defaults to initial regions)
            force_rescan: If True, clears cache and performs a fresh scan of all regions
            
        Returns:
            Dict with structure {"models": {region: {model_id: model_details}}}
        """
        # If force_rescan is True, clear the cache and perform a fresh scan
        if force_rescan:
            self.logger.info("Force rescan requested, clearing cache and performing full scan")
            try:
                self.clear_cache()
            except Exception as e:
                self.logger.warning(f"Error clearing cache before rescan: {str(e)}")
                # Continue even if cache clearing fails
            
            # Delegate to _scan_all_regions to perform actual scanning
            return self._scan_all_regions(regions, refresh_cache=True)
            
        # Normal cache-only behavior
        # Get full model mapping from cache
        result = self.cache.get_model_mapping()
        
        # If specific regions requested, filter results
        if regions:
            # Copy structure but only include requested regions
            filtered_models = {"models": {}}
            for region in regions:
                if region in result["models"]:
                    filtered_models["models"][region] = result["models"][region]
                else:
                    # Add empty dict for regions with no cached data
                    filtered_models["models"][region] = {}
            result = filtered_models
        
        return result
    
    def _scan_all_regions(self, regions: Optional[List[str]] = None, refresh_cache: bool = False) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Scan AWS regions to discover Bedrock models and inference profiles,
        using parallel scanning for efficiency.
        
        [Design principles]
        - Parallel scanning for performance
        - Cache-first approach with refresh option
        - Complete model discovery
        - Latency measurement during scanning
        - Combined model and profile discovery
        
        [Implementation details]
        - Uses ThreadPoolExecutor for parallel scanning
        - Updates both model and profile caches
        - Measures and records region latencies
        - Handles regions where Bedrock is not available
        - Associates profiles with models
        - Returns data in format matching bedrock_model_profile_mapping.json
        
        Args:
            regions: Optional list of regions to scan (defaults to initial regions)
            refresh_cache: Whether to force a refresh of cached data
            
        Returns:
            Dict with "models" key mapping to regions and model details
        """
        # Start with format matching bedrock_model_profile_mapping.json
        result = {"models": {}}
        
        # If not forcing a refresh, try to use cache first
        if not refresh_cache:
            # Try to get complete mapping from cache
            cached_mapping = self.cache.get_model_mapping()
            if cached_mapping and cached_mapping.get("models"):
                result = cached_mapping
                
                # If specific regions requested, filter the result
                if regions:
                    filtered_models = {"models": {}}
                    for region in regions:
                        if region in cached_mapping["models"]:
                            filtered_models["models"][region] = cached_mapping["models"][region]
                    result = filtered_models
        
        # If we still need to scan any regions
        regions_to_scan = []
        if regions:
            # Only scan specified regions not found in cache
            existing_regions = result.get("models", {}).keys()
            regions_to_scan = [r for r in regions if r not in existing_regions]
        elif not result.get("models") or refresh_cache:
            # If no results from cache or forced refresh, get all regions
            regions_to_scan = self.get_all_regions()
        
        if regions_to_scan:
            self.logger.info(f"Scanning {len(regions_to_scan)} AWS regions for Bedrock models and profiles...")
            
            # Define scan function to use with parallel scanner
            def region_scan_func(region):
                models, profiles = scan_region_combined(
                    region, 
                    self.client_factory,
                    self.latency_tracker,
                    self.project_supported_models,
                    self.cache,
                    self.logger
                )
                
                # Associate profiles with models
                if models and profiles:
                    models = associate_profiles_with_models(models, profiles, self.logger)
                    
                    # Convert list of models to model_id -> model_details map
                    # This matches the format in bedrock_model_profile_mapping.json
                    model_dict = {}
                    for model in models:
                        model_id = model.get("modelId")
                        if model_id:
                            model_dict[model_id] = model
                    
                    # Update region in result
                    result["models"][region] = model_dict
                    
                return model_dict
            
            # Use parallel scanning from base class
            region_models = self.scan_regions_parallel(
                regions_to_scan, 
                region_scan_func
            )
            
            # Merge results if needed (should already be updated in result)
            for region, models in region_models.items():
                if region not in result["models"]:
                    result["models"][region] = models
            
            # Save the complete model mapping to cache
            try:
                self.logger.debug("Saving complete model mapping to cache after region scan")
                self.cache.save_model_mapping(result)
            except Exception as e:
                self.logger.warning(f"Failed to save model mapping to cache: {str(e)}")
        
        return result
    
    def _scan_region(self, region: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
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
            
        Returns:
            List of dicts with model information in the region
        """
        models = []
        all_models = []
        project_models = []
        start_time = time.time()
        
        try:
            # Get Bedrock client for this region
            bedrock_client = self.client_factory.get_client("bedrock", region_name=region)
            
            # List available foundation models
            response = bedrock_client.list_foundation_models()
            
            # Calculate and record latency
            latency = time.time() - start_time
            self.latency_tracker.update_latency(region, latency)
            
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
                    self.logger.debug(f"Model {model_id} requires an inference profile")
                
                all_models.append(model_info)
                
                # Check if this is a project-supported model
                model_base_id = model_id.split(":")[0]
                is_supported = any(
                    model_id.startswith(supported_id.split(":")[0]) 
                    for supported_id in self.project_supported_models
                )
                
                if is_supported:
                    project_models.append(model_info)
            
            total_models = len(all_models)
            project_model_count = len(project_models)
            
            self.logger.info(f"Found {total_models} active models in region {region}, {project_model_count} supported by project")
            
            # If we found project models, return only those for caching
            # Otherwise return all models (for discovery purposes)
            models = project_models if project_models else all_models
            
            return models
            
        except botocore.exceptions.ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            
            if error_code == "UnrecognizedClientException":
                self.logger.warning(f"Bedrock is not available in region {region}")
            else:
                self.logger.warning(f"Error scanning region {region}: {error_code} - {error_message}")
            
            return []
        except Exception as e:
            self.logger.warning(f"Unexpected error scanning region {region}: {str(e)}")
            return []
    
    def _get_all_regions(self) -> List[str]:
        """
        [Method intent]
        Get list of all AWS regions where Bedrock might be available.
        
        [Design principles]
        - Dynamic discovery of available regions
        - Combination of static and dynamic information
        - Fallback to known regions
        
        [Implementation details]
        - Uses initial known Bedrock regions
        - Attempts to discover all AWS regions
        - Filters for regions likely to have Bedrock
        - Returns unique list of regions to check
        
        Returns:
            List of region names to check for Bedrock availability
        """
        regions_to_check = set(self.INITIAL_BEDROCK_REGIONS)
        
        try:
            # Get EC2 client to list all AWS regions
            ec2_client = self.client_factory.get_client('ec2', region_name='us-east-1')
            response = ec2_client.describe_regions()
            
            # Add all AWS regions to the list
            for region in response['Regions']:
                regions_to_check.add(region['RegionName'])
                
        except Exception as e:
            self.logger.warning(f"Failed to discover all AWS regions: {str(e)}")
            self.logger.warning("Using initial regions list only")
            
        return list(regions_to_check)
    
    def get_model_regions(self, model_id: str) -> List[str]:
        """
        [Method intent]
        Get all regions where a specific model is available.
        
        [Design principles]
        - Cache-first approach for efficiency
        - On-demand scanning when needed
        - Clear error reporting
        
        [Implementation details]
        - Checks cache for regions with model available
        - Falls back to full scan if model not found in cache
        - Returns list of regions with model
        - Handles model variants appropriately
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            List of region names where the model is available
        """
        available_regions = []
        
        # Get model mapping from cache
        model_mapping = self.cache.get_model_mapping()
        
        # Check each region for the model
        for region, models in model_mapping.get("models", {}).items():
            if model_id in models:
                available_regions.append(region)
                
        return available_regions
    
    def get_best_regions_for_model(
        self,
        model_id: str,
        preferred_regions: Optional[List[str]] = None
    ) -> List[str]:
        """
        [Method intent]
        Get the best regions for a specific model, with optimization for latency 
        and respect for user preferences.
        
        [Design principles]
        - User preference priority
        - Latency-based ordering for optimal performance
        - Complete model availability information
        
        [Implementation details]
        - Gets all available regions for the model
        - Prioritizes user's preferred regions when specified
        - Sorts remaining regions by measured latency
        - Returns ordered list from fastest to slowest
        
        Args:
            model_id: The Bedrock model ID
            preferred_regions: Optional list of preferred AWS regions
            
        Returns:
            List of region names ordered by preference and latency
        """
        # Get all regions where the model is available
        available_regions = self.get_model_regions(model_id)
        
        if not available_regions:
            return []
            
        # If preferred regions specified, prioritize those first
        result = []
        other_regions = available_regions.copy()
        
        if preferred_regions:
            # Add preferred regions that are available, maintaining preference order
            for region in preferred_regions:
                if region in available_regions:
                    result.append(region)
                    other_regions.remove(region)
        
        # Sort remaining regions by latency (from lowest to highest)
        sorted_by_latency = self.latency_tracker.get_sorted_regions(other_regions)
        result.extend(sorted_by_latency)
        
        return result
    
    def is_model_available_in_region(self, model_id: str, region: str) -> bool:
        """
        [Method intent]
        Check if a specific model is available in a given region.
        
        [Design principles]
        - Cache-first approach
        - Direct checking for efficiency
        - Clear availability reporting
        
        [Implementation details]
        - Checks cache first for fast response
        - Falls back to direct API check if needed
        - Updates cache with discovery results
        - Returns boolean indicating availability
        
        Args:
            model_id: The Bedrock model ID
            region: AWS region to check
            
        Returns:
            True if the model is available in the region, False otherwise
        """
        # Check cache first
        region_models = self.cache.get_models_by_region(region)
        if region_models and model_id in region_models:
            return True
        
        # If not in cache or cache expired, check directly
        try:
            # Scan region directly
            models_list = self._scan_region(region)
            
            if not models_list:
                return False
            
            # Convert list to dict for cache format
            model_dict = {}
            for model in models_list:
                model_id_key = model.get("modelId")
                if model_id_key:
                    model_dict[model_id_key] = model
            
            # Update cache with new structure
            self.cache.save_models_by_region(region, model_dict)
            
            # Check if model is available
            return model_id in model_dict
            
        except Exception as e:
            self.logger.warning(f"Error checking model availability in {region}: {str(e)}")
            return False
    
    def get_all_models(self) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get information about all available models across all regions.
        
        [Design principles]
        - Complete model discovery
        - Deduplication across regions
        - Comprehensive metadata
        
        [Implementation details]
        - Retrieves model mapping from cache
        - Combines model information across regions
        - Deduplicates by model ID
        - Maps models to available regions
        
        Returns:
            List of dicts with model information across all regions
        """
        # Get model mapping from cache
        model_mapping = self.cache.get_model_mapping()
        
        # Create model ID to model info mapping
        model_map = {}
        model_regions = {}
        
        # Process models from all regions
        for region, models in model_mapping.get("models", {}).items():
            for model_id, model in models.items():
                # Track which regions have this model
                if model_id not in model_regions:
                    model_regions[model_id] = []
                model_regions[model_id].append(region)
                
                # Store or update model info
                if model_id not in model_map:
                    model_map[model_id] = copy.deepcopy(model)
        
        # Add region availability to model info
        for model_id, model_info in model_map.items():
            model_info["availableRegions"] = model_regions.get(model_id, [])
        
        # Return as a list
        return list(model_map.values())
    
    def get_json_model_mapping(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Get the complete model mapping in the exact structure of bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Consistent with external JSON format
        - Complete model and profile information
        - Direct compatibility with raw_api_profile_test.py
        
        [Implementation details]
        - Uses cache's get_model_mapping method
        - Returns complete nested structure with regions and models
        - Format is {"models": {region: {model_id: model_details}}}
        
        Returns:
            Dict with structure matching bedrock_model_profile_mapping.json
        """
        return self.cache.get_model_mapping()
    
    def _get_project_supported_models(self) -> List[str]:
        """
        [Method intent]
        Get the list of Bedrock models supported by the project from model classes.
        
        [Design principles]
        - Dynamic model discovery from project files
        - No hardcoding of model IDs
        - Centralized model reference list
        
        [Implementation details]
        - Imports model classes dynamically to avoid circular imports
        - Extracts SUPPORTED_MODELS class variables from model classes
        - Handles import errors gracefully
        - Returns consolidated list of model IDs
        
        Returns:
            List[str]: List of model IDs supported by project model classes
        """
        supported_models = []
        
        try:
            # Import model classes dynamically to avoid circular imports
            from ..models.claude3 import ClaudeClient
            supported_models.extend(ClaudeClient.SUPPORTED_MODELS)
            self.logger.debug(f"Found {len(ClaudeClient.SUPPORTED_MODELS)} Claude models")
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Could not load Claude models: {str(e)}")
        
        try:
            from ..models.nova import NovaClient
            supported_models.extend(NovaClient.SUPPORTED_MODELS)
            self.logger.debug(f"Found {len(NovaClient.SUPPORTED_MODELS)} Nova models")
        except (ImportError, AttributeError) as e:
            self.logger.warning(f"Could not load Nova models: {str(e)}")
            
        # Deduplicate the list
        return list(set(supported_models))
    
    def get_model(self, model_id: str, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get detailed information about a specific model, optionally from a specific region.
        Includes associated inference profiles if available.
        
        [Design principles]
        - Complete model information retrieval
        - Profile association when available
        - Latency-optimized region selection
        - Deep copy to prevent cache modification
        
        [Implementation details]
        - Determines best region if not specified
        - Retrieves model data from cache or API
        - Includes associated inference profiles
        - Returns copy of data to prevent cache modification
        
        Args:
            model_id: The Bedrock model ID
            region: Optional specific region to get the model from
            
        Returns:
            Dict with complete model information or None if not found
        """
        # If region not specified, find the best region for this model
        if not region:
            regions = self.get_best_regions_for_model(model_id)
            if not regions:
                return None
            region = regions[0]
        
        # Get models for the specified region
        region_models = self.cache.get_models_by_region(region)
        if not region_models:
            return None
            
        # Check if the model exists in this region
        if model_id in region_models:
            # Return a deep copy to prevent modifying the cache
            return copy.deepcopy(region_models[model_id])
                
        return None
        
    def clear_cache(self) -> None:
        """
        [Method intent]
        Clear all cached model data.
        
        [Design principles]
        - Complete cache clearing
        - Thread safety
        
        [Implementation details]
        - Removes all model mapping from cache
        - Saves updated cache state to disk
        - Logs clearing operations
        
        Returns:
            None
        """
        try:
            # Clear the models key from memory cache
            with self.cache._cache_lock:
                if "models" in self.cache._memory_cache:
                    del self.cache._memory_cache["models"]
            
            # Save updated cache state to disk
            try:
                self.cache.save()
            except Exception as save_err:
                self.logger.warning(f"Failed to save cache after clearing: {str(save_err)}")
                
            self.logger.info("Model discovery cache cleared")
        except Exception as e:
            self.logger.warning(f"Error clearing model cache: {str(e)}")
