# Hierarchical Semantic Tree Context: internal_tools

## Directory Purpose
This directory contains internal MCP tools that provide implementation for functionality exposed through public tools. These internal tools are not intended to be used directly by MCP clients but are accessed through the public tools defined in the MCP server. The directory implements a clear separation between public and internal tools with consistent interfaces, proper naming conventions, and common error handling patterns.

## Child Directories
<!-- No child directories with HSTC.md -->

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
  - timestamp: "2025-04-16T09:25:00Z"
    summary: "Created internal tools package by CodeAssistant"
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
    summary: "Created base internal tools structure by CodeAssistant"
    details: "Defined InternalMCPTool base class"
```

### `consistency.py`
```yaml
source_file_intent: |
  Implements internal tools for consistency analysis within the MCP server.
  
source_file_design_principles: |
  - Provides consistency checking functionality for MCP resources and tools
  - Follows the internal tool interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through public tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created consistency analysis tool"
    details: "Implemented internal consistency analysis functionality"
```

### `recommendations.py`
```yaml
source_file_intent: |
  Implements internal tools for generating and applying recommendations within the MCP server.
  
source_file_design_principles: |
  - Provides recommendation generation and application functionality
  - Follows the internal tool interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through public tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created recommendations tools"
    details: "Implemented internal recommendation generation and application functionality"
```

### `relationships.py`
```yaml
source_file_intent: |
  Implements internal tools for managing document relationships within the MCP server.
  
source_file_design_principles: |
  - Provides document relationship management functionality
  - Follows the internal tool interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through public tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created document relationships tool"
    details: "Implemented internal document relationship management functionality"
```

### `visualization.py`
```yaml
source_file_intent: |
  Implements internal tools for visualization generation within the MCP server.
  
source_file_design_principles: |
  - Provides visualization generation functionality, particularly for Mermaid diagrams
  - Follows the internal tool interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through public tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-23T14:58:00Z"
    summary: "Created visualization tool"
    details: "Implemented internal Mermaid diagram generation functionality"
```

<!-- End of HSTC.md file -->
