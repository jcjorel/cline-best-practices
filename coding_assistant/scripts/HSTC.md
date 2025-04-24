# Hierarchical Semantic Tree Context: scripts

## Directory Purpose
This directory contains utility scripts for the Documentation-Based Programming system, specifically focused on maintaining and managing the Hierarchical Semantic Tree Context (HSTC) infrastructure. The scripts provide tools for identifying directories that require HSTC updates, retrieving design mode context, and ensuring the documentation system remains consistent and up-to-date. These utilities are designed to be run either manually by developers or automatically as part of system processes, supporting the documentation-first approach of the DBP system.

## Child Directories
<!-- No child directories with HSTC.md -->

## Local Files

### `get_design_mode_context.py`
```yaml
source_file_intent: |
  Retrieves and formats design mode context documents to provide necessary
  documentation context for GenAI assistants during DESIGN mode operation.
  
source_file_design_principles: |
  - MIME-type message formatting for GenAI compatibility
  - Hierarchical document retrieval based on importance
  - Paginated output for context window management
  
source_file_constraints: |
  - Must respect document hierarchy and relationships
  - Should handle different tiers of documents
  - Must paginate large documents appropriately
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  - kind: codebase
    dependency: doc/DOCUMENT_RELATIONSHIPS.md
  
change_history:
  - timestamp: "2025-04-10T16:30:00Z"
    summary: "Created design mode context retrieval script"
    details: "Implemented document loading and pagination for design mode context"
```

### `identify_hstc_updates.py`
```yaml
source_file_intent: |
  Identifies directories that require HSTC.md file updates or creation based on project requirements.
  This script helps maintain the Hierarchical Semantic Tree Context by finding directories that:
  1. Contain HSTC_REQUIRES_UPDATE.md files (indicating pending updates)
  2. Do not contain HSTC.md files (indicating missing HSTC documentation)
  The script respects .gitignore patterns to avoid processing ignored files and directories.
  
source_file_design_principles: |
  - Single responsibility: Focus solely on identifying directories needing HSTC updates
  - Non-destructive: Read-only operations, no modifications to filesystem
  - Respect project configuration: Honor .gitignore patterns
  - Prioritize by complexity: Sort results by path length to handle more complex directories first
  
source_file_constraints: |
  - Must work on Unix-like and Windows systems
  - Should handle large directory structures efficiently
  - Must parse and respect all .gitignore files in the directory tree
  
dependencies:
  - kind: codebase
    dependency: doc/DESIGN.md
  
change_history:
  - timestamp: "2025-04-08T14:20:00Z"
    summary: "Created HSTC updates identification script"
    details: "Implemented directory scanning with gitignore support and hierarchical ordering"
```

<!-- End of HSTC.md file -->
