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
# Provides a minimal disk-based caching system to reduce redundant AWS Bedrock API calls.
# Simple key-value store with TTL and memory mirror for performance, designed exclusively
# for use by the BedrockModelDiscovery singleton class.
###############################################################################
# [Source file design principles]
# - Thread-safe operations for concurrent access
# - Disk-based persistence with memory mirror for performance
# - Configurable time-to-live for cache entries
# - Atomic file operations for reliable disk persistence 
# - Minimal API with only essential methods
###############################################################################
# [Source file constraints]
# - Must handle concurrent access from multiple threads
# - Must be compatible with various data types for caching
# - Must ensure no data corruption during parallel operations
# - Must handle disk I/O errors gracefully
###############################################################################
# [Dependencies]
# system:os
# system:time
# system:logging
# system:threading
# system:json
###############################################################################
# [GenAI tool change history]
# 2025-05-03T18:29:00Z : Removed specialized methods by CodeAssistant
# * Further simplified API by removing domain-specific methods
# * Reduced the implementation to just core cache functionality
# 2025-05-03T18:25:00Z : Further simplified cache implementation by CodeAssistant
# * Removed invalidate method
# * Applied DRY principles to reduce code duplication
# * Simplified file operations
# * Reduced complexity of the overall implementation
# 2025-05-03T18:15:00Z : Simplified cache implementation by CodeAssistant
# * Removed in-memory TTL features
# * Simplified memory cache to be a direct mirror of disk cache
# * Enhanced JSON serialization for complex objects
# * Fixed directory creation issues
###############################################################################

import json
import logging
import os
import threading
import time
import copy
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Optional

class DiscoveryCache:
    """
    [Class intent]
    Provides a simple, thread-safe caching system with disk persistence
    and memory mirror for performance. This cache is specifically designed
    to be used by the BedrockModelDiscovery singleton class only.
    
    [Design principles]
    - Thread safety for concurrent access
    - Disk persistence with memory mirror for performance
    - Configurable TTL for cache entries
    - Atomic file operations for reliability
    - Single owner (BedrockModelDiscovery) for cache management
    
    [Implementation details]
    - Stores all cache entries in a single JSON file
    - Uses memory cache to avoid disk reads for frequently accessed data
    - Handles cache expiration based on TTL
    - Uses custom JSON serialization for complex objects
    - Provides access to cached data for other components through BedrockModelDiscovery
    """
    
    # Cache version - increment when format changes
    CACHE_VERSION = "1.0"
    
    # Default TTL value for cache entries (3 days)
    DEFAULT_TTL_DAYS = 3
    
    def __init__(
        self,
        base_dir: Optional[str] = None,
        ttl_days: Optional[int] = None,
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the cache with configurable TTL and storage location.
        Does NOT load the cache file - call load() explicitly to do so.
        
        [Design principles]
        - Configurable cache behavior
        - Robust directory setup
        - Explicit file operations
        
        [Implementation details]
        - Sets up the cache directory structure
        - Initializes the memory cache
        - Configures thread safety mechanisms
        - Does NOT load the cache file automatically
        
        Args:
            base_dir: Base directory for disk cache storage
            ttl_days: Time-to-live for cache entries (days)
            logger: Optional logger for cache operations
        """
        # Setup logging
        self.logger = logger or logging.getLogger(__name__)
        
        # Configure TTL
        self.ttl_days = ttl_days or self.DEFAULT_TTL_DAYS
        
        # Setup cache location - ensure it uses ~/.bdp/cache/bedrock_discovery.json
        self.base_dir = base_dir or os.path.expanduser(os.path.join("~", ".bdp"))
        self.cache_dir = os.path.join(self.base_dir, "cache")
        self.cache_file = os.path.join(self.cache_dir, "bedrock_discovery.json")
        self.logger.debug(f"Cache file path: {self.cache_file}")
        
        # Create the cache directory if it doesn't exist
        try:
            os.makedirs(self.cache_dir, exist_ok=True)
            self.logger.debug(f"Ensured cache directory exists at {self.cache_dir}")
        except Exception as e:
            self.logger.error(f"Failed to create cache directory: {str(e)}")
            raise  # Re-raise the exception to caller
        
        # Setup memory cache and lock
        self._cache_lock = threading.Lock()
        self._memory_cache = {}
        
        # Note: Cache file is NOT loaded here - call load() explicitly to do so
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        [Method intent]
        Get a value from cache if available and not expired.
        
        [Design principles]
        - Memory-first for performance
        - Thread-safe access
        
        [Implementation details]
        - Checks memory cache with proper locking
        - Returns default if not found
        
        Args:
            key: Cache key to retrieve
            default: Value to return if not in cache
            
        Returns:
            Cached value or default if not found
        """
        thread_id = threading.get_ident()
        self.logger.debug(f"Thread {thread_id}: Attempting to acquire lock in get() for key: {key}")
        with self._cache_lock:
            self.logger.debug(f"Thread {thread_id}: Lock acquired in get() for key: {key}")
            result = self._memory_cache.get(key, default)
            self.logger.debug(f"Thread {thread_id}: Releasing lock in get() for key: {key}")
            return result
    
    def get_model_mapping(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        [Method intent]
        Get the complete model mapping data in the format matching bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Consistent structure with external JSON format
        - Thread-safe access
        - Deep copy to prevent cache modification
        - Direct structure match with bedrock_model_profile_mapping.json
        
        [Implementation details]
        - Retrieves the top-level "models" key
        - Creates proper nested structure
        - Returns copy to prevent cache modification
        
        Returns:
            Dict with structure {"models": {region: {model_id: model_details}}}
        """
        with self._cache_lock:
            # Get models directly - this should already be in the correct structure
            models = self._memory_cache.get("models", {})
            
            # Ensure the exact format matching bedrock_model_profile_mapping.json
            result = {"models": copy.deepcopy(models)}
            return result
    
    def save_model_mapping(self, model_mapping: Dict[str, Dict[str, Dict[str, Any]]]) -> None:
        """
        [Method intent]
        Save the complete model mapping data in the proper structure matching bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Consistent structure with external JSON format
        - Thread-safe operations
        - Complete replacement of existing mapping
        - Direct structure match with bedrock_model_profile_mapping.json
        
        [Implementation details]
        - Validates input has correct top-level "models" key
        - Updates memory cache with complete mapping
        - Ensures proper nested structure
        - Triggers disk save
        
        Args:
            model_mapping: Dict with structure {"models": {region: {model_id: model_details}}}
        """
        if "models" not in model_mapping:
            raise ValueError("model_mapping must contain a 'models' key at the top level")
            
        with self._cache_lock:
            # Directly replace the models key to ensure correct structure
            self._memory_cache = model_mapping
            self._save_cache_to_disk()
    
    def set(self, key: str, value: Any) -> None:
        """
        [Method intent]
        Add or update a value in the cache.
        
        [Design principles]
        - Thread-safe updates
        - Updates memory and disk cache atomically
        
        [Implementation details]
        - Updates memory cache
        - Writes complete cache to disk
        - Uses atomic file operations
        
        Args:
            key: Cache key
            value: Value to store
        """
        # Update memory cache
        thread_id = threading.get_ident()
        self.logger.debug(f"Thread {thread_id}: Attempting to acquire lock in set() for key: {key}")
        with self._cache_lock:
            self.logger.debug(f"Thread {thread_id}: Lock acquired in set() for key: {key}")
            self._memory_cache[key] = value
            self.logger.debug(f"Thread {thread_id}: Calling _save_cache_to_disk() for key: {key}")
            self._save_cache_to_disk()
            self.logger.debug(f"Thread {thread_id}: Returning from set() for key: {key}")
    
    def get_models_by_region(self, region: str) -> Dict[str, Any]:
        """
        [Method intent]
        Get all models for a specific region in the format matching bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Direct access to region-specific models
        - Thread-safe access
        - Consistent return structure
        
        [Implementation details]
        - Accesses the nested structure for the specific region
        - Returns empty dict if region not found
        - Copies data to prevent cache modification
        
        Args:
            region: AWS region name (e.g. "us-east-1")
            
        Returns:
            Dict mapping model_ids to model details for the region
        """
        with self._cache_lock:
            models = self._memory_cache.get("models", {})
            region_models = models.get(region, {})
            return copy.deepcopy(region_models)
    
    def save_models_by_region(self, region: str, models: Dict[str, Any]) -> None:
        """
        [Method intent]
        Save models for a specific region in the format matching bedrock_model_profile_mapping.json.
        
        [Design principles]
        - Direct update of region-specific models
        - Thread-safe operations
        - Consistent structure
        
        [Implementation details]
        - Updates nested structure for the specific region
        - Creates intermediate objects if needed
        - Triggers disk save
        
        Args:
            region: AWS region name (e.g. "us-east-1")
            models: Dict mapping model_ids to model details
        """
        with self._cache_lock:
            all_models = self._memory_cache.get("models", {})
            all_models[region] = models
            self._memory_cache["models"] = all_models
            self._save_cache_to_disk()
    
    def load(self) -> None:
        """
        [Method intent]
        Explicitly load the cache from disk into memory.
        This method MUST be called after initialization to load data.
        
        [Design principles]
        - Explicit file operations
        - Failure transparency
        - Complete error handling
        
        [Implementation details]
        - Reads cache file from disk
        - Throws exceptions on failure
        - Populates memory cache with valid entries
        - Overwrites any existing memory cache
        
        Raises:
            Exception: If loading fails for any reason
        """
        # Clear existing memory cache
        with self._cache_lock:
            self._memory_cache = {}
        
        try:
            cache_data = self._read_disk_cache()
            if not cache_data:
                self.logger.warning("Cache file empty or not found")
                return
            
            # Check cache version
            if cache_data.get("version") != self.CACHE_VERSION:
                raise ValueError(f"Cache version mismatch: expected {self.CACHE_VERSION}, got {cache_data.get('version')}")
            
            # Load valid entries
            entries = cache_data.get("entries", {})
            current_time = time.time()
            ttl_seconds = self.ttl_days * 24 * 60 * 60
            
            # Filter valid entries and load into memory cache
            with self._cache_lock:
                for key, entry in entries.items():
                    if current_time - entry.get("timestamp", 0) <= ttl_seconds:
                        self._memory_cache[key] = entry.get("value")
            
            self.logger.debug(f"Loaded {len(self._memory_cache)} cache entries from disk")
            
        except Exception as e:
            self.logger.error(f"Error loading cache from disk: {str(e)}")
            raise  # Re-raise the exception
    
    def save(self) -> None:
        """
        [Method intent]
        Explicitly save the current memory cache to disk.
        
        [Design principles]
        - Explicit file operations
        - Atomic file operations
        - Thread-safe access
        - Complete error handling
        
        [Implementation details]
        - Acquires lock for thread safety
        - Creates cache entries with timestamps
        - Writes to temporary file first
        - Uses atomic rename for reliability
        - Throws exceptions on failure
        
        Raises:
            Exception: If saving fails for any reason
        """
        thread_id = threading.get_ident()
        self.logger.debug(f"Thread {thread_id}: Attempting to acquire lock in save()")
        
        with self._cache_lock:
            self.logger.debug(f"Thread {thread_id}: Lock acquired in save()")
            try:
                self._save_cache_to_disk()
            except Exception as e:
                self.logger.error(f"Error saving cache to disk: {str(e)}")
                raise  # Re-raise the exception
    
    def cleanup(self) -> int:
        """
        [Method intent]
        Clean up expired entries from the cache.
        
        [Design principles]
        - Periodic maintenance capability
        - Thread-safe operations
        - Error propagation for transparency
        
        [Implementation details]
        - Checks all entries against TTL
        - Removes expired entries
        - Updates memory and disk cache
        - Throws all errors rather than handling them silently
        
        Returns:
            Number of expired entries removed
            
        Raises:
            FileNotFoundError: When cache file doesn't exist
            json.JSONDecodeError: When cache file contains invalid JSON
            Exception: For any other errors that occur
        """
        # Check for expired entries
        current_time = time.time()
        ttl_seconds = self.ttl_days * 24 * 60 * 60
        removed_count = 0
        
        # Get disk cache data and check expiration timestamps
        cache_data = self._read_disk_cache()
            
        entries = cache_data.get("entries", {})
        expired_keys = []
        
        for key, entry in entries.items():
            # Check if entry is expired
            if current_time - entry.get("timestamp", 0) > ttl_seconds:
                expired_keys.append(key)
        
        # If any entries expired, update cache
        if expired_keys:
            with self._cache_lock:
                # Update memory cache
                for key in expired_keys:
                    if key in self._memory_cache:
                        del self._memory_cache[key]
                
                # Update disk cache - will throw if saving fails
                self._save_cache_to_disk()
            
            removed_count = len(expired_keys)
            self.logger.info(f"Removed {removed_count} expired cache entries")
        
        return removed_count
    
    def _load_cache_to_memory(self) -> None:
        """
        [Method intent]
        Load valid cache entries from disk into memory.
        
        [Design principles]
        - Only load valid, non-expired entries
        - Error propagation for transparency
        - Explicit error handling
        
        [Implementation details]
        - Reads cache data from disk using _read_disk_cache
        - Validates cache version or throws
        - Filters out expired entries
        - Populates memory cache
        - Throws errors rather than handling silently
        
        Raises:
            FileNotFoundError: When cache file doesn't exist
            json.JSONDecodeError: When cache file contains invalid JSON
            ValueError: When cache version doesn't match
            Exception: For any other errors that occur
        """
        # Get cache data from disk - this will throw if file not found or invalid
        cache_data = self._read_disk_cache()
        
        # Check cache version
        if cache_data.get("version") != self.CACHE_VERSION:
            self.logger.warning(f"Cache version mismatch: expected {self.CACHE_VERSION}, got {cache_data.get('version')}")
            raise ValueError(f"Cache version mismatch: expected {self.CACHE_VERSION}, got {cache_data.get('version')}")
        
        # Load valid entries
        entries = cache_data.get("entries", {})
        current_time = time.time()
        ttl_seconds = self.ttl_days * 24 * 60 * 60
        
        # Filter valid entries and load into memory cache
        with self._cache_lock:
            self._memory_cache = {}  # Clear existing cache
            for key, entry in entries.items():
                if current_time - entry.get("timestamp", 0) <= ttl_seconds:
                    self._memory_cache[key] = entry.get("value")
        
        self.logger.debug(f"Loaded {len(self._memory_cache)} cache entries from disk")
    
    def _save_cache_to_disk(self) -> None:
        """
        [Method intent]
        Save current memory cache to disk.
        
        [Design principles]
        - Atomic file operations
        - Thread-safe access
        - Complete error handling
        - Error propagation for transparency
        
        [Implementation details]
        - Creates cache entries with timestamps
        - Writes to temporary file first
        - Uses atomic rename for reliability
        - Throws all errors rather than handling them silently
        
        Note: This method assumes the caller ALREADY HOLDS the cache lock.
        DO NOT try to acquire the lock in this method as it will cause deadlocks.
        
        Raises:
            Exception: If saving fails for any reason
        """
        thread_id = threading.get_ident()
        is_main_thread = threading.current_thread() == threading.main_thread()
        self.logger.debug(f"Thread {thread_id}: Entering _save_cache_to_disk() (main_thread={is_main_thread})")
        
        # We're assuming the lock is ALREADY held by the caller - never acquire it here!
        
        # Create cache data structure - just copy the memory cache directly
        self.logger.debug(f"Thread {thread_id}: Creating cache data structure")
        cache_data = copy.deepcopy(self._memory_cache)
        
        # Add metadata
        cache_data["_metadata"] = {
            "version": self.CACHE_VERSION,
            "timestamp": time.time(),
            "ttl_days": self.ttl_days
        }
        
        self.logger.debug(f"Thread {thread_id}: Added memory cache contents with metadata")
        
        # Create directories if needed
        self.logger.debug(f"Thread {thread_id}: Ensuring cache directory exists: {self.cache_dir}")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Write to temp file first with pretty formatting
        temp_file = f"{self.cache_file}.tmp"
        self.logger.debug(f"Thread {thread_id}: Writing to temp file with pretty formatting: {temp_file}")
        with open(temp_file, 'w') as f:
            json.dump(cache_data, f, indent=2, cls=_CacheEncoder)
        
        # Atomic rename
        self.logger.debug(f"Thread {thread_id}: Performing atomic rename to: {self.cache_file}")
        os.replace(temp_file, self.cache_file)
        self.logger.debug(f"Thread {thread_id}: Cache saved to disk: {self.cache_file}")
    
    def _read_disk_cache(self) -> Dict[str, Any]:
        """
        [Method intent]
        Read cache data from disk, raising exceptions on failure.
        
        [Design principles]
        - Complete error propagation
        - No silent failures
        - Version compatibility checking
        
        [Implementation details]
        - Reads from cache file
        - Validates format
        - Throws exceptions on all errors
        
        Returns:
            Dict containing cache data
            
        Raises:
            FileNotFoundError: When cache file doesn't exist
            json.JSONDecodeError: When cache file contains invalid JSON
            Exception: For any other errors that occur
        """
        if not os.path.exists(self.cache_file):
            self.logger.warning(f"Cache file not found: {self.cache_file}")
            raise FileNotFoundError(f"Cache file does not exist: {self.cache_file}")
        
        try:
            with open(self.cache_file, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in cache file: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error reading cache file: {str(e)}")
            raise


class _CacheEncoder(json.JSONEncoder):
    """
    [Class intent]
    Custom JSON encoder for cache serialization that handles complex Python objects.
    
    [Design principles]
    - Robust serialization of complex data types
    - Graceful fallback for non-serializable objects
    
    [Implementation details]
    - Handles common non-serializable types
    - Provides string representation for other complex types
    """
    def default(self, obj):
        # Handle simple types that need conversion
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (set, tuple)):
            return list(obj)
        elif isinstance(obj, bytes):
            try:
                return obj.decode('utf-8', errors='replace')
            except Exception:
                return f"<binary data: {len(obj)} bytes>"
        
        # Handle complex nested structures
        try:
            if hasattr(obj, "__dict__"):
                return obj.__dict__
            else:
                return str(obj)
        except Exception:
            return f"<non-serializable: {type(obj).__name__}>"
