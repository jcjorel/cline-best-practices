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
# Defines the abstract base classes (ABCs) for Model Context Protocol (MCP)
# tools and resources. These classes establish the required interface that all
# concrete tools and resources exposed by the DBP MCP server must implement.
###############################################################################
# [Source file design principles]
# - Uses `abc.ABC` and `abc.abstractmethod` to define clear interfaces.
# - `MCPTool` defines the structure for executable actions, including input/output schemas.
# - `MCPResource` defines the structure for accessing data sources via URIs.
# - Provides a consistent foundation for building MCP capabilities.
# - Design Decision: Abstract Base Classes (2025-04-15)
#   * Rationale: Enforces a standard contract for all tools and resources, ensuring they integrate correctly with the MCP server framework.
#   * Alternatives considered: Protocol classes (less explicit inheritance), Duck typing (no formal contract).
###############################################################################
# [Source file constraints]
# - Concrete implementations must inherit from these base classes and implement abstract methods.
# - Input/output schemas should ideally follow JSON Schema standards.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:51:20Z : Initial creation of MCP protocol base classes by CodeAssistant
# * Defined MCPTool and MCPResource abstract base classes.
###############################################################################

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class MCPTool(ABC):
    """
    Abstract base class for all tools exposed via the MCP server.
    Concrete tools must inherit from this class and implement the required methods.
    """

    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the MCPTool.

        Args:
            name: The unique name of the tool (used in MCP requests).
            description: A human-readable description of what the tool does.
            logger_override: Optional logger instance.
        """
        if not name or not isinstance(name, str):
             raise ValueError("Tool name must be a non-empty string.")
        self._name = name
        self._description = description
        self.logger = logger_override or logger.getChild(f"MCPTool.{self.name}")
        # Eagerly get schemas in constructor
        self._input_schema = self._get_input_schema()
        self._output_schema = self._get_output_schema()
        self.logger.debug(f"MCPTool '{self.name}' initialized.")

    @property
    def name(self) -> str:
        """The unique identifier name for this tool."""
        return self._name

    @property
    def description(self) -> str:
        """A human-readable description of the tool's purpose."""
        return self._description

    @property
    def input_schema(self) -> Dict[str, Any]:
        """The JSON schema describing the expected input data for the execute method."""
        return self._input_schema

    @property
    def output_schema(self) -> Dict[str, Any]:
        """The JSON schema describing the structure of the data returned by the execute method."""
        return self._output_schema

    @abstractmethod
    def _get_input_schema(self) -> Dict[str, Any]:
        """
        Abstract method to be implemented by subclasses.
        Should return a dictionary representing the JSON schema for the tool's input parameters.
        """
        pass

    @abstractmethod
    def _get_output_schema(self) -> Dict[str, Any]:
        """
        Abstract method to be implemented by subclasses.
        Should return a dictionary representing the JSON schema for the tool's output result.
        """
        pass

    @abstractmethod
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes the core logic of the tool.

        Args:
            data: A dictionary containing the input parameters for the tool,
                  validated against the input_schema.
            auth_context: Optional dictionary containing information about the
                          authenticated client, if authentication is enabled.

        Returns:
            A dictionary containing the result of the tool's execution, which
            should conform to the output_schema.

        Raises:
            Exception: Subclasses may raise specific exceptions for execution errors,
                       which should be handled by the MCP server's error handler.
        """
        pass


class MCPResource(ABC):
    """
    Abstract base class for all resources exposed via the MCP server.
    Concrete resources must inherit from this class and implement the required methods.
    """

    def __init__(self, name: str, description: str, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the MCPResource.

        Args:
            name: The unique name (typically the root URI path segment) for this resource.
            description: A human-readable description of the resource.
            logger_override: Optional logger instance.
        """
        if not name or not isinstance(name, str):
             raise ValueError("Resource name must be a non-empty string.")
        self._name = name
        self._description = description
        self.logger = logger_override or logger.getChild(f"MCPResource.{self.name}")
        self.logger.debug(f"MCPResource '{self.name}' initialized.")

    @property
    def name(self) -> str:
        """The unique identifier name (URI prefix) for this resource."""
        return self._name

    @property
    def description(self) -> str:
        """A human-readable description of the resource."""
        return self._description

    @abstractmethod
    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Retrieves the resource data.

        Args:
            resource_id: The specific identifier for the resource instance being accessed
                         (e.g., a specific document path following the resource name prefix).
                         Can be None if accessing the root of the resource collection.
            params: A dictionary of query parameters provided in the request.
            auth_context: Optional dictionary containing information about the
                          authenticated client, if authentication is enabled.

        Returns:
            A dictionary containing the resource data.

        Raises:
            Exception: Subclasses may raise specific exceptions (e.g., ResourceNotFoundError,
                       PermissionError) which should be handled by the MCP server's error handler.
        """
        pass

    # Add other methods like 'put', 'post', 'delete' if the resource supports modification
    # @abstractmethod
    # def put(self, resource_id: str, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    #     pass
