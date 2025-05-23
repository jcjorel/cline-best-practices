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
# Implements the ComponentSystem class, a minimalist system for managing component
# lifecycle (registration, initialization, shutdown) that replaces the previous
# complex orchestration system with a much simpler KISS approach.
###############################################################################
# [Source file design principles]
# - Ultra-simple component management with minimal code complexity
# - Dictionary-based component registry instead of complex classes
# - Direct dependency validation without complex graph algorithms
# - Sequential initialization based on simple dependency order
# - Clear error reporting rather than sophisticated recovery
###############################################################################
# [Source file constraints]
# - Components must implement the Component interface
# - Initialization errors fail fast rather than attempting recovery
# - All components are stored in a single dictionary
# - No complex transactions or rollbacks beyond basic cleanup
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T10:54:00Z : Updated config access to use get_typed_config() by CodeAssistant
# * Replaced deprecated ConfigurationManager.get() calls with get_typed_config()
# * Updated component enablement configuration access to use direct attribute access
# * Fixed server startup failures caused by deprecated method usage
# * Improved type safety through Pydantic model usage
# 2025-04-25T09:51:14Z : Added component enablement check to initialization by CodeAssistant
# * Modified initialize_all to check component_enabled configuration before initialization
# * Added strict validation for component enablement configuration
# * Updated documentation to reflect component enablement functionality
# * Improved error handling for component enablement configuration access
# 2025-04-25T08:43:00Z : Improved error handling with specific exceptions by CodeAssistant
# * Replaced CircularDependencyError with imported one from exceptions module
# * Modified get_component to raise ComponentNotFoundError and ComponentNotInitializedError
# * Changed return type from Optional[Component] to Component for strict error checking
# * Updated docstring to reflect the new fail-fast behavior
# 2025-04-20T19:15:00Z : Added watchdog keepalive to prevent deadlocks by CodeAssistant
# * Added keep_alive call before each component initialization
# * Ensured watchdog doesn't trigger false alarms during long component initializations
# * Fixed issue where watchdog wasn't properly updated between initializations
###############################################################################

import logging
from typing import Any, Dict, List, Set, Optional
import sys
import traceback

from .component import Component, InitializationContext
from .exceptions import CircularDependencyError, ComponentNotFoundError, ComponentNotInitializedError, ComponentError

logger = logging.getLogger(__name__)

class ComponentSystem:
    """
    [Class intent]
    Ultra-simple component system for managing component lifecycle
    following KISS principles. Handles registration, initialization,
    and shutdown with minimal complexity.
    
    [Implementation details]
    Uses a dictionary-based registry and simple dependency resolution
    algorithm without complex graph theory. Provides clear error reporting
    rather than sophisticated recovery mechanisms.
    
    [Design principles]
    Maximum simplicity over sophisticated features.
    Direct component access over layers of abstraction.
    Clear error messages over complex recovery strategies.
    """
    
    # Singleton instance for access from InitializationContext
    _instance: Optional['ComponentSystem'] = None
    
    @classmethod
    def get_instance(cls) -> Optional['ComponentSystem']:
        """
        [Function intent]
        Provides access to the singleton ComponentSystem instance.
        
        [Implementation details]
        Returns the current instance of ComponentSystem if available.
        Used by InitializationContext to access components.
        
        [Design principles]
        Simple global access pattern for compatibility with legacy code.
        
        Returns:
            Optional[ComponentSystem]: Current singleton instance or None if not set
        """
        return cls._instance
    
    def __init__(self, config: Any, logger: logging.Logger):
        """
        [Function intent]
        Initializes the ComponentSystem with configuration and logger.
        
        [Implementation details]
        Sets up the component dictionary and initialization tracking.
        Sets the singleton instance for global access.
        
        [Design principles]
        Minimal setup with explicit dependencies.
        Simple singleton pattern for legacy compatibility.
        
        Args:
            config: Application configuration object
            logger: Logger instance for status reporting
        """
        self.config = config
        self.logger = logger
        self.components: Dict[str, Component] = {}  # name -> component
        self._initialized: List[str] = []  # Initialization order for shutdown
        self.dependencies: Dict[str, List[str]] = {}  # name -> list of dependency names
        
        # Set singleton instance
        ComponentSystem._instance = self
    
    def register(self, component: Component, dependencies: List[str]) -> None:
        """
        [Function intent]
        Registers a component with the system by name and defines its dependencies.
        
        [Implementation details]
        Stores the component in the components dictionary with its name as key.
        Stores the dependencies for use during initialization.
        
        [Design principles]
        Simple dictionary-based registration with explicit dependency declaration.
        
        Args:
            component: Component instance to register
            dependencies: List of dependency names
            
        Raises:
            ValueError: If a component with the same name is already registered
        """
        name = component.name
        if name in self.components:
            raise ValueError(f"Component '{name}' already registered")
        
        # Enhanced logging for component registration
        self.logger.info(f"Registering component: '{name}' with dependencies: {dependencies}")
        self.components[name] = component
        self.dependencies[name] = dependencies
    
    def get_component(self, name: str) -> Component:
        """
        [Function intent]
        Retrieves a component by name with strict validation.
        
        [Implementation details]
        Looks up the component in the components dictionary and validates initialization.
        Raises specific exceptions for different error conditions.
        
        [Design principles]
        Fail-fast with specific exceptions rather than returning None.
        Clear error messages for easier troubleshooting.
        
        Args:
            name: Name of the component to retrieve
            
        Returns:
            Component: The initialized component
            
        Raises:
            ComponentNotFoundError: If the component is not registered
            ComponentNotInitializedError: If the component is registered but not initialized
        """
        component = self.components.get(name)
        if component is None:
            raise ComponentNotFoundError(name)
        if not component.is_initialized:
            raise ComponentNotInitializedError(name)
        return component
    
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
    
    def initialize_all(self) -> bool:
        """
        [Function intent]
        Initializes all registered components in dependency order,
        respecting component enablement configuration.
        
        [Implementation details]
        Validates dependencies, calculates initialization order,
        checks if each component is enabled in configuration,
        and initializes components sequentially with clear error reporting.
        
        [Design principles]
        Simple sequential process with explicit error handling.
        Respects component enablement configuration.
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
            raise ComponentError(f"Dependency validation failed with {len(missing)} errors")
        
        # Calculate initialization order
        try:
            init_order = self._calculate_init_order()
            self.logger.info(f"Component initialization order: {', '.join(init_order)}")
        except CircularDependencyError as e:
            self.logger.error(f"Circular dependency detected: {e}")
            # Re-raise the circular dependency exception
            raise e
        
        # Get component enablement configuration
        config_manager = self.components.get('config_manager')
        if not config_manager:
            raise ComponentNotFoundError('config_manager')
        
        # Get the component_enabled configuration from the typed config model
        typed_config = config_manager.get_typed_config()
        enabled_config = typed_config.component_enabled
        
        # We expect this to be a Pydantic model (ComponentEnabledConfig)
        self.logger.info(f"Using component enablement configuration: {enabled_config}")
        
        # Initialize components in order
        for name in init_order:
            component = self.components[name]
            
            # Check if component is enabled in configuration
            # Access component enablement directly via attribute access on the Pydantic model
            is_enabled = getattr(enabled_config, name)  # Dynamic attribute access using component name
            if not is_enabled:
                self.logger.info(f"Skipping disabled component: '{name}'")
                continue
            
            # Skip already initialized components
            if component.is_initialized:
                self.logger.debug(f"Component '{name}' already initialized, skipping")
                if name not in self._initialized:
                    self._initialized.append(name)
                continue
                
            try:
                # Enhanced logging before initialization
                self.logger.info(f"Initializing component '{name}'...")
                self.logger.debug(f"Component '{name}' class: {component.__class__.__name__}")
                
                # Update watchdog keepalive to prevent false deadlock detection during initialization
                try:
                    from .watchdog import keep_alive
                    keep_alive()
                    self.logger.debug(f"Updated watchdog keepalive before initializing '{name}'")
                except ImportError:
                    self.logger.debug(f"Watchdog module not available, skipping keepalive")
                
                # Create the initialization context
                # Components expect a config manager with get() method, not the raw config
                try:
                    config_manager = self.components.get('config_manager')
                    if not config_manager:
                        raise ComponentNotFoundError('config_manager')
                except ComponentError as e:
                    self.logger.error(f"Config manager error during initialization of '{name}': {e}")
                    self._rollback()
                    # Re-raise the original exception
                    raise e
                
                # Get the typed configuration - throw on error
                typed_config = config_manager.get_typed_config()
                
                context = InitializationContext(
                    config=config_manager,
                    logger=self.logger.getChild(component.name),  # Use child logger
                    typed_config=typed_config  # Include typed configuration
                )
                
                # Add logging for initialization context
                self.logger.info(f"Initializing component '{name}' with context type: {type(context)}")
                self.logger.info(f"Context attributes: config={type(context.config)}, logger={type(context.logger)}")
                
                # Resolve dependencies for this component
                component_deps = self.dependencies.get(name, [])
                resolved_deps = {}
                
                for dep_name in component_deps:
                    dep_component = self.components.get(dep_name)
                    if not dep_component:
                        self.logger.error(f"Dependency '{dep_name}' not found for component '{name}'")
                        self._rollback()
                        raise ComponentNotFoundError(dep_name)
                    if not dep_component.is_initialized:
                        self.logger.error(f"Dependency '{dep_name}' for component '{name}' is not initialized")
                        self._rollback()
                        raise ComponentNotInitializedError(dep_name)
                    resolved_deps[dep_name] = dep_component
                
                # Add logging for dependencies
                if resolved_deps:
                    self.logger.info(f"Resolved {len(resolved_deps)} dependencies for component '{name}'")
                
                # Initialize with dependencies
                component.initialize(context, resolved_deps)
                
                # Verify initialization flag with more detailed diagnostics
                if not component.is_initialized:
                    self.logger.error(f"Component '{name}' failed to set is_initialized flag to True")
                    self.logger.error(f"Component '{name}' current is_initialized value: {component.is_initialized}")
                    self._rollback()
                    raise ComponentError(f"Component '{name}' failed to set is_initialized flag to True after initialization")
                    
                # Track initialization for shutdown order
                self._initialized.append(name)
                self.logger.info(f"Component '{name}' initialized successfully")
                
            except Exception as e:
                # Enhanced error logging with exception details and stack trace
                self.logger.error(f"Failed to initialize component '{name}': {str(e)}")
                self.logger.error(f"Exception type: {type(e).__name__}")
                
                # Get and log the traceback
                exc_info = sys.exc_info()
                tb_lines = traceback.format_exception(*exc_info)
                
                # Log the full traceback with proper indentation for readability
                for line in tb_lines:
                    for subline in line.splitlines():
                        if subline.strip():
                            self.logger.error(f"  {subline}")
                
                # Log component state information if available
                if hasattr(component, 'get_debug_info'):
                    try:
                        debug_info = component.get_debug_info()
                        self.logger.error(f"Component '{name}' debug info: {debug_info}")
                    except Exception as debug_err:
                        self.logger.error(f"Failed to get component debug info: {debug_err}")
                
                # Log dependency states to help with troubleshooting
                if hasattr(component, 'dependencies'):
                    for dep_name in component.dependencies:
                        dep = self.components.get(dep_name)
                        if dep:
                            self.logger.error(f"Dependency '{dep_name}' initialized: {dep.is_initialized}")
                
                self._rollback()
                # Re-raise the original exception
                raise e
        
        self.logger.info("All components initialized successfully")
        return True
    
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
    
    def _rollback(self) -> None:
        """
        [Function intent]
        Rolls back initialization in case of errors.
        
        [Implementation details]
        Shuts down components in reverse initialization order.
        
        [Design principles]
        Simple cleanup with minimal error handling.
        
        Returns:
            None
        """
        if not self._initialized:
            self.logger.error("No components to roll back")
            return
            
        self.logger.warning(f"Rolling back initialization of {len(self._initialized)} components")
        
        # Shutdown in reverse initialization order
        for name in reversed(self._initialized):
            try:
                component = self.components[name]
                if component.is_initialized:
                    self.logger.info(f"Rolling back component '{name}'...")
                    component.shutdown()
            except Exception as e:
                self.logger.error(f"Error during rollback of component '{name}': {e}", exc_info=True)
                # Continue with other components even if one fails
        
        self._initialized = []
    
    def shutdown_all(self) -> None:
        """
        [Function intent]
        Shuts down all initialized components in reverse initialization order.
        
        [Implementation details]
        Iterates through components in reverse initialization order,
        calling shutdown on each with error handling.
        
        [Design principles]
        Simple reverse-order shutdown with error logging.
        Continues shutdown process even if individual components fail.
        
        Returns:
            None
        """
        if not self._initialized:
            self.logger.info("No components to shut down")
            return
            
        self.logger.info(f"Shutting down {len(self._initialized)} components")
        
        # Shutdown in reverse initialization order
        for name in reversed(self._initialized):
            try:
                component = self.components[name]
                if component.is_initialized:
                    self.logger.info(f"Shutting down component '{name}'...")
                    component.shutdown()
                    if component.is_initialized:
                        self.logger.warning(f"Component '{name}' still reports as initialized after shutdown")
            except Exception as e:
                self.logger.error(f"Error shutting down component '{name}': {e}", exc_info=True)
                # Continue with other components even if one fails
        
        self._initialized = []
        self.logger.info("All components shut down")
