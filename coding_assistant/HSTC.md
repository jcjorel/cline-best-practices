# Hierarchical Semantic Tree Context: coding_assistant

## Directory Purpose
The coding_assistant directory contains tools, templates, and resources that support the GenAI coding assistant in working with the Documentation-Based Programming system. It provides standardized templates for code headers and function documentation, scripts for gathering design context and identifying HSTC updates, and management of coding assistant-specific data. This directory serves as the bridge between the documentation-based programming system and the AI coding assistants that help maintain and develop it, ensuring consistency and adherence to the project's documentation standards.

## Child Directories

### dbp
Contains resources and tools specific to the Documentation-Based Programming system that are used by the coding assistant, including a dedicated database and recommendation storage.

### logs
Stores logs from coding assistant operations, providing audit trails and debugging information for coding assistant activities.

### scripts
Contains utility scripts used by the coding assistant for tasks like gathering design context, identifying HSTC updates, and other automation needs.

## Local Files

### `GENAI_FUNCTION_TEMPLATE.txt`
```yaml
source_file_intent: |
  Defines standardized templates for function, method, and class documentation across different programming languages, ensuring consistent documentation structure.
  
source_file_design_principles: |
  - Standardized documentation format for all code elements
  - Language-specific formatting while maintaining consistent structure
  - Clear separation of intent, design principles, and implementation details
  
source_file_constraints: |
  - Must be compatible with various programming languages
  - Must maintain the three-section documentation pattern across all templates
  
dependencies:
  - kind: codebase
    dependency: doc/CODING_GUIDELINES.md
  
change_history:
  - timestamp: "2025-04-24T23:23:35Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of GENAI_FUNCTION_TEMPLATE.txt in HSTC.md"
```

### `GENAI_HEADER_TEMPLATE.txt`
```yaml
source_file_intent: |
  Defines the standardized file header template that must be included at the top of all source code files in the project.
  
source_file_design_principles: |
  - Comprehensive file metadata in a consistent format
  - Clear documentation of file intent, design principles, constraints, and dependencies
  - Structured change history tracking
  
source_file_constraints: |
  - Must be applied to all non-markdown files
  - Must maintain backward compatibility for automated tools
  
dependencies:
  - kind: codebase
    dependency: doc/CODING_GUIDELINES.md
  
change_history:
  - timestamp: "2025-04-24T23:23:35Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of GENAI_HEADER_TEMPLATE.txt in HSTC.md"
```

### `MARKDOWN_CHANGELOG.md`
```yaml
source_file_intent: |
  Tracks changes made to markdown files within the coding_assistant directory, maintaining a chronological record of documentation updates.
  
source_file_design_principles: |
  - Chronological ordering of changes with timestamps
  - Concise change descriptions with file references
  - Limited entry count to maintain relevance
  
source_file_constraints: |
  - Must be updated whenever markdown files in the directory are modified
  - Must maintain a strict 20-entry limit, removing oldest entries when exceeded
  
dependencies:
  - kind: codebase
    dependency: doc/CODING_GUIDELINES.md
  
change_history:
  - timestamp: "2025-04-24T23:23:35Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of MARKDOWN_CHANGELOG.md in HSTC.md"
