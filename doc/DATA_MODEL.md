# Documentation-Based Programming Data Model

This document defines the data structures and relationships for the Documentation-Based Programming system, focusing specifically on how recommendations are generated, stored, and processed.

## Metadata Extraction Model

The system uses Claude 3.7 Sonnet LLM to extract the following metadata from code files:

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
- Uses Claude 3.7 Sonnet's semantic understanding instead of keyword-based parsing
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
  filename: String             // Generated filename (YYMMDD-HHmmSS-NAME.md)
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
  status: Enum                 // Pending, Active, Accepted, Rejected, Amended
  developerFeedback: String    // Feedback for AMEND status
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

2. **Consistency Analysis**:
   - System analyzes changes against existing documentation
   - Inconsistencies are identified and recorded
   - Related documents are discovered through dependency graph

3. **Recommendation Creation**:
   - Inconsistencies are grouped by related impact
   - Recommendation objects are created for each group
   - Markdown files are generated from recommendation objects
   - Files are stored in recommendations directory with timestamped names

4. **Queue Management**:
   - System maintains FIFO queue of recommendations
   - Oldest recommendation is moved to PENDING_RECOMMENDATION.md
   - Status of recommendation is updated to Active

5. **Feedback Processing**:
   - System monitors PENDING_RECOMMENDATION.md for changes
   - Developer decision is extracted and processed
   - For ACCEPT: Changes are automatically applied
   - For REJECT: Recommendation is removed from queue
   - For AMEND: New recommendation is generated with feedback

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

## MCP Server Tool Data Model

The MCP server provides two primary tools with their own data models:

### dbp_general_query Tool

```python
DBPGeneralQueryRequest {
  query: String | Object    // Natural language query or structured JSON object
  queryType: Enum           // NaturalLanguage, StructuredJSON
  scope: {                  // Optional scope constraints
    filePatterns: String[], // File patterns to include in query scope
    directories: String[],  // Directories to search
    excludePatterns: String[] // Patterns to exclude
  }
  responseFormat: Enum      // Concise, Detailed, JSON, Markdown
  context: Object           // Additional context for the query
  timeout: Integer          // Maximum execution time in seconds
}

DBPGeneralQueryResponse {
  results: Object           // Query results (format depends on request)
  metadata: {               // Information about the query execution
    executionTimeMs: Integer, // Time taken to execute the query in milliseconds
    modelsUsed: String[],   // LLMs utilized for this query
    filesProcessed: Integer, // Number of files processed
    tools: {                // Tools used to fulfill the query
      name: String,         // Tool name
      executionTimeMs: Integer // Time taken by this tool in milliseconds
    }[],
    totalCost: Number,      // Cumulated price cost for all LLM requests
    backgroundTaskProgress: {  // Information about background task progress
      status: Enum,         // NotStarted, InProgress, Complete, Error
      processedFiles: Integer, // Number of files processed so far
      totalFiles: Integer,  // Total number of files to process
      percentComplete: Integer, // Percentage of completion (0-100)
      currentActivity: String, // Description of current background activity
      estimatedCompletionTimeMs: Integer // Estimated time until completion in milliseconds
    }
  }
  suggestions: String[]     // Related queries that might be useful
}
```

### dbp_commit_message Tool

```python
DBPCommitMessageRequest {
  sinceDiff: String         // Optional: Git diff output or similar formatted diff
  sinceCommit: String       // Optional: commit hash to use as starting point
                            // Note: If neither sinceDiff nor sinceCommit are supplied,
                            // the MCP server will automatically detect the last Git commit
  includeImpact: Boolean    // Whether to include impact analysis
  format: Enum              // Conventional, Detailed, Summary
  scope: String             // Optional commit scope
  maxLength: Integer        // Maximum length for commit message
}

DBPCommitMessageResponse {
  commitMessage: {          // Generated commit message
    title: String,          // Commit message title/subject
    body: String,           // Detailed description
    footer: String          // Optional footer with references, etc.
  }
  impactAnalysis: {         // Present if includeImpact is true
    severity: Enum,         // None, Minor, Moderate, Major
    affectedAreas: String[], // Code areas affected
    suggestedReviewFocus: String[] // Areas that need careful review
  }
  changedFiles: {           // Information about changed files
    path: String,           // File path
    changeType: Enum,       // Added, Modified, Deleted, Renamed
    summary: String         // Summary of changes
  }[]
  metadata: {
    executionTimeMs: Integer, // Time taken to execute the request in milliseconds
    modelsUsed: String[],   // LLMs utilized for this request
    totalCost: Number,      // Cumulated price cost for all LLM requests
    backgroundTaskProgress: {  // Information about background task progress
      status: Enum,         // NotStarted, InProgress, Complete, Error
      processedFiles: Integer, // Number of files processed so far
      totalFiles: Integer,  // Total number of files to process
      percentComplete: Integer, // Percentage of completion (0-100)
      currentActivity: String, // Description of current background activity
      estimatedCompletionTimeMs: Integer // Estimated time until completion in milliseconds
    }
  }
}
```

### Internal Tool Execution Data Model

```python
InternalToolExecution {
  toolName: String          // Name of the internal tool
  toolParameters: Object    // Parameters provided to the tool
  modelUsed: String         // LLM model used for this tool
  startTime: Timestamp      // When tool execution started
  endTime: Timestamp        // When tool execution completed
  executionTimeMs: Integer  // Execution time in milliseconds
  result: Object            // Result returned by the tool
  error: String             // Error message if execution failed
  dependencies: String[]    // Other tools this tool depends on
  cost: Number              // Cost of this specific tool execution
}
```

## Database Implementation

The Documentation-Based Programming system uses a persistent SQLite database with the following characteristics:

- **Local Persistence**: Metadata stored in a SQLite database file for persistence across application restarts
- **Change Detection**: Uses file modification timestamps and file sizes to detect changes in source files
- **Incremental Updates**: Only re-extracts metadata for changed files, improving performance
- **Efficient Representation**: Optimized schema design to minimize storage requirements
- **Fast Access Patterns**: Indexed for quick lookups and relationship traversal
- **Isolated Projects**: Complete separation between multiple projects
- **Reduced CPU Usage**: Minimizes computational overhead for large codebases
- **Faster Startup**: Significant performance improvement after initial indexing

The SQLite database schema is organized as a series of related tables:

1. **DocumentReferences**: All document references indexed by path, including metadata timestamps
2. **DocumentRelationships**: Bidirectional graph of document relationships
3. **Inconsistencies**: Active inconsistencies indexed by status
4. **Recommendations**: FIFO queue of pending recommendations
5. **DeveloperDecisions**: Record of all developer decisions
6. **FileMetadata**: Tracking data including last known file size and modification time

### Change Detection Strategy

The system implements an efficient change detection strategy:

1. On startup, compares file system metadata (modification time, file size) with stored values
2. During runtime, monitors file system events for changes
3. Only triggers metadata re-extraction when actual file content changes are detected
4. Maintains a processing queue for files that need metadata updates

### Database Migration Strategy

To support future schema changes:

1. Database includes a version table to track schema version
2. Application checks schema version on startup
3. Automatic migration process for schema updates
4. Fallback to rebuild database from scratch if migration fails
