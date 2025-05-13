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
# Implements the MCPClientAPI class, which acts as the client-side interface
# for communicating with the DBP MCP server. It handles constructing HTTP requests
# based on MCP tool/resource calls, sending them to the configured server URL,
# handling authentication headers, and processing the MCP responses (including errors).
###############################################################################
# [Source file design principles]
# - Abstracts HTTP request/response logic for MCP communication.
# - Uses the `requests` library for making HTTP calls.
# - Integrates with `AuthenticationManager` to get necessary auth headers.
# - Provides specific methods for common DBP operations (analyze, recommend, etc.),
#   which map to corresponding MCP tool/resource calls.
# - Handles common HTTP errors and MCP-specific errors returned by the server.
# - Includes configurable timeout for requests.
# - Design Decision: Dedicated API Client Class (2025-04-15)
#   * Rationale: Encapsulates all server communication logic, making command handlers cleaner and simplifying testing of API interactions.
#   * Alternatives considered: Making HTTP requests directly in command handlers (less reusable, mixes concerns).
###############################################################################
# [Source file constraints]
# - Requires the `requests` library (`pip install requests`).
# - Depends on `AuthenticationManager` for auth headers.
# - Depends on `ConfigurationManager` for server URL and timeout.
# - Relies on the MCP server adhering to the expected request/response formats.
# - Error handling maps HTTP/MCP errors to CLI-specific exceptions.
###############################################################################
# [Dependencies]
# other:- src/dbp_cli/auth.py
# other:- src/dbp_cli/config.py
# other:- src/dbp_cli/exceptions.py
# system:- src/dbp/mcp_server/data_models.py (MCPRequest/Response/Error structure)
###############################################################################
# [GenAI tool change history]
# 2025-05-12T19:33:00Z : Completely redesigned error handling in get_server_status() by CodeAssistant
# * Implemented separate debug logging system to completely suppress stacktraces
# * Created a robust nested exception handling structure to prevent any exceptions from propagating
# * Added fallback handlers to ensure a clean, user-friendly response in all error scenarios
# * Enhanced diagnostics while maintaining clean client output
# 2025-05-02T00:40:26Z : Deprecated analyze_consistency method by CodeAssistant
# * Made the method return a deprecation error since the consistency_analysis component has been removed
# 2025-04-26T11:22:00Z : Fixed health endpoint response handling by CodeAssistant
# * Modified get_server_status() to make direct request to health endpoint
# * Fixed issue where health endpoint response was empty (returning only {})
# * Bypassed the _make_request() result extraction to get full health data
# * Ensured complete health endpoint JSON is returned for server status display
###############################################################################

import logging
import json
import uuid
from typing import Dict, Any, Optional, List

# Try importing requests, handle if missing
try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logging.getLogger(__name__).error("The 'requests' library is required for MCPClientAPI. Please install it (`pip install requests`).")

# Assuming local imports
try:
    from .auth import AuthenticationManager
    from .exceptions import (
        AuthenticationError, AuthorizationError, ConnectionError,
        APIError, ClientError, ConfigurationError
    )
    # Import MCP data models for type hints if available, otherwise use Any
    # from ...dbp.mcp_server.data_models import MCPRequest, MCPResponse, MCPError # Example relative path
    MCPRequest = Any
    MCPResponse = Any
    MCPError = Any
except ImportError as e:
    logging.getLogger(__name__).error(f"MCPClientAPI ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    AuthenticationManager = object
    AuthenticationError = Exception
    AuthorizationError = Exception
    ConnectionError = Exception
    APIError = Exception
    ClientError = Exception
    ConfigurationError = Exception
    MCPRequest = object
    MCPResponse = object
    MCPError = object


logger = logging.getLogger(__name__)

class MCPClientAPI:
    """API client for interacting with the DBP MCP server."""

    def __init__(self, auth_manager: AuthenticationManager, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the MCPClientAPI.

        Args:
            auth_manager: The AuthenticationManager instance for retrieving API keys.
            logger_override: Optional logger instance.
        """
        if not HAS_REQUESTS:
            raise ImportError("The 'requests' library is required for MCPClientAPI.")
        if not isinstance(auth_manager, AuthenticationManager):
             logger.warning("MCPClientAPI initialized with potentially incorrect auth_manager type.")

        self.auth_manager = auth_manager
        self.config_manager = auth_manager.config_manager # Get config manager via auth manager
        self.logger = logger_override or logger
        self.server_url: Optional[str] = None
        self.timeout: int = 30
        self._initialized: bool = False
        self.logger.debug("MCPClientAPI initialized.")

    def initialize(self):
        """Loads configuration like server URL and timeout."""
        if self._initialized:
            return
        self.logger.debug("Initializing MCPClientAPI configuration...")
        
        # Compute URL from host and port
        config = self.config_manager.get_typed_config()
        host = config.mcp_server.host
        port = config.mcp_server.port
        self.server_url = f"http://{host}:{port}"
        self.timeout = int(config.server.timeout)

        if not self.server_url:
            raise ConfigurationError("MCP server URL could not be computed from host and port.")

        # Ensure URL ends with a slash for easier endpoint joining
        if not self.server_url.endswith('/'):
            self.server_url += '/'

        self._initialized = True
        self.logger.info(f"MCP Client initialized for server: {self.server_url}")

    def _check_initialized(self):
        """Raises an error if the client hasn't been initialized."""
        if not self._initialized:
            raise ClientError("MCPClientAPI has not been initialized. Call initialize() first.")

    def _make_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Internal helper to make an HTTP request to the MCP server.

        Args:
            method: HTTP method ('GET', 'POST', etc.).
            endpoint: The API endpoint path (e.g., 'mcp/tool/analyze').
            params: Dictionary of query parameters for GET requests.
            data: Dictionary of data to send in the request body for POST/PUT etc.

        Returns:
            The parsed JSON response dictionary from the server.

        Raises:
            ConnectionError: If connection to the server fails.
            AuthenticationError: If the server returns an authentication error.
            AuthorizationError: If the server returns an authorization error.
            APIError: For other server-side errors reported via MCPError.
            ClientError: For unexpected client-side issues or response formats.
            ConfigurationError: If the client is not configured.
            TimeoutError: If the request times out.
        """
        self._check_initialized()
        if not self.server_url: # Should be caught by _check_initialized, but safety check
             raise ConfigurationError("MCP server URL is not set.")

        url = self.server_url + endpoint.lstrip('/') # Ensure single slash
        headers = {"Content-Type": "application/json", "Accept": "application/json"}
        
        # First try without authentication
        self.logger.debug(f"Making initial MCP request without authentication: {method} {url}")
        if data: self.logger.debug(f"Request Data: {json.dumps(data)}")
        if params: self.logger.debug(f"Request Params: {params}")

        try:
            # First try the request without authentication
            response = requests.request(
                method=method.upper(),
                url=url,
                headers=headers,
                params=params, # For GET requests
                json=data,     # For POST/PUT requests
                timeout=self.timeout
            )
            
            # If we get a 401 Unauthorized, try to add authentication headers and retry
            if response.status_code == 401:
                self.logger.debug("Received 401 Unauthorized response, retrying with authentication")
                try:
                    # Now try to get auth headers
                    auth_headers = self.auth_manager.get_auth_headers()
                    headers.update(auth_headers)
                    
                    # Retry the request with authentication
                    self.logger.debug(f"Retrying MCP request with authentication: {method} {url}")
                    response = requests.request(
                        method=method.upper(),
                        url=url,
                        headers=headers,
                        params=params,
                        json=data,
                        timeout=self.timeout
                    )
                except AuthenticationError as e:
                    # If we can't get auth headers, convert the original 401 to an AuthenticationError
                    self.logger.error(f"Authentication required but no API key available: {e}")
                    raise AuthenticationError(
                        "Authentication required by server: No API key found. "
                        "Set DBP_API_KEY environment variable, use --api-key flag, "
                        "or configure 'mcp_server.api_key' in config file."
                    ) from e

            # Now check for HTTP errors
            response.raise_for_status()

            # Parse JSON response
            response_data = response.json()
            self.logger.debug(f"Response Status: {response_data.get('status')}")

            # Check for MCP-level errors
            if response_data.get("status") == "error":
                mcp_error_data = response_data.get("error", {})
                code = mcp_error_data.get("code", "UNKNOWN_API_ERROR")
                message = mcp_error_data.get("message", "Unknown error from MCP server.")
                self.logger.error(f"MCP server returned error: Code={code}, Message={message}")
                if code == "AUTHENTICATION_FAILED":
                    raise AuthenticationError(message)
                elif code == "AUTHORIZATION_FAILED":
                    raise AuthorizationError(message)
                else:
                    raise APIError(message, code=code)

            # Return the result part of the successful response
            return response_data.get("result", {})

        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"Connection error contacting MCP server at {self.server_url}: {e}")
            raise ConnectionError(f"Could not connect to MCP server at {self.server_url}.") from e
        except requests.exceptions.Timeout as e:
            self.logger.error(f"Request to MCP server timed out ({self.timeout}s): {e}")
            raise TimeoutError(f"Request timed out after {self.timeout} seconds.") from e
        except requests.exceptions.RequestException as e:
            # Handle other requests errors (e.g., HTTP errors handled by raise_for_status, SSL errors)
            self.logger.error(f"HTTP request error for {method} {url}: {e}", exc_info=True)
            # Try to get more specific info from response if available
            error_msg = str(e)
            if e.response is not None:
                 try:
                      error_detail = e.response.json().get("error", {}).get("message", e.response.text)
                      error_msg = f"HTTP {e.response.status_code}: {error_detail}"
                 except json.JSONDecodeError:
                      error_msg = f"HTTP {e.response.status_code}: {e.response.text}"

            # Map common HTTP errors to specific CLI exceptions
            if e.response is not None:
                 if e.response.status_code == 401: raise AuthenticationError(error_msg) from e
                 if e.response.status_code == 403: raise AuthorizationError(error_msg) from e
                 if e.response.status_code == 404: raise APIError(error_msg, code="NOT_FOUND") from e # e.g., tool not found

            raise APIError(f"MCP request failed: {error_msg}") from e
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to decode JSON response from {url}: {e}")
            raise ClientError(f"Received invalid JSON response from server.") from e
        except Exception as e:
             self.logger.error(f"Unexpected error during MCP request: {e}", exc_info=True)
             raise ClientError(f"An unexpected client error occurred: {e}") from e


    # --- Methods for specific DBP MCP Tools ---

    def call_tool(self, tool_name: str, tool_data: Dict[str, Any]) -> Dict[str, Any]:
         """Generic method to call any MCP tool."""
         # Assume MCP server exposes tools at /mcp/tool/{tool_name} via POST
         endpoint = f"mcp/tool/{tool_name}"
         # MCP request body typically has 'id' and 'data' keys
         request_payload = {
              "id": str(uuid.uuid4()), # Generate client-side request ID
              "data": tool_data
         }
         return self._make_request("POST", endpoint, data=request_payload)

    def get_resource(self, resource_uri: str, params: Optional[Dict] = None) -> Dict[str, Any]:
         """Generic method to get any MCP resource."""
         # Assume MCP server exposes resources at /mcp/resource/{uri...} via GET
         endpoint = f"mcp/resource/{resource_uri}"
         return self._make_request("GET", endpoint, params=params)

    # --- Convenience methods mapping to specific tools/resources ---

    def analyze_consistency(self, code_file_path: str, doc_file_path: str, **kwargs) -> Dict[str, Any]:
        """
        [DEPRECATED] This method is no longer supported as the consistency_analysis component has been removed.
        """
        self.logger.error("analyze_consistency method is deprecated - consistency_analysis component has been removed")
        raise APIError("Operation not supported: consistency_analysis component has been removed", code="DEPRECATED_OPERATION")

    def generate_recommendations(self, inconsistency_ids: List[str], **kwargs) -> Dict[str, Any]:
        """
        Calls the general query tool for recommendation generation.
        
        Following the MCP server refactoring, this now routes through the dbp_general_query tool
        with an operation-specific structure.
        """
        tool_data = {
            "query": {
                "operation": "recommendations",
                "inconsistency_ids": inconsistency_ids
            },
            "context": kwargs.get("context", {}),
            "parameters": {k: v for k, v in kwargs.items() if k != "context"}
        }
        result = self.call_tool("dbp_general_query", tool_data)
        # Extract the actual result data from the wrapper response
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    def apply_recommendation(self, recommendation_id: str, **kwargs) -> Dict[str, Any]:
        """
        Calls the general query tool to apply a recommendation.
        
        Following the MCP server refactoring, this now routes through the dbp_general_query tool
        with an operation-specific structure.
        """
        tool_data = {
            "query": {
                "operation": "recommendations",
                "recommendation_id": recommendation_id,
                "apply": True
            },
            "context": kwargs.get("context", {}),
            "parameters": {k: v for k, v in kwargs.items() if k != "context"}
        }
        result = self.call_tool("dbp_general_query", tool_data)
        # Extract the actual result data from the wrapper response
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    def get_doc_relationships(self, document_path: str) -> Dict[str, Any]:
        """
        Gets relationships for a document via the general query tool.
        
        Following the MCP server refactoring, this now routes through the dbp_general_query tool
        with an operation-specific structure.
        """
        tool_data = {
            "query": {
                "operation": "document_relationship",
                "doc_file_path": document_path,
                "analysis_type": "all"
            }
        }
        result = self.call_tool("dbp_general_query", tool_data)
        # Extract the actual result data from the wrapper response
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    def get_mermaid_diagram(self, document_paths: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Gets a Mermaid diagram via the general query tool.
        
        Following the MCP server refactoring, this now routes through the dbp_general_query tool
        with an operation-specific structure.
        """
        tool_data = {
            "query": {
                "operation": "visualization",
                "diagram_type": "mermaid"
            }
        }
        if document_paths:
            tool_data["query"]["document_paths"] = document_paths
            
        result = self.call_tool("dbp_general_query", tool_data)
        # Extract the actual result data from the wrapper response
        if isinstance(result, dict) and "result" in result:
            return result["result"]
        return result

    def generate_commit_message(self, since_commit: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """
        Calls the commit message tool to generate a commit message.
        
        Args:
            since_commit: Optional commit hash to use as base reference
            **kwargs: Additional parameters to control commit message generation
                - format: Format style ("conventional", "detailed", "simple")
                - include_scope: Whether to include scope information
                - max_length: Maximum length for the message
                - files: List of specific files to include
                
        Returns:
            Dictionary with commit message and additional metadata
        """
        tool_data = {k: v for k, v in kwargs.items()}
        if since_commit:
            tool_data["since_commit"] = since_commit
            
        return self.call_tool("dbp_commit_message", tool_data)

    def get_server_status(self) -> Dict[str, Any]:
        """
        Gets the server status via the health check endpoint.
        
        Returns a dictionary with server status information.
        If the server is unreachable, returns a status object with error information
        instead of raising an exception.
        """
        # Use the health endpoint that's implemented in the server
        self.logger.debug("Calling get_server_status() - Making request to health endpoint")
        
        # Prepare basic result structure with error status
        result = {
            "status": "error",
            "connected": False,
            "message": "Unknown error"
        }
        
        # This import is used only within this method to avoid circular imports
        import logging
        logger = logging.getLogger(__name__)
        
        # Create a separate logger that doesn't output to console
        debug_logger = logging.getLogger(__name__ + ".debug")
        # Remove any existing handlers to prevent console output
        for handler in debug_logger.handlers:
            debug_logger.removeHandler(handler)
        # Set the level to DEBUG to capture all messages
        debug_logger.setLevel(logging.DEBUG)
        
        try:
            self._check_initialized()
            if not self.server_url:
                logger.error("Server URL not configured")
                result["message"] = "Server URL not configured"
                return result

            url = self.server_url + "health"
            headers = {"Content-Type": "application/json", "Accept": "application/json"}
            
            # Direct try/except block around the HTTP request to completely suppress exception propagation
            try:
                # Make direct request to health endpoint without extracting result
                response = requests.get(url, headers=headers, timeout=self.timeout)
                response.raise_for_status()
                
                # Parse full JSON response without extracting a "result" key
                server_response = response.json()
                logger.debug(f"get_server_status() success - Result: {server_response}")
                
                # Merge the server response with our status wrapper
                result = {
                    "status": "ok",
                    "connected": True,
                    "server_data": server_response
                }
                if "version" in server_response:
                    result["version"] = server_response["version"]
                
                return result
            except requests.exceptions.ConnectionError as e:
                # Just log the error message without the stack trace
                logger.error(f"Connection error: Could not connect to server at {url}")
                
                # Get the underlying error message for better diagnostics
                cause = getattr(e, '__cause__', None)
                if cause and "connection refused" in str(cause).lower():
                    result["message"] = "Connection to server refused. Check if the MCP server is running."
                elif cause:
                    result["message"] = f"Connection to MCP server failed: {str(cause).split(':')[-1].strip()}"
                else:
                    result["message"] = "Connection to MCP server failed. Check server status and network connectivity."
                
                return result
                
            except requests.exceptions.Timeout:
                # Log a user-friendly message with no stack trace
                logger.error(f"Connection timed out after {self.timeout}s")
                result["message"] = f"Connection to MCP server timed out after {self.timeout} seconds."
                return result
                
            except requests.exceptions.RequestException as e:
                # Log a user-friendly message with no stack trace
                logger.error(f"HTTP request failed: {str(e).split(':')[0]}")
                result["message"] = "HTTP request to MCP server failed. Check server URL and configuration."
                return result
                
            except Exception as e:
                # Log a user-friendly message for unexpected errors with no stack trace
                logger.error(f"Unexpected error connecting to server: {type(e).__name__}")
                result["message"] = f"An unexpected error occurred: {type(e).__name__}"
                return result
                
        except Exception as e:
            # This is a fallback catch-all to prevent any exceptions from propagating
            # Log a simple message to the main logger with no stack trace
            logger.error("Failed to check server status due to an internal error")
            result["message"] = "Internal error while checking server status"
            return result
