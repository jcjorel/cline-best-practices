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
# Implements the ConfigurationManager for the DBP CLI application. This class
# handles loading, merging, accessing, and saving configuration settings specific
# to the CLI, such as server URL, API key, output preferences, etc., from various
# sources (defaults, files, environment variables).
###############################################################################
# [Source file design principles]
# - Provides a centralized point for managing CLI configuration.
# - Defines default configuration values.
# - Loads configuration from standard locations (~/.dbp/, ./.dbp.json).
# - Allows overriding settings via environment variables (DBP_CLI_...).
# - Supports saving configuration changes (e.g., setting API key).
# - Uses deep merging to combine configuration sources.
# - Design Decision: Simple Dictionary-Based Config (2025-04-15)
#   * Rationale: Sufficient for managing the relatively simple configuration needs of the CLI client.
#   * Alternatives considered: Pydantic (potentially overkill for client-side config), ConfigParser (less flexible for nested structures).
###############################################################################
# [Source file constraints]
# - Depends on `json` library.
# - File loading/saving depends on filesystem permissions.
# - Environment variable names follow a specific prefix (DBP_CLI_).
###############################################################################
# [Dependencies]
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:57:10Z : Initial creation of CLI ConfigurationManager by CodeAssistant
# * Implemented config loading, merging, get/set, and saving logic.
# 2025-04-15T14:13:00Z : Added logger instance initialization by CodeAssistant
# * Fixed 'ConfigurationManager' object has no attribute 'logger' error
# 2025-04-15T14:15:00Z : Fixed infinite recursion in path expansion by CodeAssistant
# * Modified _expand_paths to directly update config dictionary instead of using self.set()
# 2025-04-15T14:16:30Z : Enhanced set method to prevent recursion by CodeAssistant
# * Added skip_path_expansion parameter to safely control path expansion behavior
###############################################################################

import os
import json
import logging
import copy
from pathlib import Path
from typing import Dict, Any, Optional

# Assuming exceptions are defined
try:
    from .exceptions import ConfigurationError
except ImportError:
    logging.getLogger(__name__).error("Failed to import CLI exceptions.")
    ConfigurationError = Exception # Placeholder

logger = logging.getLogger(__name__)

# Define default config paths
DEFAULT_USER_CONFIG_FILE = Path.home() / ".dbp" / "cli_config.json"
DEFAULT_LOCAL_CONFIG_FILE = Path(".dbp.cli.json") # Config in current directory

class ConfigurationManager:
    """
    [Class intent]
    Manages configuration settings for the DBP CLI, providing a central repository
    for accessing, modifying, and persisting configuration values across various
    sources with defined precedence.
    
    [Implementation details]
    Implements a hierarchical configuration system that loads settings from multiple
    sources (defaults, user config file, local config file, environment variables)
    with clear precedence rules. Uses a nested dictionary structure for configuration 
    storage with dot notation access. Handles path expansion, type conversion, 
    and deep merging of configuration sources.
    
    [Design principles]
    Layered configuration - loads from multiple sources with defined precedence.
    Dot notation access - provides intuitive key.subkey.value access pattern.
    Defensive coding - handles missing values and type conversions gracefully.
    Path aware - automatically expands user paths in directory/file settings.
    Persistence - supports saving modified configuration to disk.
    """

    DEFAULT_CONFIG = {
        "mcp_server": {
            "url": "http://localhost:6231", # Default MCP port
            "api_key": None,
            "timeout": 30 # Default request timeout in seconds
        },
        "cli": {
            "output_format": "text", # text, json, markdown, html
            "color": True,
            "progress_bar": True,
            "cache_dir": "~/.dbp/cli_cache" # Cache dir for CLI specific data
        },
        "analysis": { # Default parameters for analysis commands
            "default_severity": "all",
            "default_limit": 10,
            "show_code_snippets": False, # Default to false for brevity
            "show_doc_snippets": False
        }
        # Add other sections as needed
    }

    def __init__(self, config_file_override: Optional[str] = None):
        """
        Initializes the ConfigurationManager.

        Args:
            config_file_override: Optional path to a specific config file to load last.
        """
        self.logger = logger  # Initialize instance logger
        self._config: Dict[str, Any] = copy.deepcopy(self.DEFAULT_CONFIG)
        self._load_configuration(config_file_override)
        self._load_env_variables()
        self._expand_paths() # Expand paths like cache_dir after loading
        logger.debug("CLI ConfigurationManager initialized.")

    def _load_configuration(self, config_file_override: Optional[str] = None):
        """
        [Function intent]
        Load configuration settings from multiple sources in priority order.
        
        [Implementation details]
        Loads configuration from three potential sources in order of increasing priority:
        1. User config file (~/.dbp/cli_config.json)
        2. Local config file (.dbp.cli.json in current directory)
        3. Optional override file specified by parameter
        Each source overwrites any values from previous sources.
        
        [Design principles]
        Layered configuration - multiple sources with well-defined priority.
        Progressive overrides - later sources override earlier ones.
        Flexible configuration - supports multiple locations and override option.
        
        Args:
            config_file_override: Optional path to a specific config file to load last
        """
        # Load from user config first
        self.load_from_file(DEFAULT_USER_CONFIG_FILE)
        # Load from local config (overrides user config)
        self.load_from_file(DEFAULT_LOCAL_CONFIG_FILE)
        # Load from override file (overrides all others)
        if config_file_override:
            self.load_from_file(Path(config_file_override))

    def load_from_file(self, file_path: Path):
        """
        [Function intent]
        Load configuration settings from a specified JSON file.
        
        [Implementation details]
        Expands user directory symbols in the path.
        Checks if the file exists before attempting to read it.
        Reads and parses the JSON content, then merges it with the current configuration.
        Handles empty files, JSON parsing errors, and other exceptions gracefully.
        Logs success or failure at appropriate log levels.
        
        [Design principles]
        Robust error handling - catches and logs all potential errors.
        Non-blocking - continues execution even if file loading fails.
        Defensive coding - checks file existence and content before processing.
        
        Args:
            file_path: Path to the configuration file to load
        """
        path = file_path.expanduser()
        if path.is_file():
            self.logger.debug(f"Attempting to load configuration from: {path}")
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.strip():
                        config_data = json.loads(content)
                        self._deep_update(self._config, config_data)
                        self.logger.info(f"Loaded configuration from: {path}")
                    else:
                         self.logger.debug(f"Configuration file is empty: {path}")
            except json.JSONDecodeError as e:
                self.logger.warning(f"Error decoding JSON from config file {path}: {e}")
            except Exception as e:
                self.logger.warning(f"Error loading configuration from {path}: {e}", exc_info=True)
        else:
             self.logger.debug(f"Configuration file not found: {path}")

    def _load_env_variables(self):
        """
        [Function intent]
        Load configuration settings from environment variables with the DBP_CLI_ prefix.
        
        [Implementation details]
        Scans all environment variables for those starting with DBP_CLI_.
        Converts variable names from uppercase with underscores to lowercase with dots.
        Maps values to appropriate types (boolean, integer, float, or string).
        Builds a nested dictionary structure matching the configuration hierarchy.
        Merges environment-based configuration with the existing configuration.
        
        [Design principles]
        Convention-based naming - uses standard prefix for all related variables.
        Automatic type conversion - intelligently converts string values to appropriate types.
        Hierarchical mapping - converts flat env vars to nested configuration structure.
        """
        self.logger.debug("Loading configuration from environment variables...")
        prefix = "DBP_CLI_"
        env_config = {}
        count = 0
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert DBP_CLI_MCP_SERVER_URL to mcp_server.url
                config_key = key[len(prefix):].lower().replace('_', '.')
                # Build nested dict structure
                parts = config_key.split('.')
                d = env_config
                for i, part in enumerate(parts):
                     if i == len(parts) - 1:
                          # Basic type conversion attempt
                          if value.lower() in ['true', 'yes', '1']: d[part] = True
                          elif value.lower() in ['false', 'no', '0']: d[part] = False
                          else:
                               try: d[part] = int(value)
                               except ValueError:
                                    try: d[part] = float(value)
                                    except ValueError: d[part] = value # Keep as string
                     else:
                          d = d.setdefault(part, {})
                count += 1
        if count > 0:
             self.logger.info(f"Loaded {count} configuration values from environment variables.")
             self._deep_update(self._config, env_config)


    def _expand_paths(self):
         """
        [Function intent]
        Expand user directory symbols (~) in path-related configuration values.
        
        [Implementation details]
        Identifies path-related configuration values (containing 'dir' or 'file').
        Expands user directory symbols using Path.expanduser().
        Updates configuration values directly to avoid recursion issues.
        
        [Design principles]
        User convenience - allows use of ~ shorthand in configuration paths.
        Platform independence - works across different operating systems.
        Recursion avoidance - directly updates dictionary to prevent infinite recursion.
        """
         cache_dir = self.get("cli.cache_dir")
         if cache_dir and isinstance(cache_dir, str):
              # Directly update the config dictionary to avoid infinite recursion
              # that would occur when using self.set() which calls _expand_paths again
              parts = "cli.cache_dir".split('.')
              d = self._config
              for part in parts[:-1]:
                  d = d.setdefault(part, {})
              d[parts[-1]] = str(Path(cache_dir).expanduser())


    def _deep_update(self, target: Dict, source: Dict):
        """
        [Function intent]
        Recursively merge two nested dictionaries, updating the target with values from source.
        
        [Implementation details]
        For each key in the source dictionary:
        - If the key exists in target and both values are dictionaries, recurse into them.
        - Otherwise, update the target value with the source value unless it's None.
        This preserves nested structures rather than overwriting entire branches.
        
        [Design principles]
        Deep merge - preserves nested structure instead of shallow overwrites.
        Null protection - avoids overwriting existing values with None.
        Recursive pattern - handles arbitrary nesting depth.
        
        Args:
            target: Dictionary to update (modified in-place)
            source: Dictionary containing values to update with
        """
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            elif value is not None: # Avoid overwriting with None from partial configs
                target[key] = value

    def save_to_user_config(self):
        """
        [Function intent]
        Save the current configuration to the user's default configuration file.
        
        [Implementation details]
        Creates the parent directory if it doesn't exist.
        Serializes the configuration dictionary to JSON with indentation and sorted keys.
        Handles file writing errors by logging and raising a ConfigurationError.
        
        [Design principles]
        Error transparency - propagates file writing errors with appropriate context.
        Maintainable format - uses indentation and sorted keys for readable JSON.
        Directory creation - ensures parent directory exists before writing file.
        
        Raises:
            ConfigurationError: If the configuration cannot be saved
        """
        path = DEFAULT_USER_CONFIG_FILE.expanduser()
        self.logger.info(f"Saving configuration to user file: {path}")
        try:
            path.parent.mkdir(parents=True, exist_ok=True) # Ensure directory exists
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, sort_keys=True)
            self.logger.debug("Configuration saved successfully.")
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {path}: {e}", exc_info=True)
            raise ConfigurationError(f"Failed to save configuration: {e}") from e

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        [Function intent]
        Retrieve a configuration value using dot notation path.
        
        [Implementation details]
        Splits the key path by dots to navigate through nested dictionaries.
        Traverses the configuration dictionary following the path components.
        Returns the default value if any part of the path doesn't exist or isn't a dictionary.
        Catches and logs any unexpected errors during retrieval.
        
        [Design principles]
        Dot notation - provides intuitive access to nested configuration values.
        Safe navigation - returns default value when path doesn't exist instead of raising error.
        Defensive coding - handles edge cases and unexpected errors gracefully.
        
        Args:
            key_path: The dot-separated key path (e.g., 'mcp_server.url')
            default: The default value to return if the key is not found

        Returns:
            The configuration value or the default
        """
        try:
            parts = key_path.split('.')
            value = self._config
            for part in parts:
                if isinstance(value, dict):
                    value = value[part]
                else:
                    # Cannot traverse further
                    return default
            return value
        except KeyError:
            return default
        except Exception as e:
             self.logger.warning(f"Error accessing config key '{key_path}': {e}")
             return default

    def set(self, key_path: str, value: Any, skip_path_expansion: bool = False):
        """
        [Function intent]
        Set a configuration value using dot notation path.
        
        [Implementation details]
        Splits the key path by dots to navigate through nested dictionaries.
        Creates intermediate dictionaries if they don't exist.
        Sets the value at the final path component and logs the change.
        Optionally re-expands paths after setting if a path-related value was changed.
        
        [Design principles]
        Auto-creation - creates intermediate dictionaries as needed.
        Dot notation - provides intuitive access to nested configuration values.
        Path awareness - automatically handles path expansion for file/directory settings.
        Change logging - logs configuration changes for debugging and auditing.
        
        Args:
            key_path: The dot-separated key path (e.g., 'mcp_server.url')
            value: The value to set
            skip_path_expansion: If True, skips path expansion to avoid recursion
            
        Raises:
            ConfigurationError: If the key path is invalid (intermediate key is not a dictionary)
        """
        try:
            parts = key_path.split('.')
            d = self._config
            for part in parts[:-1]:
                # Create nested dicts if they don't exist
                d = d.setdefault(part, {})
                if not isinstance(d, dict):
                     raise ConfigurationError(f"Cannot set key '{key_path}': intermediate key '{part}' is not a dictionary.")
            d[parts[-1]] = value
            self.logger.debug(f"Configuration value set in memory: {key_path} = {value}")
            # Re-expand paths if a path value was changed
            if not skip_path_expansion and ('dir' in key_path or 'file' in key_path):
                 self._expand_paths()
        except Exception as e:
            self.logger.error(f"Error setting config key '{key_path}': {e}", exc_info=True)
            raise ConfigurationError(f"Failed to set configuration key '{key_path}': {e}") from e

    def reset(self, key_path: Optional[str] = None):
        """
        [Function intent]
        Reset configuration to default values, either entirely or for a specific path.
        
        [Implementation details]
        If no key path is provided, resets entire configuration to defaults.
        If a key path is provided, finds the default value for that path and sets it.
        Expands paths after reset to ensure path values are properly expanded.
        Handles missing keys in default configuration gracefully.
        
        [Design principles]
        Targeted reset - allows resetting specific settings without affecting others.
        Complete reset - supports full configuration reset to factory defaults.
        Safe defaults - uses deep copy to prevent default values from being modified.
        
        Args:
            key_path: Optional dot-separated key path to reset (resets all if None)
        """
        if key_path is None:
            self._config = copy.deepcopy(self.DEFAULT_CONFIG)
            self._expand_paths()
            self.logger.info("Reset all configuration to defaults.")
        else:
            # Find default value
            try:
                 parts = key_path.split('.')
                 default_value = self.DEFAULT_CONFIG
                 for part in parts:
                      default_value = default_value[part]
                 # Set specific key back to default
                 self.set(key_path, copy.deepcopy(default_value))
                 self.logger.info(f"Reset configuration key '{key_path}' to default.")
            except KeyError:
                 self.logger.warning(f"Cannot reset key '{key_path}': key not found in default configuration.")
            except Exception as e:
                 self.logger.error(f"Error resetting key '{key_path}': {e}")


    def get_config_dict(self) -> Dict[str, Any]:
         """
        [Function intent]
        Provide a complete copy of the current configuration dictionary.
        
        [Implementation details]
        Creates a deep copy of the internal configuration dictionary.
        Returns the copy to prevent direct modification of internal state.
        
        [Design principles]
        Encapsulation - prevents direct access to internal configuration state.
        Defensive copying - returns a deep copy to prevent indirect modification.
        
        Returns:
            A deep copy of the current configuration dictionary
        """
         return copy.deepcopy(self._config)
