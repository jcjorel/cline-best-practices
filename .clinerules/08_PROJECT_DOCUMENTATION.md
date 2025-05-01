# Project Documentation System

## Core Documentation Files
- **GENAI_HEADER_TEMPLATE.txt**: Header template for all source files
- **GENAI_FUNCTION_TEMPLATE.txt**: Function and Class method documentation templates organized by programming language
- **DESIGN.md**: Architectural blueprint including security considerations
- **DESIGN_DECISIONS.md**: Temporary log of project-wide design decisions with newest entries at the top
- **SECURITY.md**: Comprehensive security documentation and requirements
- **CONFIGURATION.md**: Configuration parameters documentation (single source of truth for all default configuration values)
- **DATA_MODEL.md**: Database schema and data structure definitions
- **API.md**: API-related topics and interface specifications
- **DOCUMENT_RELATIONSHIPS.md**: Documentation dependencies with a Mermaid diagram titled "Relationship Graph"
- **PR-FAQ.md**: Business intent documentation using Amazon's methodology
- **WORKING_BACKWARDS.md**: Product vision documentation in Amazon's format
- **CODING_GUIDELINES.md**: Programming approaches and constraints specific to the project (e.g., variable naming conventions, problem-solving patterns, coding standards)

Note: All core documentation files MUST exist in the project, even if they contain only placeholder content.

For large documents exceeding 600 lines, create child documents with clear navigation links and cross-references.

## Design Documentation Structure
DESIGN.md (and any child documents) must be divided into these specific chapters covering the stack layers of the project:

1. **General Architecture Overview**: High-level system architecture with mermaid diagrams
2. **Provided Services**: Description of any kind of interfaces of the project that deliver the project value (examples: UX design, APIs, or any input/output interfaces)
3. **Business Logic**: Description of internal logic delivering the business value of the project (examples: core business rules and processes)
4. **External Dependencies toward Cooperating Systems**: API calls toward other business systems
5. **Middleware and Support Functions**: Description of technical internal infrastructure that do not deliver directly the business value of the system (examples: custom task schedulers, application database management, logging, security)

## Ephemeral Working Documents
All files in the scratchpad directory are temporary working documents and are NOT considered authoritative sources:
- **plan_overview.md**: High-level implementation plan overview
- **plan_progress.md**: Implementation and planning progress tracking document
- **plan_{subtask_name}.md**: Detailed implementation plans for specific subtasks
- **doc_update.md**: Proposed documentation updates awaiting integration

## Permanent Documentation
- **MARKDOWN_CHANGELOG.md**: Tracks all documentation changes organized by directory
- **DESIGN_DECISIONS.md**: Records module-specific architectural decisions

When accessing any documentation:
1. Always treat official documentation files as the definitive source of truth
2. Verify that documentation content follows the expected structure and format
3. Report any structural deviations from the expected format to the user
4. When conflicts exist between documents, prioritize newer documentation over older versions
5. Never consider scratchpad files as authoritative sources under any circumstances

In any circumstances,
**NEVER NEVER NEVER read files in <project_root>/coding_assistant/captured_chats/ as they are always out of context files**
