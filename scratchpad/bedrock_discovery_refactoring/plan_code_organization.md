# Bedrock Discovery Refactoring: Code Organization and Profile Integration

## Current Issues

1. `models.py` is already large and adding profile scanning would make it even larger
2. `BedrockProfileDiscovery` duplicates region scanning logic from `BedrockModelDiscovery`
3. We want profile discovery to happen in threads already created by `scan_all_regions`

## Proposed File Structure

To address code organization concerns while meeting the integration requirements, we'll reorganize the code into these files:

```
src/dbp/llm/bedrock/discovery/
├── models.py           # Slimmed down BedrockModelDiscovery core functionality
├── profiles.py         # Slimmed down BedrockProfileDiscovery (cache-only)
├── discovery_core.py   # NEW: Core discovery functionality shared between models and profiles
├── association.py      # NEW: Profile-to-model association functionality
├── scan_utils.py       # NEW: Scanning utilities for both models and profiles
├── cache.py            # Existing: Cache implementation
└── latency.py          # Existing: Latency tracking
```

## Code Distribution

### 1. discovery_core.py (New File)

This file will contain shared functionality between model and profile discovery:

```python
# discovery_core.py
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Set, Callable, Tuple

from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from ....api_providers.aws.client_factory import AWSClientFactory

class BaseDiscovery:
    """
    Base class for AWS Bedrock discovery operations.
    Provides common functionality for model and profile discovery.
    """
    # Common constants
    INITIAL_BEDROCK_REGIONS = [
        "us-east-1", "us-west-2", "eu-west-1", "ap-northeast-1", 
        "ap-southeast-1", "ap-southeast-2", "eu-central-1"
    ]
    
    def __init__(
        self,
        cache: Optional[DiscoveryCache] = None,
        client_factory: Optional[AWSClientFactory] = None,
        latency_tracker: Optional[RegionLatencyTracker] = None,
        logger: Optional[logging.Logger] = None
    ):
        self.cache = cache or DiscoveryCache()
        self.client_factory = client_factory or AWSClientFactory.get_instance()
        self.latency_tracker = latency_tracker or RegionLatencyTracker(cache=self.cache)
        self.logger = logger or logging.getLogger(__name__)
    
    def get_all_regions(self) -> List[str]:
        """Get list of all AWS regions where Bedrock might be available."""
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

    def scan_regions_parallel(
        self, 
        regions: List[str],
        scan_function: Callable[[str], Any],
        max_workers: int = 10
    ) -> Dict[str, Any]:
        """
        Generic method to scan regions in parallel using a provided scan function.
        
        Args:
            regions: List of regions to scan
            scan_function: Function to execute for each region
            max_workers: Maximum number of parallel workers
            
        Returns:
            Dict mapping regions to scan results
        """
        result = {}
        
        self.logger.info(f"Scanning {len(regions)} AWS regions in parallel...")
        
        # Use ThreadPoolExecutor to scan regions in parallel
        with ThreadPoolExecutor(max_workers=min(max_workers, len(regions))) as executor:
            # Submit scanning tasks
            future_to_region = {
                executor.submit(scan_function, region): region
                for region in regions
            }
            
            # Process results as they complete
            for future in as_completed(future_to_region):
                region = future_to_region[future]
                try:
                    scan_result = future.result()
                    if scan_result:
                        result[region] = scan_result
                except Exception as e:
                    self.logger.warning(f"Error scanning region {region}: {str(e)}")
        
        return result
```

### 2. scan_utils.py (New File)

This file will contain the actual scanning logic:

```python
# scan_utils.py
import time
import logging
from typing import Dict, List, Optional, Any, Tuple

import boto3
import botocore.exceptions

from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError

def scan_region_for_models(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    project_supported_models: List[str],
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """Scan a region for Bedrock models."""
    # Implementation from _scan_region in BedrockModelDiscovery
    # But without profile scanning
    pass

def scan_region_for_profiles(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    logger: logging.Logger
) -> List[Dict[str, Any]]:
    """Scan a region for Bedrock inference profiles."""
    # Implementation from scan_profiles_in_region in BedrockProfileDiscovery
    pass

def scan_region_combined(
    region: str,
    client_factory: AWSClientFactory,
    latency_tracker: RegionLatencyTracker,
    project_supported_models: List[str],
    cache: DiscoveryCache,
    logger: logging.Logger
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Scan a region for both models and profiles in a single operation.
    
    Returns:
        Tuple of (models, profiles) lists
    """
    models = []
    all_models = []
    project_models = []
    profiles = []
    start_time = time.time()
    
    try:
        # Get Bedrock client for this region
        bedrock_client = client_factory.get_client("bedrock", region_name=region)
        
        # 1. Scan for models
        # [Model scanning code from _scan_region]
        
        # 2. Scan for profiles if needed
        profile_needed = any(model.get("requiresInferenceProfile", False) 
                           for model in (project_models if project_models else all_models))
        
        if profile_needed:
            try:
                # [Profile scanning code]
                
                # Store profiles in cache
                cache.set_profile_cache(region, profiles)
            except Exception as e:
                logger.warning(f"Error scanning profiles in region {region}: {str(e)}")
        
        # Return models and profiles
        models = project_models if project_models else all_models
        return models, profiles
        
    except Exception as e:
        logger.warning(f"Error scanning region {region}: {str(e)}")
        return [], []
```

### 3. association.py (New File)

This file will contain code for associating profiles with models:

```python
# association.py
import logging
from typing import Dict, List, Optional, Any

def associate_profiles_with_models(
    models: List[Dict[str, Any]], 
    profiles: List[Dict[str, Any]],
    logger: Optional[logging.Logger] = None
) -> List[Dict[str, Any]]:
    """
    Associate profiles with models using ARN-based extraction from profiles.
    
    Args:
        models: List of model information dictionaries
        profiles: List of profile information dictionaries
        logger: Optional logger
        
    Returns:
        The updated models list with embedded profile information
    """
    if logger is None:
        logger = logging.getLogger(__name__)
        
    # Process each profile
    for profile in profiles:
        profile_id = profile.get("inferenceProfileId")
        if not profile_id:
            continue
            
        # Examine each model ARN in this profile
        for model_ref in profile.get("models", []):
            model_arn = model_ref.get("modelArn", "")
            if not model_arn or "/" not in model_arn:
                continue
                
            # Extract model ID directly from ARN
            # ARN format: arn:aws:bedrock:{region}::foundation-model/{model_id}
            arn_parts = model_arn.split("/")
            if len(arn_parts) >= 2:
                referenced_model_id = arn_parts[-1]
                
                # Find matching model
                for model in models:
                    if model.get("modelId") == referenced_model_id:
                        # Initialize referencedByInstanceProfiles if needed
                        if "referencedByInstanceProfiles" not in model:
                            model["referencedByInstanceProfiles"] = []
                        
                        # Avoid duplicates
                        profile_already_added = any(
                            p.get("inferenceProfileId") == profile_id 
                            for p in model["referencedByInstanceProfiles"]
                        )
                        
                        if not profile_already_added:
                            # Add the complete profile data to the model
                            logger.debug(f"Adding profile {profile_id} to model {referenced_model_id}")
                            model["referencedByInstanceProfiles"].append(profile)
    
    return models
```

### 4. Updated models.py

The slimmed down `models.py` file will focus on the core functionality:

```python
# models.py (Slimmed down version)
import logging
import threading
import copy
from typing import Dict, List, Optional, Any, Set

# Local imports
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from .discovery_core import BaseDiscovery
from .scan_utils import scan_region_combined
from .association import associate_profiles_with_models

# External imports
from ....api_providers.aws.client_factory import AWSClientFactory


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
    
    @classmethod
    def get_instance(cls, 
                    cache: Optional[DiscoveryCache] = None, 
                    client_factory: Optional[AWSClientFactory] = None, 
                    latency_tracker: Optional[RegionLatencyTracker] = None, 
                    initial_scan: bool = True,
                    logger: Optional[logging.Logger] = None):
        """Get or create the singleton instance."""
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
                cache: Optional[DiscoveryCache] = None, 
                client_factory: Optional[AWSClientFactory] = None, 
                latency_tracker: Optional[RegionLatencyTracker] = None, 
                initial_scan: bool = False,
                logger: Optional[logging.Logger] = None):
        """Initialize the discovery service."""
        # Initialize base class
        super().__init__(cache, client_factory, latency_tracker, logger)
        
        # Additional initialization
        self._region_lock = threading.Lock()
        
        # Get project supported models from model classes
        self.project_supported_models = self._get_project_supported_models()
        self.logger.info(f"Loaded {len(self.project_supported_models)} project-supported models")
        
        # Try to perform initial scan if requested
        if initial_scan:
            self.scan_all_regions()
    
    def scan_all_regions(self, regions: Optional[List[str]] = None, refresh_cache: bool = False) -> Dict[str, List[Dict[str, Any]]]:
        """Scan regions for models and profiles."""
        result = {}
        
        # If not forcing refresh, try to use cache
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
            regions_to_scan = self.get_all_regions()
        
        if regions_to_scan:
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
                    # Cache updated models
                    self.cache.set_model_cache(region, models)
                    
                return models
            
            # Use parallel scanning from base class
            scanned_results = self.scan_regions_parallel(
                regions_to_scan, 
                region_scan_func
            )
            
            # Merge results
            result.update(scanned_results)
        
        return result
    
    # [Keep other essential methods like get_model_regions, get_best_regions_for_model, etc.]
    # ...
    
    def get_model(self, model_id: str, region: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a specific model, optionally from a specific region.
        Includes associated inference profiles if available.
        
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
        
        # Check if model is available in the specified region
        cached_models = self.cache.get_model_cache(region)
        if not cached_models:
            return None
            
        # Find the model in the cache
        for model in cached_models:
            if model["modelId"] == model_id:
                # Return a deep copy to prevent modifying the cache
                return copy.deepcopy(model)
                
        return None
        
    def _get_project_supported_models(self) -> List[str]:
        """Get the list of Bedrock models supported by the project from model classes."""
        # [Implementation]
```

### 5. Updated profiles.py

The updated `profiles.py` will be slimmed down to focus on cache-only operations:

```python
# profiles.py (Slimmed down version)
import logging
import threading
import time
import warnings
from typing import Dict, List, Optional, Any, Set

# Local imports
from .cache import DiscoveryCache
from .latency import RegionLatencyTracker
from .discovery_core import BaseDiscovery
from .association import associate_profiles_with_models

# External imports
from ....api_providers.aws.client_factory import AWSClientFactory


class BedrockProfileDiscovery(BaseDiscovery):
    """
    [Class intent]
    Provides information about AWS Bedrock inference profiles across regions,
    enabling optimal provisioned throughput selection based on region availability and latency.
    Uses cached data gathered by BedrockModelDiscovery.
    
    [Design principles]
    - Clean separation from model discovery
    - Thread-safe operations for concurrent access
    - Latency-aware region selection
    - Complete metadata extraction
    - Singleton pattern for project-wide reuse
    - Cache-first approach for performance
    """
    
    # Class variables for singleton pattern
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, 
                    cache: Optional[DiscoveryCache] = None, 
                    client_factory: Optional[AWSClientFactory] = None, 
                    latency_tracker: Optional[RegionLatencyTracker] = None, 
                    model_discovery = None,
                    logger: Optional[logging.Logger] = None):
        """Get or create the singleton instance."""
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
                cache: Optional[DiscoveryCache] = None, 
                client_factory: Optional[AWSClientFactory] = None, 
                latency_tracker: Optional[RegionLatencyTracker] = None,
                model_discovery = None,
                logger: Optional[logging.Logger] = None):
        """Initialize the profile discovery service."""
        # Initialize base class
        super().__init__(cache, client_factory, latency_tracker, logger)
        
        # Additional initialization
        self._profile_lock = threading.Lock()
        self._model_to_profiles_map = {}  # {model_id: {region: [profile_ids]}}
        
        # Import model_discovery here to avoid circular imports
        if model_discovery is None:
            from .models import BedrockModelDiscovery
            self.model_discovery = BedrockModelDiscovery.get_instance(
                cache=self.cache,
                client_factory=self.client_factory,
                latency_tracker=self.latency_tracker
            )
        else:
            self.model_discovery = model_discovery
    
    def scan_profiles_in_region(self, region: str, model_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        [DEPRECATED] Scan a region for inference profiles.
        
        This method is deprecated and will be removed in a future version.
        The profile scanning is now automatically performed by BedrockModelDiscovery.scan_all_regions().
        """
        warnings.warn(
            "scan_profiles_in_region is deprecated. Profile scanning is now automatically "
            "performed by BedrockModelDiscovery.scan_all_regions()",
            DeprecationWarning, 
            stacklevel=2
        )
        
        # Force a rescan of the region to get latest profiles
        self.model_discovery.scan_all_regions([region], refresh_cache=True)
        
        # Return profiles from cache
        return self.cache.get_profile_cache(region, model_id)
    
    # [Keep other essential methods like get_inference_profile_ids, get_inference_profile, etc.]
    # but update them to be cache-only
    # ...
```

## Implementation Plan

### Phase 1: Create New Files
1. Create `discovery_core.py` with BaseDiscovery class
2. Create `scan_utils.py` with scanning utilities
3. Create `association.py` with association utilities

### Phase 2: Update Existing Files
1. Slim down `models.py` to use new shared functionality
2. Slim down `profiles.py` to be cache-only
3. Ensure proper circular import handling

### Phase 3: Testing & Migration
1. Test the refactored code
2. Update any code that relied on direct scanning
3. Document API changes and migration paths

## Benefits

1. **Better Code Organization**: Functionality distributed across logically separated files
2. **Reduced Duplication**: Scanning code centralized in one place
3. **Clearer Responsibilities**: Each file has a specific purpose
4. **Better Maintainability**: Smaller, more focused files
5. **Efficient API Usage**: Profile scanning happens in model discovery threads

## Migration Path

For users of the current API:
- All existing public methods will continue to work
- BedrockProfileDiscovery.scan_profiles_in_region() will show a deprecation warning
- BedrockModelDiscovery.get_instance() will now trigger scanning by default
