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
# Implements the ConfigManagerComponent class, which wraps the ConfigurationManager
# singleton in a Component-compatible interface to integrate with the component
# lifecycle framework. This enables the configuration manager to be available
# to other components via the component registry.
###############################################################################
# [Source file design principles]
# - Acts as an adapter between ConfigurationManager singleton and Component protocol
# - Provides access to configuration via the component system
# - Has no dependencies itself (should be one of the first components initialized)
# - Design Decision: Component Wrapper for ConfigurationManager (2025-04-16)
#   * Rationale: Allows configuration access through the standard component mechanism
#   * Alternatives considered: Direct singleton access (less consistent with component model)
###############################################################################
# [Source file constraints]
# - Depends on ConfigurationManager being implemented as a singleton
# - Must be registered early in the component initialization sequence
# - Must be named "config_manager" to meet dependency declarations
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/CONFIGURATION.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - src/dbp/core/component.py
# - src/dbp/config/config_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T01:25:43Z : Initial creation by CodeAssistant
# * Created ConfigManagerComponent implementing Component protocol
# * Wrapped ConfigurationManager singleton
###############################################################################

import logging
from typing import List, Optional, Dict, Any

# Import core component types
from ..core.component import Component, InitializationContext
from .config_manager import ConfigurationManager

logger = logging.getLogger(__name__)

class ConfigManagerComponent(Component):
    """
    Component implementation that wraps the ConfigurationManager singleton,
    providing access to configuration via the component system.
    """

    def __init__(self, config_manager: Optional[ConfigurationManager] = None):
        """
        Initializes the ConfigManagerComponent.
        
        Args:
            config_manager: Optional pre-initialized ConfigurationManager instance.
                           If None, uses the singleton instance.
        """
        self._is_initialized = False
        # Use provided instance or get singleton
        self._config_manager = config_manager or ConfigurationManager()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "config_manager"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # No dependencies - this should be one of the first components initialized
        return []

    def initialize(self, config: Any) -> None:
        """
        Initializes the ConfigManagerComponent.
        If the ConfigurationManager is not already initialized, initializes it.
        
        Args:
            config: Configuration object with application settings
        """
        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        if not self._config_manager.initialized_flag:
            self.logger.info("ConfigurationManager not yet initialized. Initializing now.")
            self._config_manager.initialize()
        
        self._is_initialized = True
        self.logger.info(f"Component '{self.name}' initialized successfully.")

    def shutdown(self) -> None:
        """
        Performs graceful shutdown.
        No cleanup needed for ConfigurationManager.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        self._is_initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._is_initialized

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value using dot notation.
        
        Args:
            key: The configuration key in dot notation.
            default: The value to return if the key is not found.
            
        Returns:
            The configuration value or the default.
        """
        return self._config_manager.get(key, default)

    def set(self, key: str, value: Any) -> bool:
        """
        Sets a configuration value at runtime using dot notation.
        
        Args:
            key: The configuration key in dot notation.
            value: The value to set.
            
        Returns:
            True if the value was set and validated successfully, False otherwise.
        """
        return self._config_manager.set(key, value)
        
    def get_default_config(self, section: str) -> Dict[str, Any]:
        """
        Returns the default configuration for a specific section.
        
        Args:
            section: The configuration section name.
            
        Returns:
            Dictionary containing default values for the section.
        """
        # Get default values from the Pydantic model
        default_config = self._config_manager._config.dict().get(section, {})
        return default_config
