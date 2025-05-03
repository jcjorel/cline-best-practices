# Bedrock Discovery Simplification: Model Discovery Implementation Plan

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Purpose

This document details our plan to simplify the BedrockModelDiscovery class, focusing on reducing complexity while maintaining essential functionality and API compatibility.

## Current Implementation Issues

The current BedrockModelDiscovery implementation has several complexity issues:

1. **Complex Constructor**: Takes multiple optional components (cache, client_factory, latency_tracker, logger)
2. **Multiple Scanning Methods**: Several overlapping methods (`scan_all_regions`, `_scan_all_regions`, `_scan_region`)
3. **Complex Caching Logic**: Relies on an external DiscoveryCache component with sophisticated logic
4. **Redundant Latency Handling**: Depends on a separate RegionLatencyTracker component
5. **Excessive Thread Safety**: Multiple locks for different operations
6. **Parameter Proliferation**: Many methods have numerous parameters with complex interactions

## Simplification Approach

### 1. Simplify Singleton Implementation

Current implementation:
```python
@classmethod
def get_instance(cls):
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
```

Simplified implementation:
```python
@classmethod
def get_instance(cls, scan_on_init=False):
    """
    [Method intent]
    Get the singleton instance of BedrockModelDiscovery, creating it if needed.
    
    [Design principles]
    - Thread-safe singleton access
    - Lazy initialization
    - Simple parameter-free access by default
    
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
```

### 2. Simplify Constructor

Current implementation:
```python
def __init__(self, 
            cache: Optional[DiscoveryCache] = None, 
            client_factory: Optional[AWSClientFactory] = None, 
            latency_tracker: Optional[RegionLatencyTracker] = None, 
            logger: Optional[logging.Logger] = None):
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
```

Simplified implementation:
```python
def __init__(self):
    """
    [Method intent]
    Initialize the BedrockModelDiscovery singleton with simplified internals.
    
    [Design principles]
    - Protected constructor for singleton pattern
    - Minimal dependencies
    - Simple initialization
    
    [Implementation details]
    - Gets required dependencies directly
    - Uses integrated caching instead of external components
    - Creates a single lock for thread safety
    - Loads supported models automatically
    """
    # Enforce singleton pattern
    if self.__class__._instance is not None:
        raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
        
    # Get minimal required dependencies
    self.client_factory = AWSClientFactory.get_instance()
    self.logger = logging.getLogger(__name__)
    
    # Single lock for thread safety
    self._lock = threading.Lock()
    
    # Initialize simple internal cache
    self._memory_cache = {
        "models": {},
        "latency": {},
        "last_updated": {}
    }
    
    # Initial bedrock regions - will be expanded through discovery
    self.bedrock_regions = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", 
        "ap-southeast-1", "ap-southeast-2", "eu-central-1"
    ]
    
    # Get project supported models from model classes
    self.project_supported_models = self._get_project_supported_models()
    self.logger.info(f"Loaded {len(self.project_supported_models)} project-supported models")
```

### 3. Consolidated Scanning Method

Current implementation has multiple overlapping scanning methods:
- `scan_all_regions(regions, force_rescan)`
- `_scan_all_regions(regions, refresh_cache)`
- `_scan_region(region)`

Consolidated implementation:
```python
def scan_all_regions(self, regions=None, force_refresh=False):
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
    regions_to_scan = regions or self.bedrock_regions
    
    # Check if we can use cache
    if not force_refresh:
        with self._lock:
            cached_models = self._memory_cache.get("models", {})
            
            # Use cached data when available
            for region in regions_to_scan:
                if region in cached_models:
                    result["models"][region] = cached_models[region]
    
    # Determine which regions need scanning
    missing_regions = [r for r in regions_to_scan if r not in result["models"]]
    
    if missing_regions or force_refresh:
        # Scan missing or all regions in parallel
        to_scan = regions_to_scan if force_refresh else missing_regions
        self.logger.info(f"Scanning {len(to_scan)} regions for Bedrock models")
        
        with ThreadPoolExecutor() as executor:
            future_to_region = {
                executor.submit(self._scan_region, region): region 
                for region in to_scan
            }
            
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    models = future.result()
                    
                    # Convert to required format (model_id -> model details)
                    model_dict = {}
                    for model in models:
                        model_id = model.get("modelId")
                        if model_id:
                            model_dict[model_id] = model
                    
                    # Update result and cache
                    result["models"][region] = model_dict
                    with self._lock:
                        if "models" not in self._memory_cache:
                            self._memory_cache["models"] = {}
                        self._memory_cache["models"][region] = model_dict
                        self._memory_cache["last_updated"]["models"] = time.time()
                
                except Exception as e:
                    self.logger.warning(f"Error scanning region {region}: {str(e)}")
                    # Add empty dict for failed regions
                    result["models"][region] = {}
    
    return result
```

### 4. Simplified Region Selection Logic

The current implementation has complex region selection with multiple helper methods. We'll simplify this to a single, clear mechanism:

```python
def get_best_regions_for_model(self, model_id, preferred_regions=None):
    """
    [Method intent]
    Get the best regions for a specific model, prioritizing preferred regions
    and latency-optimized ordering.
    
    [Design principles]
    - User preference prioritization
    - Simple latency-based ordering
    - Clear region selection logic
    
    [Implementation details]
    - Finds all regions where model is available
    - Prioritizes user's preferred regions
    - Sorts remaining regions by measured latency
    - Returns ordered list for optimal region selection
    
    Args:
        model_id: The Bedrock model ID
        preferred_regions: Optional list of preferred AWS regions
            
    Returns:
        List of region names ordered by preference and latency
    """
    # Get all regions with the model
    available_regions = []
    
    with self._lock:
        cached_models = self._memory_cache.get("models", {})
        for region, models in cached_models.items():
            if model_id in models:
                available_regions.append(region)
    
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
```

### 5. Integrated Latency Tracking

Rather than using a separate RegionLatencyTracker component, we'll incorporate a simplified version directly into the BedrockModelDiscovery class:

```python
def update_latency(self, region, latency_seconds):
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
```

### 6. Simplified Cache Management

Instead of using the complex DiscoveryCache component, we'll implement a simpler caching mechanism directly in the BedrockModelDiscovery class:

```python
def load_cache_from_file(self, file_path=None):
    """
    [Method intent]
    Load model and latency data from a JSON file.
    
    [Design principles]
    - Simple file I/O
    - Optional operation
    - Default path handling
    
    [Implementation details]
    - Uses default path if none specified
    - Basic JSON file loading
    - Updates memory cache with loaded data
    
    Args:
        file_path: Optional path to cache file
            
    Returns:
        bool: True if loading succeeded, False otherwise
    """
    path = file_path or os.path.join(os.path.expanduser("~"), ".bedrock_discovery_cache.json")
    
    try:
        if not os.path.exists(path):
            return False
            
        with open(path, "r") as f:
            data = json.load(f)
        
        # Update memory cache with loaded data
        with self._lock:
            if "models" in data:
                self._memory_cache["models"] = data["models"]
            if "latency" in data:
                self._memory_cache["latency"] = data["latency"]
            self._memory_cache["last_updated"] = data.get("last_updated", {})
            
        self.logger.info(f"Loaded model discovery cache from {path}")
        return True
        
    except Exception as e:
        self.logger.warning(f"Error loading cache from {path}: {str(e)}")
        return False

def save_cache_to_file(self, file_path=None):
    """
    [Method intent]
    Save current model and latency data to a JSON file.
    
    [Design principles]
    - Simple file I/O
    - Optional operation
    - Default path handling
    
    [Implementation details]
    - Uses default path if none specified
    - Basic JSON file saving
    - Creates parent directories if needed
    
    Args:
        file_path: Optional path to cache file
            
    Returns:
        bool: True if saving succeeded, False otherwise
    """
    path = file_path or os.path.join(os.path.expanduser("~"), ".bedrock_discovery_cache.json")
    
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        # Create a copy of the data to save
        with self._lock:
            data = {
                "models": copy.deepcopy(self._memory_cache.get("models", {})),
                "latency": copy.deepcopy(self._memory_cache.get("latency", {})),
                "last_updated": copy.deepcopy(self._memory_cache.get("last_updated", {}))
            }
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
            
        self.logger.info(f"Saved model discovery cache to {path}")
        return True
        
    except Exception as e:
        self.logger.warning(f"Error saving cache to {path}: {str(e)}")
        return False
```

## Simplified API Summary

The simplified BedrockModelDiscovery API will consist of:

1. **Core Singleton Access**:
   - `get_instance(scan_on_init=False)`: Get/create the singleton instance

2. **Model Discovery**:
   - `scan_all_regions(regions=None, force_refresh=False)`: Scan regions for models
   - `get_model(model_id, region=None)`: Get model details from a specific or best region
   - `get_all_models()`: Get all discovered models across regions

3. **Region Selection**:
   - `get_model_regions(model_id)`: Get all regions where a model is available
   - `get_best_regions_for_model(model_id, preferred_regions=None)`: Get optimal regions for a model
   - `is_model_available_in_region(model_id, region)`: Check if model is in a specific region

4. **Cache Management**:
   - `load_cache_from_file(file_path=None)`: Load cache from file (optional)
   - `save_cache_to_file(file_path=None)`: Save cache to file (optional)
   - `clear_cache()`: Clear the in-memory cache

5. **Internal Methods** (not part of public API):
   - `_scan_region(region)`: Scan a single region
   - `_get_project_supported_models()`: Get models supported by the project
   - `update_latency(region, latency_seconds)`: Update region latency

## Implementation Plan

1. **Simplify BaseDiscovery** (if still needed)
2. **Create Consolidated Scan Utilities**
3. **Implement Simplified BedrockModelDiscovery Class**:
   - Simple constructor
   - Consolidated scanning method
   - Integrated caching
   - Integrated latency tracking
4. **Update Documentation and Examples**

## Backwards Compatibility

The simplified implementation will maintain compatibility with existing code:
- All core public methods will be preserved
- Return types will remain the same
- Method signatures may be simplified, but with defaults to maintain compatibility
- Internal implementation changes will be invisible to callers

## Benefits of Simplification

1. **Reduced Code Size**: Fewer lines of code without sacrificing functionality
2. **Simplified API**: Clearer method signatures with fewer parameters
3. **Reduced Dependencies**: Minimal external component dependencies
4. **Improved Maintainability**: Easier to understand and modify
5. **Thread Safety**: Maintained with simpler locking
