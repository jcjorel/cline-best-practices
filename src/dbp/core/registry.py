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
# Implements the ComponentRegistry class, a central store for all manageable
# system components. It allows registering components directly or via factory
# functions for lazy instantiation and provides methods to retrieve components by name.
###############################################################################
# [Source file design principles]
# - Provides a thread-safe registry using RLock.
# - Supports both eager registration (component instances) and lazy registration (factories).
# - Ensures component names are unique.
# - Retrieves components by name, instantiating via factory if necessary.
# - Design Decision: Combined Instance/Factory Registration (2025-04-15)
#   * Rationale: Offers flexibility in how components are provided to the registry, supporting both pre-created instances and on-demand creation.
#   * Alternatives considered: Separate registries for instances and factories (more complex).
###############################################################################
# [Source file constraints]
# - Component names must be unique strings.
# - Factory functions must return an object conforming to the Component protocol.
# - Concurrent registration and retrieval are handled via locking.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - scratchpad/dbp_implementation_plan/plan_component_init.md
# - src/dbp/core/component.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:47:30Z : Initial creation of ComponentRegistry class by CodeAssistant
# * Implemented registration for instances and factories, retrieval logic, and thread safety.
###############################################################################

import threading
import logging
from typing import Dict, List, Callable, Optional

# Assuming component.py defines the Component protocol
try:
    from .component import Component
except ImportError:
    # Define a placeholder if running standalone or structure differs
    from typing import Protocol
    class Component(Protocol):
        @property
        def name(self) -> str: ...
        @property
        def is_initialized(self) -> bool: ...
        # Add other methods/properties if needed by registry logic


logger = logging.getLogger(__name__)

class ComponentRegistry:
    """
    A thread-safe registry for managing system components.

    Allows registering component instances directly or factory functions
    for lazy instantiation. Components are retrieved by their unique names.
    """

    def __init__(self):
        """Initializes the ComponentRegistry."""
        # Stores already instantiated components: name -> Component instance
        self._components: Dict[str, Component] = {}
        # Stores factory functions for lazy creation: name -> Callable[[], Component]
        self._factories: Dict[str, Callable[[], Component]] = {}
        self._lock = threading.RLock() # Reentrant lock for thread safety
        logger.debug("ComponentRegistry initialized.")

    def register(self, component: Component):
        """
        Registers a pre-instantiated component.

        Args:
            component: An instance of an object conforming to the Component protocol.

        Raises:
            ValueError: If a component or factory with the same name is already registered.
            TypeError: If the provided object does not have a 'name' property.
        """
        if not hasattr(component, 'name') or not isinstance(component.name, str):
             logger.error("Attempted to register a component without a valid string 'name' property.")
             raise TypeError("Registered component must have a valid string 'name' property.")

        component_name = component.name
        with self._lock:
            if component_name in self._components or component_name in self._factories:
                logger.error(f"Component or factory with name '{component_name}' already registered.")
                raise ValueError(f"Component name conflict: '{component_name}' is already registered.")
            self._components[component_name] = component
            logger.info(f"Component instance registered: '{component_name}' ({type(component).__name__})")

    def register_factory(self, name: str, factory: Callable[[], Component]):
        """
        Registers a factory function for creating a component lazily.
        The factory will be called the first time the component is requested via `get()`.

        Args:
            name: The unique name of the component this factory creates.
            factory: A callable (e.g., function, lambda) that takes no arguments
                     and returns an instance conforming to the Component protocol.

        Raises:
            ValueError: If a component or factory with the same name is already registered.
            TypeError: If the factory is not callable.
        """
        if not callable(factory):
            logger.error(f"Attempted to register a non-callable factory for component '{name}'.")
            raise TypeError(f"Factory for '{name}' must be callable.")

        with self._lock:
            if name in self._components or name in self._factories:
                logger.error(f"Component or factory with name '{name}' already registered.")
                raise ValueError(f"Component name conflict: '{name}' is already registered.")
            self._factories[name] = factory
            logger.info(f"Component factory registered for: '{name}'")

    def get(self, name: str) -> Component:
        """
        Retrieves a component by its unique name.

        If the component has not been instantiated yet but a factory is registered,
        the factory will be called to create the instance, which is then stored
        and returned.

        Args:
            name: The name of the component to retrieve.

        Returns:
            The requested Component instance.

        Raises:
            KeyError: If no component or factory with the given name is registered.
        """
        with self._lock:
            # Check if instance already exists
            if name in self._components:
                return self._components[name]

            # Check if a factory exists
            if name in self._factories:
                logger.debug(f"Component '{name}' not found, attempting creation via factory.")
                factory = self._factories[name]
                try:
                    component_instance = factory()
                    # Basic check to ensure factory returned something component-like
                    if not (hasattr(component_instance, 'name') and component_instance.name == name):
                         logger.error(f"Factory for '{name}' returned an invalid component (name mismatch or missing).")
                         # Remove broken factory?
                         # del self._factories[name]
                         raise TypeError(f"Factory for '{name}' did not return a valid Component instance.")

                    logger.info(f"Component '{name}' created via factory.")
                    # Store the created instance and remove the factory
                    self._components[name] = component_instance
                    # del self._factories[name] # Keep factory? Or assume one-shot? Let's keep it for now.
                    return component_instance
                except Exception as e:
                    logger.error(f"Error calling factory for component '{name}': {e}", exc_info=True)
                    # Should we remove the factory if it fails?
                    # del self._factories[name]
                    raise RuntimeError(f"Failed to create component '{name}' from factory.") from e

            # If neither instance nor factory exists
            logger.error(f"Component '{name}' not found in registry.")
            raise KeyError(f"Component '{name}' not registered.")

    def get_all_names(self) -> List[str]:
        """Returns a list of names of all registered components and factories."""
        with self._lock:
            # Combine keys from both dictionaries
            all_names = set(self._components.keys()) | set(self._factories.keys())
            return sorted(list(all_names))

    def get_all_initialized_components(self) -> List[Component]:
         """Returns a list of all component instances that are currently initialized."""
         with self._lock:
              # Note: This relies on components correctly implementing is_initialized.
              # It only checks components that have been instantiated.
              return [comp for comp in self._components.values() if comp.is_initialized]

    def get_all_component_instances(self) -> List[Component]:
         """Returns a list of all component instances currently held by the registry."""
         with self._lock:
              return list(self._components.values())

    def is_registered(self, name: str) -> bool:
         """Checks if a component or factory with the given name is registered."""
         with self._lock:
              return name in self._components or name in self._factories
