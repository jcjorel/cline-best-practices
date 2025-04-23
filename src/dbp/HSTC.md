# Hierarchical Semantic Tree Context: dbp

## Directory Purpose
This directory contains the core implementation of the Documentation-Based Programming (DBP) system. DBP is an architecture that leverages documentation as a primary project asset to maintain consistency between code and documentation, provide context for AI tools, and enforce project standards. The system includes components for configuration management, filesystem monitoring, document relationship tracking, consistency analysis, metadata extraction, LLM coordination, and MCP server functionality.

## Child Directories

### internal_tools
This directory contains components related to internal_tools.

### memory_cache
This directory contains components related to memory_cache.

### database
This directory contains the database layer of the DBP system, responsible for data persistence, schema management, and database interactions. It implements a robust ORM architecture using SQLAlchemy, with separate components for database connection handling, model definitions, migration management, and data access repositories. The architecture follows the repository pattern to abstract database operations and provides a comprehensive set of repositories for different entity types, supporting schema evolution through Alembic-managed migrations.

### mcp_server
This directory implements the Model Context Protocol (MCP) server integration for the Documentation-Based Programming (DBP) system. It provides a complete MCP server implementation that enables AI assistants to interact with the DBP system through standardized tools and resources. The MCP server exposes functionality for document relationships analysis, consistency checking, and recommendation generation to AI assistants while maintaining proper authentication and authorization controls. The implementation follows the component architecture of the DBP system and integrates with its lifecycle management.

### recommendation_generator
This directory contains components related to recommendation_generator.

### doc_relationships
This directory implements the documentation relationship management subsystem of the DBP system. It provides components for analyzing, tracking, and visualizing relationships between documentation files and between documentation and code. The system enables impact analysis to understand how changes in one document affect others, builds relationship graphs for visualization, detects changes in document relationships over time, and provides query capabilities for exploring documentation connections. This functionality is critical for maintaining consistency across the documentation ecosystem.

### config
This directory contains components responsible for configuration management in the Documentation-Based Programming (DBP) system. It implements a layered configuration approach with a singleton ConfigurationManager that loads settings from multiple sources (defaults, files, environment variables, CLI args), validates them using Pydantic models, and provides type-safe access. The ConfigManagerComponent acts as an adapter between the ConfigurationManager singleton and the component lifecycle framework, making configuration available to other components via the registry.

### llm
This directory contains components related to llm.

### consistency_analysis
This directory implements the consistency analysis subsystem of the DBP system, responsible for detecting inconsistencies between code and documentation. It provides components for analyzing code-documentation alignment, identifying potential issues, assessing their impact, and generating comprehensive reports. The system uses a repository pattern for storing analysis results and a registry for tracking consistency rules and validation strategies. The impact analyzer enables understanding how documentation changes affect code quality and vice versa.

### core
This directory implements the foundational infrastructure of the Documentation-Based Programming (DBP) system. It provides the component lifecycle framework, dependency injection system, registry for component discovery, file access abstractions, and system-level utilities. These core components form the backbone of the DBP architecture, enabling modular design, proper initialization sequences, and standardized interaction patterns between subsystems. The core framework emphasizes type safety, structured error handling, and clean separation of concerns throughout the system.

### llm_coordinator
This directory contains components related to llm_coordinator.

### scheduler
This directory contains components related to scheduler.

### metadata_extraction
This directory contains components related to metadata_extraction.

### fs_monitor
This directory contains components related to fs_monitor.

## Local Files

<!-- No local files at top level of this directory -->

<!-- End of HSTC.md file -->
