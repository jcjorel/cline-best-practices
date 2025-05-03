# Bedrock Model Discovery Refactoring Plan

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Documentation References
- [Source file intent](src/dbp/llm/bedrock/model_discovery.py) - Current Bedrock model discovery implementation 
- [Example usage](src/dbp/llm/bedrock/examples/model_discovery_example.py) - Example of how the model discovery is used

## Current Issues
- File truncation in `model_discovery.py` due to large monolithic implementation
- Lack of dedicated AWS client management system for multiple regions
- Mixed responsibilities in the current discovery implementation
- Inference profile handling mixed with model discovery

## Refactoring Goals
1. Create a centralized AWS client factory for efficient client reuse across regions and services
2. Split model discovery into focused components with clear responsibilities
3. Separate model scanning from inference profile scanning
4. Implement latency-based region sorting for optimal performance
5. Enhance caching system with proper versioning and TTL management
6. Implement singleton pattern for all discovery components to avoid duplicate scanning/caching

## Implementation Structure

```
src/dbp/
├── api_providers/
│   └── aws/
│       ├── __init__.py
│       ├── client_factory.py       # Central AWS client management (singleton)
│       └── exceptions.py           # Common AWS-specific exceptions
├── llm/
│   └── bedrock/
│       ├── discovery/
│       │   ├── __init__.py
│       │   ├── models.py           # Model discovery components (singleton)
│       │   ├── profiles.py         # Inference profile components (singleton)
│       │   ├── latency.py          # Region latency tracking
│       │   └── cache.py            # Caching mechanisms
│       └── __init__.py
```

## Components

### 1. AWSClientFactory
A centralized singleton factory for creating and caching AWS clients:
- Thread-safe with minimal locking overhead
- Region and service-specific client caching
- Configurable retry and timeout policies
- Support for different credential sources
- Standard configuration profiles for different service types
- Implemented as a singleton for project-wide reuse

### 2. RegionLatencyTracker
Tracks and manages API latency metrics for AWS regions:
- Thread-safe latency tracking
- Exponential moving average for stable metrics
- Efficient region sorting based on measured latencies
- Persistence of latency data between runs

### 3. DiscoveryCache
Provides caching for discovery results with customizable TTL:
- Thread-safe memory cache
- Disk persistence with atomic file operations
- Versioned cache format
- Separate TTLs for memory and disk caches

### 4. BedrockModelDiscovery
Discovers and provides information about Bedrock models:
- Singleton implementation for project-wide reuse
- Parallel region scanning with ThreadPoolExecutor
- Integration with latency tracking
- Clean separation from caching concerns
- Focused on model discovery only

### 5. BedrockProfileDiscovery
Dedicated component for Bedrock inference profiles:
- Singleton implementation for project-wide reuse
- Clean separation from model discovery
- Profile metadata extraction
- Profile-to-model mapping

## Implementation Plan

### Phase 1: AWS Client Factory
- Create directory structure
- Implement `AWSClientFactory` in `src/dbp/api_providers/aws/client_factory.py` as a singleton
- Add AWS-specific exceptions if needed

### Phase 2: Discovery Components
- Implement `RegionLatencyTracker` in `src/dbp/llm/bedrock/discovery/latency.py`
- Implement `DiscoveryCache` in `src/dbp/llm/bedrock/discovery/cache.py`
- Ensure robust thread-safety throughout

### Phase 3: Model & Profile Discovery
- Implement `BedrockModelDiscovery` in `src/dbp/llm/bedrock/discovery/models.py` as a singleton
- Implement `BedrockProfileDiscovery` in `src/dbp/llm/bedrock/discovery/profiles.py` as a singleton
- Integrate with client factory, cache, and latency tracker

### Phase 4: Integration Testing
- Create tests to validate the integration between components
- Verify correct behavior for all use cases from the example file
- Ensure backward compatibility where needed

## Implementation Progress
Progress is tracked in [plan_progress.md](scratchpad/bedrock_discovery_refactoring/plan_progress.md).

## Detailed Plans
The following detailed implementation plans are available:
1. [AWS Client Factory](scratchpad/bedrock_discovery_refactoring/plan_aws_client_factory.md)
2. [Discovery Cache System](scratchpad/bedrock_discovery_refactoring/plan_discovery_cache.md)
3. [Region Latency Tracker](scratchpad/bedrock_discovery_refactoring/plan_region_latency_tracker.md)
4. [Bedrock Model Discovery](scratchpad/bedrock_discovery_refactoring/plan_model_discovery.md)
5. [Bedrock Profile Discovery](scratchpad/bedrock_discovery_refactoring/plan_profile_discovery.md)

## Singleton Pattern Implementation

All major components will be implemented as singletons to ensure:
- Single point of access across the project
- Shared caching to avoid duplicate API calls
- Consistent configuration and state
- Reduced memory footprint
- Thread-safety for concurrent access

The singleton pattern will be implemented with the following approach:

```python
class ComponentName:
    _instance = None
    _lock = threading.Lock()
    
    @classmethod
    def get_instance(cls, **kwargs):
        """Get the singleton instance, creating it if needed"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(**kwargs)
        return cls._instance
        
    def __init__(self, **kwargs):
        # Check if called through get_instance()
        if self.__class__._instance is not None:
            raise RuntimeError(f"{self.__class__.__name__} is a singleton and should be accessed via get_instance()")
        # Initialize instance
