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
# [Reference documentation]
# - scratchpad/dbp_implementation_plan/plan_python_cli.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:57:10Z : Initial creation of CLI ConfigurationManager by CodeAssistant
# * Implemented config loading, merging, get/set, and saving logic.
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
    """Manages configuration settings for the DBP CLI."""

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
        self._config: Dict[str, Any] = copy.deepcopy(self.DEFAULT_CONFIG)
        self._load_configuration(config_file_override)
        self._load_env_variables()
        self._expand_paths() # Expand paths like cache_dir after loading
        logger.debug("CLI ConfigurationManager initialized.")

    def _load_configuration(self, config_file_override: Optional[str] = None):
        """Loads configuration from default files and optional override file."""
        # Load from user config first
        self.load_from_file(DEFAULT_USER_CONFIG_FILE)
        # Load from local config (overrides user config)
        self.load_from_file(DEFAULT_LOCAL_CONFIG_FILE)
        # Load from override file (overrides all others)
        if config_file_override:
            self.load_from_file(Path(config_file_override))

    def load_from_file(self, file_path: Path):
        """Loads configuration from a specific JSON file."""
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
        """Loads configuration overrides from environment variables (DBP_CLI_...)."""
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
         """Expands user directory symbols (~) in configured paths."""
         cache_dir = self.get("cli.cache_dir")
         if cache_dir and isinstance(cache_dir, str):
              self.set("cli.cache_dir", str(Path(cache_dir).expanduser()))


    def _deep_update(self, target: Dict, source: Dict):
        """Recursively updates nested dictionaries."""
        for key, value in source.items():
            if isinstance(value, dict) and key in target and isinstance(target[key], dict):
                self._deep_update(target[key], value)
            elif value is not None: # Avoid overwriting with None from partial configs
                target[key] = value

    def save_to_user_config(self):
        """Saves the current configuration to the user's default config file."""
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
        Retrieves a configuration value using dot notation (e.g., 'mcp_server.url').

        Args:
            key_path: The dot-separated key path.
            default: The default value to return if the key is not found.

        Returns:
            The configuration value or the default.
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

    def set(self, key_path: str, value: Any):
        """
        Sets a configuration value using dot notation. This modifies the in-memory
        configuration. Call `save_to_user_config()` to persist changes.

        Args:
            key_path: The dot-separated key path.
            value: The value to set.

        Raises:
            ConfigurationError: If the key path is invalid.
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
            if 'dir' in key_path or 'file' in key_path:
                 self._expand_paths()
        except Exception as e:
            self.logger.error(f"Error setting config key '{key_path}': {e}", exc_info=True)
            raise ConfigurationError(f"Failed to set configuration key '{key_path}': {e}") from e

    def reset(self, key_path: Optional[str] = None):
        """Resets configuration to default values."""
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
         """Returns a copy of the current configuration dictionary."""
         return copy.deepcopy(self._config)
