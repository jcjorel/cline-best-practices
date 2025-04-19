# Phase 1: Core Infrastructure Changes

This document details the changes needed for the core infrastructure components to support centralized dependency declaration and automatic dependency injection.

## 1. Modify Component Base Class

File: `src/dbp/core/component.py`

### Current Implementation Summary

Currently, the Component base class:
- Defines an abstract `dependencies` property that returns a list of component names
- Defines an `initialize(self, context: InitializationContext)` method that components use to initialize themselves
- Components must manually fetch their dependencies using `context.get_component(name)`

### Required Changes

1. Update the `initialize` method signature to accept dependencies:

```python
def initialize(self, context: 'InitializationContext', dependencies: Optional[Dict[str, 'Component']] = None) -> None:
    """
    [Function intent]
    Initializes the component with context information and resolved dependencies.
    
    [Implementation details]
    Must be implemented by concrete component classes.
    If dependencies are provided, they should be used directly instead of fetching via context.
    MUST set self._initialized = True when initialization succeeds.
    
    [Design principles]
    Explicit initialization with clear success/failure indication.
    Direct dependency injection for improved performance and testability.
    
    Args:
        context: Initialization context with configuration and resources
        dependencies: Optional dictionary of pre-resolved dependencies {name: component_instance}
    """
    raise NotImplementedError("Component must implement initialize method")
```

2. Add a new helper method to access dependencies safely:

```python
def get_dependency(self, dependencies: Dict[str, 'Component'], name: str) -> Any:
    """
    [Function intent]
    Safely access a dependency by name from the provided dependencies dictionary.
    
    [Implementation details]
    Returns the dependency if found, otherwise raises KeyError.
    
    [Design principles]
    Safe dependency access with clear error messages.
    
    Args:
        dependencies: Dictionary of dependencies {name: component_instance}
        name: Name of the dependency to retrieve
        
    Returns:
        The requested dependency component
        
    Raises:
        KeyError: If the dependency is not found
    """
    if name not in dependencies:
        raise KeyError(f"Required dependency '{name}' not found in provided dependencies")
    return dependencies[name]
```

3. Update the docstring for the `dependencies` property:

```python
@property
def dependencies(self) -> List[str]:
    """
    [Function intent]
    Returns a list of component names that this component depends on.
    
    [Implementation details]
    Default implementation returns an empty list (no dependencies).
    This property is deprecated and will be removed in a future version.
    Dependencies should now be declared during component registration.
    
    [Design principles]
    Explicit dependency declaration for clear initialization order.
    
    Returns:
        List[str]: List of component names this component depends on
    """
    return []
```

## 2. Enhance ComponentSystem

File: `src/dbp/core/system.py`

### Current Implementation Summary

Currently, ComponentSystem:
- Maintains a dictionary of registered components
- Validates dependencies using the `dependencies` property of each component
- Initializes components in dependency order
- Components fetch dependencies manually using `context.get_component()`

### Required Changes

1. Update the class to include dependency tracking:

```python
def __init__(self, config: Any, logger: logging.Logger):
    # Existing code...
    self.components: Dict[str, Component] = {}  # name -> component
    self._initialized: List[str] = []  # Initialization order for shutdown
    # New attributes
    self.dependencies: Dict[str, List[str]] = {}  # name -> list of dependency names
    
    # Set singleton instance
    ComponentSystem._instance = self
```

2. Modify the `register` method to accept dependencies:

```python
def register(self, component: Component, dependencies: Optional[List[str]] = None) -> None:
    """
    [Function intent]
    Registers a component with the system by name and optionally defines its dependencies.
    
    [Implementation details]
    Stores the component in the components dictionary with its name as key.
    If dependencies are provided, they override the component's dependencies property.
    
    [Design principles]
    Simple dictionary-based registration with explicit dependency declaration.
    
    Args:
        component: Component instance to register
        dependencies: Optional explicit list of dependency names
        
    Raises:
        ValueError: If a component with the same name is already registered
    """
    name = component.name
    if name in self.components:
        raise ValueError(f"Component '{name}' already registered")
    
    # Get dependencies from parameter or component's property
    component_deps = dependencies if dependencies is not None else component.dependencies
    
    # Enhanced logging for component registration
    self.logger.info(f"Registering component: '{name}' with dependencies: {component_deps}")
    self.components[name] = component
    self.dependencies[name] = component_deps
```

3. Update `validate_dependencies` to use the stored dependencies:

```python
def validate_dependencies(self) -> List[str]:
    """
    [Function intent]
    Validates that all component dependencies are registered.
    
    [Implementation details]
    Checks dependencies from the dependencies dictionary against registered components.
    
    [Design principles]
    Early validation with clear error reporting.
    
    Returns:
        List[str]: List of error messages, empty if all dependencies valid
    """
    missing = []
    registered_components = set(self.components.keys())
    
    self.logger.debug(f"Validating dependencies. Registered components: {registered_components}")
    
    for name, deps in self.dependencies.items():
        for dep_name in deps:
            if dep_name not in self.components:
                error_msg = f"Component '{name}' depends on '{dep_name}' which is not registered"
                self.logger.error(error_msg)
                missing.append(error_msg)
                # Suggest similar component names for typos
                similar_names = [c for c in registered_components if dep_name in c or c in dep_name]
                if similar_names:
                    suggestion = f"Did you mean one of these? {', '.join(similar_names)}"
                    self.logger.error(f"Suggestion: {suggestion}")
                    missing.append(f"Suggestion: {suggestion}")
    
    if missing:
        self.logger.error(f"Dependency validation failed with {len(missing)} errors")
    else:
        self.logger.info("All component dependencies validated successfully")
        
    return missing
```

4. Update `_calculate_init_order` to use the stored dependencies:

```python
def _calculate_init_order(self) -> List[str]:
    """
    [Function intent]
    Calculates component initialization order based on dependencies.
    
    [Implementation details]
    Simple implementation that builds order ensuring dependencies 
    are initialized before dependent components.
    
    [Design principles]
    Simple algorithm without complex graph theory.
    Clear detection of circular dependencies.
    
    Returns:
        List[str]: Components in initialization order
        
    Raises:
        CircularDependencyError: If circular dependency detected
    """
    # Start with set of all components to initialize
    remaining = set(self.components.keys())
    result = []
    
    # Track initialized components
    initialized = set()
    
    # Maximum iterations to detect circular dependencies
    max_iterations = len(remaining)
    iteration = 0
    
    while remaining and iteration < max_iterations:
        iteration += 1
        # Find a component with all dependencies satisfied
        component_found = False
        
        for name in list(remaining):
            deps = set(self.dependencies.get(name, []))
            
            # If all dependencies are initialized
            if deps.issubset(initialized):
                result.append(name)
                initialized.add(name)
                remaining.remove(name)
                component_found = True
                break
        
        # If no component could be initialized this iteration,
        # we have a circular dependency
        if not component_found:
            # Try to identify the circular dependency
            cycle = []
            for name in remaining:
                cycle.append(f"{name} -> [{', '.join(self.dependencies.get(name, []))}]")
            raise CircularDependencyError(f"Circular dependency detected among: {', '.join(cycle)}")
    
    return result
```

5. Update `initialize_all` to resolve and pass dependencies:

```python
def initialize_all(self) -> bool:
    """
    [Function intent]
    Initializes all registered components in dependency order.
    
    [Implementation details]
    Validates dependencies, calculates initialization order,
    resolves dependencies for each component, and initializes
    components sequentially with clear error reporting.
    
    [Design principles]
    Simple sequential process with explicit dependency injection.
    Fail fast on validation errors.
    
    Returns:
        bool: True if all components initialized successfully, False otherwise
    """
    # Reset initialization tracking
    self._initialized = []
    
    # Log component count
    self.logger.info(f"Initializing {len(self.components)} components")
    
    # Validate dependencies first
    missing = self.validate_dependencies()
    if missing:
        for error in missing:
            self.logger.error(f"Dependency validation error: {error}")
        return False
    
    # Calculate initialization order
    try:
        init_order = self._calculate_init_order()
        self.logger.info(f"Component initialization order: {', '.join(init_order)}")
    except CircularDependencyError as e:
        self.logger.error(f"Circular dependency detected: {e}")
        return False
    
    # Initialize components in order
    for name in init_order:
        component = self.components[name]
        
        # Skip already initialized components
        if component.is_initialized:
            self.logger.debug(f"Component '{name}' already initialized, skipping")
            if name not in self._initialized:
                self._initialized.append(name)
            continue
                
        try:
            # Enhanced logging before initialization
            self.logger.info(f"Initializing component '{name}'...")
            
            # Create the initialization context
            # Components expect a config manager with get() method, not the raw config
            config_manager = self.get_component('config_manager')
            if not config_manager:
                self.logger.error(f"Required config_manager component not found during initialization of '{name}'")
                self._rollback()
                return False
            
            # Get the typed configuration - throw on error
            typed_config = config_manager.get_typed_config()
            
            context = InitializationContext(
                config=config_manager,
                logger=self.logger.getChild(component.name),  # Use child logger
                typed_config=typed_config  # Include typed configuration
            )
            
            # Resolve dependencies for this component
            component_deps = self.dependencies.get(name, [])
            resolved_deps = {}
            
            for dep_name in component_deps:
                dep_component = self.components.get(dep_name)
                if not dep_component:
                    self.logger.error(f"Dependency '{dep_name}' not found for component '{name}'")
                    self._rollback()
                    return False
                if not dep_component.is_initialized:
                    self.logger.error(f"Dependency '{dep_name}' for component '{name}' is not initialized")
                    self._rollback()
                    return False
                resolved_deps[dep_name] = dep_component
            
            # Add logging for dependencies
            if resolved_deps:
                self.logger.info(f"Resolved {len(resolved_deps)} dependencies for component '{name}'")
            
            # Initialize the component with context and resolved dependencies
            component.initialize(context, resolved_deps)
            
            # Verify initialization flag with more detailed diagnostics
            if not component.is_initialized:
                self.logger.error(f"Component '{name}' failed to set is_initialized flag to True")
                self._rollback()
                return False
                
            # Track initialization for shutdown order
            self._initialized.append(name)
            self.logger.info(f"Component '{name}' initialized successfully")
            
        except Exception as e:
            # Enhanced error logging with exception details
            self.logger.error(f"Failed to initialize component '{name}': {str(e)}")
            # Additional logging as in the original code
            # ...
            self._rollback()
            return False
    
    self.logger.info("All components initialized successfully")
    return True
```

## 3. Create Centralized ComponentRegistry

File: `src/dbp/core/registry.py` (new file)

This will be a new file that implements a centralized component registry mechanism.

```python
###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements a centralized component registry that allows components to be registered
# with their dependencies in one place. This provides a cleaner way to manage component
# dependencies and registration compared to defining dependencies in each component class.
###############################################################################
# [Source file design principles]
# - Centralized component registration with explicit dependency declaration
# - Clear separation between component definition and dependency declaration
# - Support for conditional component registration based on configuration
# - KISS approach to dependency management without complex abstractions
# - Compatibility with the existing ComponentSystem for backward compatibility
###############################################################################
# [Source file constraints]
# - Must work with the existing Component and ComponentSystem classes
# - Must provide a simple and clear API for component registration
# - Must not introduce complex abstractions or patterns
# - Should support a transition period where both approaches are supported
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-19T23:20:00Z : Initial creation of ComponentRegistry by CodeAssistant
# * Implemented centralized component registration mechanism
# * Added support for explicit dependency declaration
# * Provided helper methods for component discovery and registration
###############################################################################

import logging
from typing import Dict, List, Type, Optional, Any, Set, Callable, TypeVar, cast

# Import core components for type checking
from .component import Component

T = TypeVar('T', bound=Component)

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    [Class intent]
    Provides a centralized registry for component registration with explicit
    dependency declaration. This simplifies component management and makes
    dependencies more visible in the codebase.
    
    [Implementation details]
    Stores component classes, instances, and their dependencies in dictionaries.
    Provides methods for registering components and retrieving registration info.
    Designed to work with the existing ComponentSystem for backward compatibility.
    
    [Design principles]
    Centralized registration with explicit dependencies.
    Simple dictionary-based implementation without complex abstractions.
    Clear separation between component definition and dependency configuration.
    """
    
    def __init__(self):
        """
        [Function intent]
        Initializes the component registry with empty collections.
        
        [Implementation details]
        Creates dictionaries for storing component registrations and dependencies.
        
        [Design principles]
        Simple initialization with minimal state.
        """
        # Dictionary of component name -> component class
        self._component_classes: Dict[str, Type[Component]] = {}
        
        # Dictionary of component name -> component dependencies
        self._component_dependencies: Dict[str, List[str]] = {}
        
        # Dictionary of component name -> enabled flag
        self._component_enabled: Dict[str, bool] = {}
        
        # Dictionary of component name -> factory function
        self._component_factories: Dict[str, Callable[[], Component]] = {}
        
    def register_component(self, 
                         component_class: Type[Component], 
                         dependencies: Optional[List[str]] = None,
                         enabled: bool = True) -> None:
        """
        [Function intent]
        Registers a component class with its dependencies.
        
        [Implementation details]
        Stores the component class and its dependencies in the registry.
        Component name is determined by instantiating the class and getting its name.
        
        [Design principles]
        Simple registration with explicit dependency declaration.
        
        Args:
            component_class: The component class to register
            dependencies: Optional list of component names this component depends on
            enabled: Whether this component is enabled (default: True)
            
        Raises:
            ValueError: If a component with the same name is already registered
        """
        # Create a temporary instance to get the component name
        temp_instance = component_class()
        name = temp_instance.name
        
        if name in self._component_classes:
            raise ValueError(f"Component '{name}' already registered")
        
        # Get dependencies from parameter or component's property
        deps = dependencies if dependencies is not None else temp_instance.dependencies
        
        # Store the component class and dependencies
        self._component_classes[name] = component_class
        self._component_dependencies[name] = deps
        self._component_enabled[name] = enabled
        
        logger.debug(f"Registered component class '{name}' with dependencies: {deps}")
        
    def register_component_factory(self,
                                 name: str,
                                 factory: Callable[[], Component],
                                 dependencies: List[str],
                                 enabled: bool = True) -> None:
        """
        [Function intent]
        Registers a component factory function with dependencies.
        
        [Implementation details]
        Stores the component factory function and its dependencies in the registry.
        Useful for components that require special initialization or configuration.
        
        [Design principles]
        Flexible registration for complex component creation.
        
        Args:
            name: The name of the component
            factory: A function that creates and returns a component instance
            dependencies: List of component names this component depends on
            enabled: Whether this component is enabled (default: True)
            
        Raises:
            ValueError: If a component with the same name is already registered
        """
        if name in self._component_classes or name in self._component_factories:
            raise ValueError(f"Component '{name}' already registered")
        
        self._component_factories[name] = factory
        self._component_dependencies[name] = dependencies
        self._component_enabled[name] = enabled
        
        logger.debug(f"Registered component factory '{name}' with dependencies: {dependencies}")
        
    def get_component_dependencies(self, name: str) -> List[str]:
        """
        [Function intent]
        Returns the dependencies for a registered component.
        
        [Implementation details]
        Looks up the component in the registry and returns its dependencies.
        
        [Design principles]
        Simple accessor for stored dependency information.
        
        Args:
            name: The name of the component
            
        Returns:
            List[str]: The component's dependencies
            
        Raises:
            KeyError: If the component is not registered
        """
        if name not in self._component_dependencies:
            raise KeyError(f"Component '{name}' not registered")
        
        return self._component_dependencies[name]
        
    def is_component_enabled(self, name: str) -> bool:
        """
        [Function intent]
        Checks if a component is enabled.
        
        [Implementation details]
        Looks up the component in the registry and returns its enabled status.
        
        [Design principles]
        Simple accessor for stored enablement information.
        
        Args:
            name: The name of the component
            
        Returns:
            bool: True if the component is enabled, False otherwise
            
        Raises:
            KeyError: If the component is not registered
        """
        if name not in self._component_enabled:
            raise KeyError(f"Component '{name}' not registered")
        
        return self._component_enabled[name]
        
    def set_component_enabled(self, name: str, enabled: bool) -> None:
        """
        [Function intent]
        Sets the enabled status for a component.
        
        [Implementation details]
        Updates the component's enabled status in the registry.
        
        [Design principles]
        Simple modifier for component enablement.
        
        Args:
            name: The name of the component
            enabled: The new enabled status
            
        Raises:
            KeyError: If the component is not registered
        """
        if name not in self._component_enabled:
            raise KeyError(f"Component '{name}' not registered")
        
        self._component_enabled[name] = enabled
        
    def get_all_component_names(self) -> List[str]:
        """
        [Function intent]
        Returns the names of all registered components.
        
        [Implementation details]
        Combines component classes and factories and returns their names.
        
        [Design principles]
        Simple accessor for component discovery.
        
        Returns:
            List[str]: Names of all registered components
        """
        # Combine the keys from component classes and factories
        return list(set(self._component_classes.keys()) | set(self._component_factories.keys()))
        
    def get_enabled_component_names(self) -> List[str]:
        """
        [Function intent]
        Returns the names of all enabled components.
        
        [Implementation details]
        Filters the registered components by their enabled status.
        
        [Design principles]
        Simple filtered accessor for component discovery.
        
        Returns:
            List[str]: Names of all enabled components
        """
        return [name for name, enabled in self._component_enabled.items() if enabled]
        
    def create_component(self, name: str) -> Component:
        """
        [Function intent]
        Creates an instance of a registered component.
        
        [Implementation details]
        Either instantiates the component class or calls the factory function.
        
        [Design principles]
        Simple factory method for component instantiation.
        
        Args:
            name: The name of the component to create
            
        Returns:
            Component: A new instance of the component
            
        Raises:
            KeyError: If the component is not registered
            ValueError: If the component is not enabled
        """
        if name not in self._component_classes and name not in self._component_factories:
            raise KeyError(f"Component '{name}' not registered")
        
        if not self._component_enabled.get(name, False):
            raise ValueError(f"Component '{name}' is not enabled")
        
        # Create the component using either the class or factory
        if name in self._component_classes:
            component = self._component_classes[name]()
        else:
            component = self._component_factories[name]()
            
        # Verify component name
        if component.name != name:
            logger.warning(f"Component name mismatch: expected '{name}' but got '{component.name}'")
            
        return component
        
    def calculate_initialization_order(self, components: Optional[List[str]] = None) -> List[str]:
        """
        [Function intent]
        Calculates the initialization order for components based on dependencies.
        
        [Implementation details]
        Uses a simple algorithm to ensure dependencies are initialized before dependents.
        
        [Design principles]
        Simple dependency resolution without complex graph theory.
        
        Args:
            components: Optional list of component names to include (defaults to all enabled)
            
        Returns:
            List[str]: Component names in initialization order
            
        Raises:
            ValueError: If there are circular dependencies
        """
        # Start with all enabled components if not specified
        if components is None:
            components = self.get_enabled_component_names()
        
        # Filter out components that aren't registered
        component_set = {name for name in components if name in self._component_dependencies}
        
        # Build dependency graph (name -> set of dependencies)
        graph: Dict[str, Set[str]] = {}
        for name in component_set:
            # Only include dependencies that are in our component set
            deps = {dep for dep in self._component_dependencies[name] if dep in component_set}
            graph[name] = deps
        
        # Calculate initialization order
        result = []
        visited = set()
        
        # Start with components that have no dependencies
        no_deps = [name for name, deps in graph.items() if not deps]
        result.extend(no_deps)
        visited.update(no_deps)
        
        # Keep processing until all components are visited
        while len(visited) < len(graph):
            # Find components whose dependencies are all visited
            ready = [
                name for name, deps in graph.items()
                if name not in visited and deps.issubset(visited)
            ]
            
            if not ready:
                # Find remaining components and their unresolved dependencies
                remaining = {
                    name: deps - visited
                    for name, deps in graph.items()
                    if name not in visited
                }
                msg = "\n".join(f"- {name}: missing {deps}" for name, deps in remaining.items())
                raise ValueError(f"Circular dependency detected. Unresolved dependencies:\n{msg}")
                
            result.extend(ready)
            visited.update(ready)
            
        return result
        
    def register_with_system(self, system: Any) -> None:
        """
        [Function intent]
        Registers all enabled components with a ComponentSystem instance.
        
        [Implementation details]
        Creates component instances and registers them with the system.
        
        [Design principles]
        Bridge between centralized registry and existing ComponentSystem.
        
        Args:
            system: The ComponentSystem instance
        """
        enabled_components = self.get_enabled_component_names()
        logger.info(f"Registering {len(enabled_components)} components with system")
        
        for name in enabled_components:
            try:
                component = self.create_component(name)
                dependencies = self.get_component_dependencies(name)
                
                # Register with the system, passing explicit dependencies
                # Use duck typing to accommodate different system implementations
                if hasattr(system, 'register') and callable(system.register):
                    # Try the new API with dependencies parameter
                    try:
                        system.register(component, dependencies)
                    except TypeError:
                        # Fall back to old API without dependencies
                        system.register(component)
                else:
                    logger.warning(f"System does not have a register method, skipping component '{name}'")
                    
            except Exception as e:
                logger.error(f"Failed to register component '{name}': {str(e)}", exc_info=True)
```

## Summary of Changes

1. Component Base Class:
   - Update initialize method to accept dependencies parameter
   - Add helper method for dependency access
   - Update docstrings to reflect changes

2. ComponentSystem:
   - Add tracking of dependencies in registration
   - Update validate_dependencies to use stored dependencies
   - Update _calculate_init_order to use stored dependencies
   - Update initialize_all to resolve and pass dependencies

3. ComponentRegistry (new):
   - Create centralized registry for component registration
   - Support explicit dependency declaration
   - Provide component discovery and initialization order calculation
   - Bridge between new registry and existing ComponentSystem

These changes lay the groundwork for centralized component registration and dependency declaration while maintaining backward compatibility during the transition.
