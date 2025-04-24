# Hierarchical Semantic Tree Context: scratchpad

## Directory Purpose
The scratchpad directory serves as a working area for temporary planning documents, implementation plans, and other ephemeral content that supports the development process but is not part of the core codebase or official documentation. This directory contains documents that help developers plan implementation details, document architectural decisions before they are formalized, and track progress on specific tasks. Unlike the core documentation in doc/, the contents of this directory are not considered authoritative sources and may contain work-in-progress information that has not been fully validated or approved.

## Child Directories

### onboarding_kit
Contains documentation and resources specifically designed to help new developers and contributors understand and navigate the project, including overviews, architecture diagrams, workflows, and development guides.

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
