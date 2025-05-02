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
# Provides a comprehensive model discovery mechanism for AWS Bedrock across all
# regions. Enables applications to find where specific models are available and
# determine the optimal region for model usage based on availability and preferences.
###############################################################################
# [Source file design principles]
# - Parallel processing for efficient discovery across many regions
# - Complete model discovery beyond just supported models
# - Thread-safe caching with configurable TTL
# - Persistent caching to disk for weekly refresh cycle
# - Prioritization based on user preferences
# - Clear separation from pricing concerns
###############################################################################
# [Source file constraints]
# - Must handle AWS API throttling gracefully
# - Must maintain minimal memory footprint for cache
# - Must be thread-safe for all operations
# - Must respect AWS credentials and region configuration
# - Must be compatible with AWS API changes
# - Must persist cache to file for long-term access
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# codebase:src/dbp/config/default_config.py
# system:boto3
# system:botocore
# system:concurrent.futures
###############################################################################
# [GenAI tool change history]
# 2025-05-02T22:02:00Z : Production implementation by CodeAssistant
# * Moved implementation from scratchpad to production codebase
# * Finalized thread-safe design and caching mechanisms
# * Implemented comprehensive error handling and recovery
# 2025-05-02T15:44:00Z : Initial implementation skeleton by CodeAssistant
# * Created basic structure for BedrockModelDiscovery class
# * Added method signatures with detailed documentation
# * Implemented core caching, region discovery, and file persistence mechanisms
###############################################################################

import os
import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

import boto3
import botocore.exceptions
from botocore.config import Config

from ..common.exceptions import LLMError, ClientError, ModelNotAvailableError
from ...config.default_config import GENERAL_DEFAULTS  # For .dbp directory path


class BedrockModelDiscovery:
    """
    [Class intent]
    Provides comprehensive discovery of AWS Bedrock models across all regions.
    Handles caching of model availability, parallel scanning of regions, and 
    preference-based region selection with disk persistence for long-term caching.
    
    [Design principles]
    - Parallel processing for efficient multi-region operations
    - Full model discovery with complete metadata retention
    - Thread-safe caching with configurable TTL
    - User preference prioritization for region selection
    - Persistent caching with weekly refresh cycle
    - Clear separation from pricing concerns
    
    [Implementation details]
    - Uses ThreadPoolExecutor for parallel region scanning
    - Maintains thread-safe cache with region-model mapping
    - Persists cache to file in .dbp/ directory
    - Provides model discovery across AWS regions
    - Handles AWS credentials and region configuration
    """
    
    # Bedrock is not available in all AWS regions
    # This list can be dynamically updated through discovery
    INITIAL_BEDROCK_REGIONS = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", 
        "ap-southeast-1", "ap-southeast-2", "eu-central-1"
    ]
    
    # Cache time-to-live in seconds (1 hour for in-memory cache)
    DEFAULT_CACHE_TTL = 3600
    
    # Cache file settings
    CACHE_FILENAME = "bedrock_model_discovery.json"
    CACHE_FILE_TTL_DAYS = 7  # Refresh cache file once a week
    
    def __init__(
        self,
        cache_ttl_seconds: int = None,
        cache_file_ttl_days: int = None,
        initial_scan: bool = False,
        logger: logging.Logger = None,
        profile_name: Optional[str] = None,
        credentials: Optional[Dict[str, str]] = None
    ):
        """
        [Method intent]
        Initialize the Bedrock model discovery service with caching and authentication.
        
        [Design principles]
        - Configurable caching (both memory and disk)
        - Optional initial scanning
        - Credential management
        - Standard logging integration
        
        [Implementation details]
        - Sets up internal cache structures
        - Configures TTL for cache entries
        - Sets up file persistence paths
        - Initializes authentication
        - Optionally performs initial scan
        
        Args:
            cache_ttl_seconds: Time in seconds before in-memory cache entries expire (default: 1 hour)
            cache_file_ttl_days: Time in days before disk cache is considered stale (default: 7 days)
            initial_scan: Whether to perform an initial scan on initialization
            logger: Optional logger instance
            profile_name: AWS profile name for credentials (optional)
            credentials: Explicit AWS credentials (optional)
        """
        self._region_models_cache = {}
        self._cache_lock = Lock()
        self._cache_ttl_seconds = cache_ttl_seconds or self.DEFAULT_CACHE_TTL
        self._cache_file_ttl_days = cache_file_ttl_days or self.CACHE_FILE_TTL_DAYS
        self.logger = logger or logging.getLogger(__name__)
        
        # Store authentication configuration
        self.profile_name = profile_name
        self.credentials = credentials
        
        # Set up cache file path
        base_dir = os.path.expanduser(GENERAL_DEFAULTS["base_dir"])
        os.makedirs(base_dir, exist_ok=True)
        self._cache_file_path = os.path.join(base_dir, self.CACHE_FILENAME)
        
        
        # Try to load cache from file first
        cache_loaded = self._load_cache_from_file()
        
        # Perform initial scan if requested and cache was not loaded
        if initial_scan and not cache_loaded:
            self.scan_all_regions()
    
    def scan_all_regions(self, refresh_cache: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """
        [Method intent]
        Scan all AWS regions to discover Bedrock models and their availability.
        This method will cache ALL available models in each region, not just
        the ones supported in the codebase.
        
        [Design principles]
        - Persistent caching with file-based storage
        - Parallel scanning for efficiency
        - Complete model discovery
        - Cached results with refresh option
        - Comprehensive error handling
        
        [Implementation details]
        - Checks for valid cache file first
        - Uses ThreadPoolExecutor for parallel scanning when needed
        - Updates both in-memory and file-based cache with discovered models
        - Returns region to models mapping
        - Handles regions where Bedrock is not available
        
        Args:
            refresh_cache: Whether to force a refresh of cached data
            
        Returns:
            Dict mapping regions to lists of available models with metadata
        """
        result = {}
        discovered_regions = set()
        
        # If we're not forcing a refresh, try to use the cache file first
        if not refresh_cache and self._is_cache_file_valid():
            # If cache file is valid (exists and less than a week old), load it
            if self._load_cache_from_file():
                # Build result from loaded cache
                with self._cache_lock:
                    for region, region_data in self._region_models_cache.items():
                        result[region] = region_data["models"]
                        discovered_regions.add(region)
                
                # If we successfully loaded from cache file, return the result
                if result:
                    self.logger.info(f"Using cached model discovery data from {self._cache_file_path}")
                    return result
        
        # If we got here, we need to perform a scan (no valid cache or forced refresh)
        # Check if we have in-memory cached results and refresh is not forced
        if not refresh_cache:
            with self._cache_lock:
                if self._region_models_cache:
                    # Check if any cache entry is still valid
                    valid_entry = False
                    for region_data in self._region_models_cache.values():
                        if time.time() - region_data["timestamp"] < self._cache_ttl_seconds:
                            valid_entry = True
                            break
                    
                    if valid_entry:
                        # Build result from in-memory cache
                        for region, region_data in self._region_models_cache.items():
                            if time.time() - region_data["timestamp"] < self._cache_ttl_seconds:
                                result[region] = region_data["models"]
                                discovered_regions.add(region)
        
        # If we don't have valid cached results, perform discovery
        if not result:
            self.logger.info("Scanning AWS regions for Bedrock models...")
            # Get all regions to check
            regions_to_check = self._get_all_regions()
            
            # Use ThreadPoolExecutor to scan regions in parallel
            with ThreadPoolExecutor(max_workers=min(10, len(regions_to_check))) as executor:
                # Submit scanning tasks
                future_to_region = {
                    executor.submit(self._scan_region, region): region
                    for region in regions_to_check
                }
                
                # Process results as they complete
                for future in as_completed(future_to_region):
                    region = future_to_region[future]
                    try:
                        models = future.result()
                        if models:
                            result[region] = models
                            discovered_regions.add(region)
                            
                            # Update in-memory cache
                            with self._cache_lock:
                                self._region_models_cache[region] = {
                                    "timestamp": time.time(),
                                    "models": models
                                }
                    except Exception as e:
                        self.logger.warning(f"Error scanning region {region}: {str(e)}")
            
            # Update our known Bedrock regions based on discovery
            if discovered_regions:
                self.INITIAL_BEDROCK_REGIONS = list(discovered_regions)
            
            # Save to cache file
            self._save_cache_to_file()
        
        return result
    
    def get_model_regions(self, model_id: str) -> List[str]:
        """
        [Method intent]
        Get all regions where a specific model is available.
        
        [Design principles]
        - Cache-first approach for efficiency
        - On-demand scanning when needed
        - Clear error reporting
        
        [Implementation details]
        - Scans cache for regions with model available
        - Falls back to full scan if model not found in cache
        - Returns list of regions ordered by reliability
        - Handles model variants and versions appropriately
        
        Args:
            model_id: The Bedrock model ID
            
        Returns:
            List of region names where the model is available
        """
        available_regions = []
        
        # First, check if we have cached data
        found_in_cache = False
        with self._cache_lock:
            for region, region_data in self._region_models_cache.items():
                # Skip expired cache entries
                if time.time() - region_data["timestamp"] > self._cache_ttl_seconds:
                    continue
                
                # Check if the model is in this region
                for model in region_data["models"]:
                    if model["modelId"] == model_id:
                        available_regions.append(region)
                        found_in_cache = True
                        break
        
        # If not found in cache, perform a scan
        if not found_in_cache:
            region_models = self.scan_all_regions()
            
            # Check all regions for the model
            for region, models in region_models.items():
                for model in models:
                    if model["modelId"] == model_id:
                        available_regions.append(region)
                        break
        
        return available_regions
    
    def get_best_regions_for_model(
        self,
        model_id: str,
        preferred_regions: List[str] = None
    ) -> List[str]:
        """
        [Method intent]
        Get the best regions for a specific model, with optional preference.
        
        [Design principles]
        - User preference priority
        - Fallback to availability-based ordering
        - Complete information for decision making
        
        [Implementation details]
        - Gets all available regions for the model
        - Prioritizes user's preferred regions when specified
        - Returns ordered list of regions from best to worst
        - Handles model variants and versions appropriately
        
        Args:
            model_id: The Bedrock model ID
            preferred_regions: Optional list of preferred AWS regions
            
        Returns:
            List of region names ordered by preference/availability
        """
        # Get all regions where the model is available
        available_regions = self.get_model_regions(model_id)
        
        if not available_regions:
            return []
        
        # Filter by preferred regions if specified
        if preferred_regions:
            # First include preferred regions that are available
            result = [region for region in preferred_regions if region in available_regions]
            
            # Then add any other available regions not in preferred list
            other_regions = [region for region in available_regions if region not in preferred_regions]
            result.extend(other_regions)
            
        else:
            # If no preferences, use all available regions
            result = available_regions
        
        
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
        - Handles model variants and versions
        - Updates cache with discovery results
        
        Args:
            model_id: The Bedrock model ID
            region: AWS region to check
            
        Returns:
            True if the model is available in the region, False otherwise
        """
        # First check cache
        with self._cache_lock:
            if region in self._region_models_cache:
                region_data = self._region_models_cache[region]
                
                # Skip expired cache entries
                if time.time() - region_data["timestamp"] <= self._cache_ttl_seconds:
                    # Check if model is in this region
                    for model in region_data["models"]:
                        if model["modelId"] == model_id:
                            return True
        
        # If not in cache or cache expired, check directly
        try:
            models = self._scan_region(region)
            
            # Update cache
            with self._cache_lock:
                self._region_models_cache[region] = {
                    "timestamp": time.time(),
                    "models": models
                }
            
            # Check if model is available
            for model in models:
                if model["modelId"] == model_id:
                    return True
            
            # Model not found in region
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking model availability in {region}: {str(e)}")
            return False
    
    def clear_cache(self) -> None:
        """
        [Method intent]
        Clear all cached model data, both in-memory and on disk.
        
        [Design principles]
        - Complete cache clearing
        - Thread safety for concurrent operations
        
        [Implementation details]
        - Clears in-memory cache with proper locking
        - Removes cache file if it exists
        - Logs cache clearing operations
        
        Returns:
            None
        """
        # Clear in-memory cache
        with self._cache_lock:
            self._region_models_cache.clear()
        
        # Remove cache file if it exists
        try:
            if os.path.exists(self._cache_file_path):
                os.remove(self._cache_file_path)
                self.logger.info(f"Removed cache file: {self._cache_file_path}")
        except Exception as e:
            self.logger.warning(f"Error removing cache file: {str(e)}")
            
        self.logger.info("Model discovery cache cleared")
    
    def _get_all_regions(self) -> List[str]:
        """
        [Method intent]
        Get list of all AWS regions where Bedrock might be available.
        
        [Design principles]
        - Dynamic discovery of available regions
        - Combination of static and dynamic information
        
        [Implementation details]
        - Uses initial known Bedrock regions
        - Optionally discovers all AWS regions
        - Filters for regions likely to have Bedrock
        - Returns unique list of regions to check
        
        Returns:
            List of region names to check for Bedrock availability
        """
        regions_to_check = set(self.INITIAL_BEDROCK_REGIONS)
        
        try:
            # Create boto3 session based on credentials
            session_kwargs = {}
            if self.profile_name:
                session_kwargs["profile_name"] = self.profile_name
            
            session = boto3.Session(**session_kwargs)
            
            # Discover all AWS regions using EC2
            ec2 = session.client('ec2', region_name='us-east-1')
            response = ec2.describe_regions()
            
            # Add all AWS regions to the list
            for region in response['Regions']:
                regions_to_check.add(region['RegionName'])
                
        except Exception as e:
            self.logger.warning(f"Failed to discover all AWS regions: {str(e)}")
            self.logger.warning("Using initial regions list only")
            
        return list(regions_to_check)
    
    def _scan_region(self, region: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Scan a specific region for available Bedrock models.
        
        [Design principles]
        - Complete model discovery
        - Robust error handling
        - Full metadata collection
        
        [Implementation details]
        - Creates regional Bedrock client
        - Lists available foundation models
        - Extracts model attributes
        - Filters for active models only
        - Handles API errors gracefully
        
        Args:
            region: AWS region to scan
            
        Returns:
            List of dicts with model information in the region
        """
        try:
            # Create Bedrock client for this region
            bedrock_client = self._create_bedrock_client(region)
            
            # List available foundation models
            response = bedrock_client.list_foundation_models()
            
            # Extract model information
            models = []
            for model_summary in response.get("modelSummaries", []):
                # Check if model is active
                model_status = model_summary.get("modelLifecycle", {}).get("status")
                if model_status != "ACTIVE":
                    continue
                
                # Extract model attributes
                model_info = {
                    "modelId": model_summary["modelId"],
                    "modelName": model_summary.get("modelName", ""),
                    "provider": model_summary.get("providerName", ""),
                    "capabilities": [],
                    "status": model_status
                }
                
                # Extract capabilities if available
                if "outputModalities" in model_summary:
                    model_info["capabilities"].extend(model_summary["outputModalities"])
                
                if "inferenceTypes" in model_summary:
                    for inference_type in model_summary["inferenceTypes"]:
                        if inference_type == "ON_DEMAND":
                            model_info["capabilities"].append("on-demand")
                        elif inference_type == "PROVISIONED":
                            model_info["capabilities"].append("provisioned")
                
                models.append(model_info)
            
            self.logger.info(f"Found {len(models)} active models in region {region}")
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
    
    def _create_bedrock_client(self, region: str) -> Any:
        """
        [Method intent]
        Create an AWS Bedrock client for a specific region.
        
        [Design principles]
        - Consistent client creation
        - Authentication handling
        - Error handling for unavailable regions
        
        [Implementation details]
        - Creates boto3 session with credentials if provided
        - Creates Bedrock client for specified region
        - Handles client creation errors
        - Applies proper timeouts
        
        Args:
            region: AWS region for client
            
        Returns:
            boto3.client: Bedrock client for the specified region
            
        Raises:
            ClientError: If client creation fails
        """
        try:
            # Create session with proper credentials
            session_kwargs = {}
            client_kwargs = {
                "region_name": region,
                "config": Config(
                    retries={"max_attempts": 3},
                    connect_timeout=10,
                    read_timeout=15
                )
            }
            
            if self.profile_name:
                session_kwargs["profile_name"] = self.profile_name
            
            if self.credentials:
                client_kwargs.update({
                    "aws_access_key_id": self.credentials.get("aws_access_key_id"),
                    "aws_secret_access_key": self.credentials.get("aws_secret_access_key"),
                    "aws_session_token": self.credentials.get("aws_session_token")
                })
            
            session = boto3.Session(**session_kwargs)
            return session.client("bedrock", **client_kwargs)
            
        except Exception as e:
            raise ClientError(f"Failed to create Bedrock client for region {region}: {str(e)}")
    
    def _is_cache_file_valid(self) -> bool:
        """
        [Method intent]
        Check if the cache file exists and is still valid (less than a week old).
        
        [Design principles]
        - Clear validation criteria
        - Configurable TTL in days
        
        [Implementation details]
        - Checks file existence
        - Verifies file age against TTL
        - Handles file access errors gracefully
        
        Returns:
            bool: True if cache file is valid, False otherwise
        """
        try:
            # Check if cache file exists
            if not os.path.exists(self._cache_file_path):
                return False
            
            # Check if cache file is still valid (less than a week old)
            file_age_seconds = time.time() - os.path.getmtime(self._cache_file_path)
            max_age_seconds = self._cache_file_ttl_days * 24 * 60 * 60
            
            return file_age_seconds < max_age_seconds
            
        except Exception as e:
            self.logger.warning(f"Error checking cache file validity: {str(e)}")
            return False
    
    def _load_cache_from_file(self) -> bool:
        """
        [Method intent]
        Load model discovery cache from file if available and valid.
        
        [Design principles]
        - Graceful fallback on errors
        - Complete state restoration
        - Thread safety for updates
        
        [Implementation details]
        - Reads cache file if it exists
        - Validates file format and content
        - Updates in-memory cache with file contents
        - Handles file access and parsing errors
        
        Returns:
            bool: True if cache was successfully loaded, False otherwise
        """
        try:
            # Check if cache file exists
            if not os.path.exists(self._cache_file_path):
                return False
            
            # Read cache file
            with open(self._cache_file_path, 'r') as f:
                data = json.load(f)
            
            # Validate cache file structure
            if not isinstance(data, dict) or "version" not in data or "timestamp" not in data or "regions" not in data:
                self.logger.warning("Invalid cache file format, will perform full scan")
                return False
            
            # Check if cache is still valid
            file_timestamp = data["timestamp"]
            if time.time() - file_timestamp > self._cache_file_ttl_days * 24 * 60 * 60:
                self.logger.info("Cache file is too old, will perform full scan")
                return False
            
            # Update in-memory cache with file contents
            with self._cache_lock:
                self._region_models_cache = {}
                for region, models in data["regions"].items():
                    self._region_models_cache[region] = {
                        "timestamp": file_timestamp,
                        "models": models
                    }
            
            self.logger.info(f"Loaded {len(data['regions'])} region(s) from cache file")
            return True
            
        except Exception as e:
            self.logger.warning(f"Error loading cache from file: {str(e)}")
            return False
    
    def _save_cache_to_file(self) -> None:
        """
        [Method intent]
        Save the current model discovery cache to a file.
        
        [Design principles]
        - Safe atomic file updates
        - Complete state persistence
        - Proper error handling
        
        [Implementation details]
        - Creates parent directories if needed
        - Uses atomic file write pattern (write to temp, then rename)
        - Handles file access and writing errors
        - Persists full region and model information
        
        Returns:
            None
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._cache_file_path), exist_ok=True)
            
            # Create cache file data structure
            data = {
                "version": "1.0",
                "timestamp": time.time(),
                "regions": {}
            }
            
            # Add region models to data
            with self._cache_lock:
                for region, region_data in self._region_models_cache.items():
                    data["regions"][region] = region_data["models"]
            
            # Write to a temporary file first, then rename for atomic operation
            temp_path = f"{self._cache_file_path}.tmp"
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2)
            
            # Rename temp file to actual cache file (atomic operation)
            os.replace(temp_path, self._cache_file_path)
            
            self.logger.info(f"Saved model discovery cache to {self._cache_file_path}")
            
        except Exception as e:
            self.logger.warning(f"Error saving cache to file: {str(e)}")
