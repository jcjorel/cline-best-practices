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
# Provides a sample implementation of a streaming-capable MCP tool.
# This serves as an example and reference for creating custom streaming tools.
###############################################################################
# [Source file design principles]
# - Demonstrates proper MCPStreamingTool implementation pattern
# - Shows how to yield data chunks incrementally
# - Includes examples for different streaming scenarios
# - Handles cancellation and progress reporting
###############################################################################
# [Source file constraints]
# - For demonstration purposes only, not for production use
# - Does not perform any actual meaningful operations
###############################################################################
# [Dependencies]
# system:asyncio
# system:typing
# system:pydantic
# codebase:src/dbp/mcp_server/mcp/streaming_tool.py
# codebase:src/dbp/mcp_server/mcp/streaming.py
###############################################################################
# [GenAI tool change history]
# 2025-04-25T22:53:00Z : Initial implementation of sample streaming tool by CodeAssistant
# * Created SampleStreamingTool class extending MCPStreamingTool
# * Added example streaming implementation
# * Added sample input/output schemas
###############################################################################

import asyncio
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, AsyncGenerator

from pydantic import BaseModel, Field

from src.dbp.mcp_server.mcp_protocols import (
    MCPStreamingTool, 
    MCPCancellationToken, 
    MCPProgressReporter,
    StreamFormat,
    create_streaming_generator
)

logger = logging.getLogger(__name__)


# Input schema model for the sample tool
class SampleToolInput(BaseModel):
    """
    [Class intent]
    Defines the input parameters for the sample streaming tool.
    
    [Design principles]
    Simple model with configurable options for testing streaming behavior.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    item_count: int = Field(default=10, description="Number of items to generate in the stream")
    delay_seconds: float = Field(default=0.5, description="Delay between items in seconds")
    streaming: bool = Field(default=True, description="Whether to use streaming response")
    stream_format: Optional[str] = Field(default="json_chunks", description="Stream format (json_chunks or event_stream)")
    fail_at_item: Optional[int] = Field(default=None, description="Item number at which to simulate a failure")


# Output schema model for the sample tool
class SampleToolOutput(BaseModel):
    """
    [Class intent]
    Defines the output format for the sample streaming tool.
    
    [Design principles]
    Simple model for demonstration purposes.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    result: List[Dict[str, Any]] = Field(description="List of items in the result")
    total_items: int = Field(description="Total number of items processed")


# Sample item schema for streaming chunks
class StreamItem(BaseModel):
    """
    [Class intent]
    Defines the format of each item in the stream.
    
    [Design principles]
    Simple model for demonstration purposes.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    item_id: int = Field(description="Unique identifier for this item")
    content: str = Field(description="Content of this item")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for this item")


class SampleStreamingTool(MCPStreamingTool):
    """
    [Class intent]
    Demonstrates a basic streaming tool implementation.
    
    [Design principles]
    - Shows proper inheritance from MCPStreamingTool
    - Implements required abstract methods
    - Demonstrates streaming pattern with asyncio
    
    [Implementation details]
    - Uses asyncio for non-blocking streaming
    - Simulates data generation with configurable delay
    - Handles cancellation and progress reporting
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes the sample streaming tool.
        
        [Design principles]
        Simple initialization with clear name and description.
        
        [Implementation details]
        Calls parent constructor with tool name and description.
        """
        super().__init__(
            name="sample_stream",
            description="A sample tool demonstrating MCP streaming capabilities"
        )
        self.logger.info("SampleStreamingTool initialized")
    
    def _get_input_schema(self):
        """
        [Function intent]
        Provides the input schema for this tool.
        
        [Design principles]
        Use of Pydantic model for schema definition.
        
        [Implementation details]
        Returns the SampleToolInput model class.
        
        Returns:
            The Pydantic model class for input validation
        """
        return SampleToolInput
    
    def _get_output_schema(self):
        """
        [Function intent]
        Provides the output schema for this tool.
        
        [Design principles]
        Use of Pydantic model for schema definition.
        
        [Implementation details]
        Returns the SampleToolOutput model class.
        
        Returns:
            The Pydantic model class for output validation
        """
        return SampleToolOutput
    
    def execute(
        self,
        data: SampleToolInput,
        cancellation_token: Optional[MCPCancellationToken] = None,
        progress_reporter: Optional[MCPProgressReporter] = None,
        auth_context: Optional[Dict[str, Any]] = None
    ) -> SampleToolOutput:
        """
        [Function intent]
        Executes the tool in non-streaming mode.
        
        [Design principles]
        - Overrides parent method for non-streaming execution
        - Generates all results at once for non-streaming response
        
        [Implementation details]
        - Builds complete result set immediately
        - Used when client doesn't request streaming
        
        Args:
            data: The validated input parameters
            cancellation_token: Optional cancellation support
            progress_reporter: Optional progress reporting
            auth_context: Optional authentication context
            
        Returns:
            Complete result object with all items
        """
        # For non-streaming execution, generate all items immediately
        self.logger.info(f"Executing sample tool in non-streaming mode with {data.item_count} items")
        
        # Build items list
        items = []
        for i in range(data.item_count):
            # Check for simulated failure
            if data.fail_at_item is not None and i + 1 == data.fail_at_item:
                raise ValueError(f"Simulated failure at item {i + 1}")
                
            # Create an item
            item = {
                "item_id": i + 1,
                "content": f"Content for item {i + 1}",
                "metadata": {
                    "timestamp": f"2025-04-25T22:{i:02d}:00Z",
                    "type": "sample"
                }
            }
            items.append(item)
            
            # Report progress if reporter is provided
            if progress_reporter:
                progress = (i + 1) / data.item_count
                progress_reporter.report_progress(progress, f"Processed item {i + 1}/{data.item_count}")
                
            # Check for cancellation if token is provided
            if cancellation_token and cancellation_token.is_cancelled():
                self.logger.info("Operation cancelled")
                break
        
        # Return complete result
        return SampleToolOutput(
            result=items,
            total_items=len(items)
        )
    
    async def execute_streaming(
        self,
        data: SampleToolInput,
        cancellation_token: Optional[MCPCancellationToken] = None,
        progress_reporter: Optional[MCPProgressReporter] = None,
        auth_context: Optional[Dict[str, Any]] = None,
        stream_format: Optional[StreamFormat] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Function intent]
        Executes the tool in streaming mode, yielding results incrementally.
        
        [Design principles]
        - Core method for streaming implementation
        - Yields data incrementally with delay
        - Supports cancellation and progress reporting
        
        [Implementation details]
        - Uses asyncio.sleep for non-blocking delays
        - Checks cancellation between items
        - Reports progress throughout execution
        - Returns an async generator yielding individual items
        
        Args:
            data: The validated input parameters
            cancellation_token: Optional cancellation support
            progress_reporter: Optional progress reporting
            auth_context: Optional authentication context
            stream_format: Optional format override
            
        Yields:
            Individual stream items as they're generated
        """
        self.logger.info(f"Executing sample tool in streaming mode with {data.item_count} items")
        
        # Generate items with delay
        for i in range(data.item_count):
            # Add delay between items
            if i > 0 and data.delay_seconds > 0:
                await asyncio.sleep(data.delay_seconds)
                
            # Check for simulated failure
            if data.fail_at_item is not None and i + 1 == data.fail_at_item:
                raise ValueError(f"Simulated failure at item {i + 1}")
                
            # Create and yield an item
            item = StreamItem(
                item_id=i + 1,
                content=f"Content for item {i + 1}",
                metadata={
                    "timestamp": f"2025-04-25T22:{i:02d}:00Z",
                    "type": "sample"
                }
            )
            
            # Convert to dict for yielding
            yield item.dict()
            
            # Report progress if reporter is provided
            if progress_reporter:
                progress = (i + 1) / data.item_count
                progress_reporter.report_progress(progress, f"Streamed item {i + 1}/{data.item_count}")
                
            # Check for cancellation if token is provided
            if cancellation_token and cancellation_token.is_cancelled():
                self.logger.info("Streaming operation cancelled")
                break
        
        # Log completion
        self.logger.info("Streaming complete")


# Helper function to create and register the sample tool
def register_sample_streaming_tool(server):
    """
    [Function intent]
    Creates and registers the sample streaming tool with an MCP server.
    
    [Design principles]
    Simple helper for tool registration.
    
    [Implementation details]
    Creates a tool instance and registers it with the server.
    
    Args:
        server: The MCPServer instance to register the tool with
        
    Returns:
        The registered tool instance
    """
    tool = SampleStreamingTool()
    server.register_mcp_tool(tool)
    server._supports_streaming = True  # Enable streaming support flag
    return tool
