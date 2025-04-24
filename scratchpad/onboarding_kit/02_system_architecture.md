# System Architecture

## Technical Architecture Overview

The Documentation-Based Programming (DBP) system follows a modular component-based architecture. Each component has clearly defined responsibilities and interfaces, focusing on specific aspects of maintaining documentation consistency.

```mermaid
graph TD
    subgraph "Stack Layers"
        UI["User Interfaces<br>(CLI Client, Recommendation Interface)"]
        BL["Business Logic<br>(Metadata Extraction, Consistency Analysis, Recommendation Generation)"]
        EXT["External Dependencies<br>(AWS Bedrock, Other Services)"]
        MID["Middleware & Support Functions<br>(Monitoring, Database, Scheduling, Security, Component System)"]
       
        UI --> BL
        BL --> EXT
        BL --> MID
        MID --> EXT
    end
```

## Core Architecture Principles

1. **Documentation as Source of Truth**: Documentation takes precedence over code itself for understanding project intent
2. **Automatic Consistency Maintenance**: System actively ensures consistency between documentation and code
3. **Global Contextual Awareness**: AI assistants maintain awareness of entire project context
4. **Design Decision Preservation**: All significant design decisions are captured and maintained
5. **Reasonable Default Values**: System provides carefully selected default values while allowing customization
6. **Simplified Component Management**: System uses a minimalist component lifecycle approach for clarity

## Component System

The DBP system uses a component-based architecture with centralized registration and dependency management:

```mermaid
graph TD
    subgraph "Component Management"
        REGISTRY["Component Registry"]
        LIFECYCLE["Component Lifecycle"]
        VALIDATION["Dependency Validation"]
        
        REGISTRY --> VALIDATION
        VALIDATION --> LIFECYCLE
        
        COMP["Component Interface"]
        INIT["Initialization Context"]
        
        COMP --> REGISTRY
        INIT --> COMP
    end
    
    subgraph "Component Implementation"
        CONFIG["Config Manager<br>Component"]
        DB["Database<br>Component"]
        MONITOR["File System Monitor<br>Component"]
        LLM["LLM Coordination<br>Component"]
        
        CONFIG --> DB
        CONFIG --> MONITOR
        CONFIG --> LLM
    end
    
    REGISTRY --> CONFIG
    REGISTRY --> DB
    REGISTRY --> MONITOR
    REGISTRY --> LLM
```

### Initialization Sequence

The component initialization follows a simple and explicit sequence:

1. **Registration**: Components register with dependencies in the ComponentRegistry
2. **Validation**: All dependencies are validated before initialization begins
3. **Initialization**: Components are initialized in dependency order
4. **Shutdown**: Components are shut down in reverse initialization order

```mermaid
sequenceDiagram
    participant System
    participant Registry
    participant Component1
    participant Component2
    
    System->>Registry: register_components()
    Registry->>Registry: validate_dependencies()
    
    System->>Registry: initialize()
    Registry->>Component1: initialize(context, dependencies)
    Component1-->>Registry: initialized
    Registry->>Component2: initialize(context, dependencies)
    Component2-->>Registry: initialized
    Registry-->>System: all components initialized
    
    System->>Registry: shutdown()
    Registry->>Component2: shutdown()
    Registry->>Component1: shutdown()
    Registry-->>System: all components shut down
```

## Key Components

### 1. File System Monitor

Monitors the codebase for file changes in near real-time:

```mermaid
graph TD
    subgraph "File System Monitoring"
        OS["OS File Events<br>(inotify/FSEvents/ReadDirectoryChangesW)"]
        FILTER["Filter<br>(gitignore patterns)"]
        QUEUE["Change Queue<br>(debounced)"]
        NOTIF["Change Notifications"]
        
        OS --> FILTER
        FILTER --> QUEUE
        QUEUE --> NOTIF
    end
```

Key features:
- Uses native OS notification APIs for efficiency
- Respects .gitignore patterns and exclusion rules
- Implements debouncing to handle rapid changes
- Queue-based processing with configurable delays

### 2. Metadata Extraction

Extracts metadata from codebase files using LLM capabilities:

```mermaid
graph TD
    subgraph "Metadata Extraction"
        FILE["File Content"]
        LLM["Amazon Nova Lite<br>LLM"]
        SCHEMA["JSON Schema"]
        META["Structured Metadata"]
        DB["Metadata Database"]
        
        FILE --> LLM
        SCHEMA --> LLM
        LLM --> META
        META --> DB
    end
```

Key features:
- Uses Amazon Nova Lite for efficient metadata extraction
- Extracts file header sections, function documentation, and relationships
- Normalizes metadata into structured JSON format
- Stores metadata in SQLite database for persistence
- Implements in-memory caching for performance

### 3. Consistency Analysis

Analyzes relationships and detects inconsistencies:

```mermaid
graph TD
    subgraph "Consistency Analysis"
        META["Metadata Repository"]
        GRAPH["Relationship Graph"]
        RULES["Consistency Rules"]
        ANALYZE["Analysis Engine"]
        ISSUES["Detected Inconsistencies"]
        
        META --> GRAPH
        GRAPH --> ANALYZE
        RULES --> ANALYZE
        ANALYZE --> ISSUES
    end
```

Key features:
- Builds in-memory graph of document relationships
- Applies consistency rules to detect misalignments
- Analyzes code-documentation relationships
- Tracks dependency graph between documentation files
- Identifies contradictions between documentation files

### 4. Recommendation Generator

Creates actionable recommendations from detected inconsistencies:

```mermaid
graph TD
    subgraph "Recommendation Generation"
        ISSUES["Detected Inconsistencies"]
        STRATEGIES["Resolution Strategies"]
        ENGINE["Recommendation Engine"]
        FORMATTER["Markdown Formatter"]
        FILE["PENDING_RECOMMENDATION.md"]
        
        ISSUES --> ENGINE
        STRATEGIES --> ENGINE
        ENGINE --> FORMATTER
        FORMATTER --> FILE
    end
```

Key features:
- Generates single active recommendation file
- Uses markdown format for easy developer review
- Supports ACCEPT/REJECT/AMEND developer decisions
- Automatically invalidates when code changes
- Implements recommendations when accepted

### 5. LLM Coordination Architecture

Orchestrates multiple LLM instances for efficient processing:

```mermaid
graph TD
    subgraph "LLM Coordination"
        COORD["Coordinator LLM<br>(Amazon Nova Lite)"]
        TOOL1["Internal Tool LLM 1"]
        TOOL2["Internal Tool LLM 2"]
        TOOL3["Internal Tool LLM 3"]
        QUEUE["Job Queue"]
        RESULTS["Results Aggregation"]
        
        COORD --> QUEUE
        QUEUE --> TOOL1
        QUEUE --> TOOL2
        QUEUE --> TOOL3
        TOOL1 --> RESULTS
        TOOL2 --> RESULTS
        TOOL3 --> RESULTS
        RESULTS --> COORD
    end
```

Key features:
- Uses coordinator LLM to manage request processing
- Dispatches specialized internal tools for specific contexts
- Implements asynchronous job-based architecture
- Manages cost budgets and timeout constraints
- Aggregates results from multiple tools

### 6. MCP Server

Exposes DBP capabilities through MCP protocol:

```mermaid
graph TD
    subgraph "MCP Server"
        SERVER["MCP Server"]
        AUTH["Authentication"]
        REGISTRY["Tool Registry"]
        ADAPTER["Tool Adapter"]
        TOOLS["DBP Internal Tools"]
        RESOURCES["DBP Resources"]
        
        SERVER --> AUTH
        SERVER --> REGISTRY
        REGISTRY --> ADAPTER
        ADAPTER --> TOOLS
        ADAPTER --> RESOURCES
    end
```

Key features:
- Implements MCP protocol for AI assistant integration
- Exposes dbp_general_query and dbp_commit_message tools
- Provides access to documentation resources
- Implements authentication and authorization
- Manages resource limits and budgets

### 7. Database Layer

Persists metadata and system state:

```mermaid
graph TD
    subgraph "Database Layer"
        SQLITE["SQLite Database"]
        MODELS["SQLAlchemy Models"]
        REPOS["Repository Classes"]
        ALEMBIC["Alembic Migrations"]
        
        MODELS --> SQLITE
        REPOS --> MODELS
        ALEMBIC --> SQLITE
    end
```

Key features:
- Uses SQLite for zero-dependency local storage
- Implements repository pattern for data access
- Manages schema evolution with Alembic migrations
- Provides thread-safe access through connection pooling
- Optimized for metadata storage and retrieval

### 8. Background Task Scheduler

Manages asynchronous background tasks:

```mermaid
graph TD
    subgraph "Background Task Scheduler"
        CONTROLLER["Task Controller"]
        WORKERS["Worker Thread Pool"]
        QUEUE["Priority Queue"]
        STATUS["Task Status"]
        
        CONTROLLER --> QUEUE
        QUEUE --> WORKERS
        WORKERS --> STATUS
        STATUS --> CONTROLLER
    end
```

Key features:
- Implements thread pool for concurrent task execution
- Prioritizes tasks based on importance and dependencies
- Provides status tracking and monitoring
- Implements graceful shutdown handling
- Manages resource usage constraints

## End-to-End Workflow

Here's how the components work together in a typical workflow:

```mermaid
sequenceDiagram
    participant FS as File System
    participant Monitor as File Monitor
    participant Extraction as Metadata Extraction
    participant Analysis as Consistency Analysis
    participant Generator as Recommendation Generator
    participant File as PENDING_RECOMMENDATION.md
    participant Developer
    
    FS->>Monitor: File changed
    Monitor->>Extraction: Queue file for processing
    Extraction->>Analysis: Updated metadata
    Analysis->>Generator: Detected inconsistency
    Generator->>File: Create recommendation
    Developer->>File: Review recommendation
    Developer->>File: Mark decision (ACCEPT)
    File->>Generator: Process decision
    Generator->>FS: Apply changes
```

## MCP Client Integration

The DBP system integrates with AI assistants through the MCP protocol:

```mermaid
graph TD
    subgraph "MCP Integration"
        CLIENT["AI Assistant<br>(MCP Client)"]
        SERVER["MCP Server"]
        QUERY["dbp_general_query"]
        COMMIT["dbp_commit_message"]
        EXTRACT["Metadata Extraction"]
        ANALYSIS["Consistency Analysis"]
        
        CLIENT --> SERVER
        SERVER --> QUERY
        SERVER --> COMMIT
        QUERY --> EXTRACT
        QUERY --> ANALYSIS
        COMMIT --> EXTRACT
    end
```

## Security Architecture

The security architecture follows these principles:

```mermaid
graph TD
    subgraph "Security Architecture"
        LOCAL["Data Locality"]
        ISOLATION["Project Isolation"]
        PERMISSIONS["File System Permissions"]
        RESOURCES["Resource Constraints"]
        NOEXEC["No Code Execution"]
        
        LOCAL --> ISOLATION
        ISOLATION --> PERMISSIONS
        PERMISSIONS --> RESOURCES
        RESOURCES --> NOEXEC
    end
```

Key security features:
- All processing performed locally, no data leaves the system
- Complete separation between indexed projects
- Follows existing filesystem permissions for file access
- System never executes code from monitored files
- Limited CPU and memory usage with intelligent throttling

## Documentation Relationship Management

Documentation relationships are tracked through a graph structure:

```mermaid
graph TD
    subgraph "Document Relationships"
        DESIGN["DESIGN.md"]
        DATA["DATA_MODEL.md"]
        CONFIG["CONFIGURATION.md"]
        SECURITY["SECURITY.md"]
        DECISIONS["DESIGN_DECISIONS.md"]
        
        DECISIONS -->|"impacts"| DESIGN
        DECISIONS -->|"impacts"| DATA
        DECISIONS -->|"impacts"| CONFIG
        DECISIONS -->|"impacts"| SECURITY
        
        DESIGN -->|"depends on"| DATA
        SECURITY -->|"depends on"| DESIGN
        CONFIG -->|"depends on"| DESIGN
    end
```

This graph enables:
- Understanding which documents depend on others
- Identifying impact when documentation changes
- Maintaining global consistency across documentation
- Tracking documentation update requirements

## Next Steps

Continue to the [Key Workflows](03_key_workflows.md) document to understand how the system processes changes and generates recommendations.
