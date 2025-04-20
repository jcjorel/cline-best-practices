# Hierarchical Semantic Tree Context - DBP Root Module (Updated: 2025-04-20T22:32:43+02:00)

This directory is the root of the Document-Based Programming (DBP) system, containing all the major components and subsystems that make up the framework.

## Child Directory Summaries

### core/
Contains core system components that provide foundational functionality for the Document-Based Programming (DBP) system. This includes the Component base class, component lifecycle management, system registry, filesystem utilities, and logging tools.

### config/
Contains the configuration management components for the Document-Based Programming (DBP) system. It provides a layered configuration system with multiple sources (defaults, files, environment variables, CLI arguments) and validation using Pydantic schemas.

### consistency_analysis/
Contains the consistency analysis components for the Document-Based Programming (DBP) system. It provides a framework for detecting inconsistencies between code, documentation, and configuration artifacts.

### database/
Contains the database management components for the Document-Based Programming (DBP) system. It provides database connection management, session handling, schema migrations, and a layer of abstraction for SQLite and PostgreSQL database backends.

### doc_relationships/
Contains the document relationships components for the Document-Based Programming (DBP) system. It provides capabilities for analyzing, tracking, and visualizing relationships between documentation files to support consistency and impact analysis.

### fs_monitor/
Contains the file system monitoring components for the Document-Based Programming (DBP) system. It provides cross-platform file system change detection with platform-specific optimizations and a fallback polling mechanism.

### internal_tools/
Contains components for the LLM-powered internal tools system of the Document-Based Programming (DBP) framework. It provides context assemblage, execution, and response handling for specialized LLM tools used by the LLM Coordinator.

### mcp_server/
Contains the Model Context Protocol (MCP) server implementation for the Document-Based Programming (DBP) system, which provides API access to DBP functionalities.

### dbp_cli/
Contains the command-line interface application for the Document-Based Programming (DBP) system. It provides various commands for interacting with the system including query, commit, config, server management, and status checking operations. The CLI is built with a modular architecture based on command handlers that extend a common BaseCommandHandler class.

### llm/
Contains the Large Language Model integration components for the DBP system. It provides common interfaces and client implementations for interacting with different LLM providers (Amazon Bedrock, Claude, etc.).

### llm_coordinator/
Contains the LLM Coordinator components that manage job processing, dispatching, and orchestration for language model interactions across the system. It acts as an intermediary between system components and LLM services.

### memory_cache/
Contains the memory cache system for efficient data storage and retrieval during processing. It provides indexing, querying, and synchronization capabilities for context data used by LLM components.

### metadata_extraction/
Contains components for analyzing code and documentation to extract structured metadata used for consistency analysis and relationship tracking. It leverages LLMs for semantic understanding of file contents.

### recommendation_generator/
Contains components for generating intelligent recommendations based on system analysis. It produces actionable suggestions for improving documentation and code consistency.

### scheduler/
Contains task scheduling and background processing components used for asynchronous operations throughout the system. It manages worker pools, job queues, and execution tracking.
