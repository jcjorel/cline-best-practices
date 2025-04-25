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
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/CONFIGURATION.md
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
# system:- src/dbp/core/component.py
# other:- src/dbp/config/config_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-04-25T11:02:00Z : Updated config access to use get_typed_config() by CodeAssistant
# * Deprecated get() method with clear migration guidance
# * Updated get_default_config to return Pydantic model references directly
# * Added proper error handling for section navigation
# * Enhanced method documentation with three-section format
# 2025-04-20T10:21:00Z : Fixed initialization flag naming by CodeAssistant
# * Updated attribute name from _is_initialized to _initialized for base class compatibility
# * Added super().__init__() call in constructor to ensure proper initialization
# * Fixed is_initialized property implementation to use standard attribute name
# * Fixed shutdown method to use correct attribute name
# 2025-04-20T01:44:31Z : Completed dependency injection refactoring by CodeAssistant
# * Removed dependencies property
# * Made dependencies parameter required in initialize method
# * Updated parameter documentation for consistency
# 2025-04-19T23:49:00Z : Added dependency injection support by CodeAssistant
# * Updated initialize() method to accept dependencies parameter 
# * Enhanced method documentation using three-section format
# * Updated typing imports for consistency
###############################################################################

import logging
from typing import Dict, List, Optional, Any

# Import core component types
from ..core.component import Component, InitializationContext
from .config_manager import ConfigurationManager
from ..core.fs_utils import find_git_root

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
        super().__init__()  # Initialize the base Component class properly
        # Use provided instance or get singleton
        self._config_manager = config_manager or ConfigurationManager()
        self.logger = logging.getLogger(f"{__name__}.{self.name}")

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "config_manager"

    def initialize(self, context: InitializationContext, dependencies: Dict[str, Component]) -> None:
        """
        [Function intent]
        Initializes the ConfigManagerComponent.
        If the ConfigurationManager is not already initialized, initializes it.
        Sets the project root path from Git repository root.
        
        [Implementation details]
        Initializes the logger and ConfigurationManager.
        Sets the project root path from Git repository root.
        
        [Design principles]
        Early initialization with no dependencies.
        Consistent interface with other components.
        
        Args:
            context: The initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies (not used by this component)
        """
        self.logger = logging.getLogger(f"dbp.{self.name}")
        self.logger.info(f"Initializing component '{self.name}'...")
        
        if not self._config_manager.initialized_flag:
            self.logger.info("ConfigurationManager not yet initialized. Initializing now.")
            self._config_manager.initialize()
        
        # Find Git root and set project.root_path
        git_root = find_git_root()
        if git_root is None:
            self.logger.error("Could not find Git root directory. This is required for project.root_path.")
            raise RuntimeError("Git root directory not found. Cannot initialize configuration properly.")
            
        self.logger.info(f"Setting project.root_path to Git root: {git_root}")
        if not self._config_manager.set('project.root_path', str(git_root)):
            self.logger.error("Failed to set project.root_path in configuration")
            raise RuntimeError("Failed to set project.root_path in configuration")
        
        self._initialized = True
        self.logger.info(f"Component '{self.name}' initialized successfully.")

    def shutdown(self) -> None:
        """
        Performs graceful shutdown.
        No cleanup needed for ConfigurationManager.
        """
        self.logger.info(f"Shutting down component '{self.name}'...")
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    def get(self, key: str, resolve_templates: bool = True) -> Any:
        """
        [Function intent]
        Retrieves a configuration value using dot notation.
        THIS METHOD IS DEPRECATED. Use get_typed_config() instead.
        
        [Implementation details]
        Delegates to the ConfigurationManager but this method is deprecated.
        
        [Design principles]
        Provides backward compatibility but warns about deprecation.
        
        Args:
            key: The configuration key in dot notation.
            resolve_templates: If True, resolves any template variables in string values.
            
        Returns:
            The configuration value with template variables resolved.
            
        Raises:
            DeprecatedMethodError: Always raised to indicate this method is deprecated.
        """
        from ..core.exceptions import DeprecatedMethodError
        
        # Use the raw key path to determine the attribute access path for error message
        alternative = f"config_manager.get_typed_config().{key.replace('.', '.')}"
        self.logger.warning(f"The get() method is deprecated. Use {alternative} instead.")
        
        # Forward to the deprecated ConfigurationManager.get method
        # This will raise the appropriate DeprecatedMethodError
        return self._config_manager.get(key, resolve_templates)

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
        
    def get_typed_config(self):
        """
        [Function intent]
        Returns the strongly-typed configuration object for type-safe access.
        
        [Implementation details]
        Delegates to the ConfigurationManager's get_typed_config method.
        
        [Design principles]
        Type safety for configuration access.
        
        Returns:
            AppConfig: The validated configuration model
        """
        return self._config_manager.get_typed_config()
    
    def get_default_config(self, section: str) -> Any:
        """
        [Function intent]
        Returns the default configuration for a specific section as a Pydantic model.
        
        [Implementation details]
        Retrieves the section configuration from the typed config model
        and returns the model directly.
        
        [Design principles]
        Type-safe access to configuration sections as Pydantic models.
        
        Args:
            section: The configuration section name.
            
        Returns:
            Pydantic model section configuration object.
            
        Raises:
            ValueError: If the section doesn't exist.
        """
        try:
            # Get typed configuration
            typed_config = self._config_manager.get_typed_config()
            
            # Get the section using attribute access
            section_parts = section.split('.')
            section_config = typed_config
            
            # Navigate through the section parts
            for part in section_parts:
                section_config = getattr(section_config, part)
            
            # Return the section model directly
            return section_config
            
        except AttributeError as e:
            self.logger.error(f"Section '{section}' not found in configuration: {e}")
            raise ValueError(f"Section '{section}' not found in configuration") from e
        except Exception as e:
            self.logger.error(f"Could not get default configuration for section '{section}': {e}")
            raise ValueError(f"Could not get default configuration for section '{section}'") from e
