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
# Provides a sample implementation of a streaming-capable MCP tool using FastMCP.
# This serves as an example and reference for creating custom streaming tools.
###############################################################################
# [Source file design principles]
# - Demonstrates proper FastMCP streaming tool implementation pattern
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
# system:fastmcp
###############################################################################
# [GenAI tool change history]
# 2025-04-27T00:20:00Z : Updated to use FastMCP instead of homemade MCP implementation by CodeAssistant
# * Replaced MCPStreamingTool with FastMCP streaming tool implementation
# * Updated imports to use FastMCP
# * Simplified tool registration
# * Removed references to homemade MCP implementation
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

# Import FastMCP
from fastmcp import FastMCP
from fastmcp.streaming import StreamingTool

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
    stream_format: Optional[str] = Field(default="json", description="Stream format (json or event_stream)")
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


class SampleStreamingTool(StreamingTool):
    """
    [Class intent]
    Demonstrates a basic streaming tool implementation using FastMCP.
    
    [Design principles]
    - Shows proper inheritance from FastMCP's StreamingTool
    - Implements required methods
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
            description="A sample tool demonstrating MCP streaming capabilities",
            input_schema=SampleToolInput,
            output_schema=SampleToolOutput
        )
        self.logger = logging.getLogger("dbp.mcp_server.examples.sample_streaming_tool")
        self.logger.info("SampleStreamingTool initialized")
    
    async def execute(
        self,
        data: SampleToolInput,
        context: Optional[Dict[str, Any]] = None
    ) -> SampleToolOutput:
        """
        [Function intent]
        Executes the tool in non-streaming mode.
        
        [Design principles]
        - Implements standard execution for non-streaming response
        - Generates all results at once
        
        [Implementation details]
        - Builds complete result set immediately
        - Used when client doesn't request streaming
        
        Args:
            data: The validated input parameters
            context: Optional execution context
            
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
                    "timestamp": f"2025-04-27T00:{i:02d}:00Z",
                    "type": "sample"
                }
            }
            items.append(item)
            
            # Report progress if context supports it
            if context and "progress_callback" in context:
                progress = (i + 1) / data.item_count
                context["progress_callback"](progress, f"Processed item {i + 1}/{data.item_count}")
                
            # Check for cancellation if context supports it
            if context and "is_cancelled" in context and context["is_cancelled"]():
                self.logger.info("Operation cancelled")
                break
        
        # Return complete result
        return SampleToolOutput(
            result=items,
            total_items=len(items)
        )
    
    async def stream(
        self,
        data: SampleToolInput,
        context: Optional[Dict[str, Any]] = None
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
            context: Optional execution context
            
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
                    "timestamp": f"2025-04-27T00:{i:02d}:00Z",
                    "type": "sample"
                }
            )
            
            # Convert to dict for yielding
            yield item.dict()
            
            # Report progress if context supports it
            if context and "progress_callback" in context:
                progress = (i + 1) / data.item_count
                context["progress_callback"](progress, f"Streamed item {i + 1}/{data.item_count}")
                
            # Check for cancellation if context supports it
            if context and "is_cancelled" in context and context["is_cancelled"]():
                self.logger.info("Streaming operation cancelled")
                break
        
        # Log completion
        self.logger.info("Streaming complete")


# Helper function to create and register the sample tool
def register_sample_streaming_tool(mcp: FastMCP):
    """
    [Function intent]
    Creates and registers the sample streaming tool with a FastMCP instance.
    
    [Design principles]
    Simple helper for tool registration.
    
    [Implementation details]
    Creates a tool instance and registers it with the FastMCP instance.
    
    Args:
        mcp: The FastMCP instance to register the tool with
        
    Returns:
        The registered tool instance
    """
    tool = SampleStreamingTool()
    mcp.register_tool(tool)
    return tool
