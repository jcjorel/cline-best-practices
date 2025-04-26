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
# Provides an example implementation of an MCP tool using the MCPTool base class.
# This serves as a reference for creating custom MCP tools with the unified API.
###############################################################################
# [Source file design principles]
# - Demonstrates proper MCPTool implementation pattern
# - Shows how to implement both execute and stream methods
# - Includes examples for progress reporting and cancellation handling
# - Demonstrates how to register the tool with FastMCP
###############################################################################
# [Source file constraints]
# - For demonstration purposes only, not for production use
# - Does not perform any actual meaningful operations
###############################################################################
# [Dependencies]
# system:asyncio
# system:typing
# system:pydantic
# codebase:src/dbp/mcp_server/mcp_tool.py
###############################################################################
# [GenAI tool change history]
# 2025-04-27T00:41:00Z : Created example tool implementation by CodeAssistant
# * Implemented ExampleTool class using MCPTool base class
# * Added input, output, and chunk models
# * Implemented execute and stream methods
# * Added example registration code
###############################################################################

import asyncio
import logging
from typing import Dict, List, Any, Optional, AsyncIterable

from pydantic import BaseModel, Field

from ..mcp_tool import MCPTool

logger = logging.getLogger(__name__)


# Input model for the example tool
class ExampleToolInput(BaseModel):
    """
    [Class intent]
    Defines the input parameters for the example tool.
    
    [Design principles]
    Simple model with configurable options for testing.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    item_count: int = Field(default=5, description="Number of items to generate")
    delay_seconds: float = Field(default=0.5, description="Delay between items in seconds")
    streaming: bool = Field(default=True, description="Whether to use streaming response")
    fail_at_item: Optional[int] = Field(default=None, description="Item number at which to simulate a failure")


# Output model for the example tool
class ExampleToolOutput(BaseModel):
    """
    [Class intent]
    Defines the output format for the example tool.
    
    [Design principles]
    Simple model for demonstration purposes.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    result: List[Dict[str, Any]] = Field(description="List of items in the result")
    total_items: int = Field(description="Total number of items processed")


# Chunk model for streaming output
class ExampleToolChunk(BaseModel):
    """
    [Class intent]
    Defines the format of each chunk in the stream.
    
    [Design principles]
    Simple model for demonstration purposes.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    item_id: int = Field(description="Unique identifier for this item")
    content: str = Field(description="Content of this item")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Optional metadata for this item")


class ExampleTool(MCPTool[ExampleToolInput, ExampleToolOutput, ExampleToolChunk]):
    """
    [Class intent]
    Demonstrates a basic tool implementation using the MCPTool base class.
    
    [Design principles]
    - Shows proper inheritance from MCPTool
    - Implements required methods
    - Demonstrates progress reporting and cancellation handling
    
    [Implementation details]
    - Uses asyncio for non-blocking delays
    - Simulates data generation with configurable delay
    - Handles cancellation and progress reporting
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes the example tool.
        
        [Design principles]
        Simple initialization with clear name and description.
        
        [Implementation details]
        Calls parent constructor with tool metadata and models.
        """
        super().__init__(
            name="example_tool",
            description="An example tool demonstrating the MCPTool base class",
            input_model=ExampleToolInput,
            output_model=ExampleToolOutput,
            chunk_model=ExampleToolChunk,
            version="1.0.0"
        )
        self.logger = logging.getLogger("dbp.mcp_server.examples.example_tool")
        self.logger.info("ExampleTool initialized")
    
    async def execute(
        self,
        data: ExampleToolInput,
        context: Dict[str, Any]
    ) -> ExampleToolOutput:
        """
        [Function intent]
        Executes the tool and returns a complete result.
        
        [Design principles]
        - Implements standard execution for non-streaming response
        - Generates all results at once
        
        NOTE: This is an EXCEPTIONAL CASE where we override the execute() method.
        The recommended pattern is to ONLY implement the stream() method and let
        MCPTool's default execute() implementation handle the conversion from
        streaming to non-streaming responses. This example overrides execute()
        only to demonstrate a custom non-streaming implementation for educational
        purposes.
        
        [Implementation details]
        - Builds complete result set immediately
        - Reports progress using the context
        - Checks for cancellation
        
        Args:
            data: The validated input parameters
            context: The execution context
            
        Returns:
            Complete result object with all items
        """
        self.logger.info(f"Executing example tool with {data.item_count} items")
        
        # Get progress and cancellation callbacks from context
        progress_callback = context["progress_callback"]
        is_cancelled = context["is_cancelled"]
        
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
                    "type": "example"
                }
            }
            items.append(item)
            
            # Report progress
            progress = (i + 1) / data.item_count
            progress_callback(progress, f"Processed item {i + 1}/{data.item_count}")
                
            # Check for cancellation
            if is_cancelled():
                self.logger.info("Operation cancelled")
                break
        
        # Return complete result
        return ExampleToolOutput(
            result=items,
            total_items=len(items)
        )
    
    async def stream(
        self,
        data: ExampleToolInput,
        context: Dict[str, Any]
    ) -> AsyncIterable[ExampleToolChunk]:
        """
        [Function intent]
        Streams the tool's output as chunks.
        
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
            context: The execution context
            
        Yields:
            Individual chunks as they're generated
        """
        self.logger.info(f"Streaming example tool with {data.item_count} items")
        
        # Get progress and cancellation callbacks from context
        progress_callback = context["progress_callback"]
        is_cancelled = context["is_cancelled"]
        
        # Generate items with delay
        for i in range(data.item_count):
            # Add delay between items
            if i > 0 and data.delay_seconds > 0:
                await asyncio.sleep(data.delay_seconds)
                
            # Check for simulated failure
            if data.fail_at_item is not None and i + 1 == data.fail_at_item:
                raise ValueError(f"Simulated failure at item {i + 1}")
                
            # Create and yield an item
            chunk = ExampleToolChunk(
                item_id=i + 1,
                content=f"Content for item {i + 1}",
                metadata={
                    "timestamp": f"2025-04-27T00:{i:02d}:00Z",
                    "type": "example"
                }
            )
            
            yield chunk
            
            # Report progress
            progress = (i + 1) / data.item_count
            progress_callback(progress, f"Streamed item {i + 1}/{data.item_count}")
                
            # Check for cancellation
            if is_cancelled():
                self.logger.info("Streaming operation cancelled")
                break
        
        # Log completion
        self.logger.info("Streaming complete")



# Example registration code
def register_example_tools(mcp):
    """
    [Function intent]
    Registers the example tool with the FastMCP instance.
    
    [Design principles]
    Simple helper for tool registration.
    
    [Implementation details]
    Creates tool instance and registers it with FastMCP.
    
    Args:
        mcp: The FastMCP instance to register with
    """
    # Create and register the example tool
    example_tool = ExampleTool()
    example_tool.register(mcp)
    
    return {
        "example_tool": example_tool
    }
