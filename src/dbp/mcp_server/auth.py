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
# Implements the AuthenticationProvider class for the MCP Server. This class
# handles the authentication of incoming MCP requests based on API keys defined
# in the server configuration and performs authorization checks based on the
# permissions associated with the authenticated client.
###############################################################################
# [Source file design principles]
# - Loads API keys and permissions from the MCPServerConfig.
# - Provides methods to authenticate a request (based on headers) and authorize
#   an action (based on resource and action strings).
# - Uses a dictionary for efficient API key lookup.
# - Implements basic wildcard permission checking (*).
# - Design Decision: API Key Authentication (2025-04-15)
#   * Rationale: Simple and common method for securing server-to-server APIs like MCP.
#   * Alternatives considered: OAuth (more complex), No auth (insecure).
# - Design Decision: String-Based Permissions (2025-04-15)
#   * Rationale: Flexible way to define access control (e.g., "tool:analyze", "resource:*").
#   * Alternatives considered: Role-based access (could be built on top).
###############################################################################
# [Source file constraints]
# - Depends on `MCPServerConfig` and `APIKeyEntry` from `config_schema.py`.
# - Depends on `MCPRequest` from `data_models.py`.
# - Security relies on keeping API keys confidential.
# - Assumes API keys are passed in a specific header (`X-API-Key`).
# - Permission matching logic is basic (exact match or wildcard).
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/SECURITY.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/config/config_schema.py (MCPServerConfig, APIKeyEntry)
# - src/dbp/mcp_server/data_models.py (MCPRequest)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T16:40:59Z : Updated auth to use centralized exceptions by CodeAssistant
# * Modified imports to use AuthenticationError and AuthorizationError from exceptions module
# * Removed local exception class definitions
# 2025-04-15T10:49:30Z : Initial creation of AuthenticationProvider by CodeAssistant
# * Implemented API key loading, authentication, and authorization logic.
###############################################################################

import logging
from typing import Dict, Optional, Any, List

# Assuming necessary imports
try:
    from ..config.config_schema import MCPServerConfig, APIKeyEntry
    from .data_models import MCPRequest
    from .exceptions import AuthenticationError, AuthorizationError
except ImportError as e:
    logging.getLogger(__name__).error(f"AuthenticationProvider ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    MCPServerConfig = object
    APIKeyEntry = object
    MCPRequest = object
    AuthenticationError = Exception
    AuthorizationError = Exception

logger = logging.getLogger(__name__)


class AuthenticationProvider:
    """
    Handles authentication and authorization for MCP requests based on API keys
    defined in the configuration.
    """

    def __init__(self, config: MCPServerConfig, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the AuthenticationProvider.

        Args:
            config: The MCPServerConfig object containing API key information.
            logger_override: Optional logger instance.
        """
        self.config = config or {} # Use empty dict if config is None
        self.logger = logger_override or logger
        # Stores API key -> {"client_id": str, "permissions": Set[str]}
        self._api_keys: Dict[str, Dict[str, Any]] = {}
        self._load_api_keys()
        self.logger.debug("AuthenticationProvider initialized.")

    def _load_api_keys(self):
        """Loads and processes API keys from the configuration."""
        api_key_entries = getattr(self.config, 'api_keys', [])
        if not isinstance(api_key_entries, list):
             self.logger.error("Configuration 'api_keys' is not a list. Cannot load keys.")
             return

        count = 0
        for entry in api_key_entries:
             # Check if entry looks like the expected Pydantic model or a dict
             key = getattr(entry, 'key', None)
             client_id = getattr(entry, 'client_id', None)
             permissions = getattr(entry, 'permissions', [])

             if not key or not client_id:
                  self.logger.warning(f"Skipping invalid API key entry in config: {entry}")
                  continue

             if key in self._api_keys:
                  self.logger.warning(f"Duplicate API key found in configuration: '{key}'. Overwriting previous entry.")

             # Store permissions as a set for efficient lookup
             self._api_keys[key] = {
                 "client_id": client_id,
                 "permissions": set(permissions) if isinstance(permissions, list) else set()
             }
             count += 1
        self.logger.info(f"Loaded {count} API keys from configuration.")

    def authenticate(self, request: MCPRequest) -> Optional[Dict[str, Any]]:
        """
        Authenticates an incoming MCP request using the 'X-API-Key' header.

        Args:
            request: The MCPRequest object.

        Returns:
            A dictionary containing authentication context (client_id, permissions)
            if successful, otherwise None.
        """
        if not getattr(self.config, 'auth_enabled', False):
            self.logger.debug("Authentication is disabled. Skipping check.")
            # Return a default context indicating no authentication? Or None?
            # Returning None might imply failure, let's return a default context.
            return {"client_id": "anonymous", "permissions": set(["*:*"])} # Grant all permissions if auth disabled

        api_key = request.headers.get("X-API-Key") # Case-insensitive header get? Depends on web framework. Assume exact match for now.
        # Alternative: Check common variations
        # api_key = request.headers.get("X-API-Key") or request.headers.get("x-api-key")

        if not api_key:
            self.logger.warning("Authentication failed: Missing 'X-API-Key' header.")
            return None

        key_info = self._api_keys.get(api_key)
        if not key_info:
            self.logger.warning(f"Authentication failed: Invalid API key provided (Key ending: ...{api_key[-4:] if len(api_key) > 4 else api_key}).")
            return None

        self.logger.info(f"Authentication successful for client: {key_info['client_id']}")
        # Return a copy to prevent modification
        return key_info.copy()

    def authorize(self, auth_context: Optional[Dict[str, Any]], resource_type: str, resource_name: str, action: str = "execute") -> bool:
        """
        Checks if the authenticated client has permission to perform an action
        on a specific resource or tool.

        Args:
            auth_context: The context returned by `authenticate`.
            resource_type: The type of resource ('tool' or 'resource').
            resource_name: The name of the tool or resource URI/prefix.
            action: The action being performed (e.g., 'execute', 'read', 'write'). Defaults to 'execute'.

        Returns:
            True if authorized, False otherwise.
        """
        if not getattr(self.config, 'auth_enabled', False):
            self.logger.debug("Authorization is disabled. Granting access.")
            return True # Grant access if auth is disabled

        if not auth_context:
            self.logger.warning("Authorization check failed: No authentication context provided.")
            return False

        client_id = auth_context.get("client_id", "unknown")
        permissions = auth_context.get("permissions", set())
        if not isinstance(permissions, set): # Ensure it's a set
             permissions = set(permissions)

        # Construct required permission strings to check
        required_permission = f"{resource_type}:{resource_name}:{action}"
        wildcard_action = f"{resource_type}:{resource_name}:*"
        wildcard_resource = f"{resource_type}:*:{action}" # Less common, but possible
        wildcard_resource_action = f"{resource_type}:*:*"
        global_permission = "*:*:*" # Super admin

        # Check permissions in order of specificity
        if required_permission in permissions:
            self.logger.debug(f"Authorization granted for '{client_id}' on '{required_permission}' (exact match).")
            return True
        if wildcard_action in permissions:
            self.logger.debug(f"Authorization granted for '{client_id}' on '{required_permission}' (wildcard action match: {wildcard_action}).")
            return True
        if wildcard_resource in permissions:
             self.logger.debug(f"Authorization granted for '{client_id}' on '{required_permission}' (wildcard resource match: {wildcard_resource}).")
             return True
        if wildcard_resource_action in permissions:
             self.logger.debug(f"Authorization granted for '{client_id}' on '{required_permission}' (wildcard resource type match: {wildcard_resource_action}).")
             return True
        if global_permission in permissions:
            self.logger.debug(f"Authorization granted for '{client_id}' on '{required_permission}' (global wildcard match: {global_permission}).")
            return True

        # If no matching permission found
        self.logger.warning(f"Authorization failed: Client '{client_id}' lacks permission for '{required_permission}'. Available: {permissions}")
        return False
