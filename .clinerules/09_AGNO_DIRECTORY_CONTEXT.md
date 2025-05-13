# Agno Directory Context & Usage Guidelines

## Directory Purpose
The agno/ directory serves as a reference implementation and documentation source for the Agno framework. It contains the source code, examples, and documentation for Agno, but is not meant for direct imports in the project codebase. This directory provides an accessible way to inspect Agno's implementation details, browse examples, and understand architectural patterns when developing Agno-related features, while maintaining proper dependency management through pip installation.

## Critical Context for Coding Assistant

### IMPORTANT: Import Policy
- **DO NOT** import directly from the agno/ directory in project code
- **ALWAYS** use the pip-installed Agno package for all imports:
  ```python
  # CORRECT:
  from agno.core import Agent
  
  # INCORRECT - NEVER DO THIS:
  from project_root/agno/libs/agno/core import Agent
  ```
- The agno/ directory exists purely as a reference resource for understanding implementation details

### Directory Structure Overview
- **cookbook/** - Contains reference implementations, examples, and tutorials organized by concept
  - **agent_concepts/** - Core agent implementation patterns
  - **agents_from_scratch/** - Building blocks for creating custom agents
  - **examples/** - Practical implementation examples
  - **getting_started/** - Entry-level examples and documentation
  - **models/** - Model integration examples
  - **tools/** - Tool implementation references
  - **workflows/** - Workflow orchestration patterns
  
- **evals/** - Evaluation frameworks and test suites
  - **accuracy/** - Accuracy measurement implementations
  - **performance/** - Performance benchmarking tools
  - **reliability/** - Reliability testing frameworks
  
- **libs/** - Core library implementation
  - **agno/** - Main Agno framework code
  - **infra/** - Infrastructure and support code
  
- **scripts/** - Utility scripts for development, testing, and setup

### Key Design Principles
1. **Agent-Centric Architecture**: Agno is designed around the concept of autonomous agents with well-defined boundaries and responsibilities
2. **Composability**: Components are designed to be combined and orchestrated in various ways
3. **Modularity**: Clear separation of concerns between different functional areas
4. **Extensibility**: Framework is built to be extended with custom tools, models, and workflows
5. **Observability**: Built-in support for tracking, logging, and debugging agent operations

### Quick Reference Guide to Critical Files

When implementing Agno-related features, these are the key locations to examine for reference:

#### Core Agent Implementation
- `agno/libs/agno/agent/` - Core agent implementation patterns
- `agno/libs/agno/tools/` - Standard tool implementations
- `agno/libs/agno/memory/` - Memory and state management

#### Model Integration
- `agno/libs/agno/models/` - Model abstractions and integrations
- `agno/cookbook/models/` - Example model implementations and usage patterns

#### Workflow Patterns
- `agno/libs/agno/workflows/` - Workflow orchestration framework
- `agno/cookbook/workflows/` - Example workflow implementations

#### Best Practices
- `agno/cookbook/getting_started/` - Starting templates and patterns
- `agno/cookbook/examples/` - Full implementation examples

### When to Use the Agno Directory
- **DO USE** when:
  - Researching how specific Agno features are implemented
  - Understanding the detailed behavior of Agno components
  - Looking for implementation examples and patterns
  - Debugging issues that may be related to Agno internals
  
- **DO NOT USE** when:
  - Importing functionality for production code (use pip-installed package)
  - Modifying Agno core functionality (contribute to Agno directly instead)

## Relationship to Project Architecture
The project leverages Agno as a dependency while implementing project-specific agents and workflows. The HSTC Agno commands in src/dbp_cli/commands/hstc_agno/ represent project-specific implementations that use the Agno framework installed via pip, not the reference code in the agno/ directory.

## Documentation Resources
- `agno/README.md` - Overview documentation for Agno
- `agno/cookbook/README.md` - Guide to example implementations
- `agno/CONTRIBUTING.md` - Contribution guidelines

## Version Compatibility
Always ensure that the reference implementation in agno/ directory is compatible with the pip-installed version being used in the project. Inconsistencies between versions can lead to confusion when using the reference code as guidance.
