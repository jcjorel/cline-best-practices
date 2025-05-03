# Bedrock Model Discovery Implementation Plan

## Overview
The `BedrockModelDiscovery` component is a singleton service that discovers and provides information about available Bedrock models across AWS regions. It optimizes performance by caching results, measuring region latencies, and implementing efficient parallel scanning.

## File Location
`src/dbp/llm/bedrock/discovery/models.py`

## Class Structure

```python
class BedrockModelDiscovery:
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
```

## Singleton Pattern Implementation

```python
    @classmethod
    def get_instance(cls, 
                    cache=None, 
                    client_factory=None, 
                    latency_tracker=None, 
                    initial_scan=False,
                    logger=None):
        """
        [Method intent]
        Get the singleton instance of BedrockModelDiscovery, creating it if needed.
        
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
            initial_scan: Whether to perform initial scan on initialization
            logger: Optional logger instance
            
        Returns:
            BedrockModelDiscovery: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(
                        cache=cache,
                        client_factory=client_factory,
                        latency_tracker=latency_tracker,
                        initial_scan=initial_scan,
                        logger=logger
                    )
        return cls._instance
    
    def __init__(self, 
                cache=None, 
                client_factory=None, 
                latency_tracker=None, 
                initial_scan=False,
                logger=None):
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
        - Optionally performs initial scan
        
        Raises:
            RuntimeError: If attempting to create instance directly instead of using get_instance()
        """
        # Enforce singleton pattern
        if self.__class__._instance is not None:
            raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
            
        # Initialize components and dependencies
        from ...api_providers.aws.client_factory import AWSClientFactory
        from .cache import DiscoveryCache
        from .latency import RegionLatencyTracker
        
        self.client_factory = client_factory or AWSClientFactory.get_instance()
        self.cache = cache or DiscoveryCache()
        self.latency_tracker = latency_tracker or RegionLatencyTracker(cache=self.cache)
        self.logger = logger or logging.getLogger(__name__)
        self._region_lock = threading.Lock()
        
        # Try to perform initial scan if requested
        if initial_scan:
            self.scan_all_regions()
```

## Core Scanning Functionality

```python
    def scan_all_regions(self, regions=None, refresh_cache=False) -> Dict[str, List[Dict[str, Any]]]:
        """
        [Method intent]
        Scan AWS regions to discover Bedrock models and their availability,
        using parallel scanning for efficiency.
        
        [Design principles]
        - Parallel scanning for performance
        - Cache-first approach with refresh option
        - Complete model discovery
        - Latency measurement during scanning
        
        [Implementation details]
        - Uses ThreadPoolExecutor for parallel scanning
        - Updates both in-memory and file-based cache
        - Measures and records region latencies
        - Handles regions where Bedrock is not available
        
        Args:
            regions: Optional list of regions to scan (defaults to initial regions)
            refresh_cache: Whether to force a refresh of cached data
            
        Returns:
            Dict mapping regions to lists of available models with metadata
        """
        result = {}
        
        # If not forcing a refresh, try to use cache first
        if not refresh_cache:
            # Check cache for each region
            for region in regions or self.INITIAL_BEDROCK_REGIONS:
                cached_models = self.cache.get_model_cache(region)
                if cached_models:
                    result[region] = cached_models
        
        # If we still need to scan any regions
        regions_to_scan = []
        if regions:
            # Only scan specified regions not found in cache
            regions_to_scan = [r for r in regions if r not in result]
        elif not result or refresh_cache:
            # If no results from cache or forced refresh, get all regions
            regions_to_scan = self._get_all_regions()
        
        if regions_to_scan:
            self.logger.info(f"Scanning {len(regions_to_scan)} AWS regions for Bedrock models...")
            
            # Use ThreadPoolExecutor to scan regions in parallel
            with ThreadPoolExecutor(max_workers=min(10, len(regions_to_scan))) as executor:
                # Submit scanning tasks
                future_to_region = {
                    executor.submit(self._scan_region, region): region
                    for region in regions_to_scan
                }
                
                # Process results as they complete
                for future in as_completed(future_to_region):
                    region = future_to_region[future]
                    try:
                        models = future.result()
                        if models:
                            result[region] = models
                            
                            # Update cache
                            self.cache.set_model_cache(region, models)
                    except Exception as e:
                        self.logger.warning(f"Error scanning region {region}: {str(e)}")
        
        return result
    
    def _scan_region(self, region: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Scan a specific region for available Bedrock models, measuring API latency.
        
        [Design principles]
        - Complete model discovery
        - Latency measurement for region optimization
        - Robust error handling
        - Full metadata extraction
        
        [Implementation details]
        - Creates regional Bedrock client using factory
        - Measures API response time
        - Records latency metrics
        - Extracts complete model attributes
        - Filters for active models only
        
        Args:
            region: AWS region to scan
            
        Returns:
            List of dicts with model information in the region
        """
        models = []
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
```

## Model Information Methods

```python
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
        
        # Scan all regions to find where this model is available
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
        cached_models = self.cache.get_model_cache(region)
        if cached_models:
            # Check if model is in this region's cached data
            for model in cached_models:
                if model["modelId"] == model_id:
                    return True
        
        # If not in cache or cache expired, check directly
        try:
            models = self._scan_region(region)
            
            # Update cache
            self.cache.set_model_cache(region, models)
            
            # Check if model is available
            for model in models:
                if model["modelId"] == model_id:
                    return True
            
            # Model not found in region
            return False
            
        except Exception as e:
            self.logger.warning(f"Error checking model availability in {region}: {str(e)}")
            return False
```

## Cache Management Methods

```python
    def clear_cache(self) -> None:
        """
        [Method intent]
        Clear all cached model data.
        
        [Design principles]
        - Complete cache clearing
        - Thread safety
        
        [Implementation details]
        - Invalidates all model cache entries
        - Logs clearing operations
        
        Returns:
            None
        """
        try:
            self.cache.invalidate("bedrock_models*")
            self.logger.info("Model discovery cache cleared")
        except Exception as e:
            self.logger.warning(f"Error clearing model cache: {str(e)}")
```

## Usage Examples

```python
# Example 1: Get the singleton instance
discovery = BedrockModelDiscovery.get_instance()

# Example 2: Scan all regions for available models
region_models = discovery.scan_all_regions()
print(f"Found models in {len(region_models)} regions")

# Example 3: Get optimal regions for a model
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
best_regions = discovery.get_best_regions_for_model(
    model_id,
    preferred_regions=["us-east-1", "us-west-2"]
)
print(f"Best regions for {model_id}: {best_regions}")

# Example 4: Check if a model is available in a specific region
is_available = discovery.is_model_available_in_region(
    "anthropic.claude-3-sonnet-20240229-v1:0",
    "eu-west-1"
)
print(f"Model available in eu-west-1: {is_available}")
```

## Testing Strategy

1. **Unit Tests:**
   - Test singleton behavior
   - Test region scanning with mocked responses
   - Test cached operations
   - Test latency-based sorting
   - Test thread safety with concurrent access

2. **Integration Tests:**
   - Test with actual AWS regions (limited scope)
   - Verify cache persistence between instances
   - Test dependency injection
   - Test error handling with unavailable regions

## Implementation Steps

1. Create the directory structure
2. Implement the singleton pattern
3. Add core scanning functions with latency measurement
4. Add model information and region selection methods
5. Add cache integration
6. Add comprehensive unit tests
7. Document usage patterns

## Integration with Other Components

The `BedrockModelDiscovery` component will:

1. Use `AWSClientFactory` to create AWS clients
2. Use `DiscoveryCache` to cache discovery results
3. Use `RegionLatencyTracker` to optimize region selection
4. Be used by the Bedrock client implementation for optimal region selection
5. Be used alongside `BedrockProfileDiscovery` for complete Bedrock service information
