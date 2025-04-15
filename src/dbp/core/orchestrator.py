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
# Implements the InitializationOrchestrator class, which manages the overall
# lifecycle of system components. It uses the DependencyResolver to determine
# the correct order and then iteratively initializes or shuts down components,
# passing the InitializationContext and handling potential errors.
###############################################################################
# [Source file design principles]
# - Coordinates the initialization and shutdown sequences based on resolved dependencies.
# - Creates and passes the InitializationContext to components.
# - Handles exceptions during component initialization and shutdown gracefully.
# - Ensures components are initialized/shut down in the correct order (init: dependency order, shutdown: reverse order).
# - Uses locking to prevent concurrent initialization/shutdown attempts.
# - Design Decision: Centralized Orchestration (2025-04-15)
#   * Rationale: Provides a single point of control for the application lifecycle, ensuring components are managed consistently.
#   * Alternatives considered: Decentralized initialization (harder to manage dependencies and order).
###############################################################################
# [Source file constraints]
# - Depends on `registry.py`, `resolver.py`, and `component.py`.
# - Requires configuration and logger instances to be provided during instantiation.
# - Relies on the DependencyResolver to provide a correct, cycle-free initialization order.
# - Error handling strategy for initialization failures needs careful consideration (e.g., stop all, continue partially).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - scratchpad/dbp_implementation_plan/plan_component_init.md
# - src/dbp/core/registry.py
# - src/dbp/core/resolver.py
# - src/dbp/core/component.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:48:30Z : Initial creation of InitializationOrchestrator by CodeAssistant
# * Implemented initialization and shutdown logic using dependency order. Added basic error handling.
###############################################################################

import logging
import threading
from typing import List, Optional, Any

# Assuming necessary imports from the same package
try:
    from .registry import ComponentRegistry
    from .resolver import DependencyResolver, CircularDependencyError
    from .component import Component, InitializationContext
    # Assuming config type is defined elsewhere or use Any
    # from ..config import AppConfig # Example
    Config = Any
except ImportError:
    # Placeholders for standalone execution or different structure
    ComponentRegistry = object
    DependencyResolver = object
    CircularDependencyError = Exception
    Component = object
    InitializationContext = object
    Config = object


logger = logging.getLogger(__name__)

class InitializationOrchestrator:
    """
    Orchestrates the initialization and shutdown of registered system components
    based on their declared dependencies.
    """

    def __init__(self, registry: ComponentRegistry, config: Config, base_logger: logging.Logger):
        """
        Initializes the InitializationOrchestrator.

        Args:
            registry: The ComponentRegistry containing components/factories.
            config: The application configuration object.
            base_logger: The base logger instance for the application.
        """
        if not isinstance(registry, ComponentRegistry):
             logger.warning("Orchestrator initialized with potentially incorrect registry type.")
        if base_logger is None:
             raise ValueError("A valid logger instance must be provided.")

        self.registry = registry
        self.config = config
        self.base_logger = base_logger
        self.resolver = DependencyResolver(registry)
        self._lock = threading.RLock() # Protects initialization/shutdown state
        self._initialized_components: List[str] = [] # Track successfully initialized components
        self._is_shutting_down = False

    def initialize_all(self) -> bool:
        """
        Initializes all registered components in the correct dependency order.

        Returns:
            True if all components initialized successfully, False otherwise.

        Raises:
            CircularDependencyError: If dependencies cannot be resolved.
            RuntimeError: If a critical error occurs during initialization.
        """
        with self._lock:
            if self._initialized_components:
                logger.warning("Initialization already attempted or completed. Skipping.")
                # Check if all known components were initialized successfully last time
                all_names = set(self.registry.get_all_names())
                return set(self._initialized_components) == all_names

            if self._is_shutting_down:
                 logger.error("Cannot initialize components while shutdown is in progress.")
                 return False

            self.base_logger.info("Starting component initialization sequence...")
            self._initialized_components = [] # Reset tracking

            try:
                # 1. Resolve dependency order
                init_order = self.resolver.resolve()
                self.base_logger.info(f"Component initialization order: {init_order}")

                # 2. Create Initialization Context
                # Ensure logger passed to context can be used by components
                context = InitializationContext(
                    config=self.config,
                    component_registry=self.registry,
                    logger=self.base_logger # Pass the base logger
                )

                # 3. Initialize components one by one
                for name in init_order:
                    component = self.registry.get(name) # Factory instantiation happens here if needed
                    component_logger = self.base_logger.getChild(f"component.{name}") # Create specific logger
                    context_with_component_logger = InitializationContext(
                         config=context.config,
                         component_registry=context.component_registry,
                         logger=component_logger
                    )

                    if component.is_initialized:
                         component_logger.debug(f"Component '{name}' already initialized. Skipping.")
                         self._initialized_components.append(name)
                         continue

                    component_logger.info(f"Initializing component '{name}'...")
                    try:
                        # Call the component's initialize method
                        component.initialize(context_with_component_logger)
                        # Verify initialization status if possible (relies on component implementation)
                        if not component.is_initialized:
                             # This indicates an issue with the component's initialize method
                             component_logger.error(f"Component '{name}' initialize() method completed but is_initialized is still False.")
                             raise RuntimeError(f"Component '{name}' failed to report successful initialization.")

                        self._initialized_components.append(name) # Track successful initialization
                        component_logger.info(f"Component '{name}' initialized successfully.")
                    except Exception as e:
                        component_logger.error(f"Failed to initialize component '{name}': {e}", exc_info=True)
                        # Decide on failure strategy: stop all or continue?
                        # For now, stop initialization and trigger shutdown of already initialized components.
                        self.base_logger.error("Critical component initialization failure. Aborting startup.")
                        self._rollback_initialization()
                        return False # Indicate failure

                self.base_logger.info("All components initialized successfully.")
                return True

            except CircularDependencyError as e:
                self.base_logger.error(f"Failed to resolve component dependencies: {e}")
                raise # Re-raise critical error
            except (KeyError, RuntimeError) as e:
                 self.base_logger.error(f"Failed to retrieve or instantiate a component during initialization: {e}")
                 self._rollback_initialization()
                 raise RuntimeError("Critical component retrieval error during startup.") from e
            except Exception as e:
                 self.base_logger.error(f"An unexpected error occurred during initialization: {e}", exc_info=True)
                 self._rollback_initialization()
                 raise RuntimeError("Unexpected error during component initialization.") from e


    def _rollback_initialization(self):
         """Attempts to shut down components that were successfully initialized during a failed startup."""
         self.base_logger.warning("Rolling back partially completed initialization...")
         # Shutdown components that were initialized, in reverse order of their initialization
         shutdown_order = list(reversed(self._initialized_components))
         self.base_logger.debug(f"Rollback shutdown order: {shutdown_order}")

         for name in shutdown_order:
              try:
                   component = self.registry.get(name) # Should exist as it was initialized
                   component_logger = self.base_logger.getChild(f"component.{name}")
                   if component.is_initialized: # Check again before shutting down
                        component_logger.info(f"Shutting down component '{name}' due to initialization rollback...")
                        component.shutdown()
                        component_logger.info(f"Component '{name}' shut down during rollback.")
              except Exception as e:
                   # Log shutdown errors during rollback but continue rollback process
                   component_logger.error(f"Error shutting down component '{name}' during rollback: {e}", exc_info=True)

         self._initialized_components = [] # Clear the list after rollback


    def shutdown_all(self):
        """
        Shuts down all initialized components in the reverse order of their initialization.
        """
        with self._lock:
            if self._is_shutting_down:
                 logger.warning("Shutdown already in progress.")
                 return
            if not self._initialized_components:
                logger.info("No components were initialized or initialization failed. Skipping shutdown.")
                return

            self._is_shutting_down = True
            self.base_logger.info("Starting component shutdown sequence...")

            # Use the tracked list of successfully initialized components, in reverse order
            shutdown_order = list(reversed(self._initialized_components))
            self.base_logger.info(f"Component shutdown order: {shutdown_order}")

            for name in shutdown_order:
                try:
                    component = self.registry.get(name) # Component must exist if it was initialized
                    component_logger = self.base_logger.getChild(f"component.{name}")
                    if component.is_initialized: # Check if it's still considered initialized
                         component_logger.info(f"Shutting down component '{name}'...")
                         component.shutdown()
                         component_logger.info(f"Component '{name}' shut down successfully.")
                    else:
                         component_logger.warning(f"Component '{name}' was already marked as not initialized before shutdown.")
                except KeyError:
                     # Should not happen if _initialized_components is accurate
                     self.base_logger.error(f"Component '{name}' was marked as initialized but not found in registry during shutdown.")
                except Exception as e:
                    # Log errors during shutdown but continue shutting down other components
                    component_logger.error(f"Error occurred while shutting down component '{name}': {e}", exc_info=True)

            self.base_logger.info("Component shutdown sequence complete.")
            self._initialized_components = [] # Reset state after successful shutdown
            self._is_shutting_down = False
