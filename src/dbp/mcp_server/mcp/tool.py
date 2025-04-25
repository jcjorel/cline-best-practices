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
# Defines the MCPTool abstract base class, which establishes the required interface 
# for all concrete tool implementations in the MCP server. Follows the Model Context 
# Protocol (MCP) specification for tool definition and execution.
###############################################################################
# [Source file design principles]
# - Implements MCP JSON-RPC 2.0 protocol for tools
# - Uses Pydantic models for input/output schema validation
# - Provides abstract base class with clear required methods
# - Handles all JSON-RPC request validation and response formatting
# - Supports progress reporting and cancellation
###############################################################################
# [Source file constraints]
# - Concrete implementations must inherit from MCPTool
# - All tool inputs and outputs must be JSON-serializable
# - Error handling must follow JSON-RPC 2.0 specification
###############################################################################
# [Dependencies]
# system:pydantic
# system:abc
# system:logging
# system:uuid
# codebase:src/dbp/mcp_server/mcp/error.py
# codebase:src/dbp/mcp_server/mcp/progress.py
# codebase:src/dbp/mcp_server/mcp/cancellation.py
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:49:27Z : Created during mcp_protocols.py refactoring by CodeAssistant
# * Extracted MCPTool class from mcp_protocols.py
###############################################################################

import logging
import uuid
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Union, List

from pydantic import BaseModel

from .error import MCPError, MCPErrorCode
from .progress import MCPProgressReporter
from .cancellation import MCPCancellationToken

logger = logging.getLogger(__name__)


class MCPTool(ABC):
    """
    [Class intent]
    Abstract base class for all tools exposed via the MCP server.
    Strictly follows the Model Context Protocol specification for tools.
    
    [Design principles]
    - Fully compliant with MCP JSON-RPC 2.0 protocol
    - Uses Pydantic models for input and output schema validation
    - Provides progress reporting and cancellation support
    
    [Implementation details]
    - Uses JSON Schema for input/output definitions
    - Supports MCP tool metadata requirements
    - Implements JSON-RPC execution protocol
    """

    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        [Class method intent]
        Initializes an MCP-compliant tool.
        
        [Design principles]
        - Validates core MCP tool requirements
        - Sets up logging and schema validation
        
        [Implementation details]
        - Validates tool name and description
        - Initializes Pydantic schema models
        - Sets up logging with optional override

        Args:
            name: The unique identifier name for this tool (used in MCP requests)
            description: A human-readable description of the tool's purpose
            logger_override: Optional logger instance
        """
        if not name or not isinstance(name, str):
             raise ValueError("Tool name must be a non-empty string")
        self._name = name
        self._description = description
        self.logger = logger_override or logger.getChild(f"MCPTool.{self.name}")
        
        # Initialize schema models
        self._input_schema_model = self._get_input_schema()
        self._output_schema_model = self._get_output_schema()
        
        self.logger.debug(f"MCPTool '{self.name}' initialized")

    @property
    def name(self) -> str:
        """The unique identifier for this tool."""
        return self._name

    @property
    def description(self) -> str:
        """A human-readable description of the tool's purpose."""
        return self._description

    @property
    def input_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Provides the Pydantic model class for input validation.
        
        [Design principles]
        - Type-safe schema definition using Pydantic
        - Aligned with MCP JSON Schema requirements
        - Enforces strict schema compliance per MCP spec
        
        [Implementation details]
        - Returns cached schema model from initialization
        - Schema enforces strict validation via Config settings
        
        Returns:
            A Pydantic model class for validating input data
        """
        return self._input_schema_model

    @property
    def output_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Provides the Pydantic model class for output validation.
        
        [Design principles]
        - Type-safe schema definition using Pydantic
        - Aligned with MCP JSON Schema requirements
        - Enforces strict schema compliance per MCP spec
        
        [Implementation details]
        - Returns cached schema model from initialization
        - Schema enforces strict validation via Config settings
        
        Returns:
            A Pydantic model class for validating output data
        """
        return self._output_schema_model
    
    @property
    def metadata(self) -> Dict[str, Any]:
        """
        [Function intent]
        Provides MCP-compliant tool metadata.
        
        [Design principles]
        - Follows MCP tool metadata specification from modelcontextprotocol.io
        - Includes all required information for tool discovery
        
        [Implementation details]
        - Generates metadata based on properties and schemas
        - Converts Pydantic schemas to JSON Schema format
        - Ensures proper additionalProperties settings in schemas
        
        Returns:
            Dictionary containing MCP-compliant tool metadata
        """
        # Get schema dictionaries
        input_schema_dict = self.input_schema.schema()
        output_schema_dict = self.output_schema.schema()
        
        # Ensure additionalProperties is set to false as per MCP recommendation
        # This prevents unspecified fields from being accepted
        if 'additionalProperties' not in input_schema_dict:
            input_schema_dict['additionalProperties'] = False
            
        if 'additionalProperties' not in output_schema_dict:
            output_schema_dict['additionalProperties'] = False
        
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": input_schema_dict,
            "output_schema": output_schema_dict,
            "version": "1.0",  # Tool version (optional in MCP spec)
            "specification": "https://modelcontextprotocol.io/specification/2025-03-26"
        }

    @abstractmethod
    def _get_input_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Abstract method to define the input schema for the tool.
        
        [Design principles]
        - Uses Pydantic model for schema definition
        - Must align with MCP JSON Schema requirements
        
        [Implementation details]
        - Must be implemented by concrete tool classes
        - Should return a Pydantic BaseModel subclass
        
        Returns:
            A Pydantic model class defining the input structure
        """
        pass

    @abstractmethod
    def _get_output_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Abstract method to define the output schema for the tool.
        
        [Design principles]
        - Uses Pydantic model for schema definition
        - Must align with MCP JSON Schema requirements
        
        [Implementation details]
        - Must be implemented by concrete tool classes
        - Should return a Pydantic BaseModel subclass
        
        Returns:
            A Pydantic model class defining the output structure
        """
        pass

    @abstractmethod
    def execute(self, data: BaseModel, cancellation_token: Optional[MCPCancellationToken] = None, 
                progress_reporter: Optional[MCPProgressReporter] = None, 
                auth_context: Optional[Dict[str, Any]] = None) -> BaseModel:
        """
        [Function intent]
        Executes the core logic of the tool with validated input data.
        
        [Design principles]
        - Type-safe input and output using Pydantic models
        - Supports MCP cancellation and progress reporting
        - Clear separation of validation from business logic
        
        [Implementation details]
        - Receives pre-validated Pydantic model as input
        - Must return data conforming to output schema model
        - Abstract method to be implemented by subclasses

        Args:
            data: A Pydantic model containing the validated input parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context

        Returns:
            A Pydantic model containing the result of the tool's execution

        Raises:
            MCPError: For tool-specific execution errors
            Exception: Other exceptions will be converted to MCPError
        """
        pass
        
    def handle_json_rpc(self, request: Dict[str, Any], session: Optional[Any] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Handles JSON-RPC 2.0 requests for this tool.
        
        [Design principles]
        - Fully compliant with MCP JSON-RPC 2.0 protocol
        - Consistent error handling per JSON-RPC specification
        - Complete request validation and execution flow
        - Supports capability negotiation through session tracking
        
        [Implementation details]
        - Validates JSON-RPC request structure
        - Creates cancellation token and progress reporter
        - Executes tool and formats response according to JSON-RPC 2.0
        - Handles all errors with appropriate JSON-RPC error objects
        - Adapts behavior based on session capabilities

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
                
            if method != "executeTool":
                raise MCPError(MCPErrorCode.METHOD_NOT_FOUND, f"Method '{method}' not found")
                
            # Get parameters
            params = request.get("params", {})
            if not isinstance(params, dict):
                raise MCPError(MCPErrorCode.INVALID_PARAMS, "Params must be an object")
                
            # Set up cancellation and progress reporting based on session capabilities
            cancellation_token = None
            progress_reporter = None
            
            # Create objects only if we don't have a session or if session has the capability
            if session is None or session.has_capability("cancellation"):
                cancellation_token = MCPCancellationToken()
                
            if session is None or session.has_capability("progress_tracking"):
                progress_reporter = MCPProgressReporter()
            
            # Extract auth context if provided
            auth_context = params.get("auth_context")
            
            # Validate parameters against schema
            try:
                input_model = self.input_schema.parse_obj(params)
            except Exception as e:
                raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Invalid parameters: {str(e)}")
            
            # Execute the tool
            try:
                result = self.execute(
                    input_model, 
                    cancellation_token=cancellation_token,
                    progress_reporter=progress_reporter,
                    auth_context=auth_context
                )
                
                # Convert result to dict
                result_dict = result.dict()
                
                # Return JSON-RPC response
                return {
                    "jsonrpc": "2.0",
                    "result": result_dict,
                    "id": request_id
                }
                
            except MCPError as e:
                # Tool raised an MCP error
                error_response = e.to_json_rpc()
                error_response["jsonrpc"] = "2.0"
                error_response["id"] = request_id
                return error_response
                
            except Exception as e:
                # Unexpected error during execution
                self.logger.error(f"Error executing tool {self.name}: {str(e)}", exc_info=True)
                error = MCPError(
                    MCPErrorCode.TOOL_EXECUTION_ERROR, 
                    f"Tool execution error: {str(e)}"
                )
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
            self.logger.error(f"Internal error in tool {self.name}: {str(e)}", exc_info=True)
            error = MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
            error_response = error.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            return error_response
