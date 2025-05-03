# Bedrock Profile Discovery Implementation Plan

## Overview
The `BedrockProfileDiscovery` component is a singleton service that discovers and provides information about AWS Bedrock inference profiles across regions. It complements the Model Discovery component by focusing specifically on provisioned throughput offerings.

## File Location
`src/dbp/llm/bedrock/discovery/profiles.py`

## Class Structure

```python
class BedrockProfileDiscovery:
    """
    [Class intent]
    Discovers and provides information about AWS Bedrock inference profiles across regions,
    enabling optimal provisioned throughput selection based on region availability and latency.
    
    [Design principles]
    - Clean separation from model discovery
    - Thread-safe operations for concurrent access
    - Latency-aware region selection
    - Complete metadata extraction
    - Singleton pattern for project-wide reuse
    
    [Implementation details]
    - Uses AWSClientFactory for client access
    - Implements model-to-profile mapping
    - Caches discovery results with configurable TTL
    - Provides region-specific profile information
    - Maps profile availability by region and model
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
```

## Singleton Pattern Implementation

```python
    @classmethod
    def get_instance(cls, 
                    cache=None, 
                    client_factory=None, 
                    latency_tracker=None, 
                    model_discovery=None,
                    logger=None):
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
                cache=None, 
                client_factory=None, 
                latency_tracker=None,
                model_discovery=None,
                logger=None):
        """
        [Method intent]
        Initialize the Bedrock profile discovery service.
        
        [Design principles]
        - Protected constructor for singleton pattern
        - Component dependency management
        - Thread-safe initialization
        
        [Implementation details]
        - Sets up dependencies (creating if not provided)
        - Initializes internal state
        - Connects with related discovery services
        
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
        from .models import BedrockModelDiscovery
        
        self.client_factory = client_factory or AWSClientFactory.get_instance()
        self.cache = cache or DiscoveryCache()
        self.latency_tracker = latency_tracker or RegionLatencyTracker(cache=self.cache)
        self.model_discovery = model_discovery or BedrockModelDiscovery.get_instance()
        self.logger = logger or logging.getLogger(__name__)
        
        self._profile_lock = threading.Lock()
        self._model_to_profiles_map = {}  # {model_id: {region: [profile_ids]}}
```

## Core Profile Discovery Methods

```python
    def get_inference_profile_ids(self, model_id: str, region: str = None) -> List[str]:
        """
        [Method intent]
        Get all inference profile IDs for a model, optionally in a specific region.
        
        [Design principles]
        - Cache-first approach for efficiency
        - Model-specific profile discovery
        - Region-aware operation
        
        [Implementation details]
        - Checks cache for profile information
        - Scans regions if needed for discovery
        - Returns profile IDs mapped to the model
        - Handles multiple regions if not specified
        
        Args:
            model_id: The Bedrock model ID
            region: Optional specific region to check
            
        Returns:
            List of inference profile IDs for the model
        """
        profile_ids = []
        
        # If region specified, check only that region
        if region:
            profiles = self._get_profiles_in_region(region)
            if profiles:
                for profile in profiles:
                    if profile.get("modelId") == model_id:
                        profile_ids.append(profile["inferenceProfileId"])
            return profile_ids
        
        # If no region specified, check all regions where the model is available
        model_regions = self.model_discovery.get_model_regions(model_id)
        
        for region in model_regions:
            region_profiles = self._get_profiles_in_region(region)
            if region_profiles:
                for profile in region_profiles:
                    if profile.get("modelId") == model_id:
                        profile_id = profile["inferenceProfileId"]
                        if profile_id not in profile_ids:
                            profile_ids.append(profile_id)
        
        return profile_ids
    
    def get_inference_profile(self, model_id: str, profile_id: str, region: str = None) -> Optional[Dict[str, Any]]:
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
        - Makes direct API call if needed
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
                    return profile
        
        # If not in cache or cache miss, make direct API call
        try:
            bedrock_client = self.client_factory.get_client("bedrock", region_name=region)
            
            # Measure latency for this operation
            start_time = time.time()
            response = bedrock_client.get_inference_profile(
                inferenceProfileId=profile_id
            )
            latency = time.time() - start_time
            self.latency_tracker.update_latency(region, latency)
            
            # Extract profile details
            profile_info = {
                "inferenceProfileId": response.get("inferenceProfileId"),
                "inferenceProfileName": response.get("inferenceProfileName", ""),
                "modelId": response.get("modelId"),
                "status": response.get("status", ""),
                "provisionedThroughput": response.get("provisionedThroughput", {}),
                "region": region,
                "creationTime": response.get("creationTime"),
                "lastModifiedTime": response.get("lastModifiedTime")
            }
            
            # Update cache with individual profile
            self._update_profile_in_cache(region, profile_info)
            
            return profile_info
            
        except Exception as e:
            self.logger.warning(f"Error retrieving profile {profile_id} in {region}: {str(e)}")
            return None
    
    def scan_profiles_in_region(self, region: str, model_id: str = None) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Scan a region for all available inference profiles, optionally filtered by model.
        
        [Design principles]
        - Complete profile discovery
        - Latency measurement
        - Optional model filtering
        - Cache integration
        
        [Implementation details]
        - Makes direct API calls to list profiles
        - Records latency for region optimization
        - Updates cache with discovered profiles
        - Optionally filters by model ID
        
        Args:
            region: AWS region to scan
            model_id: Optional model ID to filter profiles
            
        Returns:
            List of profile information dictionaries
        """
        # First check cache
        if not model_id:
            cached_profiles = self.cache.get_profile_cache(region)
            if cached_profiles:
                return cached_profiles
        else:
            cached_profiles = self.cache.get_profile_cache(region, model_id)
            if cached_profiles:
                return cached_profiles
        
        # If not in cache or filtered by model_id, scan the region
        try:
            bedrock_client = self.client_factory.get_client("bedrock", region_name=region)
            
            # Measure latency
            start_time = time.time()
            response = bedrock_client.list_inference_profiles()
            latency = time.time() - start_time
            self.latency_tracker.update_latency(region, latency)
            
            profiles = []
            
            for profile_summary in response.get("inferenceProfileSummaries", []):
                # Create basic profile info from summary
                profile_info = {
                    "inferenceProfileId": profile_summary.get("inferenceProfileId"),
                    "inferenceProfileName": profile_summary.get("inferenceProfileName", ""),
                    "modelId": profile_summary.get("modelId"),
                    "status": profile_summary.get("status", ""),
                    "provisionedThroughput": profile_summary.get("provisionedThroughput", {}),
                    "region": region
                }
                
                # Filter by model if specified
                if model_id and profile_info["modelId"] != model_id:
                    continue
                    
                profiles.append(profile_info)
            
            # Update cache with all profiles
            if profiles and not model_id:
                self.cache.set_profile_cache(region, profiles)
                
                # Update model-to-profile map
                self._update_model_profile_map(region, profiles)
            
            self.logger.info(f"Found {len(profiles)} inference profiles in region {region}")
            
            return profiles
            
        except Exception as e:
            self.logger.warning(f"Error scanning profiles in region {region}: {str(e)}")
            return []
```

## Helper Methods

```python
    def _get_profiles_in_region(self, region: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get all inference profiles in a specific region, using cache when possible.
        
        [Design principles]
        - Cache-first approach
        - Direct scanning when needed
        - Error handling
        
        [Implementation details]
        - Checks cache for region profiles
        - Falls back to direct scanning if needed
        - Returns all profile data for the region
        
        Args:
            region: AWS region to get profiles for
            
        Returns:
            List of profile information dictionaries
        """
        # Check cache first
        cached_profiles = self.cache.get_profile_cache(region)
        if cached_profiles:
            return cached_profiles
            
        # If not in cache, scan the region
        return self.scan_profiles_in_region(region)
    
    def _find_regions_for_profile(self, profile_id: str, model_id: str = None) -> List[str]:
        """
        [Method intent]
        Find regions where a specific profile is available.
        
        [Design principles]
        - Cache-first approach
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
            # This is less efficient but necessary if we don't know the model
            for region in self.model_discovery.INITIAL_BEDROCK_REGIONS:
                profiles = self._get_profiles_in_region(region)
                for profile in profiles:
                    if profile.get("inferenceProfileId") == profile_id:
                        regions_with_profile.append(region)
                        break
        
        # Sort by latency for optimal access
        return self.latency_tracker.get_sorted_regions(regions_with_profile)
    
    def _update_profile_in_cache(self, region: str, profile: Dict[str, Any]) -> None:
        """
        [Method intent]
        Update a specific profile in the cache.
        
        [Design principles]
        - Efficient cache updates
        - Consistent cache state
        - Thread safety
        
        [Implementation details]
        - Gets existing cache data
        - Updates or adds profile information
        - Writes back to cache atomically
        
        Args:
            region: AWS region for the profile
            profile: Profile information dictionary
        """
        # Get existing profiles from cache
        cached_profiles = self.cache.get_profile_cache(region) or []
        
        # Find if profile already exists
        found = False
        for i, p in enumerate(cached_profiles):
            if p.get("inferenceProfileId") == profile["inferenceProfileId"]:
                # Update existing profile
                cached_profiles[i] = profile
                found = True
                break
                
        if not found:
            # Add new profile
            cached_profiles.append(profile)
            
        # Update cache
        self.cache.set_profile_cache(region, cached_profiles)
        
        # Update model-to-profile map
        if "modelId" in profile:
            model_id = profile["modelId"]
            profile_id = profile["inferenceProfileId"]
            self._add_to_model_profile_map(model_id, region, profile_id)
    
    def _update_model_profile_map(self, region: str, profiles: List[Dict[str, Any]]) -> None:
        """
        [Method intent]
        Update the internal model-to-profile mapping.
        
        [Design principles]
        - Efficient mapping updates
        - Thread-safe operations
        - Complete relationship tracking
        
        [Implementation details]
        - Processes profiles to extract model relationships
        - Updates internal mapping with thread safety
        - Groups profiles by model ID
        
        Args:
            region: AWS region for the profiles
            profiles: List of profile information dictionaries
        """
        with self._profile_lock:
            for profile in profiles:
                model_id = profile.get("modelId")
                profile_id = profile.get("inferenceProfileId")
                
                if model_id and profile_id:
                    self._add_to_model_profile_map(model_id, region, profile_id)
    
    def _add_to_model_profile_map(self, model_id: str, region: str, profile_id: str) -> None:
        """
        [Method intent]
        Add a profile to the model-to-profile mapping.
        
        [Design principles]
        - Thread safety
        - Efficient data structure updates
        - Support for multi-region models
        
        [Implementation details]
        - Creates nested mapping structure as needed
        - Ensures thread-safe updates
        - Prevents duplicate entries
        
        Args:
            model_id: The model ID
            region: AWS region for the profile
            profile_id: The profile ID
        """
        with self._profile_lock:
            # Initialize model entry if needed
            if model_id not in self._model_to_profiles_map:
                self._model_to_profiles_map[model_id] = {}
                
            # Initialize region entry if needed
            if region not in self._model_to_profiles_map[model_id]:
                self._model_to_profiles_map[model_id][region] = []
                
            # Add profile ID if not already present
            if profile_id not in self._model_to_profiles_map[model_id][region]:
                self._model_to_profiles_map[model_id][region].append(profile_id)
```

## Model ID Resolution

```python
    def get_model_id_for_profile(self, profile_id: str, region: str = None) -> Optional[str]:
        """
        [Method intent]
        Get the model ID associated with a specific inference profile.
        
        [Design principles]
        - Efficient resolution
        - Region-specific lookup
        - Cache-first approach
        
        [Implementation details]
        - Checks internal mapping first
        - Falls back to cache or API calls
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
        for region in self.model_discovery.INITIAL_BEDROCK_REGIONS:
            profile = self._get_profile_by_id(profile_id, region)
            if profile and "modelId" in profile:
                return profile["modelId"]
                
        return None
    
    def _get_profile_by_id(self, profile_id: str, region: str) -> Optional[Dict[str, Any]]:
        """
        [Method intent]
        Get a profile by ID from a specific region.
        
        [Design principles]
        - Cache-first approach
        - Direct API access when needed
        - Error handling
        
        [Implementation details]
        - Checks cache for the profile
        - Makes API call if not found in cache
        - Returns complete profile information
        
        Args:
            profile_id: Inference profile ID
            region: AWS region to check
            
        Returns:
            Dict with profile information or None if not found
        """
        # Check cache first
        cached_profiles = self.cache.get_profile_cache(region)
        if cached_profiles:
            for profile in cached_profiles:
                if profile.get("inferenceProfileId") == profile_id:
                    return profile
        
        # If not in cache, make direct API call
        try:
            bedrock_client = self.client_factory.get_client("bedrock", region_name=region)
            
            # Measure latency
            start_time = time.time()
            response = bedrock_client.get_inference_profile(
                inferenceProfileId=profile_id
            )
            latency = time.time() - start_time
            self.latency_tracker.update_latency(region, latency)
            
            if "inferenceProfile" in response:
                profile_data = response["inferenceProfile"]
                profile_info = {
                    "inferenceProfileId": profile_data.get("inferenceProfileId"),
                    "inferenceProfileName": profile_data.get("inferenceProfileName", ""),
                    "modelId": profile_data.get("modelId"),
                    "status": profile_data.get("status", ""),
                    "provisionedThroughput": profile_data.get("provisionedThroughput", {}),
                    "region": region
                }
                
                # Update cache with this profile
                self._update_profile_in_cache(region, profile_info)
                
                return profile_info
                
            return None
            
        except Exception as e:
            self.logger.debug(f"Profile {profile_id} not found in {region}: {str(e)}")
            return None
```

## Cache Management Methods

```python
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
            self.cache.invalidate("bedrock_profiles*")
            
            # Clear internal mapping
            with self._profile_lock:
                self._model_to_profiles_map.clear()
                
            self.logger.info("Profile discovery cache cleared")
        except Exception as e:
            self.logger.warning(f"Error clearing profile cache: {str(e)}")
```

## Usage Examples

```python
# Example 1: Get the singleton instance
profile_discovery = BedrockProfileDiscovery.get_instance()

# Example 2: Get inference profile IDs for a model
model_id = "anthropic.claude-3-haiku-20240307-v1:0"
profile_ids = profile_discovery.get_inference_profile_ids(model_id)
print(f"Found {len(profile_ids)} inference profiles for {model_id}")

# Example 3: Get detailed profile information
if profile_ids:
    profile_info = profile_discovery.get_inference_profile(
        model_id, 
        profile_ids[0]
    )
    print(f"Profile details: {profile_info}")

# Example 4: Get model ID for a profile
profile_id = "example-profile-id"
model_id = profile_discovery.get_model_id_for_profile(profile_id)
print(f"Profile {profile_id} is for model {model_id}")
```

## Testing Strategy

1. **Unit Tests:**
   - Test singleton behavior
   - Test profile scanning with mocked responses
   - Test cached operations
   - Test model ID resolution
   - Test thread safety with concurrent access

2. **Integration Tests:**
   - Test with actual AWS regions (limited scope)
   - Verify cache persistence between instances
   - Test dependency injection
   - Test error handling with unavailable profiles

## Implementation Steps

1. Create the directory structure
2. Implement the singleton pattern
3. Add core profile discovery functions
4. Add model-to-profile mapping
5. Add helper methods for efficient lookups
6. Add cache integration
7. Add comprehensive unit tests
8. Document usage patterns

## Integration with Other Components

The `BedrockProfileDiscovery` component will:

1. Use `AWSClientFactory` to create AWS clients
2. Use `DiscoveryCache` to cache discovery results
3. Use `RegionLatencyTracker` to optimize region selection
4. Use `BedrockModelDiscovery` to find regions for models
5. Be used by the Bedrock client implementation for profile handling
