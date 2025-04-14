# Documentation-Based Programming Data Model

This document defines the data structures and relationships for the Documentation-Based Programming system, focusing specifically on how recommendations are generated, stored, and processed.

## Metadata Extraction Model

The system uses Amazon Nova Lite LLM to extract the following metadata from code files:

```
FileMetadata {
  path: String                   // Full path to the file
  language: String               // Detected programming language
  headerSections: {              // Extracted header sections
    intent: String,              // File's purpose
    designPrinciples: String[],  // Design principles guiding implementation
    constraints: String[],       // Limitations or requirements
    referenceDocumentation: String[], // Related documentation files
    changeHistory: ChangeRecord[] // History of file changes
  }
  functions: [                   // Array of function definitions
    {
      name: String,              // Function name  
      docSections: {             // Documentation sections
        intent: String,          // Purpose of function
        designPrinciples: String[], // Design principles
        implementationDetails: String, // Technical approach
        designDecisions: String  // Why specific choices were made
      },
      parameters: String[],      // Function parameters
      lineRange: {start: Number, end: Number} // Line numbers
    }
  ],
  classes: [ /* Similar structure to functions */ ]
}
```

The extraction process has these key characteristics:
- Uses LLM semantic understanding instead of keyword-based parsing
- Extracts metadata across various programming languages without language-specific parsers
- Identifies section content based on semantic meaning rather than exact format
- Preserves hierarchical relationship between file, class, and function metadata

## Core Data Entities

### Document References

A Document Reference represents any file that contains documentation or code:

```
DocumentReference {
  path: String              // Full path to the file
  type: Enum                // Code, Markdown, Header, Config
  lastModified: Timestamp   // Last modification timestamp
  headerSections: {         // Extracted header sections (if applicable)
    intent: String,
    designPrinciples: String[],
    constraints: String[],
    referenceDocumentation: String[]
    changeHistory: ChangeRecord[]
  }
  designDecisions: DesignDecision[]  // Design decisions in this file
  dependencies: DocumentReference[]  // Other documents this depends on
}
```

### Document Relationships

Documents in the system have relationships that are captured in a directed graph structure:

```
DocumentRelationship {
  source: DocumentReference    // Source document
  target: DocumentReference    // Target document
  relationType: Enum           // DependsOn, Impacts, Implements, Extends
  topic: String                // Subject matter of the relationship
  scope: String                // How broadly the relationship applies
}
```

### Inconsistency Records

When inconsistencies are detected, they are stored as records:

```
InconsistencyRecord {
  id: UUID                     // Unique identifier
  timestamp: Timestamp         // When inconsistency was detected
  severity: Enum               // Critical, Major, Minor
  type: Enum                   // DocToDoc, DocToCode, DesignDecisionViolation
  affectedDocuments: DocumentReference[]  // Documents involved
  description: String          // Description of inconsistency
  suggestedResolution: String  // Suggested fix
  status: Enum                 // Pending, InRecommendation, Resolved
}
```

### Recommendations

Recommendations are actionable suggestions generated from inconsistencies:

```
Recommendation {
  id: UUID                     // Unique identifier
  creationTimestamp: Timestamp // When recommendation was created
  title: String                // Human-readable title
  inconsistencies: InconsistencyRecord[]  // Related inconsistencies
  affectedDocuments: DocumentReference[]  // Documents to be modified
  suggestedChanges: {          // Changes to resolve inconsistencies
    document: DocumentReference,
    changes: [                 // Array of text changes
      {
        type: Enum,            // Addition, Deletion, Modification
        location: Location,    // Where in the document
        before: String,        // Text before change (for modifications)
        after: String          // Text after change
      }
    ]
  }[]
  status: Enum                 // Active, Accepted, Rejected, Amended, Invalidated
  developerFeedback: String    // Feedback for AMEND status
  lastCodebaseChangeTimestamp: Timestamp // For automatic invalidation
}
```

### Developer Decisions

Records of developer decisions on recommendations:

```
DeveloperDecision {
  recommendation: Recommendation  // Associated recommendation
  timestamp: Timestamp         // When decision was made
  decision: Enum               // Accept, Reject, Amend
  comments: String             // Developer comments (for Amend)
  implementationTimestamp: Timestamp  // When recommendation was implemented (for Accept)
}
```

## File Formats

### Recommendation File Format

Each recommendation is stored as a Markdown file with the following structure:

```markdown
# Documentation Consistency Recommendation

## Decision Required

Choose ONE option:
- [ ] ACCEPT - Apply these changes automatically
- [ ] REJECT - Discard this recommendation
- [ ] AMEND - Request changes to this recommendation

## Amendment Comments
<!-- If choosing AMEND, provide your feedback below this line -->


<!-- Do not modify below this line -->

## Recommendation: [TITLE]

**Created**: YYYY-MM-DD HH:MM:SS
**Priority**: [PRIORITY]

### Detected Inconsistency

[Description of the inconsistency detected between documentation and code or between multiple documentation files]

### Affected Files

- `path/to/file1.md`
- `path/to/file2.js`

### Suggested Changes

#### In `path/to/file1.md`:

```diff
- Original text that contains inconsistency
+ Suggested replacement text
```

#### In `path/to/file2.js`:

```diff
- Original code that contains inconsistency
+ Suggested replacement code
```

### Rationale

[Explanation of why these changes are recommended and how they improve consistency]
```

For a real example of this format, see [Example Recommendation](../coding_assistant/dbp/recommendations/250413-155600-EXAMPLE_RECOMMENDATION.md).

### PENDING_RECOMMENDATION.md Format

This file is a copy of the oldest recommendation file, automatically renamed when it becomes the next item to review.

## Data Flow

### Recommendation Generation Process

1. **Change Detection**:
   - File system watcher detects changes in files
   - Changed files are parsed to extract documentation entities
   - Any existing recommendation is automatically invalidated

2. **Consistency Analysis**:
   - System analyzes changes against existing documentation
   - Inconsistencies are identified and recorded
   - Related documents are discovered through dependency graph

3. **Recommendation Creation**:
   - Inconsistencies are grouped by related impact
   - A single recommendation object is created
   - The recommendation is written directly to PENDING_RECOMMENDATION.md
   - Status of recommendation is set to Active

4. **Feedback Processing**:
   - System monitors PENDING_RECOMMENDATION.md for changes
   - Developer decision is extracted and processed
   - For ACCEPT: Changes are automatically applied
   - For REJECT: Recommendation is removed
   - For AMEND: New recommendation is generated with feedback

5. **Auto-Invalidation**:
   - Any change in the codebase automatically invalidates the current recommendation
   - PENDING_RECOMMENDATION.md is removed
   - System repeats the process from Change Detection to generate a new recommendation

## Security Considerations

The database system is designed with security as a core principle:

- **Data Protection**: All data is processed and stored locally, never transmitted externally
- **Isolation**: Complete separation between indexed projects ensures no cross-project data leakage
- **Local Persistence**: All data exists only in the local SQLite database file, protected by file system permissions
- **Access Control**: Follows existing filesystem permissions for all file operations
- **No Code Execution**: The system analyzes but never executes code from indexed projects
- **Resource Limitations**: Database usage is optimized to prevent excessive disk usage or performance impacts

The system operates entirely within the user's environment with no external communication channels, ensuring maximum security of sensitive source code and documentation.

## MCP CLI Client Data Model

The Python Command Line Client for MCP servers uses the following data structures to manage connections, issue requests, and process responses:

### MCP Server Connection

```python
MCPServerConnection {
  url: String              // URL endpoint of the MCP server
  name: String             // Friendly name of the server connection
  status: Enum             // Connected, Disconnected, Error
  lastConnected: Timestamp // When server was last successfully connected
  capabilities: {          // Server capabilities discovered on connection
    tools: [               // Available tools provided by this server
      {
        name: String,      // Tool name
        description: String, // Tool description
        parameters: [      // Tool parameters
          {
            name: String,  // Parameter name
            type: String,  // Parameter type
            required: Boolean, // Whether parameter is required
            description: String // Parameter description
          }
        ]
      }
    ],
    resources: [           // Available resources provided by this server
      {
        uriPattern: String, // Resource URI pattern
        description: String  // Resource description
      }
    ]
  }
}
```

### MCP Request

```python
MCPRequest {
  requestId: UUID          // Unique identifier for the request
  serverName: String       // Target MCP server name
  requestType: Enum        // Tool, Resource
  toolName: String         // If tool request, name of the tool
  resourceUri: String      // If resource request, URI of the resource
  parameters: Object       // Key-value pairs of parameters for tool requests
  timestamp: Timestamp     // When request was initiated
}
```

### MCP Response

```python
MCPResponse {
  requestId: UUID          // Matching the request ID
  serverName: String       // Source MCP server name
  status: Enum             // Success, Error, Pending
  result: Object           // Response data from the server
  errorDetails: {          // Present only if status is Error
    code: String,          // Error code
    message: String,       // Error message
    details: Object        // Additional error details
  }
  timestamp: Timestamp     // When response was received
}
```

### CLI Configuration

```python
CLIConfiguration {
  defaultServer: String    // Default MCP server name
  servers: [               // List of configured servers
    {
      name: String,        // Server name
      url: String,         // Server URL
      port: Number,        // Server port (default: 6231)
      autoConnect: Boolean // Whether to connect on startup
    }
  ]
  outputFormat: Enum       // JSON, YAML, Formatted
  logLevel: Enum           // Error, Warning, Info, Debug
  historySize: Number      // Number of commands to keep in history
  scriptDirectories: String[] // Directories to search for custom scripts
}
```

### Command History

```python
CommandHistory {
  entries: [               // List of command history entries
    {
      command: String,     // Command text
      timestamp: Timestamp, // When command was executed
      success: Boolean,    // Whether command succeeded
      requestId: UUID      // Associated request ID if applicable
    }
  ],
  currentIndex: Number     // Index in history for up/down navigation
}
```

### Script Entry

```python
ScriptEntry {
  name: String             // Script name
  description: String      // Script description
  path: String             // Path to script file
  parameters: [            // Script parameters
    {
      name: String,        // Parameter name
      type: String,        // Parameter type
      required: Boolean,   // Whether parameter is required
      description: String  // Parameter description
    }
  ]
}
```

## CLI Client Data Flow

### Connection Establishment Process

1. **Server Discovery**:
   - Client attempts to connect to specified MCP server URL
   - Server responds with capabilities (available tools and resources)
   - Client stores connection information and capabilities

2. **Request Processing**:
   - User inputs command via CLI interface
   - Command is parsed and validated against server capabilities
   - Request object is created with unique UUID
   - Request is sent to server

3. **Response Handling**:
   - Response is received from server
   - Response is parsed and formatted according to output settings
   - Results are displayed to user
   - Command and response are added to history

4. **Configuration Management**:
   - Configuration is loaded from disk on startup
   - Changes to configuration are saved to disk
   - Server connections are managed according to configuration

## MCP Server Implementation Data Models

The MCP server implementation data models are documented in dedicated design documents:

- **[LLM Coordination Architecture](design/LLM_COORDINATION.md)**: Documents the data models for the LLM coordination system, including:
  - Coordinator request/response models
  - Internal tool job management
  - Asynchronous execution tracking

- **[Internal LLM Tools](design/INTERNAL_LLM_TOOLS.md)**: Provides the data models for specialized internal tools, including:
  - Context models for different query types
  - Tool helper function interfaces
  - Common tool interfaces

- **[Enhanced MCP Data Models](design/MCP_SERVER_ENHANCED_DATA_MODEL.md)**: Describes enhanced data models for MCP-exposed tools with:
  - Budget management parameters
  - Input/output validation
  - Partial result handling

## Database Implementation

The Documentation-Based Programming system supports both PostgreSQL and SQLite (with SQLite as the default) databases with the following characteristics:

- **Local Persistence**: Metadata stored in a database for persistence across application restarts
- **Database Flexibility**: Support for both PostgreSQL (for advanced deployments) and SQLite (zero-dependency default)
  - **Rationale**: Provides deployment flexibility while ensuring a zero-dependency default option
  - **Implementation Requirements**: 
    - SQL queries must be aligned to SQLite capabilities (SQLite types and limitations)
    - SQLite operational mode must use WAL (Write-Ahead Logging) for maximum safety
    - Database migrations must be managed through Alembic
    - All database access must be thread-safe
- **SQL Compatibility**: All queries aligned to SQLite capabilities to ensure cross-database compatibility
- **Change Detection**: Uses file modification timestamps, file sizes, and MD5 digests to detect changes in source files
- **Incremental Updates**: Only re-extracts metadata for changed files, improving performance
- **Efficient Representation**: Optimized schema design to minimize storage requirements
- **Fast Access Patterns**: Indexed for quick lookups and relationship traversal
- **Isolated Projects**: Complete separation between multiple projects
- **Reduced CPU Usage**: Minimizes computational overhead for large codebases
- **Faster Startup**: Significant performance improvement after initial indexing

The database schema is organized as a series of related tables:

1. **DocumentReferences**: All document references indexed by path, including metadata timestamps
2. **DocumentRelationships**: Bidirectional graph of document relationships
3. **Inconsistencies**: Active inconsistencies indexed by status
4. **Recommendations**: FIFO queue of pending recommendations (automatically purged after 7 days)
5. **DeveloperDecisions**: Record of all developer decisions (automatically purged after 7 days) 
6. **FileMetadata**: Tracking data including last known file size and modification time

### Change Detection Strategy

The system implements an efficient change detection strategy:

1. On startup, compares file system metadata (modification time, file size) with stored values
2. During runtime, monitors file system events for changes
3. Calculates and stores MD5 digests of files for reliable change detection
   - **Rationale**: MD5 digests provide more reliable change detection than timestamp/size alone
   - **Benefits**: Significantly reduces unnecessary metadata re-extraction 
   - **Implementation**: Digests are stored in the database as part of file metadata
4. Only triggers metadata re-extraction when actual file content changes are detected
5. Maintains a processing queue for files that need metadata updates

### Database Migration Strategy

To support future schema changes:

1. Database includes a version table to track schema version
2. Application checks schema version on startup
3. Automatic migration process for schema updates using Alembic
4. Fallback to rebuild database from scratch if migration fails
5. Safe migration path between SQLite and PostgreSQL when needed

### SQLite-Specific Implementation

When using the default SQLite database:

1. **WAL Mode**: Write-Ahead Logging mode is used for maximum safety and concurrency
2. **Thread Safety**: All database access is thread-safe through connection pooling and proper locking
3. **Performance Tuning**: Appropriate indexes and optimizations for common query patterns
4. **Automatic Maintenance**: Periodic VACUUM operations to maintain performance

### PostgreSQL-Specific Implementation

When using PostgreSQL:

1. **Connection Pooling**: Efficient connection management to avoid resource exhaustion
2. **Thread Safety**: Concurrent access handled through PostgreSQL's transaction system
3. **Schema Design**: Leverages PostgreSQL capabilities while maintaining SQLite compatibility
4. **Performance Tuning**: PostgreSQL-specific optimizations while maintaining query compatibility

### Recommendation Lifecycle Management

The system implements automatic recommendation cleanup to prevent database growth:

1. Recommendations and related developer decisions are automatically purged after 7 days
2. Purge mechanism tracks recommendation age based on creation timestamp
3. Purged recommendations are removed from both database and filesystem
4. Purge threshold is configurable through system configuration
