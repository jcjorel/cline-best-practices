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
# 2025-04-16T16:20:07Z : Added missing BaseModel import by CodeAssistant
# * Fixed NameError in get() method by adding missing import from pydantic
# 2025-04-15T09:36:15Z : Initial creation of ConfigurationManager class by CodeAssistant
# * Implemented singleton structure, loading logic for files/env/cli, merging, and access methods.
###############################################################################

import os
import json
import yaml # Requires PyYAML
import logging
import argparse
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import threading

from pydantic import BaseModel, ValidationError

# Assuming config_schema.py is in the same directory or accessible
try:
    from .config_schema import AppConfig
except ImportError:
    from config_schema import AppConfig


logger = logging.getLogger(__name__)

# Define default config paths relative to standard locations
DEFAULT_SYSTEM_CONFIG_DIR = Path("/etc/dbp")
DEFAULT_USER_CONFIG_DIR = Path.home() / ".config" / "dbp"
DEFAULT_PROJECT_CONFIG_DIR = Path(".dbp") # Relative to project root

class ConfigurationManager:
    """
    Manages loading, validation, and access to application configuration
    using a singleton pattern and layered approach.
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


    def _apply_configuration_hierarchy(self):
        """
        Merges configurations from all sources (files, env, cli) onto defaults
        and validates the final configuration using the Pydantic schema.
        Priority: CLI > Env Vars > Project Config > User Config > System Config > Defaults
        """
        logger.debug("Applying configuration hierarchy...")
        # Start with an empty dict, defaults are handled by AppConfig model
        merged_config_dict = {}

        # Order of loading matters for precedence (later overrides earlier)
        # 1. Standard Config Files (System -> User)
        # Sort file paths to ensure consistent loading order (e.g., system before user)
        sorted_file_paths = sorted(self._config_files_data.keys())
        for file_path in sorted_file_paths:
             # Ensure project config is applied after user/system if it exists
             # This logic assumes project config path is distinct and loaded correctly
             # A more robust way might involve tagging config sources.
             is_project_config = ".dbp" in file_path # Heuristic check
             if not is_project_config:
                 logger.debug(f"Merging config from standard file: {file_path}")
                 self._merge_dict(merged_config_dict, self._config_files_data[file_path])

        # 2. Project Config File (if loaded)
        project_config_path_str = next((p for p in self._config_files_data if ".dbp" in p), None)
        if project_config_path_str:
             logger.debug(f"Merging config from project file: {project_config_path_str}")
             self._merge_dict(merged_config_dict, self._config_files_data[project_config_path_str])


        # 3. Environment Variables
        if self._env_vars:
            logger.debug("Merging config from environment variables...")
            env_dict = self._nested_dict_from_keys(self._env_vars)
            self._merge_dict(merged_config_dict, env_dict)

        # 4. Command-Line Arguments
        if self._cli_args:
            logger.debug("Merging config from command-line arguments...")
            cli_dict = self._nested_dict_from_keys(self._cli_args)
            self._merge_dict(merged_config_dict, cli_dict)

        # Store the raw merged dictionary
        self._raw_config_dict = merged_config_dict

        # Validate the final merged dictionary against the Pydantic model
        try:
            # Pass the merged dict to AppConfig for validation and default filling
            self._config = AppConfig(**self._raw_config_dict)
            logger.debug("Configuration validated successfully against schema.")
        except ValidationError as e:
            logger.error(f"Configuration validation failed. Using default values. Errors:\n{e}")
            # Fallback to default configuration on validation error
            self._config = AppConfig()
            # Optionally raise the error or handle it differently
            # raise e

    def _nested_dict_from_keys(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Converts a flat dictionary with dot-notation keys to a nested dictionary."""
        nested = {}
        for key, value in flat_dict.items():
            parts = key.split('.')
            d = nested
            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # Convert value type before assignment
                    d[part] = self._convert_value(value)
                else:
                    d = d.setdefault(part, {})
                    if not isinstance(d, dict):
                         logger.warning(f"Configuration key conflict: '{'.'.join(parts[:i+1])}' is both a value and a section.")
                         # Overwrite non-dict intermediate with a dict to proceed
                         d = {}
                         # Need to re-attach d to its parent if overwritten
                         parent_d = nested
                         for p in parts[:i]:
                             parent_d = parent_d[p]
                         parent_d[part] = d

        return nested

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


    def _merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]):
        """Recursively merges source dict into target dict (source values overwrite target)."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            elif value is not None: # Avoid merging None values unless explicitly intended
                target[key] = value

    def get(self, key: str, default: Any = None) -> Any:
        """
        Retrieves a configuration value using dot notation (e.g., 'database.type').

        Args:
            key: The configuration key in dot notation.
            default: The value to return if the key is not found.

        Returns:
            The configuration value or the default.
        """
        if not self.initialized_flag:
             logger.warning("Accessing configuration before initialization. Returning default.")
             # Fallback to trying to access default AppConfig if not initialized
             try:
                 parts = key.split('.')
                 value = AppConfig() # Get defaults
                 for part in parts:
                     value = getattr(value, part)
                 return value
             except (AttributeError, KeyError):
                 return default


        try:
            parts = key.split('.')
            value = self._config
            for part in parts:
                # Check if the current value is a Pydantic model before getattr
                if isinstance(value, BaseModel):
                    value = getattr(value, part)
                # Handle cases where part of the path might be a dict (less common with Pydantic)
                elif isinstance(value, dict):
                     value = value[part]
                else:
                     # If it's neither a model nor a dict, we can't go deeper
                     raise AttributeError(f"Cannot access part '{part}' in non-model/dict value")
            return value
        except (AttributeError, KeyError, IndexError):
            logger.debug(f"Configuration key '{key}' not found, returning default.")
            return default
        except Exception as e:
            logger.error(f"Error retrieving configuration key '{key}': {e}", exc_info=True)
            return default

    def set(self, key: str, value: Any) -> bool:
        """
        Sets a configuration value at runtime using dot notation.
        The configuration is re-validated after setting. If validation fails,
        the change is reverted.

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
            original_config_dict = self._config.dict() # Keep backup
            temp_config_dict = self._config.dict() # Work on a copy

            try:
                parts = key.split('.')
                d = temp_config_dict
                for part in parts[:-1]:
                    d = d.setdefault(part, {})
                d[parts[-1]] = value # Set the new value

                # Attempt to validate the modified configuration
                AppConfig(**temp_config_dict)

                # If validation succeeds, update the main config object
                self._config = AppConfig(**temp_config_dict)
                # Also update the raw dict representation if needed for consistency
                self._raw_config_dict = temp_config_dict
                logger.info(f"Configuration value set and validated: {key} = {value}")
                return True

            except ValidationError as e:
                logger.error(f"Validation failed when setting '{key}' to '{value}'. Change reverted. Errors:\n{e}")
                # Revert is implicit as self._config was not updated
                return False
            except (TypeError, KeyError) as e:
                 logger.error(f"Error navigating configuration structure to set key '{key}': {e}")
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
