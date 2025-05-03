# Bedrock Model Discovery Simplification Plan

⚠️ **CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN**

## Documentation References
- [Current Implementation](src/dbp/llm/bedrock/discovery/models.py) - Current BedrockModelDiscovery implementation
- [Previous Refactoring Plan](scratchpad/bedrock_discovery_refactoring/plan_overview.md) - Previous refactoring effort
- [Previous Refactoring Progress](scratchpad/bedrock_discovery_refactoring/plan_progress.md) - Status of previous refactoring

## Current Issues

1. **Excessive Parameterization**: The class has numerous configuration options and parameters across many methods, most of which are rarely customized.

2. **Overly Complex Component Structure**: The current design relies on multiple interdependent components (DiscoveryCache, RegionLatencyTracker, etc.) that add complexity without clear necessity.

3. **Redundant Methods**: There are multiple methods with overlapping functionality (`scan_all_regions`, `_scan_all_regions`, `_scan_region`).

4. **Thread Safety Overhead**: Multiple locks are used for concurrency control, adding complexity when simpler patterns could suffice.

5. **Complex Caching Logic**: The caching mechanism is overly sophisticated with multiple cache types and refresh strategies.

## Simplification Goals

1. **Maintain Singleton Pattern**: Preserve the core singleton implementation for project-wide reuse.

2. **Simplify Component Dependencies**: Reduce the number of external dependencies and simplify their interactions.

3. **Streamline Method Interfaces**: Reduce the number of parameters and options across methods.

4. **Consolidate Redundant Logic**: Merge overlapping methods and eliminate unnecessary code paths.

5. **Simplify Caching**: Implement a more straightforward caching approach.

6. **Maintain Core Functionality**: Preserve essential features like:
   - Model discovery across regions
   - Latency-based region optimization
   - Thread safety for concurrent access
   - Model profile association

## Implementation Structure

The simplified implementation will maintain the existing file structure while reducing complexity within each file:

```
src/dbp/llm/bedrock/discovery/
├── models.py           # Simplified BedrockModelDiscovery singleton
├── cache.py            # Simplified caching (if needed)
├── discovery_core.py   # Simplified base discovery class
└── scan_utils.py       # Streamlined scanning utilities
```

## Implementation Plan

### Phase 1: Code Analysis & Planning
- **Task 1.1**: Audit existing parameter usage
  - Identify parameters that can be removed or simplified
  - Determine which options are rarely used or unnecessary
  - Document essential vs. non-essential parameters

- **Task 1.2**: Analyze method dependencies
  - Map call hierarchies between methods
  - Identify redundant methods that can be consolidated
  - Document method responsibilities and overlaps

- **Task 1.3**: Review component interactions
  - Analyze dependencies between BedrockModelDiscovery and other components
  - Identify opportunities for simplification or merging
  - Document critical vs. optional component interactions

### Phase 2: Core Architecture Simplification

- **Task 2.1**: Simplify Base Discovery Class
  - Streamline `BaseDiscovery` in discovery_core.py
  - Remove unnecessary parameters and options
  - Simplify threading model and locking mechanisms
  - Focus on essential functionality only

- **Task 2.2**: Simplify Scan Utilities
  - Consolidate scan functions in scan_utils.py
  - Reduce parameter complexity 
  - Standardize error handling
  - Remove rarely-used options

### Phase 3: BedrockModelDiscovery Implementation

- **Task 3.1**: Simplify Singleton Implementation
  - Streamline get_instance() method
  - Reduce initialization complexity
  - Simplify component dependency management

- **Task 3.2**: Consolidate Scanning Methods
  - Merge overlapping scanning methods
  - Create a single clear scanning implementation
  - Reduce method parameter complexity

- **Task 3.3**: Streamline Caching Approach
  - Simplify cache interaction patterns
  - Reduce caching options and complexity
  - Maintain only essential caching functionality

### Phase 4: API Refinement

- **Task 4.1**: Streamline Public API
  - Simplify parameter lists for public methods
  - Set sensible defaults instead of requiring configuration
  - Document simplified API usage

- **Task 4.2**: Update Documentation
  - Update all docstrings to reflect simplified design
  - Add clear examples of typical usage patterns
  - Document changes from previous implementation

### Phase 5: Testing & Verification

- **Task 5.1**: Create Verification Tests
  - Ensure all core functionality is preserved after simplification
  - Test thread safety with concurrent access patterns
  - Verify error handling with various failure scenarios

- **Task 5.2**: Performance Testing
  - Measure any performance improvements from simplification
  - Ensure no performance regressions in common use cases
  - Document performance characteristics

## Implementation Deliverables

1. **Simplified BedrockModelDiscovery Class**:
   - Fewer parameters
   - Cleaner method interfaces
   - More consistent error handling
   - Maintain singleton pattern and thread safety

2. **Updated Base Classes**:
   - Simplified BaseDiscovery
   - Streamlined scan utilities
   - Reduced component dependencies

3. **Implementation Guidance**:
   - Documentation of simplification choices
   - Migration guidance for dependent code
   - Usage examples for common scenarios

## Progress Tracking

Progress will be tracked in [plan_progress.md](scratchpad/bedrock_discovery_simplification/plan_progress.md).

## Detailed Plans
The following detailed implementation plans will be available:

1. [Parameter Analysis](scratchpad/bedrock_discovery_simplification/plan_parameter_analysis.md)
2. [Core Architecture Simplification](scratchpad/bedrock_discovery_simplification/plan_core_architecture.md)
3. [BedrockModelDiscovery Simplification](scratchpad/bedrock_discovery_simplification/plan_model_discovery.md)
4. [API Refinement](scratchpad/bedrock_discovery_simplification/plan_api_refinement.md)
