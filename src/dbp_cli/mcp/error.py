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
# Defines error handling components for the Model Context Protocol (MCP) client implementation.
# Provides standardized error codes and error types that adhere to the MCP specification
# and JSON-RPC 2.0 protocol requirements.
###############################################################################
# [Source file design principles]
# - Uses Enum for type-safe error codes
# - Provides consistent error representation following JSON-RPC 2.0 spec
# - Error objects support creation from JSON-RPC 2.0 error responses
# - Provides both standard JSON-RPC error codes and MCP-specific codes
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with JSON-RPC 2.0 error structure
# - Error codes must follow the MCP specification guidelines
# - Standard JSON-RPC codes must be in the -32xxx range
# - MCP-specific codes should be in the 32xxx range
###############################################################################
# [Dependencies]
# system:enum
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:03:00Z : Initial implementation of MCP client error handling by CodeAssistant
# * Created MCPErrorCode and MCPError classes for client-side error handling
###############################################################################

from enum import Enum
from typing import Dict, Any, Optional, Union, ClassVar


class MCPErrorCode(Enum):
    """
    [Class intent]
    Represents standardized MCP error codes based on JSON-RPC 2.0 specification.
    Per the MCP specification at https://modelcontextprotocol.io/specification/2025-03-26
    
    [Design principles]
    - Follows JSON-RPC 2.0 standard error codes
    - Extends with MCP-specific error codes
    - Identical to server-side error codes for consistency
    
    [Implementation details]
    - Uses an Enum for type-safe error codes
    - Includes standard JSON-RPC 2.0 error codes (-32xxx range)
    - Includes MCP-specific error codes (32xxx range)
    """
    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = -32700        # Invalid JSON was received
    INVALID_REQUEST = -32600    # The JSON sent is not a valid Request object
    METHOD_NOT_FOUND = -32601   # The method does not exist / is not available
    INVALID_PARAMS = -32602     # Invalid method parameter(s)
    INTERNAL_ERROR = -32603     # Internal JSON-RPC error
    
    # MCP-specific errors
    TOOL_EXECUTION_ERROR = 32000  # Error during tool execution (e.g., tool function threw exception)
    RESOURCE_NOT_FOUND = 32001    # Requested resource does not exist
    UNAUTHORIZED = 32002          # Client lacks permission to access tool/resource
    TIMEOUT = 32003               # Operation exceeded time limit
    CANCELLED = 32004             # Operation was cancelled
    
    # Client-side specific errors (not in server implementation)
    CONNECTION_ERROR = 32100      # Connection to server failed 
    SERVER_UNAVAILABLE = 32101    # Server is not available
    SSL_ERROR = 32102             # SSL/TLS connection error
    CAPABILITY_NEGOTIATION_ERROR = 32103  # Error during capability negotiation
    CLIENT_IMPLEMENTATION_ERROR = 32104   # Error in client implementation


class MCPError(Exception):
    """
    [Class intent]
    Represents an MCP protocol error with standard error code and message.
    Provides client-side error handling for MCP communications.
    
    [Design principles]
    - Follows JSON-RPC 2.0 error structure
    - Provides consistent error handling across MCP client operations
    - Allows both creating errors and parsing received errors
    
    [Implementation details]
    - Extends Exception with additional error code and data fields
    - Supports parsing errors from JSON-RPC 2.0 error responses
    - Enables clear error propagation up the client stack
    """
    
    # Maps HTTP status codes to MCP error codes for convenient conversion
    HTTP_STATUS_MAP: ClassVar[Dict[int, MCPErrorCode]] = {
        400: MCPErrorCode.INVALID_REQUEST,
        401: MCPErrorCode.UNAUTHORIZED,
        403: MCPErrorCode.UNAUTHORIZED,
        404: MCPErrorCode.RESOURCE_NOT_FOUND,
        405: MCPErrorCode.METHOD_NOT_FOUND,
        408: MCPErrorCode.TIMEOUT,
        500: MCPErrorCode.INTERNAL_ERROR,
        502: MCPErrorCode.SERVER_UNAVAILABLE,
        503: MCPErrorCode.SERVER_UNAVAILABLE,
        504: MCPErrorCode.TIMEOUT
    }
    
    def __init__(self, code: Union[int, MCPErrorCode], message: str, data: Any = None):
        """
        [Class method intent]
        Initializes a new MCP client error.
        
        [Design principles]
        - Follows JSON-RPC 2.0 error structure
        - Provides detailed error information
        
        [Implementation details]
        - Accepts error code as either int or MCPErrorCode enum
        - Stores optional data for additional error information
        
        Args:
            code: The error code (from MCPErrorCode or custom code)
            message: The error message
            data: Optional additional data about the error
        """
        self.code = code.value if isinstance(code, MCPErrorCode) else code
        self.message = message
        self.data = data
        super().__init__(message)
    
    @classmethod
    def from_http_status(cls, status_code: int, message: Optional[str] = None) -> 'MCPError':
        """
        [Function intent]
        Creates an MCPError from an HTTP status code.
        
        [Design principles]
        - Maps common HTTP errors to appropriate MCP error codes
        - Provides convenient error creation from HTTP responses
        
        [Implementation details]
        - Uses HTTP_STATUS_MAP to determine the appropriate error code
        - Falls back to INTERNAL_ERROR for unmapped status codes
        
        Args:
            status_code: HTTP status code
            message: Optional error message (defaults to generic message based on status)
            
        Returns:
            A new MCPError instance
        """
        if message is None:
            message = f"HTTP error: {status_code}"
            
        error_code = cls.HTTP_STATUS_MAP.get(status_code, MCPErrorCode.INTERNAL_ERROR)
        return cls(error_code, message)
    
    @classmethod
    def from_json_rpc(cls, error_obj: Dict[str, Any]) -> 'MCPError':
        """
        [Function intent]
        Creates an MCPError from a JSON-RPC error object.
        
        [Design principles]
        - Supports parsing server-returned error responses
        - Converts JSON-RPC error structure to MCPError
        
        [Implementation details]
        - Extracts code, message, and data from error object
        - Handles potential missing or malformed fields
        
        Args:
            error_obj: Dictionary containing a JSON-RPC error object
            
        Returns:
            A new MCPError instance
        """
        if not isinstance(error_obj, dict):
            return cls(MCPErrorCode.PARSE_ERROR, "Invalid error object")
        
        error_data = error_obj.get("error", {})
        if not isinstance(error_data, dict):
            return cls(MCPErrorCode.PARSE_ERROR, "Invalid error structure")
            
        code = error_data.get("code", MCPErrorCode.INTERNAL_ERROR.value)
        message = error_data.get("message", "Unknown error")
        data = error_data.get("data")
        
        return cls(code, message, data)
    
    def to_json_rpc(self) -> Dict[str, Any]:
        """
        [Function intent]
        Converts this error to a JSON-RPC 2.0 error object.
        
        [Design principles]
        - Follows JSON-RPC 2.0 error structure specification
        - Ensures consistent error response format
        
        [Implementation details]
        - Creates a dictionary with code, message, and optional data
        
        Returns:
            A dictionary representing a JSON-RPC 2.0 error object
        """
        error_obj = {"code": self.code, "message": self.message}
        if self.data is not None:
            error_obj["data"] = self.data
        return {"error": error_obj}
    
    def __str__(self) -> str:
        """
        [Function intent]
        Creates a human-readable string representation of the error.
        
        [Design principles]
        - Provides useful information for logging and debugging
        - Shows both code and message for clarity
        
        [Implementation details]
        - Returns formatted string with code and message
        
        Returns:
            A string representation of the error
        """
        return f"MCP Error {self.code}: {self.message}"
