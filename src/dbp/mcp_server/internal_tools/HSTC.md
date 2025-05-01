# Hierarchical Semantic Tree Context: internal_tools

## Directory Purpose
This directory contains internal MCP tool implementations that are used by public MCP tools but not directly exposed to MCP clients. It provides a clear separation between public interfaces and internal implementation details, with consistent error handling patterns and interface definitions. The internal tools provide underlying functionality for visualization, particularly Mermaid diagram generation, which supports public facing tools.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports the internal tool classes for use by public MCP tools.
  This module is not intended to be used directly by MCP clients.
  
source_file_design_principles: |
  - Simple exports to make internal tools available to public tools
  - No direct functionality, just re-exports
  - Clear documentation of internal status
  
source_file_constraints: |
  - Only for use by public tools in tools.py
  - Not to be exposed directly to MCP clients
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-05-02T00:37:49Z"
    summary: "Removed consistency analysis tool"
    details: "Removed import and export of InternalConsistencyAnalysisTool, removed reference from __all__ list"
  - timestamp: "2025-04-16T09:25:00Z"
    summary: "Created internal tools package"
    details: "Added exports for internal tool classes"
```

### `base.py`
```yaml
source_file_intent: |
  Defines base classes and common utilities for internal MCP tools that are not
  directly exposed to clients. These internal tools provide the implementation
  for functionality that is exposed through the documented public tools.
  
source_file_design_principles: |
  - Clear separation between public and internal tools
  - Consistent interface for all internal tools
  - Proper naming conventions to indicate internal/private status
  - Common error handling and validation patterns
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through the public tools defined in tools.py
  - Must maintain compatibility with existing tool functionality
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T08:55:00Z"
    summary: "Created base internal tools structure"
    details: "Defined InternalMCPTool base class"
```

### `visualization.py`
```yaml
source_file_intent: |
  Implements internal tools for visualization, particularly for generating
  Mermaid diagrams from various data structures. These tools support
  the public dbp_general_query tool but are not directly exposed.
  
source_file_design_principles: |
  - Prefix class names with 'Internal' to indicate private status
  - Maintain consistent interface with other internal tools
  - Use common base class and error handling
  - Follow consistent interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through the public tools defined in tools.py
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-05-02T00:20:30Z"
    summary: "Removed doc_relationships dependencies"
    details: "Removed dependency on doc_relationships component, implemented standalone mermaid diagram generation, updated tool interface to work without external components"
  - timestamp: "2025-04-16T09:24:00Z"
    summary: "Created visualization internal tool"
    details: "Created placeholder implementation for Mermaid diagram generation"
```

End of HSTC.md file
