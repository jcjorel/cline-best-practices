# Phase 2: InitializationContext Enhancement

## Implementation Plan for InitializationContext Enhancement

### Current State

Currently, the InitializationContext class:
- Is defined as a simple dataclass in `src/dbp/core/component.py`
- Contains two fields: `config` (Any type) and `logger` (logging.Logger)
- Has a compatibility method `get_component(name: str) -> Any` to access other components
- Provides no type safety for configuration access

### Goal

Enhance InitializationContext to provide strong typing for configuration access by leveraging the new ConfigurationManager.get_typed_config() method from Phase 1.

### Detailed Implementation Steps

#### 1. Import AppConfig Type

Add the necessary import to `src/dbp/core/component.py`:

```python
from typing import Any, Dict, List, TypeVar, Optional, Union, TYPE_CHECKING
from dataclasses import dataclass, field

if TYPE_CHECKING:
    from .system import ComponentSystem  # Forward reference
    from ..config.config_schema import AppConfig  # Forward reference for type annotations
```

#### 2. Update InitializationContext Definition

Modify the InitializationContext dataclass to include a typed_config field and improve overall typing:

```python
@dataclass
class InitializationContext:
    """
    [Class intent]
    Context object passed to components during initialization that provides
    access to necessary resources and configuration.
    
    [Implementation details]
    Contains the configuration manager reference, logger instance, and typed configuration object.
    Provides methods to access other components and retrieve strongly-typed configuration.
    
    [Design principles]
    Dependency injection for component initialization.
    Strong typing for configuration access.
    """
    config: Any  # For backward compatibility
    logger: logging.Logger
    typed_config: Optional['AppConfig'] = None  # New field for strongly-typed configuration
    
    def get_component(self, name: str) -> Any:
        """
        [Function intent]
        Provides access to other initialized components by name.
        
        [Implementation details]
        Retrieves components from the ComponentSystem singleton.
        
        [Design principles]
        Component dependency resolution without direct coupling.
        
        Args:
            name: Name of the component to retrieve
            
        Returns:
            The requested component instance or None if not found
        """
        from .system import ComponentSystem
        system = ComponentSystem.get_instance()
        return system.get_component(name) if system else None
    
    def get_typed_config(self) -> 'AppConfig':
        """
        [Function intent]
        Provides access to the strongly-typed configuration model.
        
        [Implementation details]
        Returns the stored typed_config if available, otherwise returns
        a default AppConfig instance.
        
        [Design principles]
        Type safety for configuration access.
        
        Returns:
            AppConfig: The strongly-typed configuration model
        """
        if self.typed_config is None:
            # This should not happen if the context is properly initialized,
            # but we provide a fallback for robustness
            from ..config.config_schema import AppConfig
            return AppConfig()
        
        return self.typed_config
```

#### 3. Update ComponentSystem Initialization Logic

In the ComponentSystem class (src/dbp/core/system.py), update the initialization context creation to include the typed configuration:

```python
def _initialize_component(self, component: Component) -> bool:
    """Initialize a single component with proper context."""
    try:
        # Get typed config from configuration manager
        config_manager = self.get_component("config_manager")
        typed_config = config_manager.get_typed_config() if config_manager else None
        
        # Create initialization context with both regular and typed config
        context = InitializationContext(
            config=config_manager,
            logger=self.logger.getChild(component.name),
            typed_config=typed_config
        )
        
        # Call component's initialize method
        component.initialize(context)
        
        return component.is_initialized
    except Exception as e:
        self.logger.error(f"Failed to initialize component {component.name}: {e}", exc_info=True)
        if hasattr(component, 'set_initialization_error'):
            component.set_initialization_error(e)
        return False
```

#### 4. Update Documentation

Update the documentation in comments and docstrings to reflect the new typed configuration access.

### Impact Analysis

The enhancement to InitializationContext:
- Provides a foundation for strongly-typed configuration access in component initialization
- Maintains backward compatibility with existing code using the `config` field
- Adds type safety for configuration access in component implementations
- Will simplify component implementations by eliminating the need for string-based configuration access
- Will be leveraged in Phase 3 for strong typing on Component.initialize() method

### Testing Strategy

- Unit test the enhanced InitializationContext with both typed and untyped configuration
- Verify that get_typed_config() returns the correct AppConfig instance
- Test integration with ComponentSystem initialization flow
- Ensure backward compatibility with existing components that rely on the original fields
