# Component Dependency Declaration Refactoring Plan

⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

## Documentation References

| File | Relevance |
|------|-----------|
| [doc/DESIGN.md](../../doc/DESIGN.md) | Overall system architecture |
| [doc/design/COMPONENT_INITIALIZATION.md](../../doc/design/COMPONENT_INITIALIZATION.md) | Current component initialization approach |
| [src/dbp/core/component.py](../../src/dbp/core/component.py) | Component base class implementation |
| [src/dbp/core/system.py](../../src/dbp/core/system.py) | ComponentSystem implementation |
| [src/dbp/core/lifecycle.py](../../src/dbp/core/lifecycle.py) | Component registration and lifecycle management |

## Problem Statement

Currently, each component defines its dependencies in its own class via the `dependencies` property. This approach:
- Scatters essential configuration across many files
- Makes it difficult to understand the dependency graph
- Separates component registration from dependency declaration

Additionally, components need to manually fetch their dependencies using `get_component()` during initialization, making the code more verbose and error-prone.

## Solution Overview

1. Create a centralized component registration mechanism that allows registering components and declaring dependencies in one place
2. Enhance the Component.initialize() method to accept a `dependencies` dictionary with already resolved references
3. Update the ComponentSystem to resolve dependencies and pass them to initialize()
4. Update all component implementations to use the new approach
5. Remove all references to the old approach for component registration and dependency management

## Implementation Phases

### Phase 1: Core Infrastructure Changes

1. Modify the Component base class (`src/dbp/core/component.py`)
   - Update the initialize() method signature to accept a `dependencies` parameter
   - Provide backward compatibility during the transition

2. Enhance ComponentSystem (`src/dbp/core/system.py`)
   - Modify initialization logic to pass resolved dependencies to components
   - Update dependency resolution logic

3. Create a centralized ComponentRegistry interface (`src/dbp/core/registry.py`)
   - Define a mechanism for component registration with dependencies
   - Implement dependency graph generation

### Phase 2: Integration & Component Updates

1. Update LifecycleManager (`src/dbp/core/lifecycle.py`)
   - Refactor component registration to use the new centralized approach
   - Provide a transition mechanism for backward compatibility

2. Update each component implementation
   - Modify initialize() method to use provided dependencies
   - Remove manual dependency retrieval code

### Phase 3: Cleanup & Final Implementation

1. Remove backward compatibility code
   - Remove old component registration mechanism
   - Ensure all components use the new approach exclusively

2. Update documentation
   - Update component initialization documentation
   - Update design decisions documentation

## Detailed Implementation Plan Files

The following files contain detailed implementation plans for each phase:

- [plan_phase1_core_infrastructure.md](./plan_phase1_core_infrastructure.md) - Core class modifications
- [plan_phase2_integration.md](./plan_phase2_integration.md) - Integration and component updates
- [plan_phase3_cleanup.md](./plan_phase3_cleanup.md) - Final cleanup and documentation

## Implementation Progress Tracking

Progress is tracked in the [plan_progress.md](./plan_progress.md) file.
