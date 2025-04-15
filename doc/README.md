# Documentation-Based Programming: Documentation Index

## Overview

This index provides a centralized entry point to all documentation for the Documentation-Based Programming system. This system treats documentation as the single source of truth in a project, ensuring consistency between documentation and code.

## Quick Navigation

### Core Documentation

- [DESIGN.md](DESIGN.md) - Architectural principles, components, and design decisions
- [DATA_MODEL.md](DATA_MODEL.md) - Data structures and relationships
- [SECURITY.md](SECURITY.md) - Security considerations and architecture
- [CONFIGURATION.md](CONFIGURATION.md) - Configuration parameters and default values
- [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md) - Mapping of dependencies between documentation files
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) - Log of project-wide design decisions
- [PR-FAQ.md](PR-FAQ.md) - Product requirements as press release and FAQ
- [WORKING_BACKWARDS.md](WORKING_BACKWARDS.md) - Product vision and customer experience

### Implementation Details

- [design/LLM_COORDINATION.md](design/LLM_COORDINATION.md) - LLM coordination architecture details
- [design/INTERNAL_LLM_TOOLS.md](design/INTERNAL_LLM_TOOLS.md) - Specialized internal tools documentation
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - Enhanced data models for MCP
- [design/COMPONENT_INITIALIZATION.md](design/COMPONENT_INITIALIZATION.md) - Component initialization and lifecycle
- [design/BACKGROUND_TASK_SCHEDULER.md](design/BACKGROUND_TASK_SCHEDULER.md) - Background processing architecture

### LLM Prompts

- [llm/prompts/README.md](llm/prompts/README.md) - Overview of LLM prompt templates
- [llm/prompts/coordinator_get_codebase_context.md](llm/prompts/coordinator_get_codebase_context.md) - Context extraction from codebase
- [llm/prompts/coordinator_get_documentation_context.md](llm/prompts/coordinator_get_documentation_context.md) - Documentation context extraction

## Documentation by Topic

### Architecture

- [DESIGN.md](DESIGN.md) - Overall system architecture and principles
- [design/LLM_COORDINATION.md](design/LLM_COORDINATION.md) - LLM coordination architecture
- [design/COMPONENT_INITIALIZATION.md](design/COMPONENT_INITIALIZATION.md) - Component initialization

### Data Models

- [DATA_MODEL.md](DATA_MODEL.md) - Core data structures and relationships
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - MCP server data models

### Security

- [SECURITY.md](SECURITY.md) - Comprehensive security documentation

### Configuration

- [CONFIGURATION.md](CONFIGURATION.md) - Configuration parameters and default values

### Background Processing

- [design/BACKGROUND_TASK_SCHEDULER.md](design/BACKGROUND_TASK_SCHEDULER.md) - Background task scheduling

### LLM Integration

- [design/INTERNAL_LLM_TOOLS.md](design/INTERNAL_LLM_TOOLS.md) - Internal LLM tools
- [llm/prompts/](llm/prompts/) - LLM prompt templates

### Documentation Management

- [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md) - Documentation relationship mapping
- [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) - Tracking design decisions

## Documentation for Different Users

### For Developers

Start with:
1. [DESIGN.md](DESIGN.md) - Understand the overall architecture
2. [DATA_MODEL.md](DATA_MODEL.md) - Learn about the data structures
3. [CONFIGURATION.md](CONFIGURATION.md) - Configuration options
4. Specific component documentation as needed

### For Architects

Start with:
1. [DESIGN.md](DESIGN.md) - Architectural principles
2. [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) - Design decision history
3. [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md) - Documentation relationships
4. [design/LLM_COORDINATION.md](design/LLM_COORDINATION.md) - LLM architecture

### For Product Managers

Start with:
1. [PR-FAQ.md](PR-FAQ.md) - Product requirements
2. [WORKING_BACKWARDS.md](WORKING_BACKWARDS.md) - Product vision
3. [SECURITY.md](SECURITY.md) - Security considerations

## How to Navigate the Documentation

The documentation follows these principles:

1. **Hierarchy**: Start with high-level documents (DESIGN.md, PR-FAQ.md) before diving into specific implementations
2. **Cross-References**: Documentation files reference each other with links to related concepts
3. **Relationship Graph**: See [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md) for understanding dependencies between documents
4. **Design Decisions**: All significant design choices are documented in [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md) and periodically incorporated into appropriate documentation files

## Update Process

When updating documentation:

1. Check [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md) to identify all related documents
2. Update all affected documentation to maintain consistency
3. Record significant design decisions in [DESIGN_DECISIONS.md](DESIGN_DECISIONS.md)
4. Update the relationship information if new dependencies are created

## Documentation Standards

All documentation follows these standards:

1. **Markdown Format**: All documentation is written in Markdown
2. **Cross-References**: Documents link to related files using relative paths
3. **Section Structure**: Consistent section organization within document types
4. **Naming Convention**: Documentation files use UPPERCASE_SNAKE_CASE naming
5. **Relationship Tracking**: All dependencies between documents are tracked in [DOCUMENT_RELATIONSHIPS.md](DOCUMENT_RELATIONSHIPS.md)
