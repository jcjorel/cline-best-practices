# Documentation-Based Programming System Architecture

This document describes the architectural principles, components, and design decisions for the Documentation-Based Programming system, which treats documentation as the single source of truth in a project.

## Code Analysis Approach

1. **Claude 3.7 Sonnet-Based Analysis**: The system uses Claude 3.7 Sonnet LLM to analyze codebase files and extract metadata.
2. **Metadata Extraction Capabilities**:
   - Extract header sections from source files
   - Retrieve function lists with associated documentation sections
   - Determine file coding language
3. **Analysis Method**: Claude's natural language understanding is used to perform semantic analysis of code structures without relying on keyword-based parsing.
4. **Parsing Prohibition**: Keyword-based parsing will never be used in any part of the application.

## Core Architecture Principles

1. **Documentation as Source of Truth**: Documentation takes precedence over code itself for understanding project intent.
2. **Automatic Consistency Maintenance**: System actively ensures consistency between documentation and code.
3. **Global Contextual Awareness**: AI assistants maintain awareness of entire project context.
4. **Design Decision Preservation**: All significant design decisions are captured and maintained.
5. **Zero Configuration Operation**: System functions without requiring manual setup or maintenance.

## System Components

### 1. Python CLI Client

- **Component Purpose**: Provide a simple command-line interface for interacting with MCP servers
- **Implementation Strategy**: Lightweight Python CLI tool with minimal dependencies
- **Key Features**:
  - Connect to running MCP servers (default port 6231)
  - Issue requests to MCP servers with formatted parameters
  - Display formatted responses from MCP servers
  - Support for interactive and batch modes
  - Configuration through Cline software settings
- **Performance Constraints**: <50MB memory footprint, <100ms response time for local operations
- **Design Decision (2025-04-14)**: Command-based interface pattern for extensibility
  - **Rationale**: Enables easy addition of new commands without modifying core client logic, supports both interactive and script-based usage, provides consistent user experience across different operations
  - **Key Implications**: Command handlers can be developed independently, help documentation is auto-generated from command metadata, users benefit from consistent parameter handling

### 2. Documentation Monitoring

- **Component Purpose**: Detect changes in documentation and code files
- **Implementation Strategy**: Lightweight file system watcher with debounced updates, backed by a persistent SQLite database for metadata storage
- **Performance Constraints**: <5% CPU and <100MB RAM usage
- **Response Time**: Changes detected and processing initiated after 10-second delay (configurable)
- **Background Processing**:
  - Uses Anthropic Claude 3.7 Sonnet to extract metadata from each codebase file
  - Performs extraction only for files missing from SQLite database or with outdated records
  - Initial scan processes all files to populate metadata database
  - After initial scan, transitions to event-based monitoring using inotify() or equivalent
  - Reacts to file change events by re-extracting metadata for modified files
  - Progress information returned as part of MCP server tool responses
- **Dynamic File Exclusion Strategy**:
  - System automatically scans for and respects all .gitignore files throughout the codebase
  - Additionally excludes two mandatory patterns regardless of .gitignore contents:
    - `<project_root>/scratchpad/` directory and its contents
    - Any file or directory with "deprecated" in the path
  - When .gitignore files are modified:
    - Database is purged of existing metadata records that fall under newly added exclusions
    - Files in paths that are no longer excluded (removed from .gitignore) are automatically indexed
  - This approach ensures the indexing scope always remains in sync with Git-committable content
  - Rationale: Leverages developer-defined exclusions while maintaining database consistency
- **Design Decision (2025-04-13)**: Implement a persistent SQLite database for metadata storage
  - **Rationale**: Provides persistence across application restarts, reduces repeated metadata extraction, improves performance with incremental updates
  - **Key Implications**: Faster startup times after initial indexing, reduced CPU usage for large codebases, requires database schema migration strategy

### 2. Consistency Analysis Engine

- **Component Purpose**: Analyze relationships between documentation and code
- **Implementation Strategy**: In-memory graph representation of document relationships
- **Analysis Types**:
  - Documentation-to-documentation consistency
  - Documentation-to-code alignment
  - Code-to-documentation impact analysis
- **Processing Strategy**: Background incremental processing with priority queuing
- **Design Decision (2025-04-13)**: Process only one codebase file at a time during background tasks
  - **Rationale**: Ensures consistent and predictable system resource usage, prevents resource spikes, simplifies debugging and error isolation, and allows for cleaner implementation of the processing queue
  - **Key Implications**: Processing large codebases will take longer, effective prioritization is required, and progress indicators should clearly show queue position

### 3. Recommendation Generator

- **Component Purpose**: Create actionable recommendations to maintain documentation consistency
- **Implementation Strategy**: Template-based recommendation generation with contextual awareness
- **Recommendation Types**:
  - Documentation updates based on code changes
  - Code refactoring to align with documentation
  - Inconsistency resolution between documentation files
- **File Management**: FIFO queue of individual recommendation files
- **Design Decision**: Implement a First-In-First-Out queue for recommendation processing
  - **Rationale**: Ensures older recommendations are addressed before newer ones, preventing recommendation buildup and ensuring that fundamental issues are resolved before addressing their downstream effects
  - **Key Implications**: Developers must process recommendations in the order presented, but can use AMEND to adjust inappropriate recommendations

### 4. Developer Feedback System

- **Component Purpose**: Capture and process developer decisions on recommendations
- **Implementation Strategy**: File-based feedback mechanism with ACCEPT/REJECT/AMEND options
- **Processing Logic**: Immediate response to feedback file changes
- **Amendment Handling**: Regeneration of recommendations based on developer guidance
- **Design Decision**: Use file modifications as the primary feedback mechanism
  - **Rationale**: File-based approach integrates seamlessly with existing developer workflows and version control systems without requiring additional UI components
  - **Key Implications**: All recommendation interactions visible in version control history, creating an audit trail of documentation decisions

## File Structure

```
<project_root>/
├── coding_assistant/
│   ├── GENAI_HEADER_TEMPLATE.txt      # Template for file headers
│   └── dbp/                           # Documentation-Based Programming artifacts
│       ├── recommendations/           # Directory for recommendation files
│       │   ├── YYMMDD-HHmmSS-RECOMMENDATION_NAME.md  # Individual recommendations
│       │   └── ...
│       └── PENDING_RECOMMENDATION.md  # Oldest recommendation awaiting review
└── doc/
    ├── DESIGN.md                     # This file - architectural principles
    ├── DATA_MODEL.md                 # Database structures and relationships
    ├── DOCUMENT_RELATIONSHIPS.md     # Documentation dependency graph
    ├── PR-FAQ.md                     # Product requirements as press release and FAQ
    └── WORKING_BACKWARDS.md          # Product vision and customer experience
```

## Recommendation Workflow

1. **Detection**: System detects documentation or code changes
2. **Analysis**: Changes analyzed for consistency impacts
3. **Generation**: Recommendation file created in `recommendations/` directory
4. **Prioritization**: Oldest recommendation moved to `PENDING_RECOMMENDATION.md`
5. **Developer Review**: Developer reviews and sets ACCEPT/REJECT/AMEND
6. **Processing**: System processes the developer decision:
   - ACCEPT: Implements recommendation automatically
   - REJECT: Removes recommendation from queue
   - AMEND: Regenerates recommendation with developer feedback

## Security and Data Handling

The Documentation-Based Programming system implements comprehensive security measures to protect source code and documentation. Key security features include:

- Local processing with no external data transmission
- Complete isolation between indexed projects
- Resource usage limits and intelligent throttling
- Filesystem permission enforcement
- SQLite database protected by filesystem permissions

For detailed security information, architecture, and principles, see [SECURITY.md](SECURITY.md).

## Out of Scope

- **Code Execution**: System does not execute code on developer's behalf
- **Security Testing**: No security vulnerability scanning capability
- **Performance Profiling**: No code performance analysis
- **External Integration**: No integrations with external systems/APIs

## MCP Server Implementation

### 1. MCP Server Tools

The MCP server provides two essential tools:

- **dbp_general_query**: Used to retrieve various types of codebase metadata
  - Processes both standardized JSON and natural language requests
  - Powered by Amazon Bedrock Nova Lite for fast response times
  - Coordinates parallel execution of internal LLM tools for efficiency
  - Uses specialized tools for querying file headers, function metadata, changelogs, etc.

- **dbp_commit_message**: Generates comprehensive commit messages
  - Identifies and summarizes all changes since the last commit
  - Provides context-aware descriptions of modifications
  - Includes impact analysis for structural changes

### 2. Implementation Strategy

- **LLM Coordination**: Amazon Nova Lite manages and coordinates requests
- **Parallel Processing**: Multiple internal tools can execute in parallel for better performance
- **Model Selection**: Different tasks utilize appropriate models:
  - Amazon Nova Lite for request coordination and simple queries
  - Claude 3.x models for more complex analysis tasks
- **AWS Bedrock Integration**: Initially implemented with placeholder functions
  - Actual AWS Bedrock model interactions to be implemented separately
  - Q Developer Chat will be used for implementing AWS Bedrock integration code

## Relationship to Other Components

- Integrates with Cline's context management
- Complements MCP Server architecture
- Enhances Anthropic Claude prompt effectiveness
