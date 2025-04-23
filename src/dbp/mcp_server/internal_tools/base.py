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
# Defines base classes and common utilities for internal MCP tools that are not
# directly exposed to clients. These internal tools provide the implementation
# for functionality that is exposed through the documented public tools.
###############################################################################
# [Source file design principles]
# - Clear separation between public and internal tools
# - Consistent interface for all internal tools
# - Proper naming conventions to indicate internal/private status
# - Common error handling and validation patterns
###############################################################################
# [Source file constraints]
# - Not to be used directly by MCP clients
# - Only accessed through the public tools defined in tools.py
# - Must maintain compatibility with existing tool functionality
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T08:55:00Z : Created base internal tools structure by CodeAssistant
# * Defined InternalMCPTool base class
###############################################################################

import logging
from typing import Dict, Any, Optional

# Import the base MCPTool class for compatibility
try:
    from ..mcp_protocols import MCPTool
    from ..adapter import SystemComponentAdapter
except ImportError as e:
    logging.getLogger(__name__).error(f"Internal Tools ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    class MCPTool:
        def __init__(self, name, description, logger): self.name=name; self.description=description; self.logger=logger
        def _get_input_schema(self): return {}
        def _get_output_schema(self): return {}
        def execute(self, data, auth_context): return {}
    SystemComponentAdapter = object

logger = logging.getLogger(__name__)

class InternalMCPTool:
    """
    [Class intent]
    Base class for all internal MCP tools. These tools are meant to be used
    by the public tools and not directly exposed to MCP clients.
    
    [Implementation details]
    Similar interface to MCPTool but with a leading underscore in method names
    to indicate internal/private status. Takes SystemComponentAdapter for
    accessing DBP components.
    
    [Design principles]
    Clear separation of concerns, internal implementation details hidden from
    public interface, consistent error handling across internal tools.
    """
    
    def __init__(self, name: str, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        """Initialize an internal tool with a name and component adapter."""
        self.name = f"_internal_{name}"  # Prefix with _internal_ to indicate status
        self.adapter = adapter
        self.logger = logger_override or logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
    def _get_input_schema(self) -> Dict[str, Any]:
        """Get the input schema for this internal tool."""
        raise NotImplementedError("Internal tools must implement _get_input_schema")
        
    def _get_output_schema(self) -> Dict[str, Any]:
        """Get the output schema for this internal tool."""
        raise NotImplementedError("Internal tools must implement _get_output_schema")
        
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the internal tool with the provided data."""
        self.logger.debug(f"Executing internal tool {self.name}")
        
        # Validate input (simplified - could use jsonschema)
        self._validate_input(data)
        
        try:
            # Execute tool-specific logic
            result = self._execute_implementation(data, auth_context)
            
            # Validate output (simplified - could use jsonschema)
            self._validate_output(result)
            
            return result
        except Exception as e:
            self.logger.error(f"Error executing internal tool {self.name}: {e}", exc_info=True)
            raise
        
    def _validate_input(self, data: Dict[str, Any]) -> None:
        """Validate the input data against the schema."""
        # Simplified validation - in a real implementation would use jsonschema
        schema = self._get_input_schema()
        required = schema.get("required", [])
        for field in required:
            if field not in data:
                raise ValueError(f"Missing required field: {field}")
    
    def _validate_output(self, result: Dict[str, Any]) -> None:
        """Validate the output result against the schema."""
        # Simplified validation - in a real implementation would use jsonschema
        schema = self._get_output_schema()
        required = schema.get("required", [])
        for field in required:
            if field not in result:
                raise ValueError(f"Missing required field in result: {field}")
    
    def _execute_implementation(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Implementation of tool execution.
        Must be overridden by subclasses.
        """
        raise NotImplementedError("Internal tools must implement _execute_implementation")

# Common exceptions for internal tools
class InternalToolError(Exception):
    """Base exception for internal tool errors."""
    pass

class InternalToolValidationError(InternalToolError):
    """Exception for input validation errors."""
    pass

class InternalToolExecutionError(InternalToolError):
    """Exception for execution errors."""
    pass
