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
# Implements the ToolRegistry class for the LLM Coordinator. This registry
# holds references to the callable functions that implement the internal LLM
# tools (e.g., 'coordinator_get_codebase_context'). It allows the coordinator
# to look up and invoke these tools dynamically based on their names.
###############################################################################
# [Source file design principles]
# - Provides a central, thread-safe registry for internal tools.
# - Maps tool names (strings) to callable functions.
# - Allows registration of new tools.
# - Provides methods to retrieve a tool function by name and list available tools.
# - Includes error handling for unregistered tools.
# - Design Decision: Simple Dictionary Registry (2025-04-15)
#   * Rationale: A straightforward approach for managing a known, relatively small set of internal tools.
#   * Alternatives considered: More complex plugin system (overkill for internal tools).
###############################################################################
# [Source file constraints]
# - Tool names must be unique strings.
# - Registered tool functions must be callable and adhere to an expected signature
#   (likely accepting an InternalToolJob or similar context).
# - Thread safety is ensured via RLock.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:07:25Z : Initial creation of ToolRegistry class by CodeAssistant
# * Implemented tool registration, retrieval, and listing methods.
###############################################################################

import logging
import threading
from typing import Dict, List, Callable, Optional, Any

logger = logging.getLogger(__name__)

class ToolNotFoundError(KeyError):
    """Custom exception raised when a requested tool is not found in the registry."""
    pass

class ToolRegistry:
    """
    A thread-safe registry for managing and accessing internal LLM tools used
    by the LLM Coordinator.
    """

    def __init__(self, config: Optional[Any] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ToolRegistry.

        Args:
            config: Configuration object (currently unused, but kept for consistency).
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.logger = logger_override or logger
        # Stores the mapping: tool_name -> callable_tool_function
        self._tools: Dict[str, Callable] = {}
        self._lock = threading.RLock() # Thread safety
        self.logger.debug("ToolRegistry initialized.")

    def register_tool(self, tool_name: str, tool_function: Callable):
        """
        Registers an internal tool function.

        Args:
            tool_name: The unique name identifying the tool.
            tool_function: The callable function that implements the tool's logic.
                           It's expected to accept necessary arguments (e.g., job context).

        Raises:
            ValueError: If a tool with the same name is already registered.
            TypeError: If the provided tool_function is not callable.
        """
        if not isinstance(tool_name, str) or not tool_name:
            raise TypeError("tool_name must be a non-empty string.")
        if not callable(tool_function):
            raise TypeError(f"tool_function for '{tool_name}' must be callable.")

        with self._lock:
            if tool_name in self._tools:
                self.logger.error(f"Tool with name '{tool_name}' is already registered.")
                raise ValueError(f"Tool name conflict: '{tool_name}' is already registered.")
            self._tools[tool_name] = tool_function
            self.logger.info(f"Internal tool registered: '{tool_name}' -> {getattr(tool_function, '__name__', repr(tool_function))}")

    def get_tool(self, tool_name: str) -> Callable:
        """
        Retrieves the callable function for a registered tool.

        Args:
            tool_name: The name of the tool to retrieve.

        Returns:
            The callable tool function.

        Raises:
            ToolNotFoundError: If no tool with the given name is registered.
        """
        with self._lock:
            if tool_name not in self._tools:
                self.logger.error(f"Requested tool not found in registry: '{tool_name}'")
                raise ToolNotFoundError(f"Tool '{tool_name}' is not registered.")
            return self._tools[tool_name]

    def list_tools(self) -> List[str]:
        """Returns a list of names of all registered internal tools."""
        with self._lock:
            return sorted(list(self._tools.keys()))

    def get_available_tools_description(self) -> str:
        """
        Generates a simple string describing the available tools, suitable for
        inclusion in prompts.

        Returns:
            A newline-separated string listing available tool names.
        """
        with self._lock:
            if not self._tools:
                return "No internal tools are currently available."

            descriptions = [f"- {name}" for name in sorted(self._tools.keys())]
            return "Available Internal Tools:\n" + "\n".join(descriptions)
