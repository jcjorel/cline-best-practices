# Bedrock Discovery Simplification: Core Architecture Plan

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Purpose

This document outlines how we will simplify the core architecture of the Bedrock discovery system, focusing on the base discovery class and scan utilities. Our goal is to reduce architectural complexity while maintaining essential functionality.

## Current Architecture

The current architecture consists of:

1. **BaseDiscovery** (discovery_core.py):
   - Base class with shared functionality
   - Thread management and parallel scanning

2. **Scan Utilities** (scan_utils.py):
   - Model scanning functions
   - Profile scanning functions
   - Combined scanning

3. **Model Discovery** (models.py):
   - BedrockModelDiscovery class (inherits from BaseDiscovery)
   - Model-specific functionality and caching

4. **External Dependencies**:
   - DiscoveryCache for caching
   - RegionLatencyTracker for API latency measurements
   - AWSClientFactory for AWS client creation

## Architecture Simplification Goals

1. **Streamline BaseDiscovery**: Simplify the base class to only contain truly essential shared functionality
2. **Consolidate Scan Utilities**: Reduce the number of scanning functions and simplify their interfaces
3. **Simplify Threading Model**: Make concurrency handling more straightforward
4. **Reduce Component Dependencies**: Minimize external dependencies

## Detailed Simplification Strategy

### 1. BaseDiscovery Simplification

Current state:
```python
class BaseDiscovery:
    # Complex methods for parallel scanning, region management, etc.
    # Numerous helper methods that could be simplified
    
    def scan_regions_parallel(self, regions, scan_func, max_workers=None):
        # Complex parallel scanning implementation
```

Simplification approach:

1. **Keep Only Essential Methods**:
   - Remove methods that could be in concrete classes
   - Keep only truly shared functionality
   - Simplify method interfaces

2. **Streamline Threading Model**:
   - Use a simpler threading model for parallel operations
   - Consolidate locking mechanisms
   - Make thread management more transparent

3. **Proposed BaseDiscovery Structure**:
```python
class BaseDiscovery:
    """
    Simplified base discovery class with essential functionality only.
    """
    def __init__(self, client_factory, logger=None):
        """Simplified constructor with minimal dependencies"""
        self.client_factory = client_factory
        self.logger = logger or logging.getLogger(__name__)
        self._lock = threading.Lock()  # Single lock for thread safety
        
    def scan_regions_parallel(self, regions, scan_func):
        """Simplified parallel scanning with sensible defaults"""
        # Simpler implementation with fewer parameters
```

### 2. Scan Utilities Simplification

Current state:
```python
# Multiple scan functions with varying parameters:
def scan_region_for_models(region, client_factory, latency_tracker, project_models, cache, logger):
    # Complex implementation with many components
    
def scan_region_for_profiles(region, client_factory, cache, logger):
    # Another implementation with different parameters

def scan_region_combined(region, client_factory, latency_tracker, project_models, cache, logger):
    # Combined scanning with all parameters
```

Simplification approach:

1. **Consolidate Scan Functions**:
   - Merge similar functions into a single, clear implementation
   - Create a unified scan function that handles both models and profiles

2. **Reduce Parameter Lists**:
   - Remove rarely-used parameters
   - Use consistent parameter order across functions
   - Provide sensible defaults when possible

3. **Proposed Scan Utilities Structure**:
```python
def scan_region(
    region, 
    client_factory, 
    include_models=True,
    include_profiles=True,
    project_models=None,
    logger=None
):
    """
    Unified scan function with clean parameters and defaults.
    Returns tuple (models, profiles) with empty lists for disabled scans.
    """
    # Simplified implementation
```

### 3. Models.py Simplification

Current state:
```python
class BedrockModelDiscovery(BaseDiscovery):
    # Inherits from BaseDiscovery
    # Has multiple scanning methods with similar functionality
    # Complex caching and latency handling
    # Numerous parameters across methods
```

Simplification approach:

1. **Simplify Singleton Implementation**:
   - Streamline the get_instance() method
   - Reduce dependency initialization

2. **Integrate Essential Caching**:
   - Incorporate simple caching directly in the class
   - Remove complex cache operations

3. **Simplify Latency Handling**:
   - Integrate simplified latency tracking
   - Remove external latency tracker dependency

4. **Proposed BedrockModelDiscovery Structure**:
```python
class BedrockModelDiscovery(BaseDiscovery):
    """Simplified BedrockModelDiscovery with integrated caching and latency tracking."""
    
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls):
        """Simplified singleton access"""
        # Streamlined implementation
        
    def __init__(self):
        """Simplified constructor with minimal dependencies"""
        # Required functionality only
        
    # Simplified model discovery methods
```

## Implementation Strategy

1. **Phase 1: Simplify BaseDiscovery**
   - Remove unnecessary methods
   - Streamline interface
   - Simplify threading model

2. **Phase 2: Consolidate Scan Utilities**
   - Create unified scan function
   - Remove redundant functions
   - Simplify parameter lists

3. **Phase 3: Enhance BedrockModelDiscovery**
   - Integrate simplified caching
   - Incorporate streamlined latency tracking
   - Reduce external dependencies

## Compatibility Considerations

The simplified architecture must maintain:

1. **Singleton Pattern**: Preserve singleton behavior for project-wide reuse
2. **Thread Safety**: Ensure thread-safe operations with reduced locking complexity
3. **Core Functionality**: Maintain essential discovery capabilities
4. **API Compatibility**: Preserve key public method signatures for backward compatibility

## Metrics for Success

1. **Reduced Code Size**: Fewer lines of code without losing functionality
2. **Simplified Interfaces**: Clearer, more consistent method signatures
3. **Reduced Dependencies**: Fewer external component dependencies
4. **Maintained Functionality**: All essential features remain working

## Next Steps

1. Create detailed implementation plan for BaseDiscovery simplification
2. Document specific changes to scan utilities
3. Outline BedrockModelDiscovery integration changes
