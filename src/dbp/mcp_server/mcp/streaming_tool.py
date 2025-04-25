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
# Provides a streaming-capable MCP tool implementation that extends the base MCPTool
# class. This allows tools to return large amounts of data incrementally using
# streaming responses rather than waiting for complete results.
###############################################################################
# [Source file design principles]
# - Extends MCPTool with streaming capabilities
# - Uses asyncio for non-blocking streaming
# - Maintains JSON-RPC 2.0 compatibility
# - Integrates with FastAPI streaming responses
# - Compatible with existing MCP tool capabilities
###############################################################################
# [Source file constraints]
# - Must support both streaming and non-streaming responses
# - Must handle serialization of various data types
# - Must support cancellation during streaming
###############################################################################
# [Dependencies]
# system:asyncio
# system:pydantic
# system:typing
# codebase:src/dbp/mcp_server/mcp/tool.py
# codebase:src/dbp/mcp_server/mcp/streaming.py
# codebase:src/dbp/mcp_server/mcp/error.py
# codebase:src/dbp/mcp_server/mcp/cancellation.py
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T22:47:30Z : Initial implementation of streaming-capable MCP tool by CodeAssistant
# * Created MCPStreamingTool class extending MCPTool
# * Implemented streaming support in handle_json_rpc
# * Added streaming response generation with FastAPI integration
###############################################################################

import abc
import asyncio
import logging
from typing import Dict, Any, Optional, AsyncGenerator, Type, Union, List

from fastapi import Response
from pydantic import BaseModel

from .tool import MCPTool
from .streaming import MCPStreamingResponse, StreamFormat, create_streaming_generator
from .error import MCPError, MCPErrorCode
from .cancellation import MCPCancellationToken
from .progress import MCPProgressReporter

logger = logging.getLogger(__name__)


class MCPStreamingTool(MCPTool):
    """
    [Class intent]
    Abstract base class for MCP tools that support streaming responses.
    Extends the standard MCPTool class with streaming capabilities.
    
    [Design principles]
    - Maintains compatibility with base MCPTool interface
    - Adds streaming-specific methods and overrides
    - Supports both JSON and event-stream formats
    
    [Implementation details]
    - Uses asyncio for non-blocking streaming
    - Integrates with FastAPI streaming responses
    - Maintains JSON-RPC 2.0 compatibility for each chunk
    """
    
    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        [Class method intent]
        Initializes a streaming-capable MCP tool.
        
        [Design principles]
        - Extends MCPTool initialization
        - Maintains backward compatibility
        
        [Implementation details]
        - Calls parent constructor with same parameters
        - Sets up stream format defaults
        
        Args:
            name: The unique identifier name for this tool
            description: A human-readable description of the tool's purpose
            logger_override: Optional logger instance
        """
        super().__init__(name, description, logger_override)
        self._supports_streaming = True
        self._default_stream_format = StreamFormat.JSON_CHUNKS
        
    @property
    def supports_streaming(self) -> bool:
        """Whether this tool supports streaming responses."""
        return self._supports_streaming
    
    @abc.abstractmethod
    async def execute_streaming(
        self,
        data: BaseModel,
        cancellation_token: Optional[MCPCancellationToken] = None,
        progress_reporter: Optional[MCPProgressReporter] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        stream_format: StreamFormat = None
    ) -> AsyncGenerator[Any, None]:
        """
        [Function intent]
        Executes the tool's logic and returns an async generator for streaming results.
        This is the core method that streaming tools must implement.
        
        [Design principles]
        - Similar interface to execute() but returns an async generator
        - Supports cancellation and progress reporting
        - Abstract method to be implemented by concrete tool classes
        
        [Implementation details]
        - Must be implemented by concrete streaming tool classes
        - Should yield data chunks that can be serialized to JSON
        - Should check cancellation between chunks
        
        Args:
            data: A Pydantic model containing the validated input parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context
            stream_format: Optional format override for the stream
            
        Yields:
            Data chunks for streaming to the client
            
        Raises:
            MCPError: For tool-specific execution errors
            Exception: Other exceptions will be converted to MCPError
        """
        pass
    
    def execute(
        self,
        data: BaseModel,
        cancellation_token: Optional[MCPCancellationToken] = None,
        progress_reporter: Optional[MCPProgressReporter] = None,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> BaseModel:
        """
        [Function intent]
        Non-streaming execution fallback for streaming tools.
        
        [Design principles]
        - Maintains compatibility with base MCPTool interface
        - Allows streaming tools to also work in non-streaming mode
        
        [Implementation details]
        - Default implementation raises NotImplementedError
        - Concrete classes can override to provide non-streaming behavior
        
        Args:
            data: A Pydantic model containing the validated input parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context
            
        Returns:
            A Pydantic model containing the result of the tool's execution
            
        Raises:
            NotImplementedError: By default, as streaming tools may not support non-streaming execution
        """
        raise NotImplementedError(
            f"Tool '{self.name}' is a streaming tool and does not support non-streaming execution. "
            "Use handle_streaming_request() instead or override execute() in your subclass."
        )
    
    async def handle_streaming_request(
        self,
        request: Dict[str, Any],
        session: Optional[Any] = None,
        stream_format: StreamFormat = None
    ) -> AsyncGenerator[str, None]:
        """
        [Function intent]
        Handles a JSON-RPC request for this tool with streaming response.
        
        [Design principles]
        - Similar to handle_json_rpc but returns an async generator
        - Handles all JSON-RPC protocol aspects
        - Properly formats streaming responses
        
        [Implementation details]
        - Validates request format and parameters
        - Sets up cancellation and progress tracking
        - Calls execute_streaming and streams results
        - Handles errors during streaming
        
        Args:
            request: A dictionary containing the JSON-RPC request
            session: Optional session object from capability negotiation
            stream_format: Optional format override for the stream
            
        Yields:
            Formatted stream chunks according to the specified format
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
            
            # Get stream format if specified in params
            requested_format = params.get("stream_format")
            if requested_format:
                try:
                    format_enum = StreamFormat(requested_format)
                    stream_format = format_enum
                except ValueError:
                    # Invalid format, use default
                    self.logger.warning(f"Invalid stream format requested: {requested_format}")
                    
            # Use specified format or default
            final_format = stream_format or self._default_stream_format
                
            # Validate parameters against schema
            try:
                input_model = self.input_schema.parse_obj(params)
            except Exception as e:
                raise MCPError(MCPErrorCode.INVALID_PARAMS, f"Invalid parameters: {str(e)}")
            
            # Create streaming response handler
            response_handler = MCPStreamingResponse(format=final_format)
            
            # Execute the streaming tool
            try:
                generator = self.execute_streaming(
                    input_model,
                    cancellation_token=cancellation_token,
                    progress_reporter=progress_reporter,
                    auth_context=auth_context,
                    stream_format=final_format
                )
                
                # Stream results through response handler
                async for chunk in response_handler.stream(generator, request_id, cancellation_token):
                    yield chunk
                    
            except MCPError as e:
                # Tool raised an MCP error
                self.logger.error(f"MCP error in streaming tool {self.name}: {str(e)}")
                error_response = e.to_json_rpc()
                error_response["jsonrpc"] = "2.0"
                error_response["id"] = request_id
                yield f"{error_response}\n"
                
            except Exception as e:
                # Unexpected error during execution
                self.logger.error(f"Error executing streaming tool {self.name}: {str(e)}", exc_info=True)
                error = MCPError(
                    MCPErrorCode.TOOL_EXECUTION_ERROR, 
                    f"Tool execution error: {str(e)}"
                )
                error_response = error.to_json_rpc()
                error_response["jsonrpc"] = "2.0"
                error_response["id"] = request_id
                yield f"{error_response}\n"
                
        except MCPError as e:
            # JSON-RPC protocol error
            self.logger.error(f"Protocol error in streaming tool {self.name}: {str(e)}")
            error_response = e.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            yield f"{error_response}\n"
            
        except Exception as e:
            # Unexpected error during request handling
            self.logger.error(f"Internal error in streaming tool {self.name}: {str(e)}", exc_info=True)
            error = MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                f"Internal error: {str(e)}"
            )
            error_response = error.to_json_rpc()
            error_response["jsonrpc"] = "2.0"
            error_response["id"] = request_id
            yield f"{error_response}\n"
    
    def handle_json_rpc(self, request: Dict[str, Any], session: Optional[Any] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Handles JSON-RPC 2.0 requests for this tool, detecting streaming requests.
        
        [Design principles]
        - Override of base MCPTool method
        - Detects streaming requests and delegates to streaming handler
        - Falls back to non-streaming behavior if streaming not requested
        
        [Implementation details]
        - Checks for streaming parameter in the request
        - For streaming requests, returns a special response object
        - For non-streaming requests, calls parent implementation
        
        Args:
            request: A dictionary containing the JSON-RPC request
            session: Optional session object from capability negotiation
            
        Returns:
            Either a standard JSON-RPC response or a special streaming response object
        """
        # Check if request specifies streaming
        if isinstance(request, dict) and isinstance(request.get("params"), dict):
            streaming_requested = request["params"].get("streaming", False)
            
            if streaming_requested:
                # If client requested streaming and both client and server support it
                client_supports_streaming = session and session.has_capability("streaming")
                
                if client_supports_streaming or not session:
                    # Return a special response that FastAPI handlers will recognize
                    # This is a placeholder that will be replaced with the actual streaming response
                    return {
                        "_streaming_handler": self,
                        "_request": request,
                        "_session": session
                    }
        
        # For non-streaming requests, call the parent implementation
        return super().handle_json_rpc(request, session)
    

class StreamingResponse:
    """
    [Class intent]
    A simple wrapper for FastAPI streaming responses.
    This allows us to return a streaming response from an MCP tool.
    
    [Design principles]
    - Simple interface for FastAPI streaming integration
    - Handles content type and other response parameters
    
    [Implementation details]
    - Creates a FastAPI StreamingResponse with appropriate content type
    - Connects to the streaming tool's handler
    """
    
    def __init__(
        self, 
        generator: AsyncGenerator[str, None],
        content_type: str = "application/x-ndjson",
        status_code: int = 200
    ):
        """
        [Class method intent]
        Creates a new streaming response.
        
        [Design principles]
        - Simple constructor with reasonable defaults
        
        [Implementation details]
        - Stores parameters for later use by FastAPI
        
        Args:
            generator: Async generator producing the response chunks
            content_type: MIME type for the response
            status_code: HTTP status code
        """
        self.generator = generator
        self.content_type = content_type
        self.status_code = status_code
    
    def create_response(self) -> Response:
        """
        [Function intent]
        Creates a FastAPI streaming response.
        
        [Design principles]
        - Integration with FastAPI's response system
        
        [Implementation details]
        - Uses FastAPI's StreamingResponse class
        
        Returns:
            FastAPI StreamingResponse object
        """
        from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
        return FastAPIStreamingResponse(
            self.generator,
            media_type=self.content_type,
            status_code=self.status_code
        )
