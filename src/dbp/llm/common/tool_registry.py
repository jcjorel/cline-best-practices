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
# Provides a dynamic tool registration system for LLMs. This module enables the 
# runtime registration and management of tools that LLMs can use, with validation
# of tool schemas and parameters. It serves as a central registry for all available
# tools across the application with LangChain/LangGraph integration.
###############################################################################
# [Source file design principles]
# - Dynamic registration and unregistration of tools at runtime
# - Thread-safe operations for concurrent access
# - Schema validation for tool definitions and parameters
# - Consistent interface for tool registration regardless of source
# - Support for both LangChain and custom tool formats
# - Clean separation between tool definition and execution
# - Simple discovery and filtering through tags
###############################################################################
# [Source file constraints]
# - Must validate tool schemas before registration
# - Must be thread-safe to support concurrent operations
# - Must handle tool naming conflicts appropriately
# - Must integrate with LangChain tool specifications
# - Must validate inputs and outputs against schemas
# - Must provide clear error messages for failures
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# system:typing
# system:threading
# system:pydantic
# system:inspect
# system:json
# system:langchain_core
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:00:00Z : Enhanced for LangChain/LangGraph integration by CodeAssistant
# * Added schema validation for inputs and outputs
# * Added tool execution functionality with validation
# * Added LangChainToolAdapter for bidirectional integration
# * Enhanced tagging and filtering capabilities
# 2025-05-02T10:45:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created dynamic tool registration system
###############################################################################

"""
Dynamic tool registration system for LLM tools.
"""

import threading
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union, Set, TypeVar, Type
from pydantic import BaseModel, Field, ValidationError, create_model

from langchain_core.tools import BaseTool as LangChainTool
from langchain_core.tools import Tool

from .exceptions import (
    ToolError, 
    ToolRegistrationError, 
    ToolNotFoundError, 
    ToolExecutionError, 
    ConfigurationError
)


class ToolDefinition(BaseModel):
    """
    [Class intent]
    Defines a tool that can be used by LLMs, providing metadata 
    about the tool's purpose and usage.
    
    [Design principles]
    Uses Pydantic for schema validation and clear interface definition.
    
    [Implementation details]
    Implements the basic structure required for tool definitions with
    a compatible interface to LangChain tools.
    """
    
    name: str = Field(..., description="Unique identifier for the tool")
    description: str = Field(..., description="Human-readable description of the tool's purpose")
    is_available: bool = Field(True, description="Whether this tool is currently available for use")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Parameters for the tool")
    requires_approval: bool = Field(False, description="Whether this tool requires explicit approval before use")
    tags: Set[str] = Field(default_factory=set, description="Tags for categorizing and filtering tools")
    version: Optional[str] = Field(None, description="Version identifier for the tool")


class ToolRegistry:
    """
    [Class intent]
    Provides a centralized registry for LLM tools with thread-safe 
    registration, unregistration, and lookup functionality. Supports
    schema validation, execution, and LangChain integration.
    
    [Design principles]
    Thread-safe singleton maintaining the canonical list of available tools.
    Provides validation to ensure tool integrity and correct execution.
    Supports dynamic discovery and filtering of tools.
    
    [Implementation details]
    Uses a thread lock to ensure consistent state during concurrent operations.
    Implements schema validation using Pydantic models.
    Manages tool lifecycle from registration to execution.
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes a new tool registry with empty collections.
        
        [Design principles]
        Ensures thread safety for multi-threaded environments.
        
        [Implementation details]
        Creates synchronized data structures for tool storage.
        """
        self._tools: Dict[str, Dict[str, Any]] = {}  # name -> tool metadata
        self._tags: Dict[str, Set[str]] = {}  # tag -> tool names
        self._lock = threading.RLock()
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def register_tool(
        self,
        name: str,
        func: Callable,
        description: str,
        input_schema: Dict[str, Any],
        output_schema: Optional[Dict[str, Any]] = None,
        tags: Optional[List[str]] = None,
        version: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        [Class method intent]
        Register a tool with the registry for use in LLM workflows.
        
        [Design principles]
        - Comprehensive tool metadata
        - Input/output schema validation
        - Support for tool categorization via tags
        - Clear error handling for registration failures
        
        [Implementation details]
        - Validates tool name uniqueness
        - Creates Pydantic model for input validation
        - Stores tool metadata and implementation
        - Updates tag indices for efficient lookup
        
        Args:
            name: Unique name for the tool
            func: Function implementing the tool's functionality
            description: Human-readable description of the tool
            input_schema: JSON Schema describing the tool's input
            output_schema: Optional JSON Schema describing the tool's output
            tags: Optional list of tags for categorization
            version: Optional version string for the tool
            **kwargs: Additional metadata for the tool
            
        Raises:
            ToolRegistrationError: If registration fails
        """
        with self._lock:
            # Check if tool already exists
            if name in self._tools:
                raise ToolRegistrationError(f"Tool '{name}' is already registered")
            
            try:
                # Create input model for validation
                input_model = self._create_input_model(name, input_schema)
                
                # Create output model if provided
                output_model = None
                if output_schema:
                    output_model = self._create_output_model(name, output_schema)
                
                # Create wrapped function that validates input/output
                wrapped_func = self._create_validated_function(name, func, input_model, output_model)
                
                # Store tool metadata
                self._tools[name] = {
                    "func": wrapped_func,
                    "raw_func": func,  # Store original function for inspection
                    "description": description,
                    "input_schema": input_schema,
                    "output_schema": output_schema,
                    "input_model": input_model,
                    "output_model": output_model,
                    "tags": tags or [],
                    "version": version or "1.0.0",
                    **kwargs
                }
                
                # Update tag indices
                if tags:
                    for tag in tags:
                        if tag not in self._tags:
                            self._tags[tag] = set()
                        self._tags[tag].add(name)
                
                self._logger.info(f"Registered tool '{name}' with tags {tags or []}")
            except Exception as e:
                raise ToolRegistrationError(f"Failed to register tool '{name}': {str(e)}")
    
    def _create_input_model(self, name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        [Class method intent]
        Create a Pydantic model for validating tool input based on JSON schema.
        
        [Design principles]
        - Convert JSON schema to Pydantic model
        - Support for type validation
        - Clear error messages
        
        [Implementation details]
        - Creates a dynamic Pydantic model
        - Maps JSON schema types to Python types
        - Sets up validation rules
        
        Args:
            name: Name of the tool (for model naming)
            schema: JSON Schema for the tool's input
            
        Returns:
            Type[BaseModel]: Pydantic model for input validation
            
        Raises:
            ToolRegistrationError: If schema is invalid
        """
        try:
            # Extract properties from schema
            properties = schema.get("properties", {})
            required = schema.get("required", [])
            
            # Create field definitions
            fields = {}
            for prop_name, prop_schema in properties.items():
                # Determine the field type
                field_type = self._map_schema_type(prop_schema)
                
                # Determine if the field is required
                is_required = prop_name in required
                
                # Create the field definition
                if is_required:
                    fields[prop_name] = (field_type, ...)
                else:
                    fields[prop_name] = (field_type, None)
            
            # Create the model
            model_name = f"{name.capitalize()}Input"
            return create_model(model_name, **fields)
        except Exception as e:
            raise ToolRegistrationError(f"Failed to create input model: {str(e)}")
    
    def _create_output_model(self, name: str, schema: Dict[str, Any]) -> Type[BaseModel]:
        """
        [Class method intent]
        Create a Pydantic model for validating tool output based on JSON schema.
        
        [Design principles]
        - Convert JSON schema to Pydantic model
        - Support for type validation
        - Clear error messages
        
        [Implementation details]
        - Creates a dynamic Pydantic model
        - Maps JSON schema types to Python types
        - Sets up validation rules
        
        Args:
            name: Name of the tool (for model naming)
            schema: JSON Schema for the tool's output
            
        Returns:
            Type[BaseModel]: Pydantic model for output validation
            
        Raises:
            ToolRegistrationError: If schema is invalid
        """
        # Reuse the same logic as input model creation
        return self._create_input_model(name, schema)
    
    def _map_schema_type(self, prop_schema: Dict[str, Any]) -> Type:
        """
        [Class method intent]
        Map JSON schema types to Python types for Pydantic model creation.
        
        [Design principles]
        - Support for common JSON schema types
        - Handling for complex types
        - Default to Any for unknown types
        
        [Implementation details]
        - Maps JSON schema type strings to Python types
        - Handles arrays, objects, and primitives
        
        Args:
            prop_schema: JSON Schema property definition
            
        Returns:
            Type: Corresponding Python type
        """
        schema_type = prop_schema.get("type")
        
        if schema_type == "string":
            return str
        elif schema_type == "integer":
            return int
        elif schema_type == "number":
            return float
        elif schema_type == "boolean":
            return bool
        elif schema_type == "array":
            items = prop_schema.get("items", {})
            item_type = self._map_schema_type(items)
            return List[item_type]
        elif schema_type == "object":
            return Dict[str, Any]
        else:
            return Any
    
    def _create_validated_function(
        self, 
        name: str, 
        func: Callable, 
        input_model: Type[BaseModel],
        output_model: Optional[Type[BaseModel]]
    ) -> Callable:
        """
        [Class method intent]
        Create a wrapper function that validates inputs and outputs against schemas.
        
        [Design principles]
        - Automatic validation of inputs and outputs
        - Clean error reporting
        - Transparent to function implementation
        
        [Implementation details]
        - Creates wrapper around original function
        - Validates input against input model
        - Validates output against output model if provided
        - Propagates errors with clear messages
        
        Args:
            name: Name of the tool
            func: Original function implementing the tool
            input_model: Pydantic model for input validation
            output_model: Optional Pydantic model for output validation
            
        Returns:
            Callable: Wrapped function with validation
        """
        def validated_func(**kwargs):
            try:
                # Validate input
                try:
                    validated_input = input_model(**kwargs)
                except ValidationError as e:
                    raise ToolExecutionError(f"Invalid input for tool '{name}': {str(e)}")
                
                # Call original function
                try:
                    result = func(**validated_input.model_dump())
                except Exception as e:
                    raise ToolExecutionError(f"Error executing tool '{name}': {str(e)}")
                
                # Validate output if model provided
                if output_model is not None:
                    try:
                        if isinstance(result, dict):
                            validated_output = output_model(**result)
                            return validated_output.model_dump()
                        else:
                            raise ToolExecutionError(
                                f"Tool '{name}' returned {type(result).__name__}, expected dict"
                            )
                    except ValidationError as e:
                        raise ToolExecutionError(f"Invalid output from tool '{name}': {str(e)}")
                
                return result
            except Exception as e:
                if isinstance(e, ToolExecutionError):
                    raise e
                raise ToolExecutionError(f"Error in tool '{name}': {str(e)}")
        
        # Copy function metadata
        validated_func.__name__ = func.__name__
        validated_func.__doc__ = func.__doc__
        
        return validated_func
    
    def unregister_tool(self, name: str) -> None:
        """
        [Class method intent]
        Remove a tool from the registry.
        
        [Design principles]
        - Support for dynamic tool management
        - Clean removal of all tool metadata
        - Clear error reporting
        
        [Implementation details]
        - Removes tool from main registry
        - Updates tag indices
        - Validates tool exists before removal
        
        Args:
            name: Name of the tool to unregister
            
        Raises:
            ToolNotFoundError: If the tool does not exist
        """
        with self._lock:
            # Check if tool exists
            if name not in self._tools:
                raise ToolNotFoundError(f"Tool '{name}' is not registered")
            
            # Get tool tags
            tool_tags = self._tools[name]["tags"]
            
            # Remove from tag indices
            for tag in tool_tags:
                if tag in self._tags and name in self._tags[tag]:
                    self._tags[tag].remove(name)
                    # Remove empty tag sets
                    if not self._tags[tag]:
                        del self._tags[tag]
            
            # Remove from main registry
            del self._tools[name]
            
            self._logger.info(f"Unregistered tool '{name}'")
    
    def get_tool(self, name: str) -> Dict[str, Any]:
        """
        [Class method intent]
        Get a tool by name.
        
        [Design principles]
        - Direct access to tool information
        - Complete metadata access
        - Clear error reporting
        
        [Implementation details]
        - Validates tool exists
        - Returns complete tool metadata
        
        Args:
            name: Name of the tool to retrieve
            
        Returns:
            Dict[str, Any]: Tool metadata including function and schemas
            
        Raises:
            ToolNotFoundError: If the tool does not exist
        """
        with self._lock:
            # Check if tool exists
            if name not in self._tools:
                raise ToolNotFoundError(f"Tool '{name}' is not registered")
            
            return self._tools[name]
    
    def has_tool(self, name: str) -> bool:
        """
        [Class method intent]
        Check if a tool exists in the registry.
        
        [Design principles]
        - Simple existence check
        - No exceptions for normal flow
        
        [Implementation details]
        - Checks internal registry for tool name
        
        Args:
            name: Name of the tool to check
            
        Returns:
            bool: True if the tool exists, False otherwise
        """
        with self._lock:
            return name in self._tools
    
    def list_tools(self, tag: Optional[str] = None) -> List[str]:
        """
        [Class method intent]
        List available tools, optionally filtered by tag.
        
        [Design principles]
        - Support for tool discovery
        - Optional filtering by category
        - Consistent ordering
        
        [Implementation details]
        - Returns all tool names if no tag specified
        - Filters by tag if provided
        - Sorts results for consistent ordering
        
        Args:
            tag: Optional tag to filter tools
            
        Returns:
            List[str]: List of tool names
        """
        with self._lock:
            if tag is not None:
                return sorted(self._tags.get(tag, set()))
            else:
                return sorted(self._tools.keys())
    
    def list_tags(self) -> List[str]:
        """
        [Class method intent]
        List all tags in the registry.
        
        [Design principles]
        - Support for tag discovery
        - Consistent ordering
        
        [Implementation details]
        - Returns all tag names
        - Sorts results for consistent ordering
        
        Returns:
            List[str]: List of tag names
        """
        with self._lock:
            return sorted(self._tags.keys())
    
    def get_tools_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        [Class method intent]
        Get all tools with a specific tag.
        
        [Design principles]
        - Support for category-based tool retrieval
        - Complete metadata access
        
        [Implementation details]
        - Finds all tools with the specified tag
        - Returns complete tool metadata for each
        
        Args:
            tag: Tag to filter tools
            
        Returns:
            List[Dict[str, Any]]: List of tool metadata
        """
        with self._lock:
            tool_names = self._tags.get(tag, set())
            return [self._tools[name] for name in tool_names]
    
    def execute_tool(self, name: str, **kwargs) -> Any:
        """
        [Class method intent]
        Execute a tool by name with the provided arguments.
        
        [Design principles]
        - Direct tool execution interface
        - Input validation
        - Clear error reporting
        
        [Implementation details]
        - Gets tool by name
        - Executes wrapped function with validation
        - Propagates errors with clear context
        
        Args:
            name: Name of the tool to execute
            **kwargs: Arguments to pass to the tool
            
        Returns:
            Any: Tool execution result
            
        Raises:
            ToolNotFoundError: If the tool does not exist
            ToolExecutionError: If execution fails
        """
        # Get tool
        tool = self.get_tool(name)
        
        # Execute function
        try:
            return tool["func"](**kwargs)
        except Exception as e:
            if isinstance(e, ToolExecutionError):
                raise e
            raise ToolExecutionError(f"Error executing tool '{name}': {str(e)}")
    
    def as_langchain_tool(self, name: str) -> Tool:
        """
        [Class method intent]
        Convert a registered tool to a LangChain Tool instance.
        
        [Design principles]
        - Seamless integration with LangChain
        - Preserve tool metadata
        - Type-safe conversion
        
        [Implementation details]
        - Gets tool by name
        - Creates LangChain Tool with appropriate parameters
        - Preserves description and schema information
        
        Args:
            name: Name of the tool to convert
            
        Returns:
            Tool: LangChain Tool instance
            
        Raises:
            ToolNotFoundError: If the tool does not exist
        """
        # Get tool
        tool_info = self.get_tool(name)
        
        # Convert to LangChain Tool
        return Tool(
            name=name,
            description=tool_info["description"],
            func=tool_info["func"],
            args_schema=tool_info["input_model"]
        )
    
    def get_langchain_tools(self, tags: Optional[List[str]] = None) -> List[Tool]:
        """
        [Class method intent]
        Get all tools as LangChain Tool instances, optionally filtered by tags.
        
        [Design principles]
        - Batch conversion to LangChain format
        - Support for tag filtering
        - Consistent ordering
        
        [Implementation details]
        - Optionally filters tools by tags
        - Converts each tool to LangChain format
        - Sorts by name for consistent ordering
        
        Args:
            tags: Optional list of tags to filter tools
            
        Returns:
            List[Tool]: List of LangChain Tool instances
        """
        # Get tool names
        if tags:
            # Find tools with ANY of the specified tags
            tool_names = set()
            for tag in tags:
                tool_names.update(self._tags.get(tag, set()))
            tool_names = sorted(tool_names)
        else:
            with self._lock:
                tool_names = sorted(self._tools.keys())
        
        # Convert each tool to LangChain format
        return [self.as_langchain_tool(name) for name in tool_names]
    
    def get_schema_spec(self, name: str) -> Dict[str, Any]:
        """
        [Class method intent]
        Get the OpenAPI-compatible schema specification for a tool.
        
        [Design principles]
        - Support for LLM function calling
        - Standard schema format
        - Complete type information
        
        [Implementation details]
        - Formats tool schema in OpenAPI-compatible format
        - Includes all parameters and type information
        - Compatible with LLM function calling
        
        Args:
            name: Name of the tool to get schema for
            
        Returns:
            Dict[str, Any]: OpenAPI-compatible schema spec
            
        Raises:
            ToolNotFoundError: If the tool does not exist
        """
        # Get tool
        tool_info = self.get_tool(name)
        
        # Create schema spec
        return {
            "name": name,
            "description": tool_info["description"],
            "parameters": {
                "type": "object",
                "properties": tool_info["input_schema"].get("properties", {}),
                "required": tool_info["input_schema"].get("required", [])
            }
        }
    
    def clear(self) -> None:
        """
        [Class method intent]
        Removes all tools from the registry.
        
        [Design principles]
        - Provides a way to reset the registry state.
        
        [Implementation details]
        - Thread-safe clearing of all registered tools and tags.
        """
        with self._lock:
            self._tools.clear()
            self._tags.clear()


class LangChainToolAdapter:
    """
    [Class intent]
    Adapts the ToolRegistry to work with LangChain tools.
    This enables bidirectional integration between the custom ToolRegistry
    and the LangChain tool ecosystem.
    
    [Design principles]
    - Bridge between ToolRegistry and LangChain
    - Support for both import and export of tools
    - Maintain tool metadata consistency
    
    [Implementation details]
    - Uses ToolRegistry for underlying tool management
    - Converts tools between formats
    - Preserves tool metadata during conversion
    """
    
    def __init__(self, tool_registry: ToolRegistry):
        """
        [Class method intent]
        Initialize the adapter with a ToolRegistry instance.
        
        [Design principles]
        - Composition over inheritance
        - Delegate tool management to ToolRegistry
        
        [Implementation details]
        - Stores reference to ToolRegistry
        
        Args:
            tool_registry: ToolRegistry instance
        """
        self.tool_registry = tool_registry
        self._logger = logging.getLogger(self.__class__.__name__)
    
    def import_langchain_tool(
        self, 
        tool: Union[LangChainTool, Tool], 
        tags: Optional[List[str]] = None
    ) -> None:
        """
        [Class method intent]
        Import a LangChain tool into the ToolRegistry.
        
        [Design principles]
        - Seamless integration with LangChain tools
        - Preserve tool metadata
        - Support for custom tags
        
        [Implementation details]
        - Extracts tool metadata from LangChain Tool
        - Registers tool with ToolRegistry
        - Preserves schema information
        
        Args:
            tool: LangChain Tool instance
            tags: Optional list of tags to apply to the tool
            
        Raises:
            ToolRegistrationError: If registration fails
        """
        try:
            # Extract tool metadata
            name = tool.name
            description = tool.description
            func = tool.run
            
            # Extract schema from args_schema if available
            input_schema = {}
            if hasattr(tool, "args_schema"):
                schema_cls = tool.args_schema
                if schema_cls:
                    # Extract schema from Pydantic model
                    schema_json = schema_cls.model_json_schema()
                    input_schema = {
                        "properties": schema_json.get("properties", {}),
                        "required": schema_json.get("required", [])
                    }
            
            # Register tool
            self.tool_registry.register_tool(
                name=name,
                func=func,
                description=description,
                input_schema=input_schema,
                tags=tags,
                source="langchain"
            )
            
            self._logger.info(f"Imported LangChain tool '{name}'")
        except Exception as e:
            raise ToolRegistrationError(f"Failed to import LangChain tool: {str(e)}")
    
    def import_langchain_tools(
        self, 
        tools: List[Union[LangChainTool, Tool]], 
        tags: Optional[List[str]] = None
    ) -> None:
        """
        [Class method intent]
        Import multiple LangChain tools into the ToolRegistry.
        
        [Design principles]
        - Batch import support
        - Consistent tag application
        
        [Implementation details]
        - Imports each tool individually
        - Applies the same tags to all tools
        
        Args:
            tools: List of LangChain Tool instances
            tags: Optional list of tags to apply to all tools
            
        Raises:
            ToolRegistrationError: If registration fails for any tool
        """
        for tool in tools:
            self.import_langchain_tool(tool, tags)
    
    def export_to_langchain_agent(self, tags: Optional[List[str]] = None) -> List[Tool]:
        """
        [Class method intent]
        Export tools to a format suitable for LangChain agents.
        
        [Design principles]
        - Support for LangChain agent integration
        - Tag-based tool selection
        - Consistent tool format
        
        [Implementation details]
        - Converts tools to LangChain format
        - Optionally filters by tags
        - Returns list ready for agent use
        
        Args:
            tags: Optional list of tags to filter tools
            
        Returns:
            List[Tool]: List of LangChain Tool instances
        """
        return self.tool_registry.get_langchain_tools(tags)


# Global singleton instance of the tool registry
_global_registry = ToolRegistry()

def get_tool_registry() -> ToolRegistry:
    """
    [Function intent]
    Returns the global tool registry singleton instance.
    
    [Design principles]
    Provides a consistent access point to the shared tool registry.
    
    [Implementation details]
    Returns the global registry instance for shared access across the application.
    
    Returns:
        The global ToolRegistry instance
    """
    return _global_registry
