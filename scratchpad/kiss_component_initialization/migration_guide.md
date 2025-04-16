# Migration Guide: Implementing KISS Component Initialization

This guide explains how to migrate from the complex six-stage component initialization system to the new ultra-simplified KISS approach.

## Migration Steps

### 1. Replace Core Files

Replace these files with their simplified versions:

| Old File | New File | Action |
|---------|---------|--------|
| `src/dbp/core/component.py` | `scratchpad/kiss_component_initialization/component.py` | Replace content |
| `src/dbp/core/registry.py` | - | Remove file |
| `src/dbp/core/orchestrator.py` | - | Remove file |
| `src/dbp/core/resolver.py` | - | Remove file |
| `src/dbp/core/lifecycle.py` | `scratchpad/kiss_component_initialization/lifecycle.py` | Replace content |
| - | `src/dbp/core/system.py` | Create new file from `scratchpad/kiss_component_initialization/system.py` |

### 2. Update Component Implementations

For each component implementation, modify the class to follow the new Component interface:

1. Update the `name` property to return the component name
2. Update the `dependencies` property to return a simple list of dependency names
3. Change the `initialize` method signature: `def initialize(self, config: Any) -> None:`
4. Ensure `initialize` sets `self._initialized = True` when successful
5. Ensure `shutdown` sets `self._initialized = False` when complete

#### Example Changes

**Before:**
```python
class ExampleComponent(Component):
    def __init__(self):
        super().__init__()
        self.name = "example"
        
    def initialize(self, context: InitializationContext) -> None:
        context.logger.info("Initializing example component")
        # Complex initialization...
        self._initialized = True
```

**After:**
```python
class ExampleComponent(Component):
    @property
    def name(self) -> str:
        return "example"
        
    @property
    def dependencies(self) -> List[str]:
        return ["config_manager"]
        
    def initialize(self, config: Any) -> None:
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing example component")
        # Simplified initialization...
        self._initialized = True
```

### 3. Update Component Registration

Replace the component registration system:

1. Delete the `src/dbp/core/component_registry_setup.py` file
2. In `LifecycleManager._register_components()`, directly register component instances:

```python
def _register_components(self) -> None:
    logger.info("Registering components...")
    
    try:
        # Register config manager component
        if ConfigManagerComponent and self.config_manager:
            self.system.register(ConfigManagerComponent(self.config_manager))
            
        # Register database component
        try:
            from ..database.database import DatabaseComponent
            self.system.register(DatabaseComponent())
            logger.debug("Registered DatabaseComponent")
        except ImportError as e:
            logger.error(f"Failed to register database component: {e}")
        
        # Register other components...
            
    except Exception as e:
        logger.critical(f"Failed to register components: {e}", exc_info=True)
        raise
```

### 4. Update Main Application Entry Points

Modify entry points to use the new LifecycleManager:

```python
def main():
    manager = LifecycleManager(sys.argv[1:])
    success = manager.start()
    
    if not success:
        logger.error("Application failed to start")
        return 1
        
    # Wait for termination signal
    try:
        # Keep main thread alive until signal received
        manager._shutdown_event.wait()
    except KeyboardInterrupt:
        pass
        
    # Shutdown gracefully
    manager.shutdown()
    return 0
```

### 5. Update Documentation

1. Replace `doc/design/COMPONENT_INITIALIZATION.md` with the new simplified version
2. Add the new design decision to `doc/DESIGN_DECISIONS.md`

## Testing the Migration

1. Start with a subset of components to verify the approach
2. Test component initialization order
3. Test circular dependency detection
4. Test component shutdown process
5. Test error handling during initialization

## Common Migration Issues

1. **Missing Dependencies**: Ensure all component dependencies are explicitly declared
2. **Initialization Flag**: Make sure all components set `self._initialized = True` when initialized
3. **Shutdown Flag**: Make sure all components set `self._initialized = False` in shutdown
4. **Config Access**: Components now receive `config` directly instead of through context
5. **Logger Setup**: Components should create their own logger in initialize()
