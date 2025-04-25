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
# Provides a façade for the Model Context Protocol (MCP) implementation.
# Re-exports all classes from the mcp/ module to maintain backward compatibility
# while allowing a more modular, maintainable implementation under the hood.
###############################################################################
# [Source file design principles]
# - Acts as a backward-compatible entry point for MCP protocol components
# - Maintains clean public API for MCP consumers
# - Delegates implementation to specialized modules
# - Follows façade design pattern
###############################################################################
# [Source file constraints]
# - Must maintain complete backward compatibility for external code
# - No implementation logic should be placed here
# - All actual implementations live in the mcp/ module
###############################################################################
# [Dependencies]
# codebase:src/dbp/mcp_server/mcp/__init__.py
# codebase:doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T18:53:28Z : Refactored to serve as a façade for modular mcp/ package by CodeAssistant
# * Converted from monolithic implementation to façade pattern
# * Moved all class implementations to separate files in mcp/ directory
# * Maintained backward compatibility by re-exporting all classes
# 2025-04-25T18:29:00Z : Complete refactor of MCPTool and MCPResource to strictly follow MCP spec by CodeAssistant
# * Added JSON-RPC 2.0 compliant message handling
# * Added progress reporting and cancellation support
# * Added MCP-specific error handling
# * Enhanced resource URIs and metadata
# 2025-04-25T18:09:00Z : Updated MCPTool and MCPResource to use Pydantic models by CodeAssistant
# * Converted input and output schemas to use Pydantic models
# * Added handler method to MCPTool for FastAPI integration
# * Updated execute() to use Pydantic models
# * Added default params and response schema models to MCPResource
# 2025-04-15T10:51:20Z : Initial creation of MCP protocol base classes by CodeAssistant
# * Defined MCPTool and MCPResource abstract base classes.
###############################################################################

"""
Model Context Protocol (MCP) implementation.

This module provides the abstract base classes that define the MCP protocol
interfaces. For concrete implementations, see the specific tool and resource
classes in the mcp_server package.
"""

# Re-export all MCP component classes for backward compatibility
from .mcp import (
    MCPErrorCode,
    MCPError,
    MCPProgressReporter,
    MCPCancellationToken,
    MCPTool, 
    MCPResource,
    MCPStreamingResponse,
    StreamFormat,
    StreamChunk,
    create_streaming_generator,
    MCPStreamingTool,
    StreamingResponse
)

__all__ = [
    'MCPErrorCode',
    'MCPError',
    'MCPProgressReporter',
    'MCPCancellationToken',
    'MCPTool', 
    'MCPResource',
    'MCPStreamingResponse',
    'StreamFormat',
    'StreamChunk',
    'create_streaming_generator',
    'MCPStreamingTool',
    'StreamingResponse'
]
