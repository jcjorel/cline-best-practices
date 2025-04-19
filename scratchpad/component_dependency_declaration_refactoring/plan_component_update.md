# Plan for Updating Component Implementations

This document outlines the plan for updating all remaining components to fully use the new dependency injection pattern without any backward compatibility code.

## Issue Identified

After implementing the core infrastructure changes and verifying the basic functionality, the validation script has identified several components that are still using backward compatibility code:

1. Some components are still using conditional logic to check if dependencies are provided, falling back to `context.get_component()` if not:
   ```python
   # For backwards compatibility, also get the legacy config format
   if dependencies:
       self.logger.debug("Using injected dependencies")
       config_manager = self.get_dependency(dependencies, "config_manager")
   else:
       self.logger.debug("Using context.get_component() to fetch dependencies")
       config_manager = context.get_component("config_manager")
   ```

2. Many components still implement the deprecated `dependencies` property which is no longer needed since dependencies are now declared during registration in the `LifecycleManager`.

3. Some components might not have updated their `initialize` method signature to accept the `dependencies` parameter.

## Update Strategy

For each component that needs updating, the following changes should be made:

### 1. Update the `initialize` Method

```python
# Before
def initialize(self, context: InitializationContext) -> None:
    # ...
    component = context.get_component("component_name")
    # ...

# After
def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
    # ...
    component = self.get_dependency(dependencies, "component_name")
    # ...
```

### 2. Remove the `dependencies` Property

```python
# Remove this
@property
def dependencies(self) -> List[str]:
    return ["component_a", "component_b"]
```

### 3. Remove Conditional Dependency Resolution

```python
# Remove this pattern
if dependencies:
    component = self.get_dependency(dependencies, "component_name")
else:
    component = context.get_component("component_name")

# Replace with
component = self.get_dependency(dependencies, "component_name")
```

## Components to Update

Based on the comprehensive `grep` search for `get_component` calls, the following files need to be updated:

### Core Components
1. MemoryCacheComponent (src/dbp/memory_cache/component.py)
2. MetadataExtractionComponent (src/dbp/metadata_extraction/component.py)
3. ConsistencyAnalysisComponent (src/dbp/consistency_analysis/component.py)
4. DocRelationshipsComponent (src/dbp/doc_relationships/component.py)
5. RecommendationGeneratorComponent (src/dbp/recommendation_generator/component.py)
6. SchedulerComponent (src/dbp/scheduler/component.py)
7. LLMCoordinatorComponent (src/dbp/llm_coordinator/component.py)
8. MCPServerComponent (src/dbp/mcp_server/component.py)
9. DatabaseComponent (src/dbp/database/database.py)
10. FileAccessComponent (src/dbp/core/file_access_component.py)
11. InternalToolsComponent (src/dbp/internal_tools/component.py)
12. FileSystemMonitorComponent (src/dbp/fs_monitor/component.py)

### Special Cases
1. AlembicManager (src/dbp/database/alembic_manager.py) - Uses system.get_component directly
2. MCPServerAdapter (src/dbp/mcp_server/adapter.py) - Provides wrapper methods for component access
3. FileSystemMonitorQueue (src/dbp/fs_monitor/queue.py) - Uses system.get_component

### Exemptions
The following files contain `get_component` methods that are part of the core infrastructure and should NOT be modified:

1. src/dbp/core/component.py - Defines the InitializationContext.get_component method
2. src/dbp/core/system.py - Defines the ComponentSystem.get_component method
3. src/dbp/core/registry.py - Contains registry methods

## Implementation Steps

1. For each component:
   - Update the `initialize` method to accept and use the `dependencies` parameter
   - Remove the `dependencies` property
   - Remove any conditional logic that falls back to `context.get_component()`
   
2. After each component update:
   - Run the `check_component_dependencies.sh` script to verify the component no longer uses `context.get_component()` and has removed the `dependencies` property
   
3. After updating all components:
   - Run the full validation script `validate_component_refactoring.sh` to verify all components are now using the new pattern correctly
   - Update the progress file to mark all components as completed

## Sample Implementation for LLMCoordinatorComponent

```python
def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
    """
    [Function intent]
    Initializes the LLM Coordinator component and its sub-components.
    
    [Implementation details]
    Uses the strongly-typed configuration for component setup.
    Creates internal coordinator parts (request handler, LLM, tool registry, job manager, formatter).
    Registers internal LLM tools with the registry.
    
    [Design principles]
    Explicit initialization with strong typing.
    Dependency injection for improved performance and testability.
    
    Args:
        context: Initialization context with typed configuration and resources
        dependencies: Dictionary of pre-resolved dependencies {name: component_instance}
    """
    if self._initialized:
        logger.warning(f"Component '{self.name}' already initialized.")
        return

    self.logger = context.logger
    self.logger.info(f"Initializing component '{self.name}'...")

    try:
        # Get component-specific configuration using strongly-typed config
        typed_config = context.get_typed_config()
        coordinator_config = typed_config.llm_coordinator
        
        # Get required dependencies using dependency injection
        config_manager = self.get_dependency(dependencies, "config_manager")
        default_config = config_manager.get_default_config(self.name)
        
        # Instantiate sub-components with strongly-typed config when possible
        # ...rest of initialization code...

        self._initialized = True
        self.logger.info(f"Component '{self.name}' initialized successfully.")

    except KeyError as e:
         self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
         self._initialized = False
         raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
    except Exception as e:
        self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
        self._initialized = False
        raise RuntimeError(f"Failed to initialize {self.name}") from e
```

## Verification

After all components have been updated, run these verification steps:

1. `./scripts/check_component_dependencies.sh` to verify no components are using `context.get_component()` and all have updated their `initialize` method signatures
2. `python scripts/test_component_initialization.py` to verify the initialization still works correctly with the new approach
3. `./scripts/validate_component_refactoring.sh` for a comprehensive validation

This will complete the component dependency declaration refactoring by ensuring all components follow the new pattern consistently.
