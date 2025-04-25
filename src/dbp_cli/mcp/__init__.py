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
# Package initialization for the MCP (Model Context Protocol) client implementation.
# Exports all the key classes and entities for the MCP client to provide 
# a clean, unified interface to the rest of the codebase.
###############################################################################
# [Source file design principles]
# - Acts as a facade for all MCP client components
# - Provides clean imports for consumers of the MCP client
# - Maintains clear separation of concerns via modular imports
# - Follows standard Python package initialization patterns
###############################################################################
# [Source file constraints]
# - Must re-export all necessary classes for external consumption
# - No implementation logic should be placed here
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/mcp/error.py
# codebase:src/dbp_cli/mcp/client.py
# codebase:src/dbp_cli/mcp/session.py
# codebase:src/dbp_cli/mcp/tool_client.py
# codebase:src/dbp_cli/mcp/resource_client.py
# codebase:src/dbp_cli/mcp/streaming.py
# codebase:src/dbp_cli/mcp/negotiation.py
# system:https://modelcontextprotocol.io/specification/2025-03-26
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:02:00Z : Initial creation of MCP client package by CodeAssistant
# * Created MCP client package initialization
###############################################################################

"""
Model Context Protocol (MCP) client implementation.

This module provides client implementations for interacting with MCP servers 
following the Anthropic Model Context Protocol specification.
"""

# Will re-export all MCP client classes as they're implemented
from .error import MCPErrorCode, MCPError
from .client import MCPClient
from .session import MCPSession
from .tool_client import MCPToolClient
from .resource_client import MCPResourceClient
from .streaming import MCPStreamingClient
from .negotiation import (
    ClientCapabilityType,
    ServerCapabilityType,
    NegotiationRequest,
    NegotiationResponse
)

__all__ = [
    'MCPErrorCode',
    'MCPError',
    'MCPClient',
    'MCPSession',
    'MCPToolClient',
    'MCPResourceClient',
    'MCPStreamingClient',
    'ClientCapabilityType',
    'ServerCapabilityType',
    'NegotiationRequest',
    'NegotiationResponse'
]
