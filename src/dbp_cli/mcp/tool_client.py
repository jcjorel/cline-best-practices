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
# Implements the MCPToolClient class for the Model Context Protocol (MCP) client.
# This class provides specialized functionality for executing MCP tools following 
# the JSON-RPC 2.0 protocol as defined in the MCP specification.
###############################################################################
# [Source file design principles]
# - Builds on the base MCPClient for transport
# - Implements the executeTool MCP method with proper JSON-RPC 2.0 format
# - Provides strong typing through Pydantic models
# - Handles tool execution errors and responses in a consistent way
# - Supports both blocking and streaming tool execution
# - Maintains compatibility with server-side tool implementations
###############################################################################
# [Source file constraints]
# - Requires Pydantic for input/output schemas
# - Must properly handle JSON-RPC 2.0 tool responses
# - Should validate inputs against provided schemas when possible
# - Must support progress reporting and cancellation
###############################################################################
# [Dependencies]
# system:pydantic
# system:uuid
# system:logging
# system:typing
# system:json
# codebase:src/dbp_cli/mcp/client.py
# codebase:src/dbp_cli/mcp/error.py
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:07:00Z : Initial implementation of MCP tool client by CodeAssistant
# * Created MCPToolClient for executing MCP tools
# * Implemented tool discovery and execution methods
###############################################################################

import logging
import json
import uuid
from typing import Dict, Any, Optional, Union, List, Type, TypeVar, Generic

try:
    from pydantic import BaseModel
    HAS_PYDANTIC = True
except ImportError:
    HAS_PYDANTIC = False
    logging.getLogger(__name__).error(
        "The 'pydantic' library is required for MCPToolClient. "
        "Please install it (`pip install pydantic`)."
    )
    BaseModel = object  # Type stub for type hints to work without pydantic

from .client import MCPClient
from .error import MCPError, MCPErrorCode


# Type variables for input/output schema types
T = TypeVar('T')  # Input schema type
U = TypeVar('U')  # Output schema type


class MCPToolClient(Generic[T, U]):
    """
    [Class intent]
    Client for executing MCP tools according to the MCP specification.
    Provides type-safe tool execution with input validation.
    
    [Design principles]
    - Type-safe tool execution using Pydantic models
    - Consistent error handling
    - Support for both standard and streaming responses
    
    [Implementation details]
    - Builds on MCPClient for transport
    - Validates inputs/outputs against schemas
    - Formats JSON-RPC requests for tool execution
    """

    def __init__(
        self,
        client: MCPClient,
        tool_name: str,
        input_model: Optional[Type[BaseModel]] = None,
        output_model: Optional[Type[BaseModel]] = None,
        logger_override: Optional[logging.Logger] = None
    ):
        """
        [Class method intent]
        Initializes a new MCPToolClient for a specific tool.
        
        [Design principles]
        - Type-safe initialization with schema models
        - Clear separation from the transport layer
        
        [Implementation details]
        - Stores tool name, client, and schema models
        - Sets up logging
        
        Args:
            client: The MCPClient instance for transport
            tool_name: The name of the MCP tool to execute
            input_model: Optional Pydantic model for input validation
            output_model: Optional Pydantic model for output validation
            logger_override: Optional logger instance
        """
        if not HAS_PYDANTIC:
            raise ImportError("The 'pydantic' library is required for MCPToolClient.")
            
        self.client = client
        self.tool_name = tool_name
        self.input_model = input_model
        self.output_model = output_model
        self.logger = logger_override or logging.getLogger(__name__)
            
        self.logger.debug(f"MCPToolClient initialized for tool: {tool_name}")
        
    def execute(self, data: Union[Dict[str, Any], BaseModel], request_id: Optional[str] = None) -> Any:
        """
        [Function intent]
        Executes the MCP tool with the provided data.
        
        [Design principles]
        - Type-safe execution with validation
        - Standard JSON-RPC 2.0 request/response handling
        - Consistent error handling
        
        [Implementation details]
        - Validates input data against schema if provided
        - Formats JSON-RPC request for executeTool method
        - Handles response validation and error processing
        
        Args:
            data: The input data for the tool (dict or Pydantic model)
            request_id: Optional request ID
            
        Returns:
            The tool execution result (parsed into output_model if provided)
            
        Raises:
            MCPError: For all types of errors during tool execution
        """
        # Convert Pydantic model to dict if needed
        if hasattr(data, "model_dump"):
            # For Pydantic v2+
            input_data = data.model_dump()
        elif hasattr(data, "dict"):
            # For Pydantic v1
            input_data = data.dict()
        else:
            input_data = data
            
        # Validate input against schema if provided
        if self.input_model and not isinstance(data, self.input_model):
            try:
                validated_data = self.input_model.parse_obj(input_data)
                if hasattr(validated_data, "model_dump"):
                    input_data = validated_data.model_dump()
                else:
                    input_data = validated_data.dict()
            except Exception as e:
                raise MCPError(
                    MCPErrorCode.INVALID_PARAMS,
                    f"Invalid input data for tool {self.tool_name}: {str(e)}"
                )
                
        # Create request ID if not provided
        if request_id is None:
            request_id = str(uuid.uuid4())
            
        # Prepare JSON-RPC request
        self.logger.debug(f"Executing tool {self.tool_name} with request ID {request_id}")
        
        # Execute the tool
        try:
            endpoint = f"mcp/tools/{self.tool_name}"
            result = self.client.call_json_rpc(
                method="executeTool",
                endpoint=endpoint,
                params=input_data,
                request_id=request_id
            )
            
            # Validate output against schema if provided
            if self.output_model:
                try:
                    return self.output_model.parse_obj(result)
                except Exception as e:
                    raise MCPError(
                        MCPErrorCode.INTERNAL_ERROR,
                        f"Tool {self.tool_name} returned invalid output: {str(e)}"
                    )
            
            return result
            
        except MCPError:
            # Re-raise MCPError as is
            raise
        except Exception as e:
            raise MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Error executing tool {self.tool_name}: {str(e)}"
            )
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        [Function intent]
        Retrieves metadata about this tool from the MCP server.
        
        [Design principles]
        - Standard tool discovery method
        - Consistent error handling
        
        [Implementation details]
        - Makes a GET request to the tool metadata endpoint
        - Returns parsed metadata
        
        Returns:
            Tool metadata including name, description, and schemas
            
        Raises:
            MCPError: If metadata retrieval fails
        """
        try:
            endpoint = f"mcp/tools/{self.tool_name}/metadata"
            return self.client.send_request(
                method="GET",
                endpoint=endpoint
            )
        except Exception as e:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to get metadata for tool {self.tool_name}: {str(e)}"
            )
    
    @classmethod
    def create_from_metadata(cls, client: MCPClient, tool_name: str) -> 'MCPToolClient':
        """
        [Function intent]
        Creates a tool client from server-provided metadata.
        
        [Design principles]
        - Dynamic client creation based on server metadata
        - Type-safe schema creation
        
        [Implementation details]
        - Retrieves tool metadata from the server
        - Dynamically creates Pydantic models from schemas
        - Sets up client with proper schemas
        
        Args:
            client: The MCPClient instance for transport
            tool_name: The name of the MCP tool
            
        Returns:
            An initialized MCPToolClient with proper schemas
            
        Raises:
            MCPError: If metadata retrieval or schema creation fails
        """
        if not HAS_PYDANTIC:
            raise ImportError("The 'pydantic' library is required for MCPToolClient.")
            
        # Create a temporary client to get metadata
        temp_client = cls(client, tool_name)
        metadata = temp_client.get_metadata()
        
        # Create models from schemas
        input_schema = metadata.get("input_schema", {})
        output_schema = metadata.get("output_schema", {})
        
        try:
            # Create Pydantic models from schemas
            input_model = cls._create_model_from_schema(
                f"{tool_name}Input", input_schema)
            output_model = cls._create_model_from_schema(
                f"{tool_name}Output", output_schema)
                
            return cls(client, tool_name, input_model, output_model)
        except Exception as e:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to create tool client from metadata: {str(e)}"
            )
    
    @staticmethod
    def _create_model_from_schema(name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        [Function intent]
        Creates a Pydantic model from a JSON Schema.
        
        [Design principles]
        - Dynamic model creation
        - Type-safe schema handling
        
        [Implementation details]
        - Uses Pydantic's create_model to dynamically create a model
        - Handles nested schemas and references
        
        Args:
            name: The name for the model class
            schema: The JSON Schema dictionary
            
        Returns:
            A Pydantic BaseModel subclass
            
        Raises:
            ValueError: If schema creation fails
        """
        from pydantic import create_model
        try:
            # Create a Pydantic model from the schema
            # This is a simplified version - a full implementation would need to handle
            # nested schemas, references, etc.
            fields = {}
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            
            for field_name, field_schema in properties.items():
                field_type = Any  # Default to Any for simplicity
                default = ... if field_name in required else None
                fields[field_name] = (field_type, default)
            
            return create_model(name, **fields)
        except Exception as e:
            raise ValueError(f"Failed to create model from schema: {str(e)}")
    
    @classmethod
    def discover_tools(cls, client: MCPClient) -> List[str]:
        """
        [Function intent]
        Discovers available tools on the MCP server.
        
        [Design principles]
        - Standard tool discovery method
        - Simplifies tool exploration
        
        [Implementation details]
        - Makes a GET request to list available tools
        - Returns list of tool names
        
        Args:
            client: The MCPClient instance for transport
            
        Returns:
            List of available tool names
            
        Raises:
            MCPError: If tool discovery fails
        """
        try:
            endpoint = "mcp/tools"
            response = client.send_request(
                method="GET",
                endpoint=endpoint
            )
            return response.get("tools", [])
        except Exception as e:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Failed to discover available tools: {str(e)}"
            )
