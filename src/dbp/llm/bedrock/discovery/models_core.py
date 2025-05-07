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
# Provides core functionality for discovering AWS Bedrock models across regions.
# Handles model discovery through parallel scanning and region prioritization 
# to provide efficient access to Bedrock foundation models.
# Part of a split architecture with models_capabilities.py extending this functionality.
###############################################################################
# [Source file design principles]
# - Efficient parallel scanning using ThreadPoolExecutor
# - Thread-safe operations for concurrent access
# - Latency-optimized region selection
# - Comprehensive model metadata extraction
# - Singleton pattern for project-wide reuse
# - Clear separation between core discovery and extended capabilities
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must minimize AWS API calls through effective caching
# - Must provide optimal region selection for best performance
# - Must handle AWS credential management securely
# - Must support extension through inheritance for additional capabilities
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
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
# 2025-05-06T23:23:00Z : Created models_core.py as part of models.py file split by CodeAssistant
# * Split from original models.py file
# * Extracted core discovery functionality into separate file
# * Preserved singleton pattern for use with extended capabilities class
# * Maintained backward compatibility with existing code
###############################################################################

import logging
import threading
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Set, Union, Tuple, Callable

import boto3
import botocore.exceptions

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from ....llm.common.exceptions import ModelNotAvailableError

from .discovery_core import BaseDiscovery
from .scan_utils import scan_region
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
    - Provides latency-based sorting of regions
    - Maps model availability by region
    - Simplifies API with sensible defaults
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, scan_on_init: bool = False):
        """
        [Method intent]
        Get the singleton instance of BedrockModelDiscovery, creating it if needed.
        
        [Design principles]
        - Thread-safe singleton access
        - Lazy initialization
        - Simple interface with sensible defaults
        
        [Implementation details]
        - Double-checked locking pattern
        - Creates instance only when first needed
        - Returns same instance for all callers
        - Performs initial scan only when requested
        
        Args:
            scan_on_init: If True, perform initial region scan when instance is created
            
        Returns:
            BedrockModelDiscovery: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create a new instance with simplified initialization
                    cls._instance = cls()
                    
                    # Optionally perform initial scan
                    if scan_on_init:
                        cls._instance.scan_all_regions()
        
        return cls._instance
    
    def __init__(self):
        """
        [Method intent]
        Initialize the BedrockModelDiscovery singleton with simplified internals.
        
        [Design principles]
        - Protected constructor for singleton pattern
        - Minimal dependencies
        - Simple initialization
        - Integrated cache management
        
        [Implementation details]
        - Gets required dependencies directly
        - Uses integrated caching instead of external components
        - Creates a single lock for thread safety
        - Loads supported models automatically
        """
        # Enforce singleton pattern
        if self.__class__._instance is not None:
            raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
            
        # Initialize base class
        super().__init__(
            client_factory=AWSClientFactory.get_instance(),
            logger=logging.getLogger(__name__)
        )
        
        # Initialize simple internal cache
        self._memory_cache = {
            "models": {},
            "latency": {},
            "last_updated": {}
        }
        
        # Get project supported models from client_factory
        from ..client_factory import get_all_supported_model_ids
        self.project_supported_models = get_all_supported_model_ids()
        self.logger.info(f"Loaded {len(self.project_supported_models)} project-supported models")
    
    def scan_all_regions(
        self, 
        regions: Optional[List[str]] = None, 
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Scan AWS regions for Bedrock models, either using cache or forcing a fresh scan.
        
        [Design principles]
        - Single entry point for scanning
        - Cache-first approach by default
        - Clean and simple parameter interface
        
        [Implementation details]
        - Uses regions param or defaults to known Bedrock regions
        - With force_refresh=True, performs new API calls
        - Without force_refresh, uses cached data when available
        - Updates internal cache with results
        - Returns consistent structure with models by region
        
        Args:
            regions: Optional list of regions to scan (defaults to known Bedrock regions)
            force_refresh: If True, bypasses cache and performs fresh API calls
            
        Returns:
            Dict with structure {"models": {region: {model_id: model_details}}}
        """
        result = {"models": {}}
        
        # Determine regions to scan
        regions_to_scan = regions or self.get_all_regions()
        
        # Check if we can use cache
        if not force_refresh:
            with self._lock:
                cached_models = self._memory_cache.get("models", {})
                
                # Use cached data when available
                for region in regions_to_scan:
                    if region in cached_models:
                        result["models"][region] = cached_models[region]
        
        # Determine which regions need scanning
        missing_regions = [r for r in regions_to_scan if r not in result.get("models", {})]
        
        if missing_regions or force_refresh:
            # Scan missing or all regions in parallel
            to_scan = regions_to_scan if force_refresh else missing_regions
            self.logger.info(f"Scanning {len(to_scan)} regions for Bedrock models")
            
            # Define region scan function for parallel scanner
            def scan_region_wrapper(region):
                models, profiles = scan_region(
                    region=region,
                    client_factory=self.client_factory,
                    project_models=self.project_supported_models,
                    latency_callback=self.update_latency,
                    logger=self.logger
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
                
                return model_dict
            
            # Use parallel scanning from base class
            total_regions = len(to_scan)
            scanned_regions = 0
            
            # Define a progress callback wrapper
            def scan_with_progress(region):
                nonlocal scanned_regions
                result = scan_region_wrapper(region)
                scanned_regions += 1
                if progress_callback:
                    progress_callback(scanned_regions, total_regions)
                return result
            
            scan_results = self.scan_regions_parallel(
                regions=to_scan,
                scan_function=scan_with_progress
            )
            
            # Update result and cache with scan results
            with self._lock:
                for region, model_dict in scan_results.items():
                    result["models"][region] = model_dict
                    
                    # Update cache
                    if "models" not in self._memory_cache:
                        self._memory_cache["models"] = {}
                    self._memory_cache["models"][region] = model_dict
                
                # Update last updated timestamp
                if "last_updated" not in self._memory_cache:
                    self._memory_cache["last_updated"] = {}
                self._memory_cache["last_updated"]["models"] = time.time()
        
        return result
    
    def get_model_regions(self, model_id: str, check_accessibility: bool = True) -> List[str]:
        """
        [Method intent]
        Get all regions where a specific model is available and optionally accessible.
        
        [Design principles]
        - Cache-first approach for efficiency
        - Accessibility filtering when required
        - Clear error reporting
        
        [Implementation details]
        - Checks cache for regions with model available
        - When check_accessibility=True, filters to only include regions where the model is accessible
        - Returns list of regions with model
        - Handles model variants appropriately
        
        Args:
            model_id: The Bedrock model ID
            check_accessibility: If True, only returns regions where the model is accessible
                
        Returns:
            List of region names where the model is available and accessible (if check_accessibility=True)
        """
        available_regions = []
        
        # Get model mapping from cache
        with self._lock:
            cached_models = self._memory_cache.get("models", {})
            
            # Check each region for the model
            for region, models in cached_models.items():
                if model_id in models:
                    # If check_accessibility is True, only include regions
                    # where the model is marked as accessible
                    if check_accessibility:
                        if models[model_id].get("accessible", True):
                            available_regions.append(region)
                    else:
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
        - Restricts to accessible regions only
        
        [Implementation details]
        - Gets all available regions where the model is accessible
        - Prioritizes user's preferred regions when specified
        - Sorts remaining regions by measured latency
        - Returns ordered list from fastest to slowest
        
        Args:
            model_id: The Bedrock model ID
            preferred_regions: Optional list of preferred AWS regions
            
        Returns:
            List of region names ordered by preference and latency
        """
        # Get all regions where the model is available and accessible
        available_regions = self.get_model_regions(model_id, check_accessibility=True)
        
        if not available_regions:
            return []
            
        # If preferred regions specified, prioritize those first
        result = []
        remaining_regions = available_regions.copy()
        
        if preferred_regions:
            # Add preferred regions that are available, maintaining preference order
            for region in preferred_regions:
                if region in available_regions:
                    result.append(region)
                    remaining_regions.remove(region)
        
        # Sort remaining regions by latency (from lowest to highest)
        with self._lock:
            region_latencies = self._memory_cache.get("latency", {})
        
        # Sort by latency if available, otherwise keep current order
        sorted_regions = sorted(
            remaining_regions,
            key=lambda r: region_latencies.get(r, float('inf'))
        )
        
        result.extend(sorted_regions)
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
        with self._lock:
            cached_models = self._memory_cache.get("models", {}).get(region, {})
            if cached_models and model_id in cached_models:
                return True
        
        # If not in cache, perform a scan for this region
        try:
            region_data = self.scan_all_regions(regions=[region])
            if region in region_data.get("models", {}) and model_id in region_data["models"].get(region, {}):
                return True
            return False
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
        with self._lock:
            cached_models = self._memory_cache.get("models", {})
        
        # Create model ID to model info mapping
        model_map = {}
        model_regions = {}
        
        # Process models from all regions
        for region, models in cached_models.items():
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
            Dict with complete model information or None if not found. The return structure includes:
            
            - Basic Model Information (populated from AWS ListFoundationModels API):
              - modelId (str): ID of the Bedrock model
              - modelName (str): Human-readable name of the model
              - provider (str): Provider name (e.g., "Anthropic", "Amazon")
              - status (str): Model status (typically "ACTIVE")
              - requiresInferenceProfile (bool): Whether model requires inference profile
              - accessible (bool): Whether model is accessible with current credentials
            
            - Capability Information (populated from AWS ListFoundationModels API):
              - capabilities (List[str]): Model capabilities (e.g., ["TEXT"])
              - inputModalities (List[str]): Input modalities supported
              - outputModalities (List[str]): Output modalities supported
              - responseStreamingSupported (bool): Whether streaming is supported
            
            - Detailed Model Information (populated from AWS GetFoundationModel API):
              - modelDetails (Dict): Complete model details including:
                - modelArn (str): ARN of the model
                - modelId (str): ID of the model
                - modelName (str): Human-readable name of the model
                - providerName (str): Model provider
                - inputModalities (List[str]): Input modalities
                - outputModalities (List[str]): Output modalities
                - responseStreamingSupported (bool): Streaming support
                - customizationsSupported (List[str]): Supported customizations
                - inferenceTypesSupported (List[str]): Supported inference types
                - modelLifecycle (Dict): Model lifecycle info
            
            - Availability Information (populated from AWS BedrockAgent::GetModelCustomizationJobOrFoundationModelAvailability API):
              - availabilityDetails (Dict): Model availability details:
                - agreementAvailability (Dict): Agreement availability status
                - authorizationStatus (str): Authorization status
                - entitlementAvailability (str): Entitlement availability
                - regionAvailability (str): Region availability status
                - accessible (bool): Whether model is accessible
                - modelId (str): Model ID
            
            - Associated Inference Profiles (populated from AWS ListInferenceProfiles API):
              - referencedByInstanceProfiles (List[Dict]): Associated profiles:
                - inferenceProfileId (str): Profile ID
                - inferenceProfileName (str): Profile name
                - inferenceProfileArn (str): Profile ARN
                - description (str): Profile description
                - status (str): Profile status
                - type (str): Profile type
                - region (str): Region where profile is available
                - models (List[Dict]): Models associated with this profile
                - modelArns (List[str]): Model ARNs associated with profile
        """
        # If region not specified, find the best region for this model
        if not region:
            regions = self.get_best_regions_for_model(model_id)
            if not regions:
                # Raise error if no regions available for this model
                raise ModelNotAvailableError(
                    model_name=model_id,
                    message=f"Model '{model_id}' is not available in any region",
                    context={
                        "model_id": model_id,
                        "attempted_regions": self.get_all_regions()
                    }
                )
            region = regions[0]
        
        # Get models for the specified region
        with self._lock:
            cached_region_models = self._memory_cache.get("models", {}).get(region, {})
        
        # Check if the model exists in this region
        if cached_region_models and model_id in cached_region_models:
            # Return a deep copy to prevent modifying the cache
            model_data = copy.deepcopy(cached_region_models[model_id])
            # Add region information to the returned data
            model_data["region"] = region
            return model_data
        
        # If not in cache, try a fresh scan of this region
        try:
            region_data = self.scan_all_regions(regions=[region], force_refresh=True)
            if region in region_data.get("models", {}) and model_id in region_data["models"].get(region, {}):
                model_data = copy.deepcopy(region_data["models"][region][model_id])
                # Add region information to the returned data
                model_data["region"] = region
                return model_data
        except Exception as e:
            self.logger.warning(f"Error retrieving model {model_id} from region {region}: {str(e)}")
        
        # Raise exception if model not found
        region_display = region if region else "any region"
        raise ModelNotAvailableError(
            model_name=model_id,
            message=f"Model '{model_id}' is not available in {region_display}",
            context={
                "model_id": model_id,
                "region": region,
                "attempted_regions": [region] if region else self.get_best_regions_for_model(model_id)
            }
        )
    
    def get_json_model_mapping(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Get the complete model mapping in the exact structure of bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Consistent with external JSON format
        - Complete model and profile information
        
        [Implementation details]
        - Returns complete nested structure with regions and models
        - Format is {"models": {region: {model_id: model_details}}}
        
        Returns:
            Dict with structure matching bedrock_model_profile_mapping.json
        """
        with self._lock:
            models = self._memory_cache.get("models", {})
            
        # Format to match expected structure
        return {"models": copy.deepcopy(models)}

    def update_latency(self, region: str, latency_seconds: float) -> None:
        """
        [Method intent]
        Update the latency measurement for a specific region.
        
        [Design principles]
        - Simple latency tracking
        - Thread-safe updates
        - Basic exponential smoothing
        
        [Implementation details]
        - Uses exponential smoothing with alpha=0.3
        - Thread-safe updates to shared latency data
        - Maintains history for region sorting
        
        Args:
            region: AWS region name
            latency_seconds: Measured latency in seconds
        """
        alpha = 0.3  # Smoothing factor
        
        with self._lock:
            latency_data = self._memory_cache.setdefault("latency", {})
            current = latency_data.get(region)
            
            if current is None:
                # First measurement
                latency_data[region] = latency_seconds
            else:
                # Exponential smoothing
                latency_data[region] = (alpha * latency_seconds) + ((1 - alpha) * current)
