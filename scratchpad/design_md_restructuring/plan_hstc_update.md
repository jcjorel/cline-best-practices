# HSTC Update Plan for DESIGN.md Restructuring

This document outlines the plan for updating the Hierarchical Semantic Tree Context (HSTC) files following the restructuring of DESIGN.md.

## HSTC Files Affected

After restructuring DESIGN.md, the following HSTC files will need to be updated:

1. **doc/HSTC.md**: Contains the entry for DESIGN.md
2. **HSTC.md** (project root): Contains summary of doc/ directory including DESIGN.md

## HSTC Update Process

According to the system prompt, the HSTC update process follows these steps:

1. After modifying a file header, create HSTC_REQUIRES_UPDATE.md in the same directory with the modified filename
2. When updating HSTC:
   - Update affected HSTC.md entries with new file header information
   - Ensure all local files are listed in an HSTC.md file
   - Delete the HSTC_REQUIRES_UPDATE.md file
   - Recursively update parent HSTC.md files up to project root

## Current HSTC Entry for DESIGN.md

The current entry in doc/HSTC.md for DESIGN.md is:

```markdown
### Filename 'DESIGN.md':
- Source file intent: Describes the architectural principles, components, and design decisions for the Documentation-Based Programming system
- Design principles:
  * Documentation as Source of Truth
  * Automatic Consistency Maintenance
  * Global Contextual Awareness
  * Design Decision Preservation
  * Reasonable Default Values
  * Simplified Component Management
- Implementation principles:
  * Avoid Manual Parsing
  * Metadata Normalization via LLM
  * Precise LLM Prompts
  * Thread-Safe Database Access
  * Code Size Governance
  * Explicit Error Handling
  * Centralized Exception Handling
  * LLM-Exclusive Metadata Extraction
  * Standardized Logging Format
  * Strict Configuration Access
```

## Updated HSTC Entry for Restructured DESIGN.md

After restructuring, the entry should be updated to reflect the new document organization:

```markdown
### Filename 'DESIGN.md':
- Source file intent: Describes the architectural principles, components, and design decisions for the Documentation-Based Programming system
- Document structure:
  * General Architecture Overview
  * Provided Services
  * Business Logic
  * External Dependencies toward Cooperating Systems
  * Middleware and Support Functions
- Design principles:
  * Documentation as Source of Truth
  * Automatic Consistency Maintenance
  * Global Contextual Awareness
  * Design Decision Preservation
  * Reasonable Default Values
  * Simplified Component Management
- Implementation principles:
  * Avoid Manual Parsing
  * Metadata Normalization via LLM
  * Precise LLM Prompts
  * Thread-Safe Database Access
  * Code Size Governance
  * Explicit Error Handling
  * Centralized Exception Handling
  * LLM-Exclusive Metadata Extraction
  * Standardized Logging Format
  * Strict Configuration Access
```

## Project Root HSTC Update

The entry for the doc/ directory in the project root HSTC.md will also need to be updated to reflect the new structure:

Current entry:
```markdown
### Directory 'doc/':
This directory contains the core documentation files for the Documentation-Based Programming system. It includes architectural design documents, data models, API documentation, security information, and project guidelines. Key files include:
- DESIGN.md: Architectural principles and system components
- DATA_MODEL.md: Data structures and relationships
- API.md: REST API endpoints
- DOCUMENT_RELATIONSHIPS.md: Documentation dependency mapping
- Several other specialized documentation files
```

Updated entry:
```markdown
### Directory 'doc/':
This directory contains the core documentation files for the Documentation-Based Programming system. It includes architectural design documents, data models, API documentation, security information, and project guidelines. Key files include:
- DESIGN.md: Architectural principles with layers (General Architecture, Services, Business Logic, External Dependencies, Middleware)
- DATA_MODEL.md: Data structures and relationships
- API.md: REST API endpoints
- DOCUMENT_RELATIONSHIPS.md: Documentation dependency mapping
- Several other specialized documentation files
```

## Implementation Steps

1. **Create HSTC_REQUIRES_UPDATE.md**: After restructuring DESIGN.md, create a file at doc/HSTC_REQUIRES_UPDATE.md containing:
   ```
   # Files Requiring HSTC Update
   
   The following files in this directory have been modified and require HSTC metadata update:
   
   - DESIGN.md
   ```

2. **Update doc/HSTC.md**: Replace the DESIGN.md entry with the updated version that reflects the new structure

3. **Update HSTC.md in project root**: Update the doc/ directory entry to reflect the restructured DESIGN.md

4. **Delete doc/HSTC_REQUIRES_UPDATE.md**: After completing the updates

## Example Commands

```bash
# 1. Create HSTC_REQUIRES_UPDATE.md
echo "# Files Requiring HSTC Update\n\nThe following files in this directory have been modified and require HSTC metadata update:\n\n- DESIGN.md" > doc/HSTC_REQUIRES_UPDATE.md

# 2. Update doc/HSTC.md
# (Use replace_in_file tool with proper SEARCH/REPLACE blocks)

# 3. Update root HSTC.md
# (Use replace_in_file tool with proper SEARCH/REPLACE blocks)

# 4. Delete HSTC_REQUIRES_UPDATE.md
rm doc/HSTC_REQUIRES_UPDATE.md
```

## Verification Steps

After updating the HSTC files, verify:

1. The DESIGN.md entry in doc/HSTC.md correctly reflects the new document structure
2. The doc/ directory entry in the project root HSTC.md correctly summarizes the updated DESIGN.md
3. The doc/HSTC_REQUIRES_UPDATE.md file has been deleted
4. All other entries in both HSTC files remain intact

This verification ensures the HSTC hierarchy accurately represents the current state of the documentation after restructuring DESIGN.md.
