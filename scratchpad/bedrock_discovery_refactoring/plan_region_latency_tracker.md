# Region Latency Tracker Implementation Plan

## Overview
The `RegionLatencyTracker` component will measure, track, and manage AWS API latency metrics across regions. It enables performance-optimized region selection by providing data-driven sorting based on actual measured latencies.

## File Location
`src/dbp/llm/bedrock/discovery/latency.py`

## Class Structure

```python
class RegionLatencyTracker:
    """
    [Class intent]
    Tracks and manages API latency metrics for AWS regions to optimize region selection.
    Provides data-driven region prioritization based on real performance measurements.
    
    [Design principles]
    - Thread-safe latency tracking
    - Statistical smoothing for stable metrics
    - Efficient sorting capabilities
    - Latency data persistence
    
    [Implementation details]
    - Uses exponential moving average for latency tracking
    - Implements thread-safe data structures
    - Provides sorting by measured latency
    - Handles regions without latency data
    """
    
    def __init__(self, cache=None, logger=None):
        """Initialize the latency tracker with optional cache"""
        self._latency_metrics = {}  # {region: avg_latency}
        self._sample_counts = {}    # {region: sample_count}
        self._lock = threading.Lock()
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)
        
        # Load any cached latency data
        self._load_cached_latencies()
```

## Latency Measurement and Tracking

```python
    def measure_latency(self, region, endpoint="bedrock"):
        """
        [Method intent]
        Actively measure the latency to an AWS endpoint in a specified region.
        
        [Design principles]
        - Direct latency measurement
        - Consistent measurement approach
        - Error handling for failed measurements
        
        [Implementation details]
        - Uses simple API call to measure round-trip time
        - Excludes result processing time
        - Updates latency metrics with measurement
        - Handles failures gracefully
        
        Args:
            region: AWS region to measure
            endpoint: Service endpoint to test (default: bedrock)
            
        Returns:
            float: Measured latency in seconds, or None if measurement failed
        """
        # Implementation details...
    
    def update_latency(self, region, latency):
        """
        [Method intent]
        Update latency metrics for a region using exponential moving average.
        
        [Design principles]
        - Thread-safe updates
        - Statistical smoothing of outliers
        - Weighted historical data
        
        [Implementation details]
        - Uses exponential moving average (EMA)
        - Weights recent measurements higher
        - Thread-safe updates with proper locking
        - Persists updates to cache if available
        
        Args:
            region: AWS region name
            latency: Measured latency in seconds
        """
        # Implementation details...
    
    def get_latency(self, region):
        """
        [Method intent]
        Get the average latency for a specific region.
        
        [Design principles]
        - Thread-safe access
        - Default handling for unknown regions
        
        [Implementation details]
        - Returns moving average latency if available
        - Returns None for regions without measurements
        
        Args:
            region: AWS region name
            
        Returns:
            float: Average latency in seconds, or None if unknown
        """
        # Implementation details...
```

## Region Sorting

```python
    def get_sorted_regions(self, regions):
        """
        [Method intent]
        Sort a list of regions by measured latency (lowest first).
        
        [Design principles]
        - Optimized sorting for best API performance
        - Graceful handling of unmeasured regions
        
        [Implementation details]
        - Uses measured latencies for sorting when available
        - Places regions without latency data at the end
        - Returns sorted list from fastest to slowest
        
        Args:
            regions: List of region names to sort
            
        Returns:
            List[str]: Region names sorted by ascending latency
        """
        with self._lock:
            # Create list of (region, latency) tuples for sorting
            region_latencies = []
            unmeasured_regions = []
            
            for region in regions:
                latency = self._latency_metrics.get(region)
                if latency is not None:
                    region_latencies.append((region, latency))
                else:
                    unmeasured_regions.append(region)
            
            # Sort by latency (lowest first)
            sorted_regions = [r for r, _ in sorted(region_latencies, key=lambda x: x[1])]
            
            # Append regions without latency data
            sorted_regions.extend(unmeasured_regions)
            
            return sorted_regions
```

## Cache Integration

```python
    def _load_cached_latencies(self):
        """
        [Method intent]
        Load previously measured latencies from cache if available.
        
        [Design principles]
        - Persistent latency data between runs
        - Thread-safe loading
        - Graceful handling of missing cache
        
        [Implementation details]
        - Checks for cache availability
        - Loads metrics with proper locking
        - Handles missing or invalid cache data
        """
        if not self.cache:
            return
            
        try:
            cached_data = self.cache.get("region_latencies")
            if not cached_data:
                return
                
            with self._lock:
                self._latency_metrics = cached_data.get("metrics", {})
                self._sample_counts = cached_data.get("counts", {})
                
            self.logger.debug(f"Loaded latency metrics for {len(self._latency_metrics)} regions from cache")
        except Exception as e:
            self.logger.warning(f"Error loading cached latency metrics: {str(e)}")
    
    def _save_latencies_to_cache(self):
        """
        [Method intent]
        Save current latency metrics to cache for persistence.
        
        [Design principles]
        - Persistent latency data between runs
        - Thread-safe saving
        - Efficient updates
        
        [Implementation details]
        - Checks for cache availability
        - Saves metrics with proper locking
        - Handles errors gracefully
        """
        if not self.cache:
            return
            
        try:
            with self._lock:
                cache_data = {
                    "metrics": self._latency_metrics.copy(),
                    "counts": self._sample_counts.copy(),
                    "updated_at": time.time()
                }
                
            self.cache.set("region_latencies", cache_data)
            self.logger.debug(f"Saved latency metrics for {len(self._latency_metrics)} regions to cache")
        except Exception as e:
            self.logger.warning(f"Error saving latency metrics to cache: {str(e)}")
```

## Statistical Helper Methods

```python
    def _calculate_ema(self, current_avg, new_value, count, alpha=None):
        """
        [Method intent]
        Calculate exponential moving average with adaptive alpha.
        
        [Design principles]
        - Statistical stability
        - Adaptive weighting based on sample size
        
        [Implementation details]
        - Uses exponential moving average formula
        - Adjusts alpha based on sample count
        - Handles first sample appropriately
        
        Args:
            current_avg: Current average value
            new_value: New measurement
            count: Current sample count
            alpha: Optional explicit alpha value
            
        Returns:
            float: Updated exponential moving average
        """
        if count <= 1:
            return new_value
            
        # Adaptive alpha - give more weight to early samples
        if alpha is None:
            alpha = 0.3  # Default alpha
            if count < 5:
                alpha = 0.5  # More weight to new samples when we have few data points
                
        return (alpha * new_value) + ((1 - alpha) * current_avg)
```

## Usage Examples

```python
# Example 1: Updating latency manually
latency_tracker = RegionLatencyTracker(cache=discovery_cache)

# After a timed API call
start_time = time.time()
response = boto3_client.some_api_call()
latency = time.time() - start_time

# Update the tracker with measured latency
latency_tracker.update_latency("us-west-2", latency)

# Example 2: Using with region sorting
available_regions = ["us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1"]
sorted_by_latency = latency_tracker.get_sorted_regions(available_regions)
print(f"Regions ordered by latency (fastest first): {sorted_by_latency}")

# Example 3: Active latency measurement
latency = latency_tracker.measure_latency("us-east-1", "bedrock")
print(f"Current latency to Bedrock in us-east-1: {latency:.3f} seconds")
```

## Testing Strategy

1. **Unit Tests:**
   - Test latency calculation with exponential moving average
   - Test region sorting with various input scenarios
   - Test thread safety with concurrent updates
   - Test cache integration

2. **Integration Tests:**
   - Test with actual AWS endpoints (optional, using minimal API calls)
   - Verify latency measurements are reasonable
   - Test persistence between runs with the cache system

## Implementation Steps

1. Create the file structure
2. Implement the core `RegionLatencyTracker` class
3. Add latency measurement and update methods
4. Implement statistical functions for moving averages
5. Add region sorting functionality
6. Integrate with the cache system
7. Add comprehensive unit tests
8. Document usage patterns

## Integration with Other Components

The `RegionLatencyTracker` will be primarily used by:

1. `BedrockModelDiscovery` - To sort regions by measured latency when finding optimal regions for models
2. `BedrockProfileDiscovery` - To optimize region selection for inference profile operations

Both will update latency metrics during their API operations, creating a feedback loop that continuously improves region selection over time.
