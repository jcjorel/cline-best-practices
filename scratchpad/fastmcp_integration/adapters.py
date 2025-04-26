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
# Provides adapter functions to convert existing MCPTool objects and resource handlers
# to fastmcp-compatible tool and resource functions. This enables seamless integration
# of existing MCP implementations with the fastmcp library.
###############################################################################
# [Source file design principles]
# - Clean separation between existing MCP implementation and fastmcp
# - Minimal adaptation logic to maintain simplicity
# - Preserves existing tool and resource interfaces
# - Handles asynchronous and synchronous execution patterns
# - Maintains proper error handling and logging
###############################################################################
# [Source file constraints]
# - Must handle both Pydantic v1 and v2 model interfaces
# - Must preserve error handling semantics
# - Must handle both synchronous and asynchronous execution
# - Must maintain type safety where possible
###############################################################################
# [Dependencies]
# codebase:- src/dbp/mcp_server/mcp/tool.py
# codebase:- src/dbp/mcp_server/mcp/resource.py
# system:- fastmcp
# system:- asyncio
# system:- inspect
# system:- logging
###############################################################################
# [GenAI tool change history]
# 2025-04-26T23:15:00Z : Created adapter functions for fastmcp integration by CodeAssistant
# * Implemented adapt_mcp_tool for converting MCPTool objects to fastmcp tool functions
# * Implemented adapt_mcp_resource for converting resource handlers to fastmcp resource functions
# * Added support for both synchronous and asynchronous execution
# * Added proper error handling and logging
###############################################################################

import logging
import asyncio
import inspect
from typing import Any, Callable, Dict, Optional, Type, Union

# Import fastmcp
from fastmcp import FastMCP

logger = logging.getLogger(__name__)

def adapt_mcp_tool(mcp: FastMCP, tool):
    """
    [Function intent]
    Adapts an existing MCPTool object to work with fastmcp.
    
    [Design principles]
    - Minimal adaptation logic to maintain simplicity
    - Handles both synchronous and asynchronous execution
    - Preserves error handling semantics
    
    [Implementation details]
    - Creates a wrapper function that calls the tool's execute method
    - Handles conversion between kwargs and Pydantic models
    - Registers the wrapper function with fastmcp
    - Supports both synchronous and asynchronous execution
    
    Args:
        mcp: FastMCP instance
        tool: MCPTool instance to adapt
        
    Returns:
        The registered tool function
    """
    logger.debug(f"Adapting MCPTool '{tool.name}' to fastmcp")
    
    # Check if the tool's execute method is asynchronous
    is_async = asyncio.iscoroutinefunction(tool.execute)
    
    if is_async:
        # Create an async wrapper function
        @mcp.tool(name=tool.name, description=tool.description)
        async def tool_wrapper(**kwargs):
            """Tool wrapper for fastmcp integration."""
            try:
                # Convert kwargs to a Pydantic model
                input_model = tool.input_schema(**kwargs)
                
                # Execute the tool
                result = await tool.execute(input_model)
                
                # Convert result to dict if it's a Pydantic model
                if hasattr(result, "model_dump"):
                    # Pydantic v2
                    return result.model_dump()
                elif hasattr(result, "dict"):
                    # Pydantic v1
                    return result.dict()
                return result
            except Exception as e:
                logger.error(f"Error executing tool '{tool.name}': {str(e)}", exc_info=True)
                raise
        
        return tool_wrapper
    else:
        # Create a synchronous wrapper function
        @mcp.tool(name=tool.name, description=tool.description)
        def tool_wrapper(**kwargs):
            """Tool wrapper for fastmcp integration."""
            try:
                # Convert kwargs to a Pydantic model
                input_model = tool.input_schema(**kwargs)
                
                # Execute the tool
                result = tool.execute(input_model)
                
                # Convert result to dict if it's a Pydantic model
                if hasattr(result, "model_dump"):
                    # Pydantic v2
                    return result.model_dump()
                elif hasattr(result, "dict"):
                    # Pydantic v1
                    return result.dict()
                return result
            except Exception as e:
                logger.error(f"Error executing tool '{tool.name}': {str(e)}", exc_info=True)
                raise
        
        return tool_wrapper

def adapt_mcp_resource(mcp: FastMCP, resource_name: str, handler: Callable):
    """
    [Function intent]
    Adapts an existing MCP resource handler to work with fastmcp.
    
    [Design principles]
    - Minimal adaptation logic to maintain simplicity
    - Handles both synchronous and asynchronous execution
    - Preserves error handling semantics
    
    [Implementation details]
    - Creates a wrapper function that calls the resource handler
    - Handles conversion between kwargs and resource parameters
    - Registers the wrapper function with fastmcp
    - Supports both synchronous and asynchronous execution
    
    Args:
        mcp: FastMCP instance
        resource_name: Name of the resource
        handler: Resource handler function
        
    Returns:
        The registered resource function
    """
    logger.debug(f"Adapting MCP resource '{resource_name}' to fastmcp")
    
    # Check if the handler is asynchronous
    is_async = asyncio.iscoroutinefunction(handler)
    
    if is_async:
        # Create an async wrapper function
        @mcp.resource(resource_name)
        async def resource_wrapper(**kwargs):
            """Resource wrapper for fastmcp integration."""
            try:
                # Extract resource_id from kwargs if present
                resource_id = kwargs.pop("resource_id", None)
                
                # Call the handler
                result = await handler(resource_id, kwargs, {})
                return result
            except Exception as e:
                logger.error(f"Error accessing resource '{resource_name}': {str(e)}", exc_info=True)
                raise
        
        return resource_wrapper
    else:
        # Create a synchronous wrapper function
        @mcp.resource(resource_name)
        def resource_wrapper(**kwargs):
            """Resource wrapper for fastmcp integration."""
            try:
                # Extract resource_id from kwargs if present
                resource_id = kwargs.pop("resource_id", None)
                
                # Call the handler
                result = handler(resource_id, kwargs, {})
                return result
            except Exception as e:
                logger.error(f"Error accessing resource '{resource_name}': {str(e)}", exc_info=True)
                raise
        
        return resource_wrapper
