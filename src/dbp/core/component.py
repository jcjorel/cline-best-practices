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
# Defines the core interfaces and data structures for the component initialization
# framework. This includes the `Component` protocol that all manageable system
# components must implement, and the `InitializationContext` dataclass used to
# pass shared resources like configuration and the component registry during setup.
###############################################################################
# [Source file design principles]
# - Uses Protocol (structural subtyping) for the `Component` interface to avoid
#   forcing concrete inheritance, allowing flexibility in component implementation.
# - Defines a clear contract for components (name, dependencies, initialize, shutdown, status).
# - Uses a dataclass for `InitializationContext` for simple and clear data transfer.
# - Emphasizes type hinting for clarity and static analysis.
# - Design Decision: Protocol for Component Interface (2025-04-15)
#   * Rationale: Allows any class that implements the required methods and properties to be treated as a Component without explicit inheritance, promoting loose coupling.
#   * Alternatives considered: Abstract Base Class (requires explicit inheritance).
# - Design Decision: InitializationContext Dataclass (2025-04-15)
#   * Rationale: Provides a simple, immutable (by convention) way to pass necessary context to components during initialization.
#   * Alternatives considered: Passing individual arguments (less organized), Dependency injection container (more complex for this stage).
###############################################################################
# [Source file constraints]
# - Requires Python 3.8+ for `typing.Protocol`.
# - Components must strictly adhere to the `Component` protocol.
# - `InitializationContext` relies on other framework parts (Config, Registry, Logger) being defined and passed correctly.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - scratchpad/dbp_implementation_plan/plan_component_init.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:47:05Z : Initial creation of component interfaces by CodeAssistant
# * Defined Component protocol and InitializationContext dataclass.
###############################################################################

import logging
from dataclasses import dataclass
from typing import List, Protocol, TYPE_CHECKING, Any

# Use TYPE_CHECKING to avoid circular imports at runtime
if TYPE_CHECKING:
    from .registry import ComponentRegistry # Assuming registry.py defines ComponentRegistry
    # Define placeholder types if actual config/logger types are complex or defined elsewhere
    # from ..config import AppConfig # Example if config is defined elsewhere
    Config = Any # Placeholder for actual Config type
    Logger = logging.Logger # Use standard logger type hint
else:
    # Provide dummy types for runtime if needed, though Protocol doesn't strictly require them
    ComponentRegistry = Any
    Config = Any
    Logger = Any


class Component(Protocol):
    """
    Protocol defining the standard interface for all manageable system components
    within the Documentation-Based Programming system.

    Components implementing this protocol can be registered, initialized, and shut down
    by the initialization framework.
    """

    @property
    def name(self) -> str:
        """Return the unique name of the component (e.g., 'database', 'fs_monitor')."""
        ...

    @property
    def dependencies(self) -> List[str]:
        """
        Return a list of component names that this component depends on.
        These dependencies must be initialized before this component.
        Return an empty list if there are no dependencies.
        """
        ...

    def initialize(self, context: 'InitializationContext') -> None:
        """
        Initialize the component. This method is called by the orchestrator
        after all dependencies have been successfully initialized.

        Args:
            context: An InitializationContext object providing access to shared
                     resources like configuration, logger, and other components.

        Raises:
            Exception: If initialization fails, an exception should be raised
                       to signal the failure to the orchestrator.
        """
        ...

    def shutdown(self) -> None:
        """
        Perform graceful shutdown of the component. This method is called by
        the orchestrator during the application shutdown sequence, typically
        in the reverse order of initialization.

        Implementations should release resources (e.g., close connections,
        stop threads) and ensure the component stops cleanly. Exceptions
        during shutdown should be handled internally or logged, but generally
        should not prevent other components from shutting down.
        """
        ...

    @property
    def is_initialized(self) -> bool:
        """
        Return True if the component has been successfully initialized, False otherwise.
        Used by the framework to track component state.
        """
        ...


@dataclass(frozen=True) # Use frozen=True to make context immutable after creation
class InitializationContext:
    """
    A data container holding shared resources and context passed to components
    during their `initialize` method call.
    """
    config: Config # Provides access to the application configuration
    component_registry: 'ComponentRegistry' # Allows access to other initialized components
    logger: Logger # Provides a logger instance for the component

    def get_component(self, name: str) -> Component:
        """
        Convenience method to retrieve another component instance from the registry.

        Args:
            name: The unique name of the component to retrieve.

        Returns:
            The requested Component instance.

        Raises:
            KeyError: If the requested component is not found in the registry.
            RuntimeError: If the component registry itself is not available (should not happen).
        """
        if not self.component_registry:
            # This case should ideally not happen if context is constructed correctly
            self.logger.error("Component registry is not available in InitializationContext.")
            raise RuntimeError("Component registry unavailable in context.")
        try:
            # Delegate retrieval to the registry
            component = self.component_registry.get(name)
            if not component.is_initialized:
                 # This check depends on the orchestrator ensuring dependencies are initialized first.
                 # Logging a warning might be useful.
                 self.logger.warning(f"Accessing component '{name}' which might not be fully initialized yet.")
            return component
        except KeyError:
            self.logger.error(f"Dependency component '{name}' not found in the registry.")
            raise # Re-raise KeyError to indicate missing dependency
