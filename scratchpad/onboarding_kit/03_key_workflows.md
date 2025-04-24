# Key Workflows

This document explains the primary workflows in the Documentation-Based Programming system, demonstrating how components interact to maintain documentation consistency.

## 1. File Change Detection and Processing

This workflow shows how the system detects and processes file changes:

```mermaid
flowchart TD
    subgraph "File Change Detection"
        A[Developer modifies file] --> B[File system event triggered]
        B --> C{File Monitor receives event}
        C -->|File ignored| D[Discard event]
        C -->|File monitored| E[Add to change queue]
        E --> F[Wait for debounce period]
        F --> G[Determine if metadata extraction needed]
        G -->|No changes needed| H[Done]
        G -->|Extract metadata| I[Queue for metadata extraction]
    end
```

**How it works:**
1. Developer creates, modifies, or deletes a file
2. Operating system file notification API detects the change
3. File system monitor filters events based on .gitignore patterns
4. Monitored files are added to the change queue
5. System waits for configured debounce period (default: 10 seconds)
6. System checks if metadata extraction is needed based on:
   - File existence
   - File size changes
   - Content hash changes
   - Missing metadata in database
7. If needed, file is queued for metadata extraction

## 2. Metadata Extraction Process

This workflow shows how metadata is extracted from files:

```mermaid
flowchart TD
    A[File queued for extraction] --> B[Read file content]
    B --> C[Determine file type]
    C --> D[Prepare extraction context]
    D --> E[Invoke Amazon Nova Lite LLM]
    
    E --> F[LLM extracts structured metadata]
    F --> G[Validate against JSON schema]
    
    G -->|Valid| H[Store in SQLite database]
    G -->|Invalid| I[Log error and retry]
    
    H --> J[Update in-memory cache]
    J --> K[Notify consistency analysis]
```

**How it works:**
1. Extraction worker reads file content
2. File type is determined (based on content, not just extension)
3. Extraction context is prepared including:
   - File content
   - Extraction templates
   - Expected output schema
4. Amazon Nova Lite LLM performs the extraction, identifying:
   - File header sections (intent, design principles, etc.)
   - Function/class definitions and documentation
   - Documentation references
   - Change history entries
5. Metadata is validated against JSON schema
6. Valid metadata is stored in SQLite database
7. In-memory cache is updated
8. Consistency analysis is notified of the update

## 3. Consistency Analysis

This workflow shows how the system analyzes consistency between documentation and code:

```mermaid
flowchart TD
    A[Metadata updated] --> B[Load affected document metadata]
    B --> C[Update relationship graph]
    C --> D[Apply consistency rules]
    
    D --> E{Inconsistencies detected?}
    E -->|No| F[No action needed]
    E -->|Yes| G[Create inconsistency records]
    
    G --> H[Determine severity and impact]
    H --> I[Group related inconsistencies]
    I --> J[Queue for recommendation generation]
```

**How it works:**
1. System loads metadata for affected document(s)
2. In-memory relationship graph is updated
3. Consistency rules are applied, checking for:
   - Documentation-to-documentation consistency
   - Code-to-documentation consistency
   - Design decision compliance
   - Reference validity
4. Detected inconsistencies are recorded with:
   - Severity classification
   - Affected documents
   - Type of inconsistency
   - Suggested resolution
5. Related inconsistencies are grouped
6. Groups are queued for recommendation generation

## 4. Recommendation Generation and Processing

This workflow shows how recommendations are created and processed:

```mermaid
flowchart TD
    A[Inconsistency group queued] --> B[Generate recommendation]
    B --> C[Create PENDING_RECOMMENDATION.md]
    
    C --> D[Wait for developer decision]
    D -->|ACCEPT| E[Apply changes automatically]
    D -->|REJECT| F[Remove recommendation]
    D -->|AMEND| G[Process feedback]
    
    E --> H[Update affected files]
    H --> I[Mark inconsistencies as resolved]
    
    G --> J[Regenerate recommendation]
    J --> C
    
    F --> K[Mark as rejected]
```

**How it works:**
1. System generates recommendation based on inconsistency group
2. Creates PENDING_RECOMMENDATION.md file with:
   - Detailed explanation of inconsistency
   - Affected files and locations
   - Specific suggested changes (in diff format)
   - Decision options (ACCEPT/REJECT/AMEND)
3. Developer reviews recommendation and makes decision
4. For ACCEPT:
   - System applies changes automatically
   - Affected files are updated
   - Inconsistencies are marked as resolved
5. For REJECT:
   - Recommendation is removed
   - Inconsistencies are marked as rejected
6. For AMEND:
   - Developer feedback is processed
   - New recommendation is generated
   - Process repeats

## 5. MCP Server Request Processing

This workflow shows how the MCP server processes requests using the LLM coordination system:

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as MCP Server
    participant CLLM as Coordinator LLM
    participant Tool1 as Internal Tool 1
    participant Tool2 as Internal Tool 2
    participant Tool3 as Internal Tool 3
    
    Client->>Server: Request (dbp_general_query)
    Server->>CLLM: Forward request
    
    CLLM->>CLLM: Determine required tools
    
    par Tool Execution
        CLLM->>Tool1: Create job with UUID
        CLLM->>Tool2: Create job with UUID
        CLLM->>Tool3: Create job with UUID
    end
    
    Tool1-->>CLLM: Results
    Tool2-->>CLLM: Results
    Tool3-->>CLLM: Results
    
    CLLM->>CLLM: Aggregate results
    CLLM-->>Server: Formatted response
    Server-->>Client: Response
```

**How it works:**
1. MCP client (AI assistant) sends request to MCP server
2. Server forwards request to coordinator LLM (Amazon Nova Lite)
3. Coordinator determines which internal tools are needed based on query
4. Creates jobs with unique UUIDs for each required tool
5. Internal tools execute in parallel, each with its own LLM instance
6. Tools access application data as needed
7. Results are returned to coordinator
8. Coordinator aggregates results and formats response
9. Response is returned to client

## 6. Developer Experience

This workflow demonstrates the developer experience:

```mermaid
sequenceDiagram
    participant Developer
    participant IDE as IDE/Editor
    participant File as PENDING_RECOMMENDATION.md
    participant AI as AI Assistant
    participant MCP as MCP Server
    
    Developer->>File: Makes code change
    Note over Developer,File: Change detected and processed
    Note over File: 10-15 seconds later
    
    File->>Developer: PENDING_RECOMMENDATION.md appears
    Developer->>File: Reviews recommendation
    Developer->>File: Marks decision (ACCEPT/REJECT/AMEND)
    
    Note over File: If ACCEPT, changes applied automatically
    
    Developer->>AI: "What files implement the auth system?"
    AI->>MCP: dbp_general_query
    MCP-->>AI: Detailed response
    AI-->>Developer: Answer with file list and explanation
```

**How it works:**
1. Developer makes code or documentation changes
2. System automatically processes changes (typically within 10-15 seconds)
3. If inconsistencies are detected, PENDING_RECOMMENDATION.md appears
4. Developer reviews and decides on recommendation
5. System processes the decision automatically
6. Developer can use AI assistants that leverage the MCP server
7. AI assistants provide contextually aware responses based on up-to-date project metadata

## 7. Commit Message Generation

This workflow shows how the system generates Git commit messages:

```mermaid
flowchart TD
    A[Developer asks for commit message] --> B[MCP client calls dbp_commit_message]
    B --> C[LLM coordinator processes request]
    
    C --> D[Identify changed files]
    D --> E[Extract metadata for changed files]
    
    E --> F[Analyze change patterns]
    F --> G[Determine impact of changes]
    
    G --> H[Generate structured commit message]
    H --> I[Return to client]
```

**How it works:**
1. Developer requests commit message generation
2. MCP client calls dbp_commit_message tool
3. LLM coordinator identifies changed files using:
   - Provided diff information, or
   - Git diff from last commit, or
   - File system change detection
4. System extracts metadata for changed files
5. Change patterns are analyzed
6. Impact of changes is assessed
7. Structured commit message is generated with:
   - Subject line summarizing changes
   - Detailed body explaining modifications
   - References to documentation changes
   - Impact analysis based on defined rules
8. Commit message is returned to client

## Key Resource Constraints

The system operates with these resource constraints:

1. **CPU Usage**: <5% average CPU usage
2. **Memory Usage**: <100MB RAM for core functionality
3. **Disk Usage**: Efficient SQLite storage with automatic maintenance
4. **Response Time**: 
   - Change detection: <10 seconds
   - Metadata extraction: <5 seconds per file
   - Recommendation generation: <15 seconds
   - MCP queries: <3 seconds for simple queries, <10 seconds for complex queries

## Error Handling and Recovery

The system implements robust error handling:

1. **Extraction Failures**: Retried with exponential backoff
2. **LLM Failures**: Fallback mechanisms and clear error reporting
3. **Database Failures**: Automatic reconnection with data integrity checks
4. **File Access Errors**: Logged with retry mechanisms
5. **Recommendation Failures**: Clear error messages with suggestions

## Next Steps

Continue to the [Data Models](04_data_models.md) document to understand the core data structures used throughout the system.
