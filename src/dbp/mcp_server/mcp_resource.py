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
# Provides a base class for MCP resources that simplifies implementation and unifies
# the API for resource access. This class abstracts away the MCP protocol details
# and provides a clean interface for resource developers.
###############################################################################
# [Source file design principles]
# - Hides MCP machinery from resource implementations
# - Provides a unified resource API regardless of client capabilities
# - Follows a content-first design where resources should only implement get_content() method
# - By design, get() should NOT be overridden in most cases as it automatically
#   handles content retrieval and formatting
# - Allows access to full FastMCP features when needed
# - Handles conversion between different content formats
# - Follows a clean, inheritance-based design pattern
###############################################################################
# [Source file constraints]
# - Must be compatible with FastMCP's resource registration mechanism
# - Must maintain backward compatibility with existing resources
# - Must handle different client capabilities transparently
###############################################################################
# [Dependencies]
# system:typing
# system:pydantic
# system:fastmcp
# codebase:src/dbp/mcp_server/server.py
###############################################################################
# [GenAI tool change history]
# 2025-04-27T01:50:00Z : Updated import for Resource class by CodeAssistant
# * Changed import from fastmcp.resource to fastmcp.resources to match FastMCP v2 structure
# 2025-04-27T01:25:00Z : Created MCPResource base class by CodeAssistant
# * Implemented unified resource API
# * Added automatic content formatting and handling
# * Created abstract methods for resource implementation
# * Added support for context and error handling
###############################################################################

import logging
from abc import ABC, abstractmethod
from typing import (
    Any, Dict, List, Optional, Type, TypeVar, Generic, 
    Union, get_type_hints, cast
)

from pydantic import BaseModel, Field, create_model

from fastmcp import FastMCP
from fastmcp.resources import Resource

logger = logging.getLogger(__name__)

# Type variables for parameter and content models
ParamType = TypeVar('ParamType', bound=BaseModel)
ContentType = TypeVar('ContentType', bound=BaseModel)


class MCPResource(Generic[ParamType, ContentType], ABC):
    """
    [Class intent]
    Base class for MCP resources that provides a unified API and hides MCP machinery.
    This class simplifies resource implementation by providing a consistent interface
    for resource access.
    
    [Design principles]
    - Unified resource API for all resources
    - Automatic content formatting and handling
    - Clean separation between resource logic and MCP protocol details
    - Support for context and error handling
    
    [Implementation details]
    - Uses FastMCP's Resource class under the hood
    - Registers the resource with FastMCP
    - Handles content formatting and error handling
    - Provides access to context for resource access
    """
    
    def __init__(
        self,
        name: str,
        description: str,
        param_model: Type[ParamType],
        content_model: Type[ContentType],
        version: str = "1.0.0",
    ):
        """
        [Class method intent]
        Initializes the MCP resource with the required metadata and models.
        
        [Design principles]
        Clear initialization with all required metadata.
        
        [Implementation details]
        Stores resource metadata and models for later registration.
        
        Args:
            name: The name of the resource
            description: A description of what the resource provides
            param_model: The Pydantic model for the resource's parameters
            content_model: The Pydantic model for the resource's content
            version: The version of the resource
        """
        self.name = name
        self.description = description
        self.param_model = param_model
        self.content_model = content_model
        self.version = version
        self.logger = logging.getLogger(f"dbp.mcp_server.resources.{name}")
        
        # This will be set when the resource is registered
        self._resource = None
        
    def register(self, mcp: FastMCP) -> None:
        """
        [Function intent]
        Registers the resource with the FastMCP instance.
        
        [Design principles]
        Handles registration of the resource.
        
        [Implementation details]
        Creates and registers a Resource instance.
        
        Args:
            mcp: The FastMCP instance to register with
        """
        # Create and register the resource
        self._resource = Resource(
            name=self.name,
            description=self.description,
            param_schema=self.param_model,
            content_schema=self.content_model,
            version=self.version,
            get=self._get_wrapper
        )
        mcp.register_resource(self._resource)
        
        self.logger.info(f"Registered resource '{self.name}'")
        
    async def _get_wrapper(
        self,
        params: ParamType,
        context: Optional[Dict[str, Any]] = None
    ) -> ContentType:
        """
        [Function intent]
        Wrapper for the get method that handles context preparation.
        
        [Design principles]
        Prepares context for resource access and handles exceptions.
        
        [Implementation details]
        Calls the get method with prepared context.
        
        Args:
            params: The validated parameters
            context: The execution context
            
        Returns:
            The resource's content
        """
        prepared_context = self._prepare_context(context)
        
        try:
            # Call the get method
            return await self.get(params, prepared_context)
            
        except Exception as e:
            self.logger.error(f"Error accessing resource '{self.name}': {str(e)}", exc_info=True)
            raise
            
    def _prepare_context(self, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Prepares the context for resource access.
        
        [Design principles]
        Ensures context has all required fields.
        
        [Implementation details]
        Adds any required context fields.
        
        Args:
            context: The original context
            
        Returns:
            The prepared context
        """
        prepared_context = context.copy() if context else {}
        
        # Add any required context fields here
        
        return prepared_context
        
    async def get(
        self,
        params: ParamType,
        context: Dict[str, Any]
    ) -> ContentType:
        """
        [Function intent]
        Gets the resource content based on the provided parameters.
        
        [Design principles]
        Default implementation that calls get_content and formats the result.
        
        IMPORTANT: By design, this method should NOT be overridden in most cases.
        The recommended pattern is to only implement the get_content() method, and this
        default implementation will handle the formatting and error handling.
        Override this method ONLY in exceptional cases where you need custom behavior
        that cannot be achieved through the get_content() method.
        
        [Implementation details]
        Calls get_content and formats the result.
        
        Args:
            params: The validated parameters
            context: The execution context
            
        Returns:
            The resource's content
        """
        # Get the content
        content = await self.get_content(params, context)
        
        # Format the content if needed
        return self._format_content(content)
        
    def _format_content(self, content: Any) -> ContentType:
        """
        [Function intent]
        Formats the content to match the content model.
        
        [Design principles]
        Converts raw content to the expected content model.
        
        [Implementation details]
        Default implementation assumes content is already in the correct format.
        
        Args:
            content: The raw content
            
        Returns:
            The formatted content
        """
        # If content is already a ContentType instance, return it
        if isinstance(content, self.content_model):
            return content
            
        # If content is a dict, create a ContentType instance
        if isinstance(content, dict):
            return self.content_model(**content)
            
        # If content is a string, try to create a ContentType with a 'content' field
        if isinstance(content, str):
            try:
                return self.content_model(content=content)
            except Exception:
                pass
                
        # If we can't format the content, raise an exception
        raise ValueError(
            f"Cannot format content to match {self.content_model.__name__}. "
            f"Override _format_content in your resource implementation to handle this case."
        )
        
    @abstractmethod
    async def get_content(
        self,
        params: ParamType,
        context: Dict[str, Any]
    ) -> Any:
        """
        [Function intent]
        Gets the raw content of the resource.
        
        [Design principles]
        Abstract method that must be implemented by subclasses.
        
        [Implementation details]
        Should implement the resource's logic for content retrieval.
        
        Args:
            params: The validated parameters
            context: The execution context
            
        Returns:
            The raw content of the resource
        """
        pass
