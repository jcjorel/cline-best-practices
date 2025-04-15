###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the ToolRegistry and ResourceProvider classes for the MCP Server.
# These registries manage the collection of tools and resources that the DBP
# MCP server exposes to clients, allowing for dynamic registration and lookup.
###############################################################################
# [Source file design principles]
# - Provides separate, thread-safe registries for MCP tools and resources.
# - Uses dictionaries for efficient lookup by name (for tools) or URI prefix (for resources).
# - Allows registration of tool/resource handler instances.
# - Provides methods for retrieving handlers based on request targets.
# - Design Decision: Separate Registries for Tools/Resources (2025-04-15)
#   * Rationale: Clear separation between executable actions (tools) and data access points (resources) as per MCP concepts.
#   * Alternatives considered: Single combined registry (less clear distinction).
###############################################################################
# [Source file constraints]
# - Depends on base classes/interfaces for `MCPTool` and `MCPResource`.
# - Assumes tool names and resource URI prefixes are unique within their respective registries.
# - Thread safety ensured by RLock.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/mcp_server/mcp_protocols.py (Expected location for MCPTool/MCPResource bases)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:50:45Z : Initial creation of MCP ToolRegistry and ResourceProvider by CodeAssistant
# * Implemented registration and retrieval logic for MCP tools and resources.
###############################################################################

import logging
import threading
from typing import Dict, Optional, Any, List

# Assuming base classes MCPTool, MCPResource are defined elsewhere (e.g., mcp_protocols.py)
# Define placeholders if they don't exist yet
try:
    from .mcp_protocols import MCPTool, MCPResource # Assumes mcp_protocols.py exists
except ImportError:
    logging.getLogger(__name__).warning("MCPTool or MCPResource base classes not found. Using placeholders.")
    class MCPTool:
        name: str = "placeholder_tool"
    class MCPResource:
        name: str = "placeholder_resource" # Usually corresponds to URI prefix

logger = logging.getLogger(__name__)

class ToolRegistry:
    """Manages the registration and lookup of MCP tools."""

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the ToolRegistry."""
        self.logger = logger_override or logger
        self._tools: Dict[str, MCPTool] = {}
        self._lock = threading.RLock()
        self.logger.debug("MCP ToolRegistry initialized.")

    def register_tool(self, tool: MCPTool):
        """
        Registers an MCP tool instance.

        Args:
            tool: An instance of a class implementing the MCPTool interface.

        Raises:
            ValueError: If a tool with the same name is already registered.
            TypeError: If the provided object is not a valid MCPTool instance.
        """
        if not hasattr(tool, 'name') or not isinstance(tool.name, str):
             raise TypeError("Tool object must have a valid string 'name' attribute.")
        if not isinstance(tool, MCPTool): # Check against placeholder if needed
             # Basic check, might need refinement based on actual MCPTool definition
             if MCPTool is not object and not getattr(tool, 'execute', None):
                  raise TypeError(f"Object for tool '{tool.name}' does not appear to be a valid MCPTool.")

        tool_name = tool.name
        with self._lock:
            if tool_name in self._tools:
                self.logger.error(f"MCP tool with name '{tool_name}' already registered.")
                raise ValueError(f"MCP tool name conflict: '{tool_name}' is already registered.")
            self._tools[tool_name] = tool
            self.logger.info(f"Registered MCP tool: '{tool_name}' ({type(tool).__name__})")

    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        Retrieves a registered tool by its name.

        Args:
            name: The name of the tool.

        Returns:
            The MCPTool instance, or None if not found.
        """
        with self._lock:
            tool = self._tools.get(name)
            if not tool:
                 self.logger.warning(f"MCP tool '{name}' not found in registry.")
            return tool

    def get_all_tools(self) -> List[MCPTool]:
        """Returns a list of all registered tool instances."""
        with self._lock:
            return list(self._tools.values())

    def get_tool_names(self) -> List[str]:
         """Returns a list of names of all registered tools."""
         with self._lock:
              return list(self._tools.keys())


class ResourceProvider:
    """Manages the registration and lookup of MCP resources."""

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the ResourceProvider."""
        self.logger = logger_override or logger
        # resource_name (URI prefix) -> MCPResource instance
        self._resources: Dict[str, MCPResource] = {}
        self._lock = threading.RLock()
        self.logger.debug("MCP ResourceProvider initialized.")

    def register_resource(self, resource: MCPResource):
        """
        Registers an MCP resource handler instance.

        Args:
            resource: An instance of a class implementing the MCPResource interface.

        Raises:
            ValueError: If a resource with the same name (URI prefix) is already registered.
            TypeError: If the provided object is not a valid MCPResource instance.
        """
        if not hasattr(resource, 'name') or not isinstance(resource.name, str):
             raise TypeError("Resource object must have a valid string 'name' attribute.")
        if not isinstance(resource, MCPResource): # Check against placeholder if needed
             if MCPResource is not object and not getattr(resource, 'get', None):
                  raise TypeError(f"Object for resource '{resource.name}' does not appear to be a valid MCPResource.")

        resource_name = resource.name
        with self._lock:
            if resource_name in self._resources:
                self.logger.error(f"MCP resource with name '{resource_name}' already registered.")
                raise ValueError(f"MCP resource name conflict: '{resource_name}' is already registered.")
            self._resources[resource_name] = resource
            self.logger.info(f"Registered MCP resource: '{resource_name}' ({type(resource).__name__})")

    def get_resource(self, name: str) -> Optional[MCPResource]:
        """
        Retrieves a registered resource handler by its name (URI prefix).

        Args:
            name: The name (URI prefix) of the resource.

        Returns:
            The MCPResource instance, or None if not found.
        """
        with self._lock:
            resource = self._resources.get(name)
            if not resource:
                 self.logger.warning(f"MCP resource '{name}' not found in provider registry.")
            return resource

    def get_all_resources(self) -> List[MCPResource]:
        """Returns a list of all registered resource handler instances."""
        with self._lock:
            return list(self._resources.values())

    def get_resource_names(self) -> List[str]:
         """Returns a list of names (URI prefixes) of all registered resources."""
         with self._lock:
              return list(self._resources.keys())
