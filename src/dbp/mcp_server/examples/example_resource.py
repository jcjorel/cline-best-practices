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
# Provides an example implementation of an MCP resource using the MCPResource base class.
# This serves as a reference for creating custom MCP resources with the unified API.
###############################################################################
# [Source file design principles]
# - Demonstrates proper MCPResource implementation pattern
# - Shows how to implement the get_content method
# - Includes examples for context handling
# - Demonstrates how to register the resource with FastMCP
###############################################################################
# [Source file constraints]
# - For demonstration purposes only, not for production use
# - Does not perform any actual meaningful operations
###############################################################################
# [Dependencies]
# system:typing
# system:pydantic
# codebase:src/dbp/mcp_server/mcp_resource.py
###############################################################################
# [GenAI tool change history]
# 2025-04-27T01:27:00Z : Created example resource implementation by CodeAssistant
# * Implemented ExampleResource class using MCPResource base class
# * Added parameter and content models
# * Implemented get_content method
# * Added example registration code
###############################################################################

import logging
from typing import Dict, List, Any, Optional

from pydantic import BaseModel, Field

from ..mcp_resource import MCPResource

logger = logging.getLogger(__name__)


# Parameter model for the example resource
class ExampleResourceParams(BaseModel):
    """
    [Class intent]
    Defines the parameters for the example resource.
    
    [Design principles]
    Simple model with configurable options for testing.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    item_id: Optional[int] = Field(default=None, description="ID of the item to retrieve")
    filter_type: Optional[str] = Field(default=None, description="Type of filter to apply")
    max_items: int = Field(default=10, description="Maximum number of items to return")


# Content model for the example resource
class ExampleResourceContent(BaseModel):
    """
    [Class intent]
    Defines the content format for the example resource.
    
    [Design principles]
    Simple model for demonstration purposes.
    
    [Implementation details]
    Uses Pydantic model for schema validation.
    """
    items: List[Dict[str, Any]] = Field(description="List of items in the result")
    total_items: int = Field(description="Total number of items available")
    metadata: Dict[str, Any] = Field(description="Additional metadata about the content")


class ExampleResource(MCPResource[ExampleResourceParams, ExampleResourceContent]):
    """
    [Class intent]
    Demonstrates a basic resource implementation using the MCPResource base class.
    
    [Design principles]
    - Shows proper inheritance from MCPResource
    - Implements required methods
    - Demonstrates context handling
    
    [Implementation details]
    - Simulates data retrieval
    - Handles parameters and context
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes the example resource.
        
        [Design principles]
        Simple initialization with clear name and description.
        
        [Implementation details]
        Calls parent constructor with resource metadata and models.
        """
        super().__init__(
            name="example_resource",
            description="An example resource demonstrating the MCPResource base class",
            param_model=ExampleResourceParams,
            content_model=ExampleResourceContent,
            version="1.0.0"
        )
        self.logger = logging.getLogger("dbp.mcp_server.examples.example_resource")
        self.logger.info("ExampleResource initialized")
        
        # Sample data for demonstration
        self._sample_data = [
            {
                "id": 1,
                "name": "Item 1",
                "description": "Description for Item 1",
                "type": "type_a"
            },
            {
                "id": 2,
                "name": "Item 2",
                "description": "Description for Item 2",
                "type": "type_b"
            },
            {
                "id": 3,
                "name": "Item 3",
                "description": "Description for Item 3",
                "type": "type_a"
            },
            {
                "id": 4,
                "name": "Item 4",
                "description": "Description for Item 4",
                "type": "type_c"
            },
            {
                "id": 5,
                "name": "Item 5",
                "description": "Description for Item 5",
                "type": "type_b"
            }
        ]
    
    async def get_content(
        self,
        params: ExampleResourceParams,
        context: Dict[str, Any]
    ) -> ExampleResourceContent:
        """
        [Function intent]
        Gets the content of the resource based on the provided parameters.
        
        [Design principles]
        - Implements the core resource logic
        - Handles parameters and filtering
        
        [Implementation details]
        - Filters sample data based on parameters
        - Returns formatted content
        
        Args:
            params: The validated parameters
            context: The execution context
            
        Returns:
            The resource's content
        """
        self.logger.info(f"Getting content with parameters: {params}")
        
        # Filter items based on parameters
        filtered_items = self._sample_data
        
        # Filter by item_id if provided
        if params.item_id is not None:
            filtered_items = [item for item in filtered_items if item["id"] == params.item_id]
            
        # Filter by filter_type if provided
        if params.filter_type is not None:
            filtered_items = [item for item in filtered_items if item["type"] == params.filter_type]
            
        # Limit the number of items
        filtered_items = filtered_items[:params.max_items]
        
        # Create the content
        content = ExampleResourceContent(
            items=filtered_items,
            total_items=len(self._sample_data),
            metadata={
                "timestamp": "2025-04-27T01:27:00Z",
                "source": "example_resource",
                "filter_applied": params.filter_type is not None or params.item_id is not None
            }
        )
        
        return content


# Example registration code
def register_example_resources(mcp):
    """
    [Function intent]
    Registers the example resource with the FastMCP instance.
    
    [Design principles]
    Simple helper for resource registration.
    
    [Implementation details]
    Creates resource instance and registers it with FastMCP.
    
    Args:
        mcp: The FastMCP instance to register with
    """
    # Create and register the example resource
    example_resource = ExampleResource()
    example_resource.register(mcp)
    
    return {
        "example_resource": example_resource
    }
