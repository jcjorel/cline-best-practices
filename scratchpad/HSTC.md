# Hierarchical Semantic Tree Context: scratchpad

## Directory Purpose
The scratchpad directory serves as a working area for temporary planning documents, implementation plans, and other ephemeral content that supports the development process but is not part of the core codebase or official documentation. This directory contains documents that help developers plan implementation details, document architectural decisions before they are formalized, and track progress on specific tasks. Unlike the core documentation in doc/, the contents of this directory are not considered authoritative sources and may contain work-in-progress information that has not been fully validated or approved.

## Child Directories

### fastmcp_integration
This directory contains a sample implementation for replacing the homemade MCP server implementation with the fastmcp library. The goal is to achieve optimal integration with fastmcp while preserving existing FastAPI usage and health route functionality. The implementation follows key principles including complete replacement of homemade MCP code, preservation of FastAPI integration, maintenance of the component architecture, and no backward compatibility requirements.

### onboarding_kit
Contains documentation and resources specifically designed to help new developers and contributors understand and navigate the project, including overviews, architecture diagrams, workflows, and development guides.

### mcp_capability_negotiation
This directory contains implementation planning documents for the MCP (Model Context Protocol) capability negotiation feature. It's a scratchpad area holding architectural plans, design documents, and implementation strategies focused on enhancing the MCP protocol with standardized capability discovery and negotiation mechanisms. These documents outline how clients and servers can dynamically discover each other's supported features, negotiate compatible protocol versions, and gracefully handle feature mismatches. The content serves as planning material rather than production code, providing a roadmap for implementing the capability negotiation protocol.

### mcp_server_minimized
This directory contains implementation plans and modified code for a minimized version of the Model Context Protocol (MCP) server. It serves as a scratchpad for designing a lightweight alternative to the full MCP server implementation with reduced dependencies and simplified architecture. The minimized implementation focuses on core functionality while removing advanced features that aren't essential for basic operation. This approach aims to provide faster startup times, reduced resource consumption, and easier deployment for scenarios where the full MCP server capabilities aren't required.

## Local Files

### `README.md`
```yaml
source_file_intent: |
  Provides an overview of the scratchpad directory's purpose, organization, and usage guidelines.
  
source_file_design_principles: |
  - Clear explanation of scratchpad's role in development workflow
  - Guidelines for creating and organizing scratchpad content
  - Distinction between authoritative documentation and scratchpad content
  
source_file_constraints: |
  - Must emphasize the non-authoritative nature of scratchpad content
  - Must provide clear usage instructions
  
dependencies:
  - kind: codebase
    dependency: doc/CODING_GUIDELINES.md
  
change_history:
  - timestamp: "2025-04-24T23:31:00Z"
    summary: "Created HSTC.md file"
    details: "Initial documentation of README.md in HSTC.md"
