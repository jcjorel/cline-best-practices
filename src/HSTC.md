# Hierarchical Semantic Tree Context: src

## Directory Purpose
This directory contains the source code implementation of the Documentation-Based Programming (DBP) system. The source code is organized into packages and modules that implement the core functionality, integrations, utilities, and command-line interfaces for the DBP system. The primary package is dbp, which contains the core components for configuration management, filesystem monitoring, document relationship tracking, consistency analysis, metadata extraction, LLM coordination, and MCP server functionality.

## Child Directories

### dbp
This directory contains the core implementation of the Documentation-Based Programming (DBP) system. DBP is an architecture that leverages documentation as a primary project asset to maintain consistency between code and documentation, provide context for AI tools, and enforce project standards. The system includes components for configuration management, filesystem monitoring, document relationship tracking, consistency analysis, metadata extraction, LLM coordination, and MCP server functionality. The implementation follows a component-based architecture with standardized lifecycle management, dependency injection, and proper separation of concerns.

### dbp_cli
This directory implements the command-line interface for the Documentation-Based Programming (DBP) system. It provides commands for interacting with various DBP functionalities, including configuration management, consistency analysis, document relationship tracking, and metadata extraction. The CLI follows a modular architecture with pluggable commands and standardized output formatting, supporting both human-readable and machine-parseable outputs.

## Local Files

<!-- No local files at top level of this directory -->

<!-- End of HSTC.md file -->
