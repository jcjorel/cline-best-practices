# DESIGN.md Restructuring Plan Overview

## Documentation Files Read
⚠️ CRITICAL: CODING ASSISTANT MUST READ THESE DOCUMENTATION FILES COMPLETELY BEFORE EXECUTING ANY TASKS IN THIS PLAN

| File | Location | Relevance |
|------|----------|-----------|
| GENAI_HEADER_TEMPLATE.txt | [coding_assistant/GENAI_HEADER_TEMPLATE.txt](../../coding_assistant/GENAI_HEADER_TEMPLATE.txt) | Template for file headers |
| GENAI_FUNCTION_TEMPLATE.txt | [coding_assistant/GENAI_FUNCTION_TEMPLATE.txt](../../coding_assistant/GENAI_FUNCTION_TEMPLATE.txt) | Template for function documentation |
| DESIGN.md | [doc/DESIGN.md](../../doc/DESIGN.md) | Current design documentation that needs restructuring |
| DESIGN_DECISIONS.md | [doc/DESIGN_DECISIONS.md](../../doc/DESIGN_DECISIONS.md) | Recent design decisions not yet incorporated |
| DATA_MODEL.md | [doc/DATA_MODEL.md](../../doc/DATA_MODEL.md) | Database structures and data models |
| API.md | [doc/API.md](../../doc/API.md) | External API documentation |
| DOCUMENT_RELATIONSHIPS.md | [doc/DOCUMENT_RELATIONSHIPS.md](../../doc/DOCUMENT_RELATIONSHIPS.md) | Documentation dependencies |

## Problem Statement

The current DESIGN.md file does not conform to the required chapter structure specified in the system prompt. According to the system prompt, DESIGN.md (and any child documents) must be divided into these specific chapters:

1. **General Architecture Overview**: High-level system architecture with mermaid diagrams
2. **Provided Services**: Description of interfaces that deliver project value (UX design, APIs, interfaces)
3. **Business Logic**: Description of internal logic delivering business value (core rules and processes)
4. **External Dependencies toward Cooperating Systems**: API calls toward other business systems
5. **Middleware and Support Functions**: Technical internal infrastructure (schedulers, database management, logging, security)

The current structure lacks this clear organization, making it harder for developers and AI tools to navigate and understand the system architecture.

## Implementation Strategy

This plan outlines a comprehensive approach to restructuring DESIGN.md to align with the required chapter structure while preserving all existing content and maintaining cross-document references.

### Implementation Phases

The restructuring will be executed in sequential logical phases:

1. **Analysis Phase**: Analyze the current DESIGN.md content and map it to the new chapter structure
2. **Content Restructuring**: Create a new version of DESIGN.md with the required chapter structure, reorganizing existing content
3. **Cross-Reference Validation**: Ensure all cross-references from other documents to DESIGN.md remain valid
4. **HSTC Update**: Update the HSTC entries to reflect the new structure of DESIGN.md

### Implementation Plan Files

| File | Purpose |
|------|---------|
| [plan_overview.md](./plan_overview.md) | This file - overall plan and strategy |
| [plan_progress.md](./plan_progress.md) | Tracks progress of plan creation and implementation |
| [plan_content_analysis.md](./plan_content_analysis.md) | Analysis of current content and mapping to new structure |
| [plan_restructured_design.md](./plan_restructured_design.md) | Detailed plan for the new DESIGN.md structure |
| [plan_cross_references.md](./plan_cross_references.md) | Plan for maintaining cross-document references |
| [plan_hstc_update.md](./plan_hstc_update.md) | Plan for updating HSTC entries |

## Essential Source Documentation Excerpts

### System Prompt Design Documentation Requirements

From the system prompt:

```
### Design Documentation Structure
DESIGN.md (and any child documents) must be divided into these specific chapters covering the stack layers of the project:

1. **General Architecture Overview**: High-level system architecture with mermaid diagrams
2. **Provided Services**: Description of any kind of interfaces of the project that deliver the project value (examples: UX design, APIs, or any input/output interfaces)
3. **Business Logic**: Description of internal logic delivering the business value of the project (examples: core business rules and processes)
4. **External Dependencies toward Cooperating Systems**: API calls toward other business systems
5. **Middleware and Support Functions**: Description of technical internal infrastructure that do not deliver directly the business value of the system (examples: custom task schedulers, application database management, logging, security)
```

### Current DESIGN.md Structure

Current DESIGN.md uses this organization:
- Code Analysis Approach
- Core Architecture Principles
- Implementation Principles
- System Components (with subsections for various components)
- Component Initialization System
- File Structure
- Recommendation Workflow
- Security and Data Handling
- Out of Scope
- MCP Server Implementation
- Relationship to Other Components

### HSTC Requirements

From the system prompt:

```
### HSTC.md Structure
- **Child Directory Summaries**: Plain text summaries of all <child_dir>/HSTC.md files
- **Local File Headers**: For each file in directory:
  * `Filename 'example.py':`
  * File header sections
  * Change log history

### HSTC.md Lifecycle Management
1. After modifying any file header, log only the filename in `<same_dir>/HSTC_REQUIRES_UPDATE.md`
2. When user requests "Update HSTC":
   - Locate all HSTC_REQUIRES_UPDATE.md files or directories without a HSTC.md file
   - Update affected HSTC.md entries with new file header information **or** perform full files scan if HSTC.md does not exist
   - **Ensure that all local files are listed in a HSTC.md**, update missing entries if any
   - Delete the HSTC_REQUIRES_UPDATE.md file
   - Recursively update parent HSTC.md files up to project root
