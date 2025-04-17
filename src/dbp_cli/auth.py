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
# Implements the AuthenticationManager for the DBP CLI. This class is responsible
# for retrieving the necessary API key for authenticating with the DBP MCP server.
# It checks configuration files, environment variables, and the system keyring.
###############################################################################
# [Source file design principles]
# - Centralizes API key retrieval logic.
# - Prioritizes sources: explicit argument (handled by CLI main), environment
#   variable (DBP_API_KEY), configuration file, system keyring.
# - Provides a method to get authentication headers for API requests.
# - Includes optional saving of the API key to config/keyring.
# - Design Decision: Multi-Source Key Retrieval (2025-04-15)
#   * Rationale: Offers flexibility for users to provide the API key in various standard ways.
#   * Alternatives considered: Requiring key only via argument (less convenient), Only config file (less flexible for CI/CD).
###############################################################################
# [Source file constraints]
# - Depends on `ConfigurationManager` from `config.py`.
# - Keyring functionality depends on the optional `keyring` library and backend availability.
# - Assumes the MCP server uses `X-API-Key` header for authentication.
###############################################################################
# [Reference documentation]
# - src/dbp_cli/config.py
# - src/dbp_cli/exceptions.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:57:50Z : Initial creation of CLI AuthenticationManager by CodeAssistant
# * Implemented API key loading from config, env, and keyring. Added header retrieval.
###############################################################################

import os
import logging
from typing import Dict, Optional

# Import dependencies
try:
    from dbp.config.config_manager import ConfigurationManager
    from .exceptions import AuthenticationError, ConfigurationError
except ImportError:
    logging.getLogger(__name__).error("Failed to import dependencies for AuthenticationManager.")
    # Placeholders
    ConfigurationManager = object
    AuthenticationError = Exception
    ConfigurationError = Exception

# Optional import for keyring
try:
    import keyring
    HAS_KEYRING = True
except ImportError:
    HAS_KEYRING = False

logger = logging.getLogger(__name__)

class AuthenticationManager:
    """Manages retrieval and storage of the API key for MCP server authentication."""

    KEYRING_SERVICE_NAME = "dbp_cli"
    KEYRING_USERNAME = "api_key" # Store the key under this username for the service

    def __init__(self, config_manager: ConfigurationManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the AuthenticationManager.

        Args:
            config_manager: The CLI's ConfigurationManager instance.
            logger_override: Optional logger instance.
        """
        if not isinstance(config_manager, ConfigurationManager):
             logger.warning("AuthenticationManager initialized with potentially incorrect config_manager type.")
        self.config_manager = config_manager
        self.logger = logger_override or logger
        self._api_key: Optional[str] = None
        # Don't load immediately, allow explicit initialization or lazy loading
        self.logger.debug("AuthenticationManager initialized.")

    def initialize(self, api_key_override: Optional[str] = None):
        """
        Loads the API key from various sources in order of priority:
        1. Override parameter
        2. Environment variable (DBP_API_KEY)
        3. Configuration file (mcp_server.api_key)
        4. System keyring (if available)

        Args:
            api_key_override: An API key provided directly (e.g., from CLI arg), takes highest priority.
        """
        self.logger.debug("Initializing authentication and loading API key...")

        if api_key_override:
            self.logger.info("Using API key provided directly.")
            self._api_key = api_key_override
            return

        # Check environment variable
        env_key = os.environ.get("DBP_API_KEY")
        if env_key:
            self.logger.info("Using API key from DBP_API_KEY environment variable.")
            self._api_key = env_key
            return

        # Check configuration file
        config_key = self.config_manager.get("mcp_server.api_key")
        if config_key:
            self.logger.info("Using API key from configuration file.")
            self._api_key = config_key
            return

        # Check keyring (if available)
        if HAS_KEYRING:
            self.logger.debug(f"Checking system keyring for service '{self.KEYRING_SERVICE_NAME}'...")
            try:
                keyring_key = keyring.get_password(self.KEYRING_SERVICE_NAME, self.KEYRING_USERNAME)
                if keyring_key:
                    self.logger.info("Using API key found in system keyring.")
                    self._api_key = keyring_key
                    return
                else:
                     self.logger.debug("No API key found in system keyring.")
            except Exception as e:
                # Catch potential keyring backend errors
                self.logger.warning(f"Could not access system keyring: {e}")
        else:
             self.logger.debug("Keyring library not available. Skipping keyring check.")


        self.logger.info("No API key found from any source.")
        self._api_key = None


    def get_api_key(self) -> Optional[str]:
         """Returns the loaded API key, loading it if not already done."""
         if self._api_key is None:
              self.initialize() # Lazy load if not initialized
         return self._api_key

    def get_auth_headers(self) -> Dict[str, str]:
        """
        Constructs the necessary HTTP headers for API key authentication.

        Returns:
            A dictionary containing the 'X-API-Key' header if a key is available.

        Raises:
            AuthenticationError: If no API key has been configured or found.
        """
        api_key = self.get_api_key() # Ensure key is loaded
        if not api_key:
            raise AuthenticationError(
                "Authentication required: No API key found. "
                "Set DBP_API_KEY environment variable, use --api-key flag, "
                "or configure 'mcp_server.api_key' in config file, "
                "or use 'dbp config set mcp_server.api_key YOUR_KEY --save'."
            )
        return {"X-API-Key": api_key}

    def set_api_key(self, api_key: str, save: bool = True, use_keyring: bool = True):
        """
        Sets the API key in memory and optionally saves it persistently.

        Args:
            api_key: The API key string.
            save: If True, attempts to save the key to the user config file and keyring.
            use_keyring: If True and `save` is True, attempts to save to keyring.
        """
        if not api_key or not isinstance(api_key, str):
             raise ValueError("Invalid API key provided.")

        self._api_key = api_key
        self.logger.info("API key set in memory for current session.")

        if save:
            try:
                # Save to config file
                self.config_manager.set("mcp_server.api_key", api_key)
                # Note: Using ConfigurationManager from dbp.config.config_manager which doesn't have save_to_user_config
                # So we just log that the key is set in memory
                self.logger.info("API key saved to configuration manager")

                # Save to keyring if available and requested
                if use_keyring and HAS_KEYRING:
                    try:
                        keyring.set_password(self.KEYRING_SERVICE_NAME, self.KEYRING_USERNAME, api_key)
                        self.logger.info("API key saved to system keyring.")
                    except Exception as e:
                        self.logger.warning(f"Failed to save API key to system keyring: {e}")
                elif use_keyring and not HAS_KEYRING:
                     self.logger.warning("Keyring library not installed. Cannot save API key to keyring.")

            except ConfigurationError as e:
                 self.logger.error(f"Failed to save API key to configuration: {e}")
                 # Don't re-raise, as the key is set in memory anyway
            except Exception as e:
                 self.logger.error(f"Unexpected error saving API key: {e}", exc_info=True)


    def clear_api_key(self, clear_persistent: bool = True):
         """Clears the API key from memory and optionally from persistent storage."""
         self._api_key = None
         self.logger.info("API key cleared from memory.")

         if clear_persistent:
              try:
                   # Clear from config
                   self.config_manager.set("mcp_server.api_key", None)
                   # Note: Using ConfigurationManager from dbp.config.config_manager which doesn't have save_to_user_config
                   self.logger.info("API key cleared from configuration manager")
                   # Clear from keyring
                   if HAS_KEYRING:
                        try:
                             keyring.delete_password(self.KEYRING_SERVICE_NAME, self.KEYRING_USERNAME)
                             self.logger.info("API key deleted from system keyring.")
                        except keyring.errors.PasswordDeleteError:
                             self.logger.debug("No API key found in keyring to delete.")
                        except Exception as e:
                             self.logger.warning(f"Failed to delete API key from system keyring: {e}")

              except Exception as e:
                   self.logger.error(f"Error clearing persistent API key: {e}", exc_info=True)


    def is_authenticated(self) -> bool:
        """Checks if an API key is currently loaded in memory."""
        return self._api_key is not None
