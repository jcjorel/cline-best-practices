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
# Implements the core MCPClient class for the Model Context Protocol (MCP) client.
# This class provides the foundation for all MCP communications, handling HTTP requests,
# authentication, connection management, and error handling following the
# MCP specification.
###############################################################################
# [Source file design principles]
# - Clean separation between transport layer and higher-level client operations
# - Full compliance with MCP JSON-RPC 2.0 protocol
# - Robust error handling with proper mapping of HTTP/network errors to MCP errors
# - Efficient connection management to optimize performance
# - Consistent authentication and header management
# - Support for configuration from environment or explicit settings
###############################################################################
# [Source file constraints]
# - Requires the requests library for HTTP communication
# - Must handle network errors gracefully
# - Should maintain backward compatibility with existing dbp_cli functionality
# - Must implement proper timeout and retry handling
# - Must not expose transport details to higher-level client components
###############################################################################
# [Dependencies]
# system:requests
# system:logging
# system:json
# system:uuid
# system:typing
# codebase:src/dbp_cli/mcp/error.py
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:05:00Z : Initial implementation of MCP client core by CodeAssistant
# * Created base MCPClient class for HTTP communication
# * Implemented JSON-RPC 2.0 request/response handling
# * Added error handling and authentication support
###############################################################################

import logging
import json
import uuid
import time
from typing import Dict, Any, Optional, Union, List, Tuple

# Check for the requests library
try:
    import requests
    from requests.adapters import HTTPAdapter
    from requests.packages.urllib3.util.retry import Retry
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    logging.getLogger(__name__).error(
        "The 'requests' library is required for MCPClient. "
        "Please install it (`pip install requests`)."
    )

from .error import MCPError, MCPErrorCode


class MCPClient:
    """
    [Class intent]
    The core client for Model Context Protocol (MCP) communications.
    Provides low-level JSON-RPC 2.0 protocol implementation for MCP servers.
    
    [Design principles]
    - Strictly follows MCP and JSON-RPC 2.0 specifications
    - Handles HTTP transport, authentication, and error mapping
    - Serves as foundation for specialized tool/resource clients
    
    [Implementation details]
    - Uses the requests library for HTTP communication
    - Implements automatic retries for transient failures
    - Maps HTTP and network errors to MCPError types
    - Provides JSON-RPC 2.0 message construction utilities
    """

    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RETRIES = 3
    DEFAULT_BACKOFF_FACTOR = 0.5
    DEFAULT_USER_AGENT = "MCPClient/1.0"
    DEFAULT_CONTENT_TYPE = "application/json"
    MCP_VERSION = "2025-03-26"  # Current MCP specification version
    
    def __init__(
        self,
        base_url: str,
        auth_token: Optional[str] = None,
        auth_headers: Optional[Dict[str, str]] = None,
        timeout: int = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Class method intent]
        Initializes a new MCP client with the specified configuration.
        
        [Design principles]
        - Flexible configuration with sensible defaults
        - Support for multiple authentication methods
        - Configurable timeout and retry handling
        
        [Implementation details]
        - Creates session with retry configuration
        - Sets up authentication headers
        - Initializes logging
        
        Args:
            base_url: The base URL of the MCP server (e.g., "http://localhost:8000")
            auth_token: Optional authentication token
            auth_headers: Optional dictionary of authentication headers
            timeout: Request timeout in seconds
            max_retries: Maximum number of retries for failed requests
            logger_override: Optional logger instance
        """
        if not HAS_REQUESTS:
            raise ImportError("The 'requests' library is required for MCPClient.")
            
        self.base_url = base_url.rstrip('/')  # Remove trailing slash if present
        self.timeout = timeout
        self.logger = logger_override or logging.getLogger(__name__)
        
        # Set up authentication
        self.headers = {
            "Content-Type": self.DEFAULT_CONTENT_TYPE,
            "Accept": self.DEFAULT_CONTENT_TYPE,
            "User-Agent": self.DEFAULT_USER_AGENT,
        }
        
        # Add authentication headers
        if auth_token:
            self.headers["Authorization"] = f"Bearer {auth_token}"
        if auth_headers:
            self.headers.update(auth_headers)
        
        # Create a session with retry configuration
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=self.DEFAULT_BACKOFF_FACTOR,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        self.session.mount("http://", HTTPAdapter(max_retries=retry_strategy))
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))
        
        self.logger.debug(f"MCPClient initialized for server: {base_url}")
    
    def close(self):
        """
        [Function intent]
        Closes the client's HTTP session to free resources.
        
        [Design principles]
        - Proper resource management
        - Clean shutdown of connections
        
        [Implementation details]
        - Closes the requests Session object
        """
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.debug("MCP client session closed")
    
    def _make_url(self, endpoint: str) -> str:
        """
        [Function intent]
        Constructs a full URL from the base URL and endpoint.
        
        [Design principles]
        - Ensures proper URL construction with consistent path handling
        
        [Implementation details]
        - Handles slashes in base URL and endpoint
        - Returns full absolute URL
        
        Args:
            endpoint: The API endpoint path
            
        Returns:
            The full URL
        """
        endpoint = endpoint.lstrip('/')  # Remove leading slash if present
        return f"{self.base_url}/{endpoint}"
    
    def _prepare_json_rpc_request(
        self, 
        method: str, 
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        [Function intent]
        Creates a JSON-RPC 2.0 request object.
        
        [Design principles]
        - Follows JSON-RPC 2.0 specification
        - Ensures consistent request structure
        
        [Implementation details]
        - Generates UUID for request ID if not provided
        - Formats standard JSON-RPC 2.0 request structure
        
        Args:
            method: The JSON-RPC method to call
            params: Optional parameters for the method
            request_id: Optional request ID (defaults to generated UUID)
            
        Returns:
            A dictionary containing the JSON-RPC request
        """
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        request = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }
        
        if params is not None:
            request["params"] = params
            
        return request
    
    def send_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
        headers: Optional[Dict[str, str]] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], requests.Response]:
        """
        [Function intent]
        Sends an HTTP request to the MCP server and handles the response.
        
        [Design principles]
        - Comprehensive error handling
        - Consistent request formatting and response processing
        - Support for both standard and streaming responses
        
        [Implementation details]
        - Sets proper request headers
        - Manages timeouts
        - Processes errors into proper MCP error types
        - Returns parsed JSON for standard responses or raw Response for streaming
        
        Args:
            method: HTTP method ("GET", "POST", etc.)
            endpoint: API endpoint (will be appended to base URL)
            data: Optional data to send in the request body
            params: Optional query parameters
            timeout: Optional request timeout override
            headers: Optional additional headers
            stream: Whether to return the raw response (for streaming)
            
        Returns:
            Parsed JSON response or raw Response object if stream=True
            
        Raises:
            MCPError: For all types of errors (transport, server, protocol)
        """
        url = self._make_url(endpoint)
        request_headers = self.headers.copy()
        if headers:
            request_headers.update(headers)
            
        timeout_value = timeout if timeout is not None else self.timeout
        
        self.logger.debug(f"Sending {method} request to: {url}")
        if data:
            self.logger.debug(f"Request data: {json.dumps(data)[:1000]}...")
            
        try:
            if method.upper() == "GET":
                response = self.session.get(
                    url,
                    params=params,
                    headers=request_headers,
                    timeout=timeout_value,
                    stream=stream
                )
            else:  # POST, PUT, DELETE, etc.
                response = self.session.request(
                    method=method.upper(),
                    url=url,
                    json=data,
                    params=params,
                    headers=request_headers,
                    timeout=timeout_value,
                    stream=stream
                )
                
            # Return raw response if streaming is requested
            if stream:
                return response
                
            # Check for HTTP errors and raise appropriate MCPError
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as e:
                error_message = str(e)
                
                # Try to extract more detailed error message if available
                try:
                    error_data = response.json()
                    if "error" in error_data and "message" in error_data["error"]:
                        error_message = error_data["error"]["message"]
                except (json.JSONDecodeError, KeyError, TypeError):
                    # Use response text if JSON parsing fails
                    if response.text:
                        error_message = response.text[:200]  # Limit to first 200 chars
                
                raise MCPError.from_http_status(response.status_code, error_message)
                
            # Parse the response
            try:
                data = response.json()
            except json.JSONDecodeError as e:
                raise MCPError(
                    MCPErrorCode.PARSE_ERROR, 
                    f"Failed to parse response as JSON: {e}"
                )
                
            # Check for JSON-RPC error response
            if "error" in data:
                raise MCPError.from_json_rpc(data)
                
            return data
            
        except requests.exceptions.Timeout:
            raise MCPError(
                MCPErrorCode.TIMEOUT, 
                f"Request timed out after {timeout_value} seconds"
            )
        except requests.exceptions.ConnectionError:
            raise MCPError(
                MCPErrorCode.CONNECTION_ERROR,
                f"Failed to connect to MCP server at {self.base_url}"
            )
        except requests.exceptions.RequestException as e:
            raise MCPError(
                MCPErrorCode.CLIENT_IMPLEMENTATION_ERROR,
                f"Request failed: {str(e)}"
            )
        except MCPError:
            # Re-raise MCPError as is
            raise
        except Exception as e:
            # Catch all other exceptions and convert to MCPError
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Unexpected error: {str(e)}"
            )
    
    def call_json_rpc(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None,
        timeout: Optional[int] = None,
        stream: bool = False
    ) -> Union[Dict[str, Any], requests.Response]:
        """
        [Function intent]
        Sends a JSON-RPC 2.0 request to the MCP server.
        
        [Design principles]
        - Follows JSON-RPC 2.0 protocol specification
        - Provides a clean interface for JSON-RPC communication
        - Handles request construction and error processing
        
        [Implementation details]
        - Creates proper JSON-RPC request structure
        - Uses send_request for transport
        - Returns result or raw response for streaming
        
        Args:
            method: JSON-RPC method name
            endpoint: API endpoint (will be appended to base URL)
            params: Optional method parameters
            request_id: Optional request ID (defaults to generated UUID)
            timeout: Optional request timeout override
            stream: Whether to return the raw response (for streaming)
            
        Returns:
            Parsed JSON response (or raw Response for streaming)
            
        Raises:
            MCPError: For all types of errors
        """
        request_data = self._prepare_json_rpc_request(method, params, request_id)
        response = self.send_request(
            method="POST",
            endpoint=endpoint,
            data=request_data,
            timeout=timeout,
            stream=stream
        )
        
        # Return raw response for streaming
        if stream:
            return response
            
        # Extract result data for standard responses
        if "result" not in response:
            raise MCPError(
                MCPErrorCode.PARSE_ERROR,
                "Invalid JSON-RPC response: missing 'result' field"
            )
            
        return response["result"]
    
    def health_check(self) -> Dict[str, Any]:
        """
        [Function intent]
        Checks if the MCP server is available and functioning.
        
        [Design principles]
        - Simple health check to verify connectivity
        - Uses standard endpoint pattern
        
        [Implementation details]
        - Makes a GET request to the health endpoint
        - Has shorter timeout for quick checking
        
        Returns:
            Server health status
            
        Raises:
            MCPError: If server is not available or health check fails
        """
        try:
            # Try to get server health with reduced timeout
            return self.send_request(
                method="GET",
                endpoint="health",
                timeout=5
            )
        except Exception as e:
            raise MCPError(
                MCPErrorCode.SERVER_UNAVAILABLE,
                f"Server health check failed: {str(e)}"
            )
    
    def __enter__(self):
        """
        [Function intent]
        Enables context manager pattern for the client.
        
        [Design principles]
        - Support for 'with' statement
        - Ensures proper resource management
        
        [Implementation details]
        - Returns self for use within context
        
        Returns:
            Self for use in with statement
        """
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        [Function intent]
        Cleans up resources when exiting context manager.
        
        [Design principles]
        - Proper resource cleanup
        - Completes context manager protocol
        
        [Implementation details]
        - Calls close() to free resources
        - Does not suppress exceptions
        """
        self.close()
