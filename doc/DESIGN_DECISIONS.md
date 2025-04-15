# Design Decisions

This document serves as a temporary log of project-wide design decisions that have not yet been incorporated into the appropriate documentation files. Decisions are recorded with newest entries at the top and should be periodically synced to appropriate documentation files (DESIGN.md, SECURITY.md, DATA_MODEL.md, CONFIGURATION.md).

## Default Network Binding

- **Decision**: By default, the product binds on address 127.0.0.1 for security reasons
- **Rationale**: Restricting network binding to localhost prevents external network access, protecting the service from unauthorized access and potential network-based attacks
- **Alternatives considered**: Binding to 0.0.0.0 (all interfaces) with authentication, which was rejected as it would create an unnecessary security risk for development and testing environments
- **Implications**: Enhanced security by default, requires explicit configuration for remote access scenarios, improves default security posture in development environments
- **Relationship to Other Components**: Impacts MCP server configuration and CLI connectivity options
- **Date**: 2025-04-15

## LLM-Based Metadata Extraction

- **Decision**: Metadata extraction from GenAI headers and file headers MUST be performed exclusively by LLM with no programmatic fallback
- **Rationale**: Leverages LLM's natural language understanding capabilities to interpret documentation semantics rather than relying on rigid parsing logic
- **Alternatives considered**: Hybrid approach with programmatic parsing fallback, which was rejected to maintain consistent extraction quality
- **Implications**: Complete dependency on LLM availability for metadata extraction, potential for higher token usage, improved adaptability to varied documentation formats
- **Date**: 2025-04-15

## External Prompt Template Files

- **Decision**: LLM prompts for internal tools are not hardcoded in the server but read directly from doc/llm/prompts/ with no fallback mechanism
- **Rationale**: Separates prompt content from code to enable prompt engineering without code changes and maintains prompt version control within documentation
- **Alternatives considered**: Hardcoded prompts with file-based overrides, which was rejected to enforce documentation-based approach
- **Implications**: Server will fail if prompt files are missing, ensuring documentation integrity; requires prompt files to be properly maintained
- **Date**: 2025-04-15

## Centralized Exception Handling

- **Decision**: All MCP server exceptions are defined in a single centralized exceptions.py module to prevent circular imports
- **Rationale**: Ensures consistent error handling across all MCP server modules and eliminates the risk of circular import dependencies
- **Alternatives considered**: Module-specific exceptions, base exception classes with module-specific subclasses
- **Implications**: Simplified import structure, consistent exception hierarchy, easier maintenance, better error handling in ErrorHandler
- **Date**: 2025-04-15

## LLM-Based Language Detection

- **Decision**: No programmatic language detection is needed as the Metadata extraction LLM tool will perform language detection itself
- **Rationale**: Eliminates need for maintenance of language detection rules and leverages LLM's inherent ability to identify programming languages
- **Alternatives considered**: Using language-specific file extension mapping or specialized language detection libraries, rejected to reduce dependencies
- **Implications**: Unified approach to both language detection and metadata extraction, reduced system complexity, dependency on LLM quality for language identification
- **Date**: 2025-04-15

There are also previously recorded decisions that have been successfully incorporated into the appropriate documentation files:

- Simplified Recommendation System → DESIGN.md, DATA_MODEL.md
- Database Architecture → DATA_MODEL.md
- Configuration Strategy → CONFIGURATION.md
- Recommendation Lifecycle Management → DATA_MODEL.md 
- Code Structure Governance → DESIGN.md
- LLM Processing Approach → DESIGN.md
- Prompt Template Management → design/INTERNAL_LLM_TOOLS.md
- Enhanced Metadata Extraction → DATA_MODEL.md
- MCP Client Security → SECURITY.md
- Implementation Principles → DESIGN.md

The last integration was completed on 2025-04-14T20:57:00Z.
