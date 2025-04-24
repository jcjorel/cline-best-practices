# Hierarchical Semantic Tree Context: internal_tools

## Directory Purpose
This directory contains internal implementation classes for the MCP server tools that are not directly exposed to clients. These internal tools provide the underlying functionality for public-facing MCP tools defined elsewhere. Each tool follows a consistent interface pattern with proper separation between public and internal concerns, enabling maintainable code with clear boundaries while implementing various analysis and functionality capabilities.

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
  Implements internal tools for consistency analysis between code and documentation.
  These tools support the public dbp_general_query tool but are not directly exposed.
  
source_file_design_principles: |
  - Prefix class names with 'Internal' to indicate private status
  - Maintain the same functionality as original tool
  - Use common base class and error handling
  - Follow consistent interface pattern
  
source_file_constraints: |
  - Not to be used directly by MCP clients
  - Only accessed through the public tools defined in tools.py
  - Must maintain compatibility with existing AnalyzeDocumentConsistencyTool
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T08:55:00Z"
    summary: "Created consistency analysis internal tool by CodeAssistant"
    details: "Migrated AnalyzeDocumentConsistencyTool to internal implementation"
```

### `recommendations.py`
```yaml
source_file_intent: |
  Implements internal tools for recommendation generation and application.
  
source_file_design_principles: |
  - Standardized internal tool interface pattern
  - Clear separation from public-facing tools
  - Consistent error handling and reporting
  
source_file_constraints: |
  - Only to be used by public-facing MCP tools
  - Not exposed directly to MCP clients
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T09:00:00Z"
    summary: "Created recommendations internal tools by CodeAssistant"
    details: "Implemented recommendation generator and applicator tools"
```

### `relationships.py`
```yaml
source_file_intent: |
  Implements internal tools for document relationship management.
  
source_file_design_principles: |
  - Consistent interface with other internal tools
  - Clear separation from public API
  - Follows standard error handling patterns
  
source_file_constraints: |
  - For internal use only
  - Must be called through public tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T09:15:00Z"
    summary: "Created document relationships internal tool by CodeAssistant"
    details: "Implemented tool for managing document relationships"
```

### `visualization.py`
```yaml
source_file_intent: |
  Implements internal tools for generating Mermaid diagrams from document and code relationships.
  
source_file_design_principles: |
  - Consistent interface with other internal tools
  - Separation of diagram generation logic from public tools
  
source_file_constraints: |
  - For internal use only
  - Must be called through public visualization tools
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-16T09:20:00Z"
    summary: "Created visualization internal tool by CodeAssistant"
    details: "Implemented Mermaid diagram generation capabilities"
```

<!-- End of HSTC.md file -->
