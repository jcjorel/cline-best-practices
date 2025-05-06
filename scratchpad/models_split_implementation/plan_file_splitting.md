# File Split Structure Design: models.py into Two Files

## Current File Analysis

The current `models.py` file contains a large class `BedrockModelDiscovery` with multiple responsibilities:
- Core model discovery functionality
- Region scanning and selection
- Model availability checking
- Cache management
- Latency tracking
- Capability detection (e.g., prompt caching)

This file needs to be split into two logical components to improve maintainability and avoid truncation issues.

## Split Strategy

### General Approach

1. Extract core discovery functionality into `models_core.py`
2. Extract extended capabilities into `models_capabilities.py`
3. Use inheritance to extend core functionality with capabilities

## File Content Details

### 1. `models_core.py`

#### Class Definition

```python
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
```

#### Methods to Include

Core singleton and initialization:
- `get_instance(cls, scan_on_init: bool = False)`
- `__init__(self)`

Core discovery functionality:
- `scan_all_regions(self, regions=None, force_refresh=False)`
- `get_model_regions(self, model_id, check_accessibility=True)`
- `get_best_regions_for_model(self, model_id, preferred_regions=None)`
- `is_model_available_in_region(self, model_id, region)`
- `get_all_models(self)`
- `get_model(self, model_id, region=None)`
- `get_json_model_mapping(self)`

#### Required Imports

```python
import logging
import threading
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Optional, Any, Set, Union, Tuple

import boto3
import botocore.exceptions

from ....api_providers.aws.client_factory import AWSClientFactory
from ....api_providers.aws.exceptions import AWSClientError, AWSRegionError
from ....llm.common.exceptions import ModelNotAvailableError

from .discovery_core import BaseDiscovery
from .scan_utils import scan_region
from .association import associate_profiles_with_models
```

### 2. `models_capabilities.py`

#### Class Definition

```python
from .models_core import BedrockModelDiscovery

class BedrockModelCapabilities(BedrockModelDiscovery):
    """
    [Class intent]
    Extends BedrockModelDiscovery with additional capabilities like cache management, 
    latency tracking, and model capability detection such as prompt caching support.
    
    [Design principles]
    - Cache-first approach for performance
    - Integrated caching for efficiency
    - Capability-based model feature detection
    - Seamless extension of core discovery functionality
    
    [Implementation details]
    - Adds file-based cache persistence
    - Implements capability detection for features like prompt caching
    - Provides specialized model filtering based on capabilities
    - Extends the singleton pattern for seamless usage
    """
    
    # Define models that support prompt caching
    _PROMPT_CACHING_SUPPORTED_MODELS = [
        "anthropic.claude-3-5-haiku-",  # Claude 3.5 Haiku
        "anthropic.claude-3-7-sonnet-", # Claude 3.7 Sonnet
        "amazon.nova-micro-",           # Nova Micro
        "amazon.nova-lite-",            # Nova Lite
        "amazon.nova-pro-"              # Nova Pro
    ]
    
    @classmethod
    def get_instance(cls, scan_on_init: bool = False):
        """
        [Method intent]
        Override the parent get_instance method to ensure singleton pattern works 
        properly when extending the base class.
        
        [Design principles]
        - Thread-safe singleton access
        - Seamless extension of parent class
        - Consistent interface with parent
        
        [Implementation details]
        - Overrides parent's get_instance to ensure single instance across both classes
        - Ensures proper type returned
        - Maintains thread safety
        
        Args:
            scan_on_init: If True, perform initial region scan when instance is created
            
        Returns:
            BedrockModelCapabilities: The singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # Create a new instance of the capabilities class
                    cls._instance = cls()
                    # Also update the parent class instance reference for consistency
                    BedrockModelDiscovery._instance = cls._instance
                    
                    # Optionally perform initial scan
                    if scan_on_init:
                        cls._instance.scan_all_regions()
        
        return cls._instance
```

#### Methods to Include

Cache management:
- `update_latency(self, region, latency_seconds)`
- `load_cache_from_file(self, file_path=None)`
- `save_cache_to_file(self, file_path=None)`
- `clear_cache(self)`

Capability detection:
- `supports_prompt_caching(self, model_id)`
- `get_prompt_caching_models(self)`
- `get_prompt_caching_support_status(self)`

#### Required Imports

```python
import os
import json
from typing import Dict, List, Optional, Any

from .models_core import BedrockModelDiscovery
```

## Handling the Singleton Pattern

The singleton pattern requires special attention when splitting the class. Key considerations:

1. The `BedrockModelDiscovery._instance` needs to be accessed from both classes
2. The `get_instance()` method in `BedrockModelCapabilities` must override the parent method
3. Both classes should return the same instance object

The implementation uses a specialized override of `get_instance()` in the capabilities class to ensure:
- Only one instance exists across both classes
- The instance type is `BedrockModelCapabilities` (derived class)
- Both classes reference the same instance

## Import Strategy

The strategy for imports is:
- `models_core.py` has no dependencies on `models_capabilities.py`
- `models_capabilities.py` imports from `models_core.py`

This avoids circular imports and ensures proper class hierarchy.

## Codebase Impact

By using inheritance:
- Existing code calling `BedrockModelDiscovery.get_instance()` will continue to work
- Files that need full functionality will import from `models_capabilities.py`
- Files that only need core functionality can import from `models_core.py`
