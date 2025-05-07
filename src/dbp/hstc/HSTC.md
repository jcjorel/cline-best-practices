# Hierarchical Semantic Tree Context: HSTC Module

## Directory Purpose
This directory contains the HSTC (Hierarchical Semantic Tree Context) module implementation which manages HSTC.md files across the project. It provides functionality to scan directories for files needing updates, process source files to update documentation, and generate/update HSTC.md files according to project standards. The module integrates with LLM services to provide intelligent documentation analysis and generation.

## Child Directories

### prompts
Contains prompt templates used for LLM-based processing of source files and HSTC.md file generation. These templates define the instructions and expected response formats for various LLM operations within the HSTC module.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization for the HSTC module that manages Hierarchical Semantic Tree 
  Context (HSTC) files. Provides public imports for key components and functions.
  
source_file_design_principles: |
  - Minimal imports to avoid circular dependencies
  - Clear public interface through explicit exports
  - Version information for module tracking
  
source_file_constraints: |
  - Must not contain implementation details, only imports and version
  
dependencies:
  - kind: codebase
    dependency: src/dbp/hstc/component.py
  
change_history:
  - timestamp: "2025-05-07T11:46:00Z"
    summary: "Initial creation of HSTC module package"
    details: "Created package initialization file with version information and imports"
```

### `component.py`
```yaml
source_file_intent: |
  Implements the HSTCComponent class that integrates with the DBP component system
  to provide HSTC.md file management capabilities. This component acts as the entry
  point for HSTC operations and manages the underlying services.
  
source_file_design_principles: |
  - Clean component lifecycle management (initialization, shutdown)
  - Delegation to specialized services for core functionality
  - Simple public API for HSTC operations
  - Explicit dependency declaration and management
  
source_file_constraints: |
  - Must comply with DBP component system requirements
  - Must handle initialization and shutdown correctly
  - Must manage dependencies on other components
  
dependencies:
  - kind: codebase
    dependency: src/dbp/core/component.py
  - kind: codebase
    dependency: src/dbp/hstc/manager.py
  
change_history:
  - timestamp: "2025-05-07T11:47:00Z"
    summary: "Initial implementation of HSTCComponent"
    details: "Created component class with initialization, shutdown, and public methods for HSTC operations"
```

### `exceptions.py`
```yaml
source_file_intent: |
  Defines custom exceptions for the HSTC module to provide clear error information
  and enable specific error handling.
  
source_file_design_principles: |
  - Descriptive exception names for clear error identification
  - Hierarchical exception structure with base class
  - Descriptive error messages for troubleshooting
  
source_file_constraints: |
  - Must derive from base Exception class
  - Must include descriptive docstrings for each exception
  
dependencies:
  - kind: system
    dependency: typing
  
change_history:
  - timestamp: "2025-05-07T12:21:40Z"
    summary: "Added FileAccessError exception"
    details: "Implemented FileAccessError class for file access related issues"
  - timestamp: "2025-05-07T11:46:30Z"
    summary: "Initial implementation of HSTC exceptions"
    details: "Created base HSTCError exception and specialized exception classes for different error scenarios"
```

### `manager.py`
```yaml
source_file_intent: |
  Implements the HSTCManager class that coordinates the HSTC update process
  by orchestrating the scanner, source processor, and HSTC processor components.
  This manager provides a high-level API for updating HSTC.md files throughout
  a directory tree.
  
source_file_design_principles: |
  - Clean coordination of independent services
  - Clear error handling and aggregation
  - Consistent operation reporting
  - Progress tracking and status updates
  
source_file_constraints: |
  - Must handle large directory trees efficiently
  - Must process directories in the correct order (leaves to root)
  - Must maintain consistent state across components
  
dependencies:
  - kind: codebase
    dependency: src/dbp/hstc/scanner.py
  - kind: codebase
    dependency: src/dbp/hstc/source_processor.py
  - kind: codebase
    dependency: src/dbp/hstc/hstc_processor.py
  - kind: codebase
    dependency: src/dbp/hstc/exceptions.py
  - kind: system
    dependency: logging
  - kind: system
    dependency: pathlib
  - kind: system
    dependency: typing
  - kind: system
    dependency: os
  
change_history:
  - timestamp: "2025-05-07T12:16:30Z"
    summary: "Implemented full HSTCManager functionality"
    details: "Created manager class with component coordination, HSTC update orchestration, and source file processing reporting"
  - timestamp: "2025-05-07T11:48:00Z"
    summary: "Initial placeholder implementation of HSTCManager"
    details: "Created placeholder class with interface methods and NotImplementedError responses"
```

### `scanner.py`
```yaml
source_file_intent: |
  Implements the HSTCScanner class that locates directories requiring HSTC.md file
  updates or creation. This scanner identifies directories with HSTC_REQUIRES_UPDATE.md
  files and directories without HSTC.md files, and determines the order in which they
  should be processed.
  
source_file_design_principles: |
  - Efficient directory traversal with minimal resource usage
  - Bottom-up processing of directory hierarchy
  - Clean separation from file processing logic
  - Respect for .gitignore patterns
  
source_file_constraints: |
  - Must handle large directory trees efficiently
  - Must determine correct processing order (leaves to root)
  - Must properly identify update markers and missing HSTC files
  
dependencies:
  - kind: codebase
    dependency: coding_assistant/scripts/identify_hstc_updates.py
  - kind: codebase
    dependency: src/dbp/hstc/exceptions.py
  - kind: system
    dependency: pathlib
  - kind: system
    dependency: typing
  - kind: system
    dependency: logging
  - kind: system
    dependency: os
  - kind: system
    dependency: re
  
change_history:
  - timestamp: "2025-05-07T12:03:00Z"
    summary: "Implemented full HSTCScanner functionality"
    details: "Replaced placeholder with full scanner implementation, added directory traversal and update detection logic, implemented update order determination algorithm"
  - timestamp: "2025-05-07T11:49:00Z"
    summary: "Initial placeholder implementation of HSTCScanner"
    details: "Created placeholder class with interface methods and NotImplementedError responses"
```

### `source_processor.py`
```yaml
source_file_intent: |
  Implements the SourceCodeProcessor class that processes source code files to update
  their documentation according to project standards. Uses LLM capabilities to analyze
  existing code and enhance documentation while preserving functionality.
  
source_file_design_principles: |
  - Specialized handling based on file type (.py, .js, etc.)
  - LLM integration for documentation generation using Claude models
  - Non-destructive updates that preserve code functionality
  - Structured response parsing with robust error handling
  
source_file_constraints: |
  - Must handle various source file formats and encodings
  - Must properly detect what files can be processed
  - Must provide detailed feedback on changes made
  
dependencies:
  - kind: codebase
    dependency: src/dbp/hstc/exceptions.py
  - kind: codebase
    dependency: src/dbp/core/file_access.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/client_factory.py
  - kind: system
    dependency: pathlib
  - kind: system
    dependency: typing
  - kind: system
    dependency: logging
  - kind: system
    dependency: os
  - kind: system
    dependency: json
  - kind: system
    dependency: re
  
change_history:
  - timestamp: "2025-05-07T12:05:40Z"
    summary: "Implemented full SourceCodeProcessor functionality"
    details: "Added LLM client integration with Claude model, implemented source file processing with documentation updates, added prompt template loading and response parsing logic"
  - timestamp: "2025-05-07T11:50:00Z"
    summary: "Initial placeholder implementation of SourceCodeProcessor"
    details: "Created placeholder class with interface methods and NotImplementedError responses"
```

### `hstc_processor.py`
```yaml
source_file_intent: |
  Implements the HSTCFileProcessor class that generates and updates HSTC.md files
  based on directory contents. Processes source file metadata and child directory
  information to create hierarchical semantic tree context documentation.
  
source_file_design_principles: |
  - Hierarchical tree analysis with bottom-up processing
  - LLM integration for HSTC generation using Nova models
  - Structured JSON processing for reliable parsing
  - Child directory integration in parent HSTC files
  
source_file_constraints: |
  - Must maintain hierarchical consistency in HSTC files
  - Must handle large directory structures efficiently
  - Must extract metadata from various file types
  
dependencies:
  - kind: codebase
    dependency: src/dbp/hstc/exceptions.py
  - kind: codebase
    dependency: src/dbp/core/file_access.py
  - kind: codebase
    dependency: src/dbp/llm/bedrock/client_factory.py
  - kind: system
    dependency: pathlib
  - kind: system
    dependency: typing
  - kind: system
    dependency: logging
  - kind: system
    dependency: os
  - kind: system
    dependency: json
  - kind: system
    dependency: re
  
change_history:
  - timestamp: "2025-05-07T12:12:50Z"
    summary: "Implemented full HSTCFileProcessor functionality"
    details: "Added file header extraction and child directory processing, implemented LLM integration for HSTC generation, added HSTC file creation and updating logic"
  - timestamp: "2025-05-07T11:50:30Z"
    summary: "Initial placeholder implementation of HSTCFileProcessor"
    details: "Created placeholder class with interface methods and NotImplementedError responses"
```

<!-- End of HSTC.md file -->
