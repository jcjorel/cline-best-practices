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
# Implements the ConfigurationManager singleton class responsible for loading,
# validating, merging, and providing access to the DBP system's configuration.
# It handles multiple configuration sources with a defined priority order.
###############################################################################
# [Source file design principles]
# - Singleton pattern ensures a single instance manages configuration globally.
# - Thread-safe access using RLock.
# - Layered configuration loading (defaults, files, env vars, CLI args).
# - Uses Pydantic schema (`AppConfig`) for validation and type coercion.
# - Supports JSON and YAML configuration file formats.
# - Handles environment variables with a specific prefix (`DBP_`).
# - Parses command-line arguments for overrides.
# - Provides methods for getting/setting values and loading project-specific configs.
# - Design Decision: Singleton Pattern (2025-04-14)
#   * Rationale: Ensures consistent configuration access across the application without passing instances around.
#   * Alternatives considered: Global variable (less controlled), Dependency injection (more complex for simple config access).
# - Design Decision: Layered Configuration Loading (2025-04-14)
#   * Rationale: Provides flexibility for users to override defaults at different levels (system, user, project, runtime).
#   * Alternatives considered: Single config file (less flexible), Only env vars (harder for complex configs).
# - Design Decision: No Default Values in get() Method (2025-04-17)
#   * Rationale: Forces callers to explicitly handle missing configuration values rather than relying on implicit defaults.
#   * Alternatives considered: Supporting default values in get() method (rejected to encourage explicit error handling).
###############################################################################
# [Source file constraints]
# - Requires `config_schema.py` for the `AppConfig` model.
# - Requires `PyYAML` library for YAML file support.
# - Initialization (`initialize()`) must be called before accessing configuration.
# - Project-specific configuration loading requires the project root path.
###############################################################################
# [Reference documentation]
# - doc/CONFIGURATION.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T07:39:00Z : Added automatic template variable resolution by CodeAssistant
# * Implemented _resolve_all_template_variables to recursively process all configuration values
# * Modified _apply_configuration_hierarchy to resolve all templates before marking config as ready
# * Updated get() method to expect pre-resolved values with backward compatibility support
# * Improved logging for template resolution activities
# 2025-04-17T23:04:30Z : Simplified ConfigurationManager with Pydantic-first approach by CodeAssistant
# * Refactored configuration loading to use direct Pydantic model manipulation
# * Enhanced error handling and improved descriptive error messages
# * Added helper methods for attribute path navigation
# * Improved type safety throughout configuration handling
# 2025-04-17T23:02:00Z : Implemented type-safe configuration setting by CodeAssistant
# * Added _set_config_attr_by_path helper for safely navigating configuration paths
# * Refactored set() method to use Pydantic model validation
# * Improved error reporting for configuration setting operations
# 2025-04-17T23:01:00Z : Enhanced get() method with direct model access by CodeAssistant
# * Refactored get() method to use attribute access instead of dictionary lookups
# * Improved error handling with better diagnostics for missing keys
# * Enhanced type safety through direct Pydantic model usage
###############################################################################

import os
import json
import yaml # Requires PyYAML
import logging
import argparse
import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import threading

# Use standard logging to avoid circular imports
from pydantic import BaseModel, ValidationError

# Assuming config_schema.py is in the same directory or accessible
try:
    from .config_schema import AppConfig
except ImportError:
    from config_schema import AppConfig


# Set up logger with standard logging
logger = logging.getLogger(__name__)

# Define default config paths relative to standard locations
DEFAULT_SYSTEM_CONFIG_DIR = Path("/etc/dbp")
DEFAULT_USER_CONFIG_DIR = Path.home() / ".config" / "dbp"
DEFAULT_PROJECT_CONFIG_DIR = Path(".dbp") # Relative to project root

class ConfigurationManager:
    """
    Manages loading, validation, and access to application configuration
    using a singleton pattern and layered approach. Provides both string-based
    key access and strongly-typed configuration access.
    """
    _instance = None
    _lock = threading.RLock() # Use RLock for reentrant locking if needed

    def __new__(cls, *args, **kwargs):
        # Ensure only one instance is created
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # Initialize instance attributes only once
                cls._instance._initialized_internal = False
            return cls._instance

    def __init__(self):
        """Initializes the ConfigurationManager instance (only once)."""
        # Prevent re-initialization
        if hasattr(self, '_initialized_internal') and self._initialized_internal:
            return

        with self._lock:
            # Double check initialization flag inside lock
            if hasattr(self, '_initialized_internal') and self._initialized_internal:
                 return

            self._config: AppConfig = AppConfig() # Holds the validated config
            self._raw_config_dict: Dict[str, Any] = {} # Holds merged raw data before validation
            self._cli_args: Dict[str, Any] = {}
            self._env_vars: Dict[str, Any] = {}
            self._config_files_data: Dict[str, Dict[str, Any]] = {} # path: data
            self._initialized_internal = True # Mark internal init complete
            self.initialized_flag = False # Public flag set after successful initialize() call
            logger.debug("ConfigurationManager singleton instance created.")

    def initialize(self, args: Optional[List[str]] = None, project_root: Optional[str] = None):
        """
        Initializes and loads configuration from all sources.
        This method should be called once at application startup.

        Args:
            args: List of command-line arguments (e.g., from sys.argv[1:]).
            project_root: Optional path to the project root for loading project-specific config.
        """
        if self.initialized_flag:
            logger.warning("ConfigurationManager already initialized. Skipping re-initialization.")
            return

        with self._lock:
            # Reset state before loading
            self._config = AppConfig() # Start with defaults
            self._raw_config_dict = {}
            self._cli_args = {}
            self._env_vars = {}
            self._config_files_data = {}

            logger.info("Initializing configuration...")
            try:
                # 1. Load configuration from standard file locations
                self._load_standard_config_files()

                # 2. Load project-specific configuration file if project_root is provided
                if project_root:
                    self.load_project_config(project_root, apply_hierarchy=False) # Load but don't apply yet

                # 3. Load environment variables
                self._load_environment_variables()

                # 4. Load command-line arguments (and potential --config file)
                self._load_command_line_args(args)

                # 5. Apply hierarchy and validate
                self._apply_configuration_hierarchy()

                self.initialized_flag = True # Mark public init complete
                logger.info("Configuration initialized successfully.")
            except Exception as e:
                 logger.error(f"Critical error during configuration initialization: {e}", exc_info=True)
                 # Ensure we still have default config even on error
                 self._config = AppConfig()
                 self.initialized_flag = False # Indicate failure
                 raise # Re-raise critical error

    def _load_standard_config_files(self):
        """Loads configuration from system-wide and user-specific files."""
        logger.debug("Loading standard configuration files...")
        config_paths = [
            # System-wide configuration
            DEFAULT_SYSTEM_CONFIG_DIR / "config.json",
            DEFAULT_SYSTEM_CONFIG_DIR / "config.yaml",
            DEFAULT_SYSTEM_CONFIG_DIR / "config.yml",
            # User configuration
            DEFAULT_USER_CONFIG_DIR / "config.json",
            DEFAULT_USER_CONFIG_DIR / "config.yaml",
            DEFAULT_USER_CONFIG_DIR / "config.yml",
        ]

        for path in config_paths:
            if path.exists() and path.is_file():
                self._load_and_store_config_file(path)
            else:
                logger.debug(f"Configuration file not found or not a file: {path}")

    def _load_and_store_config_file(self, path: Path):
        """Loads data from a single config file and stores it."""
        try:
            logger.debug(f"Attempting to load configuration from {path}...")
            data = self._load_config_file_content(path)
            if data: # Ensure data is not empty
                self._config_files_data[str(path)] = data
                logger.info(f"Successfully loaded configuration from {path}")
            else:
                logger.debug(f"Configuration file is empty: {path}")

        except Exception as e:
            logger.warning(f"Failed to load or parse configuration file {path}: {e}", exc_info=True)


    def _load_config_file_content(self, path: Path) -> Optional[Dict[str, Any]]:
        """Loads and parses content from a JSON or YAML file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
                if not content.strip(): # Check if file is empty or whitespace only
                    return None
                if path.suffix.lower() in ['.yaml', '.yml']:
                    return yaml.safe_load(content)
                elif path.suffix.lower() == '.json':
                    return json.loads(content)
                else:
                    logger.warning(f"Unsupported configuration file format: {path.suffix} for file {path}")
                    return None
        except FileNotFoundError:
             logger.debug(f"Configuration file not found: {path}")
             return None
        except (yaml.YAMLError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing configuration file {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error reading configuration file {path}: {e}", exc_info=True)
            return None


    def _load_environment_variables(self):
        """Loads configuration overrides from environment variables (DBP_...)."""
        logger.debug("Loading configuration from environment variables...")
        prefix = "DBP_"
        self._env_vars = {}
        count = 0
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert DBP_DATABASE_MAX_CONNECTIONS to database.max_connections
                config_key = key[len(prefix):].lower().replace('_', '.')
                self._env_vars[config_key] = value
                count += 1
        logger.debug(f"Loaded {count} configuration values from environment variables.")

    def _load_command_line_args(self, args: Optional[List[str]] = None):
        """
        Loads configuration overrides from command-line arguments (--key.subkey=value)
        and handles an optional --config argument.
        """
        logger.debug("Loading configuration from command-line arguments...")
        parser = argparse.ArgumentParser(add_help=False) # Don't interfere with main parser
        parser.add_argument('--config', help='Path to an additional configuration file.')

        # Parse only the --config argument first
        known_args, remaining_args = parser.parse_known_args(args)

        # Load the additional config file specified by --config, if any
        if known_args.config:
            config_file_path = Path(known_args.config)
            if config_file_path.exists() and config_file_path.is_file():
                 self._load_and_store_config_file(config_file_path)
            else:
                 logger.warning(f"Config file specified via --config not found or not a file: {config_file_path}")

        # Parse remaining args as key=value pairs
        self._cli_args = {}
        count = 0
        # Use remaining_args from parse_known_args
        for arg in remaining_args:
            if arg.startswith('--') and '=' in arg:
                try:
                    key, value = arg[2:].split('=', 1)
                    self._cli_args[key] = value
                    count += 1
                except ValueError:
                    logger.warning(f"Could not parse command-line argument: {arg}")
            # Silently ignore other arguments not in key=value format
        logger.debug(f"Loaded {count} configuration values from command-line arguments.")


    def _apply_config_data_to_model(self, config: AppConfig, data: Dict[str, Any]) -> None:
        """
        [Function intent]
        Applies a dictionary of configuration data to a Pydantic model.
        
        [Implementation details]
        Handles applying both direct attributes and nested paths.
        
        [Design principles]
        Safe application of configuration values with proper error handling.
        
        Args:
            config: The Pydantic model to update
            data: Dictionary of configuration data to apply
        """
        # Process each key-value pair in the data
        for key, value in data.items():
            try:
                # Check if the key exists as a direct attribute
                if hasattr(config, key):
                    if isinstance(value, dict):
                        # Get the corresponding attribute for nested processing
                        attr = getattr(config, key)
                        if isinstance(attr, BaseModel):
                            # Recursively apply to nested Pydantic models
                            for subkey, subvalue in value.items():
                                try:
                                    if isinstance(subvalue, dict) and hasattr(attr, subkey):
                                        nested_attr = getattr(attr, subkey)
                                        if isinstance(nested_attr, BaseModel):
                                            self._apply_config_data_to_model(nested_attr, subvalue)
                                        else:
                                            setattr(attr, subkey, subvalue)
                                    else:
                                        setattr(attr, subkey, subvalue)
                                except (AttributeError, ValidationError) as e:
                                    logger.warning(f"Failed to set nested config '{key}.{subkey}': {e}")
                    else:
                        # Set direct attribute
                        setattr(config, key, value)
            except (AttributeError, ValidationError) as e:
                logger.warning(f"Failed to apply configuration for '{key}': {e}")

    def _apply_configuration_hierarchy(self):
        """
        [Function intent]
        Applies configuration from all sources, validates using the Pydantic schema,
        and resolves all template variables before marking as ready.
        
        [Implementation details]
        Creates a base AppConfig instance and sequentially applies configuration from
        different sources directly to the Pydantic model, then resolves all template
        strings to ensure clients don't need to handle template resolution.
        
        [Design principles]
        Direct Pydantic model manipulation without intermediate dictionaries.
        Proper validation at each configuration layer.
        Pre-resolved template variables to eliminate client-side resolution.
        """
        logger.debug("Applying configuration hierarchy...")
        
        # Start with default configuration
        config = AppConfig()
        
        try:
            # 1. Apply standard config files (System -> User)
            sorted_file_paths = sorted(self._config_files_data.keys())
            for file_path in sorted_file_paths:
                is_project_config = ".dbp" in file_path  # Heuristic check
                if not is_project_config:
                    logger.debug(f"Applying config from standard file: {file_path}")
                    self._apply_config_data_to_model(config, self._config_files_data[file_path])
            
            # 2. Apply project config
            project_config_path_str = next((p for p in self._config_files_data if ".dbp" in p), None)
            if project_config_path_str:
                logger.debug(f"Applying config from project file: {project_config_path_str}")
                self._apply_config_data_to_model(config, self._config_files_data[project_config_path_str])
                
            # 3. Apply environment variables
            if self._env_vars:
                logger.debug("Applying config from environment variables...")
                for key, value in self._env_vars.items():
                    # Convert value to appropriate type
                    converted_value = self._convert_value(value)
                    self._set_config_attr_by_path(config, key, converted_value)
                    
            # 4. Apply CLI arguments
            if self._cli_args:
                logger.debug("Applying config from command-line arguments...")
                for key, value in self._cli_args.items():
                    # Convert value to appropriate type
                    converted_value = self._convert_value(value)
                    self._set_config_attr_by_path(config, key, converted_value)
                    
            # 5. Resolve all template variables before finalizing
            logger.debug("Resolving all template variables in configuration...")
            self._resolve_all_template_variables(config)
            
            # Store the final validated config with resolved variables
            self._config = config
            # Also maintain the raw dict for backwards compatibility
            self._raw_config_dict = config.dict()
            logger.debug("Configuration validated successfully with all template variables resolved.")
            
        except ValidationError as e:
            logger.error(f"Configuration validation failed. Using default values. Errors:\n{e}")
            # Fallback to default configuration on validation error
            self._config = AppConfig()
            self._raw_config_dict = self._config.dict()

    def _convert_value(self, value: str) -> Any:
        """Attempts to convert string value to bool, int, float, or keeps as string."""
        if isinstance(value, str):
            val_lower = value.lower()
            if val_lower in ['true', 'yes', '1', 'on']:
                return True
            if val_lower in ['false', 'no', '0', 'off']:
                return False
            try:
                return int(value)
            except ValueError:
                try:
                    return float(value)
                except ValueError:
                    return value # Keep as string if no other conversion works
        return value # Return non-string values as is


    def _resolve_all_template_variables(self, config, path=""):
        """
        [Function intent]
        Recursively resolves all template variables in the config object.
        
        [Implementation details]
        Traverses the entire Pydantic model structure and resolves any string 
        values that contain template variables in the ${key} format.
        
        [Design principles]
        Deep resolution to ensure all nested templates are resolved before clients access configuration.
        
        Args:
            config: The configuration object or sub-object to process
            path: Current path in the configuration hierarchy (for logging)
        """
        # Skip None values
        if config is None:
            return
            
        # Handle different types of configuration objects
        if isinstance(config, BaseModel):
            # Process each field in the Pydantic model
            for field_name, field_value in config.__dict__.items():
                field_path = f"{path}.{field_name}" if path else field_name
                
                if isinstance(field_value, BaseModel):
                    # Recursively process nested models
                    self._resolve_all_template_variables(field_value, field_path)
                elif isinstance(field_value, dict):
                    # Process dictionary values
                    for key, value in field_value.items():
                        dict_path = f"{field_path}.{key}"
                        if isinstance(value, str) and "${" in value:
                            resolved_value = self.resolve_template_string(value)
                            if resolved_value != value:
                                logger.debug(f"Resolved template in {dict_path}: {value} → {resolved_value}")
                                field_value[key] = resolved_value
                        elif isinstance(value, (dict, list, BaseModel)):
                            self._resolve_all_template_variables(value, dict_path)
                elif isinstance(field_value, list):
                    # Process list values
                    for i, item in enumerate(field_value):
                        item_path = f"{field_path}[{i}]"
                        if isinstance(item, str) and "${" in item:
                            resolved_item = self.resolve_template_string(item)
                            if resolved_item != item:
                                logger.debug(f"Resolved template in {item_path}: {item} → {resolved_item}")
                                field_value[i] = resolved_item
                        elif isinstance(item, (dict, list, BaseModel)):
                            self._resolve_all_template_variables(item, item_path)
                elif isinstance(field_value, str) and "${" in field_value:
                    # Resolve string templates
                    resolved_value = self.resolve_template_string(field_value)
                    if resolved_value != field_value:
                        logger.debug(f"Resolved template in {field_path}: {field_value} → {resolved_value}")
                        setattr(config, field_name, resolved_value)
        elif isinstance(config, dict):
            # Process dictionary objects
            for key, value in list(config.items()):
                dict_path = f"{path}.{key}" if path else key
                if isinstance(value, str) and "${" in value:
                    resolved_value = self.resolve_template_string(value)
                    if resolved_value != value:
                        logger.debug(f"Resolved template in {dict_path}: {value} → {resolved_value}")
                        config[key] = resolved_value
                elif isinstance(value, (dict, list, BaseModel)):
                    self._resolve_all_template_variables(value, dict_path)
        elif isinstance(config, list):
            # Process list objects
            for i, item in enumerate(config):
                item_path = f"{path}[{i}]" if path else f"[{i}]"
                if isinstance(item, str) and "${" in item:
                    resolved_item = self.resolve_template_string(item)
                    if resolved_item != item:
                        logger.debug(f"Resolved template in {item_path}: {item} → {resolved_item}")
                        config[i] = resolved_item
                elif isinstance(item, (dict, list, BaseModel)):
                    self._resolve_all_template_variables(item, item_path)

    def get(self, key: str, resolve_templates: bool = False) -> Any:
        """
        [Function intent]
        Retrieves a configuration value using dot notation (e.g., 'database.type').
        Template variables are already resolved during initialization.
        
        [Implementation details]
        Uses direct attribute access on the Pydantic AppConfig model.
        Falls back to default configuration if not initialized.
        
        [Design principles]
        Type-safe configuration access with pre-resolved template variables.
        
        Args:
            key: The configuration key in dot notation.
            resolve_templates: Whether to resolve template variables in string values.
                              This parameter is maintained for backward compatibility,
                              but all templates are already resolved at initialization.

        Returns:
            The configuration value with template variables already resolved.
            
        Raises:
            ValueError: If the configuration key doesn't exist.
        """
        # Choose the right config object based on initialization state
        if not self.initialized_flag:
            config = AppConfig()  # Get defaults
        else:
            config = self._config
            
        # Navigate through the Pydantic model hierarchy
        parts = key.split('.')
        value = config
        
        try:
            for part in parts:
                value = getattr(value, part)
                
            # For backward compatibility, provide a path to still resolve templates
            # but this should not be needed as all templates are resolved at initialization
            if resolve_templates and isinstance(value, str) and "${" in value:
                logger.warning(f"Unresolved template variable found in config key {key}: {value}. "
                              "This may indicate an initialization issue or a circular template reference.")
                value = self.resolve_template_string(value)
                
            return value
        except AttributeError as e:
            # Create a more descriptive error message
            attempted_path = []
            current_value = config
            for part in parts:
                attempted_path.append(part)
                try:
                    current_value = getattr(current_value, part)
                except AttributeError:
                    path_so_far = ".".join(attempted_path[:-1])
                    if path_so_far:
                        error_message = f"Configuration key '{key}' not found. '{path_so_far}' exists but has no attribute '{part}'."
                    else:
                        error_message = f"Configuration key '{key}' not found in configuration."
                    
                    logger.error(error_message)
                    raise ValueError(error_message) from e
            
            # This should not be reached, but just in case
            logger.error(f"Configuration key '{key}' not found")
            raise ValueError(f"Configuration key '{key}' not found in configuration") from e
        except Exception as e:
            logger.error(f"Error retrieving configuration key '{key}': {e}", exc_info=True)
            raise ValueError(f"Error retrieving configuration key '{key}': {e}") from e
            
    def resolve_template_string(self, template_str: str, max_depth: int = 10) -> str:
        """
        Resolves a string containing template variables in the format ${key},
        where key is a configuration key in dot notation.
        
        Args:
            template_str: The string containing template variables.
            max_depth: Maximum recursion depth for nested templates.
            
        Returns:
            The resolved string with all template variables replaced with their values.
        """
        # If we've reached the maximum recursion depth, just return the string
        if max_depth <= 0:
            logger.warning(f"Maximum template resolution depth reached for: '{template_str}'")
            return template_str
            
        # Define regex pattern for ${key} syntax
        pattern = r'\${([^}]+)}'
        
        # Function to replace each match with its value
        def replace_var(match):
            key = match.group(1)  # Extract the key from ${key}
            try:
                value = self.get(key, resolve_templates=False)  # Get raw value without template resolution
            except ValueError:
                logger.warning(f"Template variable '${{{key}}}' not found in configuration")
                return f"${{{key}}}"  # Return the original template if not found
                
            # Convert non-string values to string
            if not isinstance(value, str):
                return str(value)
                
            return value
            
        # Replace all template variables
        result = re.sub(pattern, replace_var, template_str)
        
        # If the result still contains template variables and we haven't reached max depth,
        # recursively resolve any nested templates that were values of replaced variables
        if '${' in result and result != template_str and max_depth > 1:
            return self.resolve_template_string(result, max_depth - 1)
            
        return result

    def _set_config_attr_by_path(self, obj: Any, path: str, value: Any) -> bool:
        """
        [Function intent]
        Sets a nested attribute on a Pydantic model using dot notation path.
        
        [Implementation details]
        Navigates through the model hierarchy and sets the value on the target attribute.
        
        [Design principles]
        Type-safe configuration updates using direct attribute access.
        
        Args:
            obj: The object to set the attribute on (typically a Pydantic model)
            path: The path in dot notation
            value: The value to set
            
        Returns:
            bool: True if successful, False if attribute doesn't exist
        """
        parts = path.split('.')
        
        # Navigate to the parent object
        for part in parts[:-1]:
            try:
                obj = getattr(obj, part)
            except AttributeError:
                logger.error(f"Couldn't navigate to '{part}' in path '{path}'")
                raise
                
        # Set the value on the target attribute
        try:
            setattr(obj, parts[-1], value)
            return True
        except (AttributeError, ValidationError) as e:
            logger.warning(f"Failed to set attribute '{parts[-1]}' on path '{path}': {e}")
            return False

    def set(self, key: str, value: Any) -> bool:
        """
        [Function intent]
        Sets a configuration value at runtime using dot notation.
        
        [Implementation details]
        Uses direct attribute setting on the Pydantic AppConfig model
        with validation.
        
        [Design principles]
        Type-safe configuration updates with validation.
        
        Args:
            key: The configuration key in dot notation.
            value: The value to set.

        Returns:
            True if the value was set and validated successfully, False otherwise.
        """
        if not self.initialized_flag:
            logger.error("Cannot set configuration before initialization.")
            return False
            
        with self._lock:
            try:
                # Create a copy of the current config
                new_config = AppConfig(**self._config.dict())
                
                # Attempt to set the value on the copy
                if not self._set_config_attr_by_path(new_config, key, value):
                    return False
                    
                # If we got here without exceptions, the update is valid
                self._config = new_config
                # Update raw dict to keep it in sync
                self._raw_config_dict = new_config.dict()
                logger.info(f"Configuration value set and validated: {key} = {value}")
                return True
                
            except ValidationError as e:
                logger.error(f"Validation failed when setting '{key}' to '{value}'. Change reverted. Errors:\n{e}")
                # Revert is implicit as self._config was not updated
                return False
            except Exception as e:
                logger.error(f"Unexpected error setting configuration key '{key}': {e}", exc_info=True)
                return False

    def load_project_config(self, project_root: str, apply_hierarchy: bool = True):
        """
        Loads project-specific configuration from .dbp/config.{json,yaml,yml}
        within the given project root directory.

        Args:
            project_root: The root directory of the project.
            apply_hierarchy: If True, re-applies the full configuration hierarchy
                             after loading the project config. Set to False if called
                             during initial load sequence before other sources are ready.
        """
        logger.info(f"Attempting to load project-specific configuration from: {project_root}")
        project_config_dir = Path(project_root) / DEFAULT_PROJECT_CONFIG_DIR
        loaded = False

        if not project_config_dir.is_dir():
            logger.debug(f"Project config directory not found: {project_config_dir}")
            return # No project config dir, nothing to load

        with self._lock:
            for ext in ["json", "yaml", "yml"]:
                config_file = project_config_dir / f"config.{ext}"
                if config_file.exists() and config_file.is_file():
                    logger.debug(f"Found project config file: {config_file}")
                    self._load_and_store_config_file(config_file)
                    loaded = True
                    break # Load only the first one found (e.g., json over yaml)

            if loaded and apply_hierarchy:
                logger.debug("Re-applying configuration hierarchy after loading project config.")
                self._apply_configuration_hierarchy()
            elif not loaded:
                 logger.debug(f"No project configuration file found in {project_config_dir}")


    def as_dict(self) -> Dict[str, Any]:
        """Returns the current validated configuration as a dictionary."""
        if not self.initialized_flag:
             logger.warning("Configuration not initialized. Returning default dictionary.")
             return AppConfig().dict()
        return self._config.dict()

    def get_raw_merged_config(self) -> Dict[str, Any]:
         """Returns the raw merged configuration dictionary before Pydantic validation."""
         return self._raw_config_dict.copy()


    def get_typed_config(self) -> AppConfig:
        """
        [Function intent]
        Returns the strongly-typed configuration object for type-safe access.
        
        [Implementation details]
        Provides direct access to the underlying Pydantic AppConfig model.
        
        [Design principles]
        Type safety for configuration access.
        
        Returns:
            AppConfig: The validated configuration model
            
        Raises:
            RuntimeError: If configuration is not initialized
        """
        if not self.initialized_flag:
            # Create and return a default AppConfig when not initialized
            logger.debug("Getting default typed configuration as manager is not initialized")
            return AppConfig()
            
        return self._config

    def validate(self) -> List[str]:
        """Validates the current configuration state against the schema."""
        try:
            AppConfig(**self._config.dict())
            logger.info("Current configuration is valid.")
            return []
        except ValidationError as e:
            logger.warning("Current configuration is invalid: %s", e)
            # Pydantic errors() method provides detailed error info
            error_details = []
            for err in e.errors():
                loc = err.get('loc', 'unknown_location') # Use .get for safety
                msg = err.get('msg', 'unknown_error')   # Use .get for safety
                error_details.append(f"{loc}: {msg}")
            return error_details
        except Exception as e:
             logger.error(f"Unexpected error during validation: {e}", exc_info=True)
             return [f"Unexpected validation error: {e}"]


# Example usage (typically done once at application startup)
# config_manager = ConfigurationManager()
# config_manager.initialize(sys.argv[1:])
# db_type = config_manager.get('database.type')
