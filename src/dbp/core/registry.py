###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
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
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-19T23:37:00Z : Initial creation of ComponentRegistry by CodeAssistant
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
