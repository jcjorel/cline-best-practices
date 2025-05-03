# Bedrock Discovery Simplification: API Refinement Plan

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Purpose

This document outlines how we will refine the BedrockModelDiscovery API to make it simpler, more consistent, and easier to use, while maintaining backward compatibility with existing code.

## Current API Assessment

The current BedrockModelDiscovery API has the following characteristics:

1. **Multiple Entry Points**: Several overlapping methods for similar functionality
2. **Inconsistent Parameter Names**: Different parameter names for similar concepts
3. **Excessive Optionality**: Too many optional parameters with complex interactions
4. **Mixed Return Types**: Some methods return dicts, others lists, with varying structures
5. **Complex Caching Logic**: Cache management spread across multiple methods

## API Refinement Principles

1. **Consistency**: Use consistent naming and parameter patterns across methods
2. **Simplicity**: Reduce the number of parameters and options
3. **Clarity**: Clear method purposes with minimal overlap
4. **Backward Compatibility**: Maintain compatibility with existing code
5. **Forward-Looking**: Design for future maintainability

## Method-by-Method Refinement

### 1. Core Singleton Access

#### Current:
```python
@classmethod
def get_instance(cls):
    # Complex implementation with component creation
```

#### Refined:
```python
@classmethod
def get_instance(cls, scan_on_init=False):
    """
    Get the singleton instance of BedrockModelDiscovery, creating it if needed.

    Args:
        scan_on_init: If True, perform initial region scan when instance is created

    Returns:
        BedrockModelDiscovery: The singleton instance
    """
```

**Changes**:
- Added optional `scan_on_init` parameter to control initial scanning
- Simplified internal implementation
- Maintained backward compatibility (default behavior unchanged)

### 2. Model Scanning Methods

#### Current:
```python
def scan_all_regions(self, regions=None, force_rescan=False):
    # Implementation that delegates to _scan_all_regions
    
def _scan_all_regions(self, regions=None, refresh_cache=False):
    # Complex implementation with cache handling
```

#### Refined:
```python
def scan_all_regions(self, regions=None, force_refresh=False):
    """
    Scan AWS regions for Bedrock models, either using cache or forcing a fresh scan.

    Args:
        regions: Optional list of regions to scan (defaults to known Bedrock regions)
        force_refresh: If True, bypasses cache and performs fresh API calls

    Returns:
        Dict with structure {"models": {region: {model_id: model_details}}}
    """
```

**Changes**:
- Merged `_scan_all_regions` into `scan_all_regions`
- Renamed `force_rescan` to `force_refresh` for clarity
- Simplified implementation with integrated caching
- Return type remains the same for compatibility

### 3. Model Retrieval Methods

#### Current:
```python
def get_model(self, model_id, region=None):
    # Get model details from specific or best region

def get_all_models(self):
    # Get all models across all regions with duplications removed
```

#### Refined:
```python
def get_model(self, model_id, region=None):
    """
    Get detailed information about a specific model, optionally from a specific region.

    Args:
        model_id: The Bedrock model ID
        region: Optional specific region to get the model from (uses best region if not specified)

    Returns:
        Dict with model details or None if not found
    """

def get_all_models(self):
    """
    Get information about all available models across all regions.

    Returns:
        List of dicts with model information
    """
```

**Changes**:
- Maintained original method signatures for compatibility
- Improved documentation
- Simplified internal implementation
- Return types remain consistent

### 4. Region Selection Methods

#### Current:
```python
def get_model_regions(self, model_id):
    # Get all regions where a model is available

def get_best_regions_for_model(self, model_id, preferred_regions=None):
    # Get regions ordered by preference and latency

def is_model_available_in_region(self, model_id, region):
    # Check if model is available in region
```

#### Refined:
```python
def get_model_regions(self, model_id):
    """
    Get all regions where a specific model is available.

    Args:
        model_id: The Bedrock model ID

    Returns:
        List of region names where the model is available
    """

def get_best_regions_for_model(self, model_id, preferred_regions=None):
    """
    Get the best regions for a specific model, with optimization for latency
    and respect for user preferences.

    Args:
        model_id: The Bedrock model ID
        preferred_regions: Optional list of preferred AWS regions

    Returns:
        List of region names ordered by preference and latency
    """

def is_model_available_in_region(self, model_id, region):
    """
    Check if a specific model is available in a given region.

    Args:
        model_id: The Bedrock model ID
        region: AWS region to check

    Returns:
        True if the model is available in the region, False otherwise
    """
```

**Changes**:
- Maintained original method signatures for compatibility
- Improved documentation
- Simplified internal implementation

### 5. New Simplified Cache Management

#### Current:
```python
def initialize_cache(self):
    # Initialize cache by loading from disk or scanning

def clear_cache(self):
    # Clear all cached model data
```

#### Refined:
```python
def load_cache_from_file(self, file_path=None):
    """
    Load model and latency data from a JSON file.

    Args:
        file_path: Optional path to cache file (uses default if not specified)

    Returns:
        bool: True if loading succeeded, False otherwise
    """

def save_cache_to_file(self, file_path=None):
    """
    Save current model and latency data to a JSON file.

    Args:
        file_path: Optional path to cache file (uses default if not specified)

    Returns:
        bool: True if saving succeeded, False otherwise
    """

def clear_cache(self):
    """
    Clear all cached model data from memory.

    Returns:
        None
    """
```

**Changes**:
- Split `initialize_cache` into clearer `load_cache_from_file` method
- Added explicit `save_cache_to_file` method
- Maintained `clear_cache` for compatibility
- Simplified caching implementation

## Parameter Standardization

### 1. Region Parameters

All methods will use these standard parameters for regions:

- `region`: Single region name (string)
- `regions`: List of region names (List[str] or None)
- `preferred_regions`: List of preferred regions (List[str] or None)

### 2. Model Parameters

All methods will use these standard parameters for models:

- `model_id`: Model identifier (string)

### 3. Cache Control Parameters

All methods will use these standard parameters for cache control:

- `force_refresh`: Boolean to force fresh data retrieval (replacing `force_rescan` and `refresh_cache`)
- `file_path`: Optional path for file operations

## Return Type Standardization

### 1. Model Information

- Single model: Dict with model details or None if not found
- All models: List of model detail dicts

### 2. Region Information

- Available regions: List of region names
- Best regions: List of region names in priority order

### 3. Cache Operations

- All cache operations: Boolean indicating success/failure

## Method Deprecation Strategy

To maintain backward compatibility while encouraging the use of the simplified API, we will:

1. **Keep Core Methods**: Maintain all public methods used by existing code
2. **Update Implementations**: Refactor internal implementations to use simplified code
3. **Add Warning Comments**: Document any methods that should be considered for future deprecation
4. **Improve Documentation**: Add clear docstrings indicating preferred methods for new code

## Backward Compatibility Guarantees

The following compatibility guarantees will be maintained:

1. **Method Signatures**: Core public method signatures will not change
2. **Return Types**: Return value structures will remain the same
3. **Behavior**: Functional behavior will be preserved
4. **Defaults**: Default behaviors will remain the same

## API Usage Examples

Before (complex):
```python
# Get model discovery instance and initialize
discovery = BedrockModelDiscovery.get_instance()
discovery.initialize_cache()  # Tries to load cache or scans

# Scan for models with complex options
model_map = discovery._scan_all_regions(refresh_cache=True)

# Find best region for a model
best_regions = discovery.get_best_regions_for_model("anthropic.claude-v2")
```

After (simplified):
```python
# Get model discovery instance with optional initial scan
discovery = BedrockModelDiscovery.get_instance(scan_on_init=True)

# Scan for models with simplified options
model_map = discovery.scan_all_regions(force_refresh=True)

# Find best region for a model (unchanged API for compatibility)
best_regions = discovery.get_best_regions_for_model("anthropic.claude-v2")
```

## Migration Guide

A migration guide will be included in the documentation:

1. **Use `get_instance(scan_on_init=True)`** instead of separate initialization
2. **Use `scan_all_regions(force_refresh=True)`** instead of `_scan_all_regions(refresh_cache=True)`
3. **Use `load_cache_from_file()`** instead of `initialize_cache()`
4. **Use explicit `save_cache_to_file()`** when cache persistence is needed

## Implementation Plan

1. **Update Method Signatures**: Implement new parameter names with backward compatibility
2. **Refactor Internal Implementation**: Update code to use the simplified approach
3. **Update Documentation**: Add clear docstrings with examples
4. **Add Migration Comments**: Include comments for future deprecation
