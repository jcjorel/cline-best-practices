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
# Defines error handling components for the Model Context Protocol (MCP) implementation.
# Provides standardized error codes and error types that adhere to the MCP specification
# and JSON-RPC 2.0 protocol requirements.
###############################################################################
# [Source file design principles]
# - Uses Enum for type-safe error codes
# - Provides consistent error representation following JSON-RPC 2.0 spec
# - Error objects support conversion to JSON-RPC 2.0 error format
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
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:46:34Z : Created during mcp_protocols.py refactoring by CodeAssistant
# * Extracted MCPErrorCode and MCPError classes from mcp_protocols.py
###############################################################################

from enum import Enum
from typing import Dict, Any, Union


class MCPErrorCode(Enum):
    """
    [Class intent]
    Represents standardized MCP error codes based on JSON-RPC 2.0 specification.
    
    [Design principles]
    - Follows JSON-RPC 2.0 standard error codes
    - Extends with MCP-specific error codes
    
    [Implementation details]
    - Uses an Enum for type-safe error codes
    - Includes standard JSON-RPC 2.0 error codes (-32xxx range)
    - Includes MCP-specific error codes (32xxx range)
    """
    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603
    
    # MCP-specific errors
    TOOL_EXECUTION_ERROR = 32000
    RESOURCE_NOT_FOUND = 32001
    UNAUTHORIZED = 32002
    TIMEOUT = 32003
    CANCELLED = 32004


class MCPError(Exception):
    """
    [Class intent]
    Represents an MCP protocol error with standard error code and message.
    
    [Design principles]
    - Follows JSON-RPC 2.0 error structure
    - Provides consistent error handling across MCP tools
    
    [Implementation details]
    - Extends Exception with additional error code and data fields
    - Converts to JSON-RPC 2.0 error object format
    """
    
    def __init__(self, code: Union[int, MCPErrorCode], message: str, data: Any = None):
        """
        [Class method intent]
        Initializes a new MCP error.
        
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
