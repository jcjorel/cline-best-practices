# Discovery Cache Implementation Plan

## Overview
The `DiscoveryCache` component provides a thread-safe caching system for model and profile discovery results. It implements a two-tier cache strategy (memory and disk) with configurable TTL and versioning to ensure optimal performance and reliability.

## File Location
`src/dbp/llm/bedrock/discovery/cache.py`

## Class Structure

```python
class DiscoveryCache:
    """
    [Class intent]
    Provides thread-safe caching for discovery results with configurable TTLs
    and disk persistence. Optimizes performance by reducing redundant AWS API calls.
    
    [Design principles]
    - Thread safety for concurrent access
    - Tiered caching (memory and disk)
    - Configurable TTL for different tiers
    - Atomic file operations for reliable persistence
    - Versioned cache format for compatibility
    
    [Implementation details]
    - Implements in-memory LRU cache for performance
    - Persists to disk with atomic file operations
    - Handles cache invalidation based on TTL
    - Maintains version tracking for format changes
    - Uses appropriate serialization for different data types
    """
    
    # Cache version - increment when format changes
    CACHE_VERSION = "1.0"
    
    # Default TTL values
    DEFAULT_MEMORY_TTL_SECONDS = 3600  # 1 hour
    DEFAULT_DISK_TTL_DAYS = 3  # 3 days
    
    def __init__(
        self,
        base_dir=None,
        memory_ttl_seconds=None,
        disk_ttl_days=None,
        logger=None
    ):
        """Initialize the cache with configurable TTLs"""
        self._memory_cache = {}  # {cache_key: {"data": any, "timestamp": float}}
        self._cache_lock = threading.Lock()
        
        # Configure TTLs
        self.memory_ttl_seconds = memory_ttl_seconds or self.DEFAULT_MEMORY_TTL_SECONDS
        self.disk_ttl_days = disk_ttl_days or self.DEFAULT_DISK_TTL_DAYS
        
        # Setup cache directory
        self.base_dir = base_dir or os.path.expanduser(os.path.join("~", ".dbp"))
        self.cache_dir = os.path.join(self.base_dir, "cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Setup logging
        self.logger = logger or logging.getLogger(__name__)
```

## Core Cache Operations

```python
    def get(self, cache_key, default=None):
        """
        [Method intent]
        Get a value from cache if available and not expired.
        
        [Design principles]
        - Memory-first, disk-fallback approach
        - Respect TTL settings
        - Thread safety
        
        [Implementation details]
        - Checks memory cache first with proper locking
        - Falls back to disk cache if needed
        - Handles expired entries appropriately
        - Returns default if not found or expired
        
        Args:
            cache_key: Unique identifier for the cache entry
            default: Value to return if cache miss or expired
            
        Returns:
            The cached value or default if not found/expired
        """
        # Check memory cache first
        with self._cache_lock:
            if cache_key in self._memory_cache:
                cache_entry = self._memory_cache[cache_key]
                
                # Check if entry is still valid
                if time.time() - cache_entry["timestamp"] <= self.memory_ttl_seconds:
                    return cache_entry["data"]
                    
                # If expired, remove from memory cache
                del self._memory_cache[cache_key]
        
        # If not in memory or expired, try disk cache
        try:
            disk_data = self._load_from_disk(cache_key)
            if disk_data is not None:
                # Update memory cache with disk data
                self.set(cache_key, disk_data)
                return disk_data
        except Exception as e:
            self.logger.warning(f"Error loading cache from disk for key {cache_key}: {str(e)}")
                
        # Cache miss - return default
        return default
    
    def set(self, cache_key, value):
        """
        [Method intent]
        Add or update a value in the cache.
        
        [Design principles]
        - Thread safety
        - Update both memory and disk
        - Proper serialization
        
        [Implementation details]
        - Updates memory cache with proper locking
        - Asynchronously updates disk cache
        - Handles different data types appropriately
        
        Args:
            cache_key: Unique identifier for the cache entry
            value: Value to cache
        """
        # Update memory cache
        timestamp = time.time()
        with self._cache_lock:
            self._memory_cache[cache_key] = {
                "data": value,
                "timestamp": timestamp
            }
        
        # Update disk cache (could be done asynchronously)
        try:
            self._save_to_disk(cache_key, value, timestamp)
        except Exception as e:
            self.logger.warning(f"Error saving cache to disk for key {cache_key}: {str(e)}")
    
    def invalidate(self, cache_key=None):
        """
        [Method intent]
        Invalidate specific cache entry or entire cache.
        
        [Design principles]
        - Selective or complete invalidation
        - Thread safety
        - Consistent memory and disk state
        
        [Implementation details]
        - Clears memory cache with proper locking
        - Removes disk cache files as needed
        - Handles both targeted and full invalidation
        
        Args:
            cache_key: Specific key to invalidate, or None for all
        """
        if cache_key is None:
            # Invalidate entire cache
            with self._cache_lock:
                self._memory_cache.clear()
                
            # Clear disk cache directory
            try:
                for filename in os.listdir(self.cache_dir):
                    if filename.endswith(".cache"):
                        os.remove(os.path.join(self.cache_dir, filename))
            except Exception as e:
                self.logger.warning(f"Error clearing disk cache: {str(e)}")
        else:
            # Invalidate specific key
            with self._cache_lock:
                if cache_key in self._memory_cache:
                    del self._memory_cache[cache_key]
            
            # Remove specific disk cache file
            disk_path = self._get_disk_path(cache_key)
            if os.path.exists(disk_path):
                try:
                    os.remove(disk_path)
                except Exception as e:
                    self.logger.warning(f"Error removing disk cache for {cache_key}: {str(e)}")
```

## Disk Cache Operations

```python
    def _get_disk_path(self, cache_key):
        """
        [Method intent]
        Get the file path for a cache key's disk storage.
        
        [Design principles]
        - Consistent path generation
        - Safe filenames
        
        [Implementation details]
        - Converts cache key to safe filename
        - Ensures correct file extension
        - Returns absolute path
        
        Args:
            cache_key: Cache key to convert to path
            
        Returns:
            str: Absolute path to cache file
        """
        # Convert cache_key to safe filename
        safe_key = hashlib.md5(cache_key.encode()).hexdigest()
        return os.path.join(self.cache_dir, f"{safe_key}.cache")
    
    def _save_to_disk(self, cache_key, value, timestamp):
        """
        [Method intent]
        Save a cache entry to disk with proper metadata.
        
        [Design principles]
        - Atomic file operations
        - Complete metadata
        - Proper serialization
        
        [Implementation details]
        - Includes version, timestamp, and TTL info
        - Uses temporary file for atomic operation
        - Handles serialization for different data types
        
        Args:
            cache_key: Cache key
            value: Value to cache
            timestamp: Creation timestamp
        """
        # Create cache entry with metadata
        cache_entry = {
            "version": self.CACHE_VERSION,
            "timestamp": timestamp,
            "ttl_days": self.disk_ttl_days,
            "key": cache_key,
            "data": value
        }
        
        # Get file path
        file_path = self._get_disk_path(cache_key)
        temp_path = f"{file_path}.tmp"
        
        # Write to temporary file first for atomic operation
        try:
            with open(temp_path, 'wb') as f:
                pickle.dump(cache_entry, f)
            
            # Atomic rename for reliability
            os.replace(temp_path, file_path)
        except Exception:
            # Clean up temp file if something went wrong
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
    
    def _load_from_disk(self, cache_key):
        """
        [Method intent]
        Load a cache entry from disk if valid.
        
        [Design principles]
        - Version compatibility checking
        - TTL enforcement
        - Error handling
        
        [Implementation details]
        - Validates cache version
        - Checks TTL against current time
        - Deserializes data properly
        - Returns None for expired/invalid entries
        
        Args:
            cache_key: Cache key to load
            
        Returns:
            The cached value or None if expired/invalid
        """
        file_path = self._get_disk_path(cache_key)
        
        if not os.path.exists(file_path):
            return None
        
        try:
            with open(file_path, 'rb') as f:
                cache_entry = pickle.load(f)
            
            # Check version compatibility
            if cache_entry.get("version") != self.CACHE_VERSION:
                self.logger.debug(f"Cache version mismatch for {cache_key}, ignoring")
                return None
            
            # Check TTL
            ttl_seconds = cache_entry.get("ttl_days", self.disk_ttl_days) * 24 * 60 * 60
            if time.time() - cache_entry.get("timestamp", 0) > ttl_seconds:
                self.logger.debug(f"Disk cache expired for {cache_key}")
                return None
            
            # Return data
            return cache_entry.get("data")
        except Exception as e:
            self.logger.warning(f"Error loading cache from disk for {cache_key}: {str(e)}")
            return None
```

## Cache Maintenance

```python
    def cleanup(self):
        """
        [Method intent]
        Clean up expired cache entries from disk.
        
        [Design principles]
        - Periodic maintenance
        - Safe cleanup
        - Logging for diagnostics
        
        [Implementation details]
        - Scans disk cache directory
        - Checks each entry for expiration
        - Removes expired files
        - Counts and logs results
        
        Returns:
            int: Number of entries removed
        """
        removed_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if not filename.endswith(".cache"):
                    continue
                    
                file_path = os.path.join(self.cache_dir, filename)
                
                try:
                    with open(file_path, 'rb') as f:
                        cache_entry = pickle.load(f)
                    
                    # Check version and TTL
                    ttl_seconds = cache_entry.get("ttl_days", self.disk_ttl_days) * 24 * 60 * 60
                    if (cache_entry.get("version") != self.CACHE_VERSION or
                        time.time() - cache_entry.get("timestamp", 0) > ttl_seconds):
                        
                        # Remove expired entry
                        os.remove(file_path)
                        removed_count += 1
                except Exception:
                    # If we can't read the file, consider it corrupted and remove
                    try:
                        os.remove(file_path)
                        removed_count += 1
                    except:
                        pass
        except Exception as e:
            self.logger.warning(f"Error cleaning up cache: {str(e)}")
        
        self.logger.debug(f"Cache cleanup removed {removed_count} expired entries")
        return removed_count
```

## Specialized Cache Methods for AWS Discovery

```python
    def get_model_cache(self, region):
        """
        [Method intent]
        Get cached Bedrock model data for a specific region.
        
        [Design principles]
        - Convenience method for common use case
        - Standardized cache keys
        
        [Implementation details]
        - Uses region-specific cache key
        - Applies standard cache logic
        
        Args:
            region: AWS region name
            
        Returns:
            List of model data or None if not in cache or expired
        """
        cache_key = f"bedrock_models:{region}"
        return self.get(cache_key)
    
    def set_model_cache(self, region, models_data):
        """
        [Method intent]
        Cache Bedrock model data for a specific region.
        
        [Design principles]
        - Convenience method for common use case
        - Standardized cache keys
        
        [Implementation details]
        - Uses region-specific cache key
        - Applies standard cache logic
        
        Args:
            region: AWS region name
            models_data: Model data to cache
        """
        cache_key = f"bedrock_models:{region}"
        self.set(cache_key, models_data)
    
    def get_profile_cache(self, region, model_id=None):
        """
        [Method intent]
        Get cached inference profile data for a region, optionally for a specific model.
        
        [Design principles]
        - Convenience method for common use case
        - Support for filtering by model
        
        [Implementation details]
        - Uses region-specific cache key
        - Filters by model ID if specified
        - Applies standard cache logic
        
        Args:
            region: AWS region name
            model_id: Optional model ID to filter profiles
            
        Returns:
            List of profile data or None if not in cache or expired
        """
        cache_key = f"bedrock_profiles:{region}"
        profiles = self.get(cache_key)
        
        if profiles is None:
            return None
            
        if model_id:
            # Filter profiles for specific model
            return [p for p in profiles if p.get("modelId") == model_id]
        
        return profiles
        
    def set_profile_cache(self, region, profiles_data):
        """
        [Method intent]
        Cache inference profile data for a specific region.
        
        [Design principles]
        - Convenience method for common use case
        - Standardized cache keys
        
        [Implementation details]
        - Uses region-specific cache key
        - Applies standard cache logic
        
        Args:
            region: AWS region name
            profiles_data: Profile data to cache
        """
        cache_key = f"bedrock_profiles:{region}"
        self.set(cache_key, profiles_data)
```

## Usage Examples

```python
# Example 1: Basic usage
cache = DiscoveryCache()

# Set a value
cache.set("my_key", {"data": "example"})

# Get a value
data = cache.get("my_key")
print(data)  # {"data": "example"}

# Example 2: Using with model discovery
model_data = [{"modelId": "model-1", "provider": "Anthropic"}, {"modelId": "model-2", "provider": "AI21"}]
cache.set_model_cache("us-west-2", model_data)

# Later retrieve it
cached_models = cache.get_model_cache("us-west-2")

# Example 3: Invalidate specific cache
cache.invalidate("bedrock_models:us-east-1")

# Example 4: Clean up expired entries
removed_count = cache.cleanup()
print(f"Removed {removed_count} expired cache entries")
```

## Testing Strategy

1. **Unit Tests:**
   - Test memory cache operations with various TTLs
   - Test disk cache persistence and recovery
   - Test cache invalidation (specific and complete)
   - Test version compatibility handling
   - Test TTL enforcement

2. **Integration Tests:**
   - Test with actual discovery data structures
   - Verify data integrity across cache tiers
   - Test cleanup functionality

## Implementation Steps

1. Create the directory structure
2. Implement the core `DiscoveryCache` class
3. Add memory cache operations with TTL handling
4. Add disk cache operations with atomic file operations
5. Add specialized methods for AWS discovery data
6. Add cache maintenance functionality
7. Add comprehensive unit tests
8. Document usage patterns

## Integration with Other Components

The `DiscoveryCache` will be used by:

1. `BedrockModelDiscovery` - To cache model discovery results by region
2. `BedrockProfileDiscovery` - To cache inference profile data by region
3. `RegionLatencyTracker` - To persist latency metrics between runs
