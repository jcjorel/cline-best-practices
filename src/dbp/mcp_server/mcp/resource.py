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
# Defines the MCPResource abstract base class, which establishes the required interface 
# for all concrete resource implementations in the MCP server. Follows the Model Context 
# Protocol (MCP) specification for resource definition and access.
###############################################################################
# [Source file design principles]
# - Implements MCP JSON-RPC 2.0 protocol for resources
# - Uses Pydantic models for parameter and response schema validation
# - Provides abstract base class with clear required methods
# - Handles all JSON-RPC request validation and response formatting
###############################################################################
# [Source file constraints]
# - Concrete implementations must inherit from MCPResource
# - All resource data must be JSON-serializable
# - Error handling must follow JSON-RPC 2.0 specification
###############################################################################
# [Dependencies]
# system:pydantic
# system:abc
# system:logging
# codebase:src/dbp/mcp_server/mcp/error.py
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:51:44Z : Created during mcp_protocols.py refactoring by CodeAssistant
# * Extracted MCPResource class from mcp_protocols.py
###############################################################################

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type

from pydantic import BaseModel, create_model

from .error import MCPError, MCPErrorCode

logger = logging.getLogger(__name__)


class MCPResource(ABC):
    """
    [Class intent]
    Abstract base class for all resources exposed via the MCP server.
    Strictly follows the Model Context Protocol specification for resources.
    
    [Design principles]
    - Fully compliant with MCP JSON-RPC 2.0 protocol for resources
    - Uses Pydantic models for parameters and response validation
    - Provides consistent resource access interface
    
    [Implementation details]
    - Defines abstract methods for resource operations
    - Uses URI templates for resource identification
    - Implements JSON-RPC protocol for resource access
    """

    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        [Class method intent]
        Initializes an MCP-compliant resource.
        
        [Design principles]
        - Validates core MCP resource requirements
        - Sets up logging and schema validation
        
        [Implementation details]
        - Validates resource name and description
        - Initializes schema models
        - Sets up logging with optional override

        Args:
            name: The unique name (typically the URI template prefix) for this resource
            description: A human-readable description of the resource
            logger_override: Optional logger instance
        """
        if not name or not isinstance(name, str):
             raise ValueError("Resource name must be a non-empty string")
        self._name = name
        self._description = description
        self.logger = logger_override or logger.getChild(f"MCPResource.{self.name}")
        
        # Create schema models
        self._params_schema_model = self._get_params_schema()
        self._response_schema_model = self._get_response_schema()
        
        self.logger.debug(f"MCPResource '{self.name}' initialized")

    @property
    def name(self) -> str:
        """The unique identifier name (URI prefix) for this resource."""
        return self._name

    @property
    def description(self) -> str:
        """A human-readable description of the resource."""
        return self._description
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        [Function intent]
        Provides MCP-compliant resource metadata.
        
        [Design principles]
        - Follows MCP resource metadata specification
        - Includes all required information for resource discovery
        
        [Implementation details]
        - Generates metadata based on properties and schemas
        - Includes URI template information
        
        Returns:
            Dictionary containing MCP-compliant resource metadata
        """
        return {
            "name": self.name,
            "description": self.description,
            "uri_template": f"{self.name}/{{id}}",
            "params_schema": self._params_schema_model.schema(),
            "response_schema": self._response_schema_model.schema(),
            "operations": ["get"],  # Default support for GET only
            "version": "1.0"  # Resource version (optional in MCP spec)
        }
        
    def _get_params_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Define the schema for query parameters.
        
        [Design principles]
        - Default implementation provides empty params model
        - Can be overridden by subclasses for specific parameter validation
        
        [Implementation details]
        - Creates a dynamic Pydantic model with no fields by default
        
        Returns:
            A Pydantic model class for validating query parameters
        """
        return create_model('ResourceParams', __base__=BaseModel)
        
    def _get_response_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Define the schema for resource responses.
        
        [Design principles]
        - Default implementation provides a generic response model
        - Should be overridden by subclasses for specific response validation
        
        [Implementation details]
        - Creates a dynamic Pydantic model allowing arbitrary fields by default
        
        Returns:
            A Pydantic model class for validating response data
        """
        # Default response schema allows any fields
        ResourceResponse = create_model('ResourceResponse', __base__=BaseModel)
        ResourceResponse.Config.extra = "allow"  # Allow arbitrary fields
        return ResourceResponse

    @abstractmethod
    def get(self, resource_id: Optional[str], params: BaseModel, 
            auth_context: Optional[Dict[str, Any]] = None, 
            session: Optional[Any] = None) -> BaseModel:
        """
        [Function intent]
        Retrieves the resource data with validated parameters.
        
        [Design principles]
        - Type-safe parameter and response validation
        - Clear resource identification pattern
        - Consistent error handling
        - Session-aware for capability negotiation
        
        [Implementation details]
        - Receives pre-validated Pydantic model for parameters
        - Must return data conforming to response schema model
        - Abstract method to be implemented by subclasses

        Args:
            resource_id: The specific identifier for the resource instance being accessed
                         (e.g., a specific document path following the resource name prefix).
                         Can be None if accessing the root of the resource collection.
            params: A Pydantic model containing validated query parameters
            auth_context: Optional dictionary containing authentication information
            session: Optional session object from capability negotiation

        Returns:
            A Pydantic model containing the resource data

        Raises:
            MCPError: For resource-specific access errors
            Exception: Other exceptions will be converted to MCPError
        """
        pass
        
    def handle_json_rpc(self, request: Dict[str, Any], session: Optional[Any] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Handles JSON-RPC 2.0 requests for this resource.
        
        [Design principles]
        - Fully compliant with MCP JSON-RPC 2.0 protocol
        - Consistent error handling per JSON-RPC specification
        - Complete request validation and access flow
        - Supports capability negotiation through session tracking
        
        [Implementation details]
        - Validates JSON-RPC request structure
        - Extracts resource ID and parameters
        - Accesses resource and formats response according to JSON-RPC 2.0
        - Handles all errors with appropriate JSON-RPC error objects
        - Passes session information to resource implementation

        Args:
            request: A dictionary containing the JSON-RPC request
            session: Optional session object from capability negotiation

        Returns:
            A dictionary containing the JSON-RPC response
        """
        # Default response ID in case request is malformed
        request_id = None
        
        try:
            # Validate JSON-RPC request
            if not isinstance(request, dict):
                raise MCPError(MCPErrorCode.INVALID_REQUEST, "Request must be a JSON object")
                
            # Check JSON-RPC version
            if request.get("jsonrpc") != "2.0":
                raise MCPError(MCPErrorCode.INVALID_REQUEST, "Invalid JSON-RPC version, must be 2.0")
                
            # Get request ID
            request_id = request.get("id")
            
            # Validate method
            method = request.get("method")
            if not method:
                raise MCPError(MCPErrorCode.INVALID_REQUEST, "Method is required")
                
            if method != "getResource":
                raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Method '{method}' not found")
                
            # Get parameters
            params = request.get("params", {})
            if not isinstance(params, dict):
                raise MCPError(MCPErrorCode.INVALID_PARAMS, "Params must be an object")
            
            # Extract resource ID
            resource_id = params.pop("id", None)
            
            # Extract auth context if provided
            auth_context = params.pop("auth_context", None)
            
            # Validate parameters against schema
            try:
                params_model = self._params_schema_model.parse_obj(params)
            except Exception as e:
                raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Invalid parameters: {str(e)}")
            
            # Access the resource
            try:
                result = self.get(resource_id, params_model, auth_context, session)
                
                # Convert result to dict
                result_dict = result.dict()
                
                # Return JSON-RPC response
                return {
                    "jsonrpc": "2.0",
                    "result": result_dict,
                    "id": request_id
                }
                
            except MCPError as e:
                # Resource raised an MCP error
                error_response = e.to_json_rpc()
                error_response["jsonrpc"] = "2.0"
                error_response["id"] = request_id
                return error_response
                
            except Exception as e:
                # Unexpected error during resource access
                self.logger.error(f"Error accessing resource {self.name}: {str(e)}", exc_info=True)
                
                # Determine appropriate error code
                if "not found" in str(e).lower():
                    error_code = MCPErrorCode.RESOURCE_NOT_FOUND
                else:
                    error_code = MCPErrorCode.INTERNAL_ERROR
                    
                error = MCPError(error_code, f"Resource access error: {str(e)}")
                error_response = error.to_json_rpc()
                error_response["jsonrpc"] = "2.0"
                error_response["id"] = request_id
                return error_response
                
        except MCPError as e:
            # JSON-RPC protocol error
            error_response = e.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            return error_response
            
        except Exception as e:
            # Unexpected error during request handling
            self.logger.error(f"Internal error in resource {self.name}: {str(e)}", exc_info=True)
            error = MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
            error_response = error.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            return error_response
