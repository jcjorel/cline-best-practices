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
# MCP Server Integration package for the Documentation-Based Programming system.
# Provides module-level imports and defines the public API for the mcp_server package.
###############################################################################
# [Source file design principles]
# - Exports only the public interfaces needed by other components
# - Maintains clean import hierarchy to avoid circular dependencies
# - Uses explicit imports rather than wildcard imports
# - Organizes imports by logical function groups
###############################################################################
# [Source file constraints]
# - Must avoid circular imports at all costs
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:53:30Z : Fixed docstring formatting by CodeAssistant
# * Corrected placement of docstring quotes
# 2025-04-15T21:52:35Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################

"""
MCP Server Integration package for the Documentation-Based Programming system.

Provides the necessary components to expose DBP functionality via the
Model Context Protocol (MCP), including the server itself, tool/resource
definitions, authentication, and request handling.

Key components:
- MCPServerComponent: The main component conforming to the core framework.
- MCPServer: Placeholder for the actual web server implementation.
- MCPTool / MCPResource: Abstract base classes for tools and resources.
- ToolRegistry / ResourceProvider: Manage registered tools and resources.
- AuthenticationProvider: Handles API key authentication/authorization.
- ErrorHandler: Standardizes error responses.
- SystemComponentAdapter: Bridge to access core DBP components.
- Data Models: Defines MCPRequest, MCPResponse, MCPError.
"""

# Expose key classes, data models, and exceptions for easier import
from .data_models import MCPRequest, MCPResponse, MCPError
from .mcp_protocols import MCPTool, MCPResource
from .registry import ToolRegistry, ResourceProvider
from .auth import AuthenticationProvider, AuthenticationError, AuthorizationError
from .error_handler import ErrorHandler
from .adapter import SystemComponentAdapter, ComponentNotFoundError
from .server import MCPServer # Placeholder server class
from .component import MCPServerComponent, ComponentNotInitializedError
# Concrete tools and resources are likely internal details, but can be exposed if needed
# from .tools import AnalyzeDocumentConsistencyTool, ...
# from .resources import DocumentationResource, ...

__all__ = [
    # Main Component
    "MCPServerComponent",
    # Core Server Class (Placeholder)
    "MCPServer",
    # Protocols / Base Classes
    "MCPTool",
    "MCPResource",
    # Data Models
    "MCPRequest",
    "MCPResponse",
    "MCPError",
    # Supporting Classes (Expose if needed externally)
    "ToolRegistry",
    "ResourceProvider",
    "AuthenticationProvider",
    "ErrorHandler",
    "SystemComponentAdapter",
    # Exceptions
    "AuthenticationError",
    "AuthorizationError",
    "ComponentNotFoundError", # From adapter
    "ComponentNotInitializedError", # From component
    # Add ToolExecutionError, ResourceAccessError etc. if defined and needed
]
