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
# Implements internal tools for visualization, particularly for generating
# Mermaid diagrams from various data structures. These tools support
# the public dbp_general_query tool but are not directly exposed.
###############################################################################
# [Source file design principles]
# - Prefix class names with 'Internal' to indicate private status
# - Maintain consistent interface with other internal tools
# - Use common base class and error handling
# - Follow consistent interface pattern
###############################################################################
# [Source file constraints]
# - Not to be used directly by MCP clients
# - Only accessed through the public tools defined in tools.py
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-05-02T00:20:30Z : Removed doc_relationships dependencies by CodeAssistant
# * Removed dependency on doc_relationships component
# * Implemented standalone mermaid diagram generation
# * Updated tool interface to work without external components
# 2025-04-16T09:24:00Z : Created visualization internal tool by CodeAssistant
# * Created placeholder implementation for Mermaid diagram generation
###############################################################################

import logging
import os
from typing import Dict, Any, Optional, List

from .base import InternalMCPTool, InternalToolValidationError, InternalToolExecutionError

# Import necessary components
try:
    from ..adapter import SystemComponentAdapter, ComponentNotFoundError
except ImportError as e:
    logging.getLogger(__name__).error(f"Visualization Tools ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception

logger = logging.getLogger(__name__)

class InternalMermaidDiagramTool(InternalMCPTool):
    """
    [Class intent]
    Internal tool for generating simple Mermaid diagrams from various data structures.
    Designed to be used only by the public dbp_general_query tool.

    [Implementation details]
    Provides a simplified implementation for generating basic Mermaid diagrams
    without relying on external components.

    [Design principles]
    Follows consistent interface pattern with other internal tools,
    consistent error handling, and integration with the internal tools framework.
    """

    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="mermaid_diagram_generator",
            adapter=adapter,
            logger_override=logger_override
        )

    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "diagram_type": {"type": "string", "enum": ["flowchart", "sequence", "class", "state", "er"], "description": "Type of diagram to generate."},
                "title": {"type": "string", "description": "Optional title for the diagram"},
                "elements": {"type": "array", "description": "Elements to include in the diagram"},
                "relationships": {"type": "array", "description": "Relationships between elements"},
                "display_options": {"type": "object", "description": "Optional display settings for the diagram"}
            },
            "required": ["diagram_type"]
        }

    def _get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "mermaid_code": {"type": "string", "description": "Generated Mermaid diagram code."},
                "diagram_info": {"type": "object", "description": "Additional information about the diagram."}
            },
            "required": ["mermaid_code"]
        }

    def _execute_implementation(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate a Mermaid diagram based on the specified parameters."""
        diagram_type = data.get("diagram_type")
        title = data.get("title", "Diagram")
        elements = data.get("elements", [])
        relationships = data.get("relationships", [])
        display_options = data.get("display_options", {})

        if not diagram_type:
            raise InternalToolValidationError("Missing required parameter: diagram_type.")

        try:
            # Generate appropriate mermaid code based on diagram type
            if diagram_type == "flowchart":
                mermaid_code = self._generate_flowchart(title, elements, relationships, display_options)
            elif diagram_type == "sequence":
                mermaid_code = self._generate_sequence_diagram(title, elements, relationships, display_options)
            elif diagram_type == "class":
                mermaid_code = self._generate_class_diagram(title, elements, relationships, display_options)
            elif diagram_type == "state":
                mermaid_code = self._generate_state_diagram(title, elements, relationships, display_options)
            elif diagram_type == "er":
                mermaid_code = self._generate_er_diagram(title, elements, relationships, display_options)
            else:
                raise InternalToolValidationError(f"Unsupported diagram type: {diagram_type}")

            return {
                "mermaid_code": mermaid_code,
                "diagram_info": {
                    "type": diagram_type,
                    "title": title,
                    "element_count": len(elements),
                    "relationship_count": len(relationships)
                }
            }

        except Exception as e:
            self.logger.error(f"Error generating {diagram_type} diagram: {e}", exc_info=True)
            raise InternalToolExecutionError(f"Failed to generate {diagram_type} diagram: {e}") from e

    def _generate_flowchart(self, title, elements, relationships, options) -> str:
        """Generate a flowchart diagram."""
        direction = options.get("direction", "TD")  # Top-Down by default
        
        # Start building the diagram
        mermaid_code = [f"flowchart {direction}"]
        
        # Add title as a comment if provided
        if title:
            mermaid_code.append(f"    %% {title}")
            
        # Add nodes (elements)
        for i, element in enumerate(elements):
            if isinstance(element, dict):
                id = element.get("id", f"node{i}")
                label = element.get("label", id)
                shape = element.get("shape", "box")
                
                # Format the node based on shape
                if shape == "rounded":
                    mermaid_code.append(f"    {id}({label})")
                elif shape == "circle":
                    mermaid_code.append(f"    {id}(({label}))")
                elif shape == "diamond":
                    mermaid_code.append(f"    {id}{{{{{label}}}}}")
                else:  # Default to box
                    mermaid_code.append(f"    {id}[{label}]")
            else:
                id = f"node{i}"
                mermaid_code.append(f"    {id}[{element}]")
                
        # Add edges (relationships)
        for rel in relationships:
            if isinstance(rel, dict):
                from_id = rel.get("from")
                to_id = rel.get("to")
                label = rel.get("label", "")
                type = rel.get("type", "-->")
                
                if from_id and to_id:
                    if label:
                        mermaid_code.append(f"    {from_id} {type}|{label}| {to_id}")
                    else:
                        mermaid_code.append(f"    {from_id} {type} {to_id}")
            elif isinstance(rel, list) and len(rel) >= 2:
                from_id, to_id = rel[0], rel[1]
                label = rel[2] if len(rel) > 2 else ""
                
                if label:
                    mermaid_code.append(f"    {from_id} -->|{label}| {to_id}")
                else:
                    mermaid_code.append(f"    {from_id} --> {to_id}")
        
        # If no elements or relationships provided, add a placeholder
        if not elements and not relationships:
            mermaid_code.append("    A[Start] --> B[End]")
            mermaid_code.append("    B --> C[Process]")
            
        return "\n".join(mermaid_code)

    def _generate_sequence_diagram(self, title, elements, relationships, options) -> str:
        """Generate a sequence diagram."""
        # Basic implementation
        mermaid_code = ["sequenceDiagram"]
        
        if title:
            mermaid_code.append(f"    title: {title}")
            
        # Define participants
        for i, element in enumerate(elements):
            if isinstance(element, dict):
                id = element.get("id", f"Participant{i}")
                label = element.get("label", id)
                mermaid_code.append(f"    participant {id} as {label}")
            else:
                mermaid_code.append(f"    participant {element}")
                
        # Define messages
        for rel in relationships:
            if isinstance(rel, dict):
                from_id = rel.get("from")
                to_id = rel.get("to")
                message = rel.get("message", "")
                arrow_type = rel.get("type", "->")
                
                if from_id and to_id and message:
                    mermaid_code.append(f"    {from_id}{arrow_type}{to_id}: {message}")
            
        # If no elements or relationships provided, add placeholder
        if not elements and not relationships:
            mermaid_code.append("    participant A as System A")
            mermaid_code.append("    participant B as System B")
            mermaid_code.append("    A->>B: Request")
            mermaid_code.append("    B-->>A: Response")
            
        return "\n".join(mermaid_code)

    def _generate_class_diagram(self, title, elements, relationships, options) -> str:
        """Generate a class diagram."""
        # Basic implementation
        mermaid_code = ["classDiagram"]
        
        if title:
            mermaid_code.append(f"    %% {title}")
            
        # Define classes
        for i, element in enumerate(elements):
            if isinstance(element, dict):
                name = element.get("name", f"Class{i}")
                attributes = element.get("attributes", [])
                methods = element.get("methods", [])
                
                # Add class definition
                mermaid_code.append(f"    class {name} {{")
                
                # Add attributes
                for attr in attributes:
                    if isinstance(attr, dict):
                        attr_name = attr.get("name", "")
                        attr_type = attr.get("type", "")
                        visibility = attr.get("visibility", "+")
                        mermaid_code.append(f"        {visibility}{attr_name} {attr_type}")
                    else:
                        mermaid_code.append(f"        +{attr}")
                        
                # Add methods
                for method in methods:
                    if isinstance(method, dict):
                        method_name = method.get("name", "")
                        return_type = method.get("return", "")
                        visibility = method.get("visibility", "+")
                        mermaid_code.append(f"        {visibility}{method_name}() {return_type}")
                    else:
                        mermaid_code.append(f"        +{method}()")
                        
                mermaid_code.append("    }")
        
        # Define relationships
        for rel in relationships:
            if isinstance(rel, dict):
                from_class = rel.get("from")
                to_class = rel.get("to")
                type = rel.get("type", "--")
                label = rel.get("label", "")
                
                if from_class and to_class:
                    if label:
                        mermaid_code.append(f"    {from_class} {type} {to_class} : {label}")
                    else:
                        mermaid_code.append(f"    {from_class} {type} {to_class}")
        
        # If no elements or relationships provided, add placeholder
        if not elements and not relationships:
            mermaid_code.append("    class Animal {")
            mermaid_code.append("        +name: string")
            mermaid_code.append("        +age: int")
            mermaid_code.append("        +makeSound()")
            mermaid_code.append("    }")
            mermaid_code.append("    class Dog {")
            mermaid_code.append("        +breed: string")
            mermaid_code.append("        +bark()")
            mermaid_code.append("    }")
            mermaid_code.append("    Animal <|-- Dog")
            
        return "\n".join(mermaid_code)

    def _generate_state_diagram(self, title, elements, relationships, options) -> str:
        """Generate a state diagram."""
        # Basic implementation
        mermaid_code = ["stateDiagram-v2"]
        
        if title:
            mermaid_code.append(f"    %% {title}")
            
        # Define states
        for i, element in enumerate(elements):
            if isinstance(element, dict):
                id = element.get("id", f"State{i}")
                label = element.get("label", id)
                mermaid_code.append(f"    {id}: {label}")
            else:
                mermaid_code.append(f"    {element}")
                
        # Define transitions
        for rel in relationships:
            if isinstance(rel, dict):
                from_state = rel.get("from")
                to_state = rel.get("to")
                label = rel.get("label", "")
                
                if from_state and to_state:
                    if label:
                        mermaid_code.append(f"    {from_state} --> {to_state}: {label}")
                    else:
                        mermaid_code.append(f"    {from_state} --> {to_state}")
        
        # If no elements or relationships provided, add placeholder
        if not elements and not relationships:
            mermaid_code.append("    [*] --> Idle")
            mermaid_code.append("    Idle --> Processing: Start")
            mermaid_code.append("    Processing --> Done: Complete")
            mermaid_code.append("    Processing --> Error: Failure")
            mermaid_code.append("    Done --> [*]")
            mermaid_code.append("    Error --> Idle: Retry")
            
        return "\n".join(mermaid_code)

    def _generate_er_diagram(self, title, elements, relationships, options) -> str:
        """Generate an entity-relationship diagram."""
        # Basic implementation
        mermaid_code = ["erDiagram"]
        
        if title:
            mermaid_code.append(f"    %% {title}")
            
        # Define entities
        for i, element in enumerate(elements):
            if isinstance(element, dict):
                name = element.get("name", f"Entity{i}")
                attributes = element.get("attributes", [])
                
                # Add entity attributes if any
                if attributes:
                    mermaid_code.append(f"    {name} {{")
                    for attr in attributes:
                        if isinstance(attr, dict):
                            attr_name = attr.get("name", "")
                            attr_type = attr.get("type", "string")
                            is_key = attr.get("primary_key", False)
                            key_indicator = "PK" if is_key else ""
                            mermaid_code.append(f"        {attr_type} {attr_name} {key_indicator}")
                        else:
                            mermaid_code.append(f"        string {attr}")
                    mermaid_code.append("    }")
        
        # Define relationships
        for rel in relationships:
            if isinstance(rel, dict):
                entity1 = rel.get("entity1")
                entity2 = rel.get("entity2")
                relation = rel.get("relationship", "")
                cardinality1 = rel.get("cardinality1", "1")
                cardinality2 = rel.get("cardinality2", "1")
                
                if entity1 and entity2:
                    mermaid_code.append(f"    {entity1} {cardinality1}--{cardinality2} {entity2} : {relation}")
        
        # If no elements or relationships provided, add placeholder
        if not elements and not relationships:
            mermaid_code.append("    CUSTOMER {")
            mermaid_code.append("        string id PK")
            mermaid_code.append("        string name")
            mermaid_code.append("        string email")
            mermaid_code.append("    }")
            mermaid_code.append("    ORDER {")
            mermaid_code.append("        string id PK")
            mermaid_code.append("        date created_at")
            mermaid_code.append("        number total")
            mermaid_code.append("    }")
            mermaid_code.append("    CUSTOMER ||--o{ ORDER : places")
            
        return "\n".join(mermaid_code)
