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
# Provides a thread-safe system for tracking AWS API latency metrics across regions.
# Enables data-driven region prioritization to optimize API performance based on
# actual measured latencies, rather than static preferences or arbitrary ordering.
###############################################################################
# [Source file design principles]
# - Thread-safe measurement and tracking
# - Statistical smoothing for stable metrics
# - Persistent latency data between runs
# - Efficient region sorting capabilities
# - Minimal API calls for measurement
# - Non-intrusive integration with existing components
###############################################################################
# [Source file constraints]
# - Must handle concurrent updates from multiple threads
# - Must minimize additional API calls for latency measurements
# - Must provide stable metrics that don't fluctuate too rapidly
# - Must integrate with caching system for persistence
# - Must work without requiring credentials for initial instantiation
###############################################################################
# [Dependencies]
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/api_providers/aws/exceptions.py
# codebase:src/dbp/llm/bedrock/discovery/cache.py
# system:boto3
# system:time
# system:logging
# system:threading
###############################################################################
# [GenAI tool change history]
# 2025-05-03T11:35:43Z : Initial implementation by CodeAssistant
# * Created RegionLatencyTracker class for AWS API latency measurement
# * Implemented exponential moving average for latency metrics
# * Added integration with the cache system for persistence
# * Implemented region sorting based on measured latencies
###############################################################################

import logging
import threading
import time
from typing import Dict, List, Optional, Any

import boto3

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from .cache import DiscoveryCache


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
    
    # Cache key for latency metrics
    LATENCY_CACHE_KEY = "region_latency_metrics"
    
    def __init__(
        self, 
        cache: Optional[DiscoveryCache] = None, 
        logger: Optional[logging.Logger] = None
    ):
        """
        [Method intent]
        Initialize the latency tracker with optional cache integration.
        
        [Design principles]
        - Optional cache integration
        - Thread-safe initialization
        - Default logging configuration
        
        [Implementation details]
        - Sets up internal data structures
        - Configures thread safety
        - Loads cached metrics if available
        - Initializes logging
        
        Args:
            cache: Optional DiscoveryCache for persistence
            logger: Optional logger for tracking operations
        """
        self._latency_metrics = {}  # {region: avg_latency}
        self._sample_counts = {}    # {region: sample_count}
        self._lock = threading.Lock()
        self.cache = cache
        self.logger = logger or logging.getLogger(__name__)
        
        # Load any cached latency data
        self._load_cached_latencies()
    
    def measure_latency(self, region: str, service_name: str = "bedrock") -> Optional[float]:
        """
        [Method intent]
        Actively measure the latency to an AWS endpoint in a specified region.
        
        [Design principles]
        - Direct latency measurement
        - Minimal API overhead
        - Error handling for failed measurements
        
        [Implementation details]
        - Uses simple API call to measure round-trip time
        - Excludes result processing time
        - Updates latency metrics with measurement
        - Handles failures gracefully
        
        Args:
            region: AWS region to measure
            service_name: Service endpoint to test (default: bedrock)
            
        Returns:
            float: Measured latency in seconds, or None if measurement failed
        """
        try:
            # Get client factory singleton
            client_factory = AWSClientFactory.get_instance()
            
            # Time the API call - use a simple operation like list_foundation_models
            start_time = time.time()
            
            # Create the client (this will make a connection to the region)
            client = client_factory.get_client(service_name, region_name=region)
            
            # For Bedrock, we can use list_foundation_models (lightweight call)
            if service_name == "bedrock":
                client.list_foundation_models(maxResults=1)
            # Add other service-specific lightweight calls as needed
            
            # Measure latency
            latency = time.time() - start_time
            
            # Update metrics
            self.update_latency(region, latency)
            
            self.logger.debug(f"Measured {service_name} latency to {region}: {latency:.3f}s")
            return latency
            
        except (AWSClientError, AWSRegionError) as e:
            self.logger.warning(f"Failed to measure latency for {region}: {str(e)}")
            return None
        except Exception as e:
            self.logger.warning(f"Unexpected error measuring latency for {region}: {str(e)}")
            return None
    
    def update_latency(self, region: str, latency: float) -> None:
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
        with self._lock:
            current_avg = self._latency_metrics.get(region)
            current_count = self._sample_counts.get(region, 0)
            
            # Update sample count
            new_count = current_count + 1
            self._sample_counts[region] = new_count
            
            # Calculate new average
            if current_avg is None:
                # First sample
                self._latency_metrics[region] = latency
            else:
                # Use exponential moving average
                self._latency_metrics[region] = self._calculate_ema(current_avg, latency, new_count)
            
            self.logger.debug(f"Updated latency for {region}: {self._latency_metrics[region]:.3f}s (sample #{new_count})")
        
        # Persist to cache if available
        self._save_latencies_to_cache()
    
    def get_latency(self, region: str) -> Optional[float]:
        """
        [Method intent]
        Get the average latency for a specific region.
        
        [Design principles]
        - Thread-safe access
        - Default handling for unknown regions
        
        [Implementation details]
        - Returns moving average latency if available
        - Returns None for regions without measurements
        - Thread-safe access to metrics
        
        Args:
            region: AWS region name
            
        Returns:
            float: Average latency in seconds, or None if unknown
        """
        with self._lock:
            return self._latency_metrics.get(region)
    
    def get_sorted_regions(self, regions: List[str]) -> List[str]:
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
    
    def clear_metrics(self, region: Optional[str] = None) -> None:
        """
        [Method intent]
        Clear latency metrics for specific region or all regions.
        
        [Design principles]
        - Selective or complete clearing
        - Thread safety
        - Cache consistency
        
        [Implementation details]
        - Clears specified region or all metrics
        - Updates cache to maintain consistency
        - Uses proper locking for thread safety
        
        Args:
            region: Specific region to clear, or None for all regions
        """
        with self._lock:
            if region is None:
                # Clear all metrics
                self._latency_metrics.clear()
                self._sample_counts.clear()
                self.logger.info("Cleared all latency metrics")
            elif region in self._latency_metrics:
                # Clear specific region
                del self._latency_metrics[region]
                if region in self._sample_counts:
                    del self._sample_counts[region]
                self.logger.info(f"Cleared latency metrics for {region}")
        
        # Update cache
        self._save_latencies_to_cache()
    
    def _calculate_ema(self, current_avg: float, new_value: float, count: int, alpha: Optional[float] = None) -> float:
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
    
    def _load_cached_latencies(self) -> None:
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
            cached_data = self.cache.get(self.LATENCY_CACHE_KEY)
            if not cached_data:
                return
                
            with self._lock:
                self._latency_metrics = cached_data.get("metrics", {})
                self._sample_counts = cached_data.get("counts", {})
                
            self.logger.debug(f"Loaded latency metrics for {len(self._latency_metrics)} regions from cache")
        except Exception as e:
            self.logger.warning(f"Error loading cached latency metrics: {str(e)}")
    
    def _save_latencies_to_cache(self) -> None:
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
                
            self.cache.set(self.LATENCY_CACHE_KEY, cache_data)
            self.logger.debug(f"Saved latency metrics for {len(self._latency_metrics)} regions to cache")
        except Exception as e:
            self.logger.warning(f"Error saving latency metrics to cache: {str(e)}")
