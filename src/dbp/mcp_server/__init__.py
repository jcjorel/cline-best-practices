# src/dbp/mcp_server/__init__.py

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
