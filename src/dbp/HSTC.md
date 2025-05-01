# Hierarchical Semantic Tree Context: dbp

## Directory Purpose
This directory contains the core implementation of the Document-Based Programming (DBP) system, which provides a comprehensive framework for managing, analyzing, and enhancing documentation and code in software projects. The system is built around a modular component architecture that follows strict dependency management principles. It leverages large language models (LLMs) for advanced analysis, maintains consistency between documentation and implementation, and provides a Model Context Protocol (MCP) server for extensible integrations. The system emphasizes type safety, clean separation of concerns, robust error handling, and efficient resource management throughout its design.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Exports core DBP classes and functions for use by external modules.
  
source_file_design_principles: |
  - Minimalist exports to control public API surface
  - Version information
  - Package-level documentation
  
source_file_constraints: |
  - Should maintain backward compatibility for public APIs
  - Must not contain implementation logic
  
dependencies: []
  
change_history:
  - timestamp: "2025-04-01T09:00:00Z"
    summary: "Initial creation of DBP package"
    details: "Created __init__.py with package exports and version information"
```

## Child Directories

### config
This directory implements the configuration management system for the DBP application, providing a robust framework for defining, validating, loading, and accessing strongly-typed configuration parameters throughout the application. The system uses Pydantic models for schema definition and validation, supports multiple configuration sources (files, environment variables, CLI arguments), and provides a central component for configuration management. The separation of schema definition from default values ensures consistent configuration across the application while maintaining a single source of truth for documentation.

### core
This directory implements the fundamental component framework and core system utilities for the DBP application. It defines the Component architecture that serves as the backbone for the entire system, providing essential services for component lifecycle management, dependency injection, system initialization, error handling, and resource management. The core module enforces consistent patterns across all components while maintaining a minimalist approach that follows KISS principles - providing just enough structure to ensure proper system operation without unnecessary complexity.

### database
This directory implements the database subsystem for the DBP application, providing persistent storage capabilities through both SQLite and PostgreSQL database backends. It includes components for database connection management, session handling, schema management, data models, and repository access patterns. The database architecture follows a layered approach with clear separation between connection management (database.py), schema migrations (alembic_manager.py), data models (models.py), and data access repositories (repositories.py). This subsystem implements thread-safe database access with connection pooling, transaction management, retry logic for transient errors, and automated schema migrations using Alembic.

### fs_monitor
This directory implements the file system monitoring subsystem for the DBP application, providing real-time tracking of file system changes across different operating system platforms. It uses a hierarchical architecture that separates platform-specific monitoring implementations from event dispatching and listening interfaces. The system supports multiple concurrent file watchers, thread-safe event dispatching, and pattern-based filtering. It includes a fallback polling mechanism for environments where native file system monitoring APIs are unavailable and implements debouncing to prevent event storms during rapid file changes.

### internal_tools
This directory implements the internal tools subsystem for the DBP application, providing reusable utilities for code and documentation analysis, LLM prompt management, and execution engines that power various DBP features. It offers specialized components for processing code and documentation, extracting semantic context, and managing the execution flow between different analysis steps. The internal tools module serves as a bridge between raw file data and higher-level DBP functionality, providing abstractions that simplify complex processing tasks while maintaining flexibility for various use cases.

### llm
This directory implements the LLM (Large Language Model) services for the DBP application, providing a unified framework for interacting with different Foundation Models through Amazon Bedrock. It offers model-specific clients, a central manager for coordinating client usage, common utilities for handling prompts and responses, and abstraction layers to support multiple model types. The architecture ensures consistent interaction patterns, efficient resource management, and robust error handling while hiding provider-specific implementation details from the rest of the application.

### llm_coordinator
This directory implements the LLM Coordination subsystem for the DBP system, which orchestrates interactions between Large Language Models and internal tools. It serves as a central hub for processing natural language requests, determining required tool operations, executing tool jobs, and formatting responses. The LLMCoordinatorComponent follows the core Component protocol and acts as a facade for the complex coordination logic, exposing a simplified interface while managing internal sub-components for request handling, tool registry, job management, LLM interactions, and response formatting.

### mcp_server
This directory implements the Model Context Protocol (MCP) server component for the DBP system, providing a standardized interface for large language model (LLM) interactions through tools and resources. The MCP server enables LLMs to access external capabilities like data retrieval, file operations, specialized processing, and API integrations. It uses the FastMCP library to ensure protocol compliance while maintaining a clean Component-based architecture. The implementation includes authentication, request validation, error handling, and extensibility through a tool/resource registration system that allows other components to provide domain-specific functionality to LLMs.

### scheduler
This directory implements the background task scheduler subsystem for the DBP application, providing an asynchronous job processing framework for handling non-interactive operations. It enables components to schedule tasks for deferred execution, manages worker threads for parallel processing, and implements priority-based job scheduling. The scheduler provides retry mechanisms for failed tasks, supports cancellation and monitoring of long-running jobs, and ensures graceful system shutdown by handling in-progress tasks appropriately.

End of HSTC.md file
