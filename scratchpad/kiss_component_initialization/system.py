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
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T15:30:41Z : Initial creation of ComponentSystem class by CodeAssistant
# * Implemented ultra-simple component management with KISS principles
###############################################################################

import logging
from typing import Any, Dict, List, Set, Optional
import sys

from .component import Component

logger = logging.getLogger(__name__)

class CircularDependencyError(Exception):
    """Exception raised when a circular dependency is detected."""
    pass

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
    
    def __init__(self, config: Any, logger: logging.Logger):
        """
        [Function intent]
        Initializes the ComponentSystem with configuration and logger.
        
        [Implementation details]
        Sets up the component dictionary and initialization tracking.
        
        [Design principles]
        Minimal setup with explicit dependencies.
        
        Args:
            config: Application configuration object
            logger: Logger instance for status reporting
        """
        self.config = config
        self.logger = logger
        self.components: Dict[str, Component] = {}  # name -> component
        self._initialized: List[str] = []  # Initialization order for shutdown
    
    def register(self, component: Component) -> None:
        """
        [Function intent]
        Registers a component with the system by name.
        
        [Implementation details]
        Stores the component in the components dictionary with its name as key.
        
        [Design principles]
        Simple dictionary-based registration with clear errors.
        
        Args:
            component: Component instance to register
            
        Raises:
            ValueError: If a component with the same name is already registered
        """
        name = component.name
        if name in self.components:
            raise ValueError(f"Component '{name}' already registered")
        
        self.logger.debug(f"Registered component: {name}")
        self.components[name] = component
    
    def validate_dependencies(self) -> List[str]:
        """
        [Function intent]
        Validates that all component dependencies are registered.
        
        [Implementation details]
        Checks each component's dependencies against registered components.
        
        [Design principles]
        Early validation with clear error reporting.
        
        Returns:
            List[str]: List of error messages, empty if all dependencies valid
        """
        missing = []
        
        for name, component in self.components.items():
            for dep_name in component.dependencies:
                if dep_name not in self.components:
                    missing.append(f"Component '{name}' depends on '{dep_name}' which is not registered")
        
        return missing
    
    def initialize_all(self) -> bool:
        """
        [Function intent]
        Initializes all registered components in dependency order.
        
        [Implementation details]
        Validates dependencies, calculates initialization order,
        and initializes components sequentially with clear error reporting.
        
        [Design principles]
        Simple sequential process with explicit error handling.
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
                self.logger.info(f"Initializing component '{name}'...")
                component.initialize(self.config)
                
                # Verify initialization flag
                if not component.is_initialized:
                    self.logger.error(f"Component '{name}' did not set initialized flag")
                    self._rollback()
                    return False
                    
                # Track initialization for shutdown order
                self._initialized.append(name)
                self.logger.info(f"Component '{name}' initialized successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize component '{name}': {e}", exc_info=True)
                self._rollback()
                return False
        
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
                component = self.components[name]
                deps = set(component.dependencies)
                
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
                    cycle.append(f"{name} -> [{', '.join(self.components[name].dependencies)}]")
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
            self.logger.debug("No components to roll back")
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
