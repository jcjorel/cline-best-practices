# Hierarchical Semantic Tree Context: src

## Directory Purpose
The src directory contains the main source code for the Documentation-Based Programming system. It implements a modular, component-based architecture that separates concerns between core infrastructure, database management, document analysis, and external interfaces. The codebase follows Python best practices with clearly defined module boundaries, dependency injection patterns, and explicit component lifecycle management. This directory houses both the backend implementation (dbp) and the command-line interface (dbp_cli) to interact with the system's functionality.

## Child Directories

### dbp
Core implementation of the Documentation-Based Programming system, containing modules for database management, consistency analysis, document relationship tracking, LLM coordination, and other specialized components that together form the complete backend functionality.

### dbp_cli
Command-line interface implementation that provides user-friendly access to the Documentation-Based Programming system's functionality through structured commands, argument parsing, and formatted output. It includes specialized modules for MCP client functionality, command handling, authentication, configuration, and progress reporting. The implementation follows a modular command pattern with consistent interfaces across all commands.

## Local Files
<!-- No files directly in the src directory, all code is organized in subdirectories -->
