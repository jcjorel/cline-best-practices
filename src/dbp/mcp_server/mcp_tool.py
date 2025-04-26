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
# Provides a base class for MCP tools that simplifies implementation and unifies
# the API for both streaming and non-streaming tools. This class abstracts away
# the MCP protocol details and provides a clean interface for tool developers.
###############################################################################
# [Source file design principles]
# - Hides MCP machinery from tool implementations
# - Provides a unified streaming API regardless of client capabilities
# - Follows a stream-first design where tools should only implement stream() method
# - By design, execute() should NOT be overridden in most cases as it automatically
#   collects chunks from stream() to provide non-streaming responses
# - Allows access to full FastMCP features when needed
# - Handles conversion between streaming and non-streaming responses
# - Follows a clean, inheritance-based design pattern
###############################################################################
# [Source file constraints]
# - Must be compatible with FastMCP's tool registration mechanism
# - Must maintain backward compatibility with existing tools
# - Must handle both streaming and non-streaming clients transparently
###############################################################################
# [Dependencies]
# system:asyncio
# system:typing
# system:pydantic
# system:fastmcp
# codebase:src/dbp/mcp_server/server.py
###############################################################################
# [GenAI tool change history]
# 2025-04-27T01:50:00Z : Updated imports for Tool and StreamingTool classes by CodeAssistant
# * Changed imports from fastmcp.tool and fastmcp.streaming to fastmcp.tools to match FastMCP v2 structure
# 2025-04-27T00:55:00Z : Simplified MCPTool class hierarchy by CodeAssistant
# * Made execute() non-abstract with default implementation that collects chunks from stream()
# * Removed SimpleMCPTool class as its functionality is now part of MCPTool
# * Maintained backward compatibility with existing tools
# * Simplified API by requiring only stream() method implementation
# 2025-04-27T00:37:00Z : Created MCPTool base class by CodeAssistant
# * Implemented unified streaming API for MCP tools
# * Added automatic conversion between streaming and non-streaming responses
# * Created abstract methods for tool implementation
# * Added support for progress reporting and cancellation
###############################################################################

import asyncio
import inspect
import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Generic, 
    AsyncGenerator, AsyncIterable, Union, get_type_hints, cast
)

from pydantic import BaseModel, Field, create_model

from fastmcp import FastMCP
from fastmcp.tools import Tool
from fastmcp.tools import StreamingTool

logger = logging.getLogger(__name__)

# Type variables for input and output models
InputType = TypeVar('InputType', bound=BaseModel)
OutputType = TypeVar('OutputType', bound=BaseModel)
ChunkType = TypeVar('ChunkType', bound=BaseModel)


class MCPTool(Generic[InputType, OutputType, ChunkType], ABC):
    """
    [Class intent]
    Base class for MCP tools that provides a unified streaming API and hides MCP machinery.
    This class simplifies tool implementation by providing a consistent interface
    regardless of whether the client supports streaming or not.
    
    [Design principles]
    - Unified streaming API for all tools
    - Automatic conversion between streaming and non-streaming responses
    - Clean separation between tool logic and MCP protocol details
    - Support for progress reporting and cancellation
    
    [Implementation details]
    - Uses FastMCP's Tool and StreamingTool classes under the hood
    - Registers both streaming and non-streaming versions of the tool
    - Handles conversion between streaming and non-streaming responses
    - Provides access to context for progress reporting and cancellation
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        input_model: Type[InputType],
        output_model: Type[OutputType],
        chunk_model: Type[ChunkType],
        version: str = "1.0.0",
    ):
        """
        [Class method intent]
        Initializes the MCP tool with the required metadata and models.
        
        [Design principles]
        Clear initialization with all required metadata.
        
        [Implementation details]
        Stores tool metadata and models for later registration.
        
        Args:
            name: The name of the tool
            description: A description of what the tool does
            input_model: The Pydantic model for the tool's input
            output_model: The Pydantic model for the tool's output
            chunk_model: The Pydantic model for streaming chunks
            version: The version of the tool
        """
        self.name = name
        self.description = description
        self.input_model = input_model
        self.output_model = output_model
        self.chunk_model = chunk_model
        self.version = version
        self.logger = logging.getLogger(f"dbp.mcp_server.tools.{name}")
        
        # These will be set when the tool is registered
        self._tool = None
        self._streaming_tool = None
        
    def register(self, mcp: FastMCP) -> None:
        """
        [Function intent]
        Registers the tool with the FastMCP instance.
        
        [Design principles]
        Handles registration of both streaming and non-streaming versions.
        
        [Implementation details]
        Creates and registers both Tool and StreamingTool instances.
        
        Args:
            mcp: The FastMCP instance to register with
        """
        # Create and register the non-streaming tool
        self._tool = Tool(
            name=self.name,
            description=self.description,
            input_schema=self.input_model,
            output_schema=self.output_model,
            version=self.version,
            execute=self._execute_wrapper
        )
        mcp.register_tool(self._tool)
        
        # Create and register the streaming tool
        self._streaming_tool = StreamingTool(
            name=f"{self.name}_stream",
            description=f"Streaming version of {self.description}",
            input_schema=self.input_model,
            output_schema=self.output_model,
            version=self.version
        )
        self._streaming_tool.execute = self._execute_wrapper
        self._streaming_tool.stream = self._stream_wrapper
        mcp.register_tool(self._streaming_tool)
        
        self.logger.info(f"Registered tool '{self.name}' and '{self.name}_stream'")
        
    async def _execute_wrapper(
        self,
        data: InputType,
        context: Optional[Dict[str, Any]] = None
    ) -> OutputType:
        """
        [Function intent]
        Wrapper for the execute method that handles context preparation.
        
        [Design principles]
        Prepares context for tool execution and handles exceptions.
        
        [Implementation details]
        Calls the execute method with prepared context.
        
        Args:
            data: The validated input data
            context: The execution context
            
        Returns:
            The tool's output
        """
        prepared_context = self._prepare_context(context)
        
        try:
            # For non-streaming clients, we need to collect all chunks
            # and build the final result
            if not self._is_streaming_requested(data, context):
                result = await self._collect_chunks_to_result(data, prepared_context)
                return result
            
            # For streaming clients, just call execute directly
            return await self.execute(data, prepared_context)
            
        except Exception as e:
            self.logger.error(f"Error executing tool '{self.name}': {str(e)}", exc_info=True)
            raise
            
    async def _stream_wrapper(
        self,
        data: InputType,
        context: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Function intent]
        Wrapper for the stream method that handles context preparation.
        
        [Design principles]
        Prepares context for tool streaming and handles exceptions.
        
        [Implementation details]
        Calls the stream method with prepared context.
        
        Args:
            data: The validated input data
            context: The execution context
            
        Yields:
            Chunks of the tool's output
        """
        prepared_context = self._prepare_context(context)
        
        try:
            async for chunk in self.stream(data, prepared_context):
                # Convert chunk to dict if it's a Pydantic model
                if isinstance(chunk, BaseModel):
                    yield chunk.dict()
                else:
                    yield chunk
                    
        except Exception as e:
            self.logger.error(f"Error streaming from tool '{self.name}': {str(e)}", exc_info=True)
            raise
            
    def _prepare_context(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Prepares the context for tool execution.
        
        [Design principles]
        Ensures context has all required fields.
        
        [Implementation details]
        Adds progress reporting and cancellation callbacks.
        
        Args:
            context: The original context
            
        Returns:
            The prepared context
        """
        prepared_context = context.copy() if context else {}
        
        # Add progress reporting if not present
        if "progress_callback" not in prepared_context:
            prepared_context["progress_callback"] = self._default_progress_callback
            
        # Add cancellation check if not present
        if "is_cancelled" not in prepared_context:
            prepared_context["is_cancelled"] = self._default_is_cancelled
            
        return prepared_context
        
    def _default_progress_callback(self, progress: float, message: str = "") -> None:
        """
        [Function intent]
        Default progress reporting callback.
        
        [Design principles]
        Provides a no-op default implementation.
        
        [Implementation details]
        Logs progress but doesn't do anything else.
        
        Args:
            progress: Progress value between 0 and 1
            message: Optional progress message
        """
        self.logger.debug(f"Progress: {progress:.2%} - {message}")
        
    def _default_is_cancelled(self) -> bool:
        """
        [Function intent]
        Default cancellation check.
        
        [Design principles]
        Provides a no-op default implementation.
        
        [Implementation details]
        Always returns False.
        
        Returns:
            False, indicating not cancelled
        """
        return False
        
    def _is_streaming_requested(
        self,
        data: InputType,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        [Function intent]
        Determines if streaming is requested by the client.
        
        [Design principles]
        Checks both data and context for streaming flags.
        
        [Implementation details]
        Looks for streaming flags in data and context.
        
        Args:
            data: The input data
            context: The execution context
            
        Returns:
            True if streaming is requested, False otherwise
        """
        # Check if data has a streaming field
        if hasattr(data, "streaming") and getattr(data, "streaming") is True:
            return True
            
        # Check if context has a streaming flag
        if context and context.get("streaming") is True:
            return True
            
        return False
        
    async def _collect_chunks_to_result(
        self,
        data: InputType,
        context: Dict[str, Any]
    ) -> OutputType:
        """
        [Function intent]
        Collects streaming chunks into a final result.
        
        [Design principles]
        Converts streaming output to non-streaming output.
        
        [Implementation details]
        Collects chunks from stream method and builds final result.
        
        Args:
            data: The input data
            context: The execution context
            
        Returns:
            The final result
        """
        chunks = []
        
        # Collect all chunks
        async for chunk in self.stream(data, context):
            chunks.append(chunk)
            
        # Build the final result
        return self._build_result_from_chunks(chunks)
        
    def _build_result_from_chunks(self, chunks: List[ChunkType]) -> OutputType:
        """
        [Function intent]
        Builds a final result from collected chunks.
        
        [Design principles]
        Converts a list of chunks to a single output.
        
        [Implementation details]
        Default implementation creates a result with a list of chunks.
        
        Args:
            chunks: The collected chunks
            
        Returns:
            The final result
        """
        # Get the field names of the output model
        output_fields = self.output_model.__fields__
        
        # Check if the output model has a 'result' field
        if "result" in output_fields:
            # Create a result with the chunks in the 'result' field
            return self.output_model(
                result=chunks,
                total_items=len(chunks)
            )
            
        # If there's no 'result' field, try to build the result
        # based on the first chunk's fields
        if chunks and isinstance(chunks[0], BaseModel):
            # Get the field names of the first chunk
            chunk_fields = chunks[0].__fields__
            
            # Create a dictionary with the fields from the first chunk
            result_dict = {
                field: getattr(chunks[0], field)
                for field in chunk_fields
                if field in output_fields
            }
            
            # Add any additional fields required by the output model
            for field in output_fields:
                if field not in result_dict:
                    if field == "total_items":
                        result_dict[field] = len(chunks)
                    elif field == "items" or field == "chunks":
                        result_dict[field] = chunks
                        
            # Create the output model instance
            return self.output_model(**result_dict)
            
        # If we can't build a result, raise an exception
        raise ValueError(
            f"Cannot build result from chunks. Override _build_result_from_chunks "
            f"in your tool implementation to handle this case."
        )
        
    async def execute(
        self,
        data: InputType,
        context: Dict[str, Any]
    ) -> OutputType:
        """
        [Function intent]
        Executes the tool and returns a complete result.
        
        [Design principles]
        Default implementation that collects chunks from stream method.
        
        IMPORTANT: By design, this method should NOT be overridden in most cases.
        The recommended pattern is to only implement the stream() method, and this
        default implementation will handle the conversion from streaming to non-streaming.
        Override this method ONLY in exceptional cases where you need custom non-streaming
        behavior that cannot be achieved through the stream() method.
        
        [Implementation details]
        Collects all chunks from stream method and builds the final result.
        
        Args:
            data: The validated input data
            context: The execution context
            
        Returns:
            The tool's output
        """
        return await self._collect_chunks_to_result(data, context)
        
    @abstractmethod
    async def stream(
        self,
        data: InputType,
        context: Dict[str, Any]
    ) -> AsyncIterable[ChunkType]:
        """
        [Function intent]
        Streams the tool's output as chunks.
        
        [Design principles]
        Abstract method that must be implemented by subclasses.
        
        [Implementation details]
        Should implement the tool's logic for streaming execution.
        
        Args:
            data: The validated input data
            context: The execution context
            
        Yields:
            Chunks of the tool's output
        """
        pass
