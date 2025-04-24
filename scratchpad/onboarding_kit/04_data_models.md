# Data Models

This document provides an overview of the core data structures used in the Documentation-Based Programming system.

## Metadata Extraction Model

The system uses Amazon Nova Lite LLM to extract the following structured metadata from code files:

```mermaid
classDiagram
    class FileMetadata {
        +String path
        +String language
        +HeaderSections headerSections
        +Function[] functions
        +Class[] classes
    }
    
    class HeaderSections {
        +String intent
        +String[] designPrinciples
        +String[] constraints
        +String[] referenceDocumentation
        +ChangeRecord[] changeHistory
    }
    
    class Function {
        +String name
        +DocSections docSections
        +String[] parameters
        +LineRange lineRange
    }
    
    class Class {
        +String name
        +DocSections docSections
        +Method[] methods
        +LineRange lineRange
    }
    
    class DocSections {
        +String intent
        +String[] designPrinciples
        +String implementationDetails
        +String designDecisions
    }
    
    class ChangeRecord {
        +String timestamp
        +String summary
        +String[] details
    }
    
    class LineRange {
        +Number start
        +Number end
    }
    
    FileMetadata --> HeaderSections
    FileMetadata "1" --> "*" Function
    FileMetadata "1" --> "*" Class
    Function --> DocSections
    Class --> DocSections
    Class "1" --> "*" Method
    HeaderSections "1" --> "*" ChangeRecord
    Function --> LineRange
    Class --> LineRange
```

Key characteristics of the metadata extraction:

- **LLM-Exclusive Processing**: Extraction performed exclusively by LLM without programmatic fallbacks
- **Language-Agnostic**: Works across programming languages without specialized parsers
- **Content-Based Identification**: Identifies sections based on semantic meaning
- **Hierarchical Structure**: Preserves relationships between files, classes, and functions

## Core Data Entities

### Document Reference

Represents any file containing documentation or code:

```mermaid
classDiagram
    class DocumentReference {
        +String path
        +Enum type
        +Timestamp lastModified
        +HeaderSections headerSections
        +DesignDecision[] designDecisions
        +DocumentReference[] dependencies
    }
    
    class HeaderSections {
        +String intent
        +String[] designPrinciples
        +String[] constraints
        +String[] referenceDocumentation
        +ChangeRecord[] changeHistory
    }
    
    class DesignDecision {
        +String id
        +Timestamp date
        +String title
        +String description
        +String rationale
        +String[] alternativesConsidered
        +String[] implications
    }
    
    DocumentReference --> HeaderSections
    DocumentReference "1" --> "*" DesignDecision
    DocumentReference "1" --> "*" DocumentReference : dependencies
```

### Document Relationship

Captures relationships between documents in a directed graph:

```mermaid
classDiagram
    class DocumentRelationship {
        +DocumentReference source
        +DocumentReference target
        +RelationType relationType
        +String topic
        +String scope
    }
    
    class RelationType {
        <<enumeration>>
        DependsOn
        Impacts
        Implements
        Extends
    }
    
    DocumentRelationship --> RelationType
```

### Inconsistency Record

Records inconsistencies detected between documentation and code:

```mermaid
classDiagram
    class InconsistencyRecord {
        +UUID id
        +Timestamp timestamp
        +Severity severity
        +InconsistencyType type
        +DocumentReference[] affectedDocuments
        +String description
        +String suggestedResolution
        +InconsistencyStatus status
    }
    
    class Severity {
        <<enumeration>>
        Critical
        Major
        Minor
    }
    
    class InconsistencyType {
        <<enumeration>>
        DocToDoc
        DocToCode
        DesignDecisionViolation
    }
    
    class InconsistencyStatus {
        <<enumeration>>
        Pending
        InRecommendation
        Resolved
    }
    
    InconsistencyRecord --> Severity
    InconsistencyRecord --> InconsistencyType
    InconsistencyRecord --> InconsistencyStatus
```

### Recommendation

Actionable suggestion generated from inconsistency records:

```mermaid
classDiagram
    class Recommendation {
        +UUID id
        +Timestamp creationTimestamp
        +String title
        +InconsistencyRecord[] inconsistencies
        +DocumentReference[] affectedDocuments
        +SuggestedChange[] suggestedChanges
        +RecommendationStatus status
        +String developerFeedback
        +Timestamp lastCodebaseChangeTimestamp
    }
    
    class SuggestedChange {
        +DocumentReference document
        +TextChange[] changes
    }
    
    class TextChange {
        +ChangeType type
        +Location location
        +String before
        +String after
    }
    
    class ChangeType {
        <<enumeration>>
        Addition
        Deletion
        Modification
    }
    
    class RecommendationStatus {
        <<enumeration>>
        Active
        Accepted
        Rejected
        Amended
        Invalidated
    }
    
    Recommendation "1" --> "*" InconsistencyRecord : inconsistencies
    Recommendation "1" --> "*" DocumentReference : affectedDocuments
    Recommendation "1" --> "*" SuggestedChange : suggestedChanges
    Recommendation --> RecommendationStatus
    SuggestedChange "1" --> "*" TextChange : changes
    TextChange --> ChangeType
```

### Developer Decision

Records developer decisions on recommendations:

```mermaid
classDiagram
    class DeveloperDecision {
        +Recommendation recommendation
        +Timestamp timestamp
        +DecisionType decision
        +String comments
        +Timestamp implementationTimestamp
    }
    
    class DecisionType {
        <<enumeration>>
        Accept
        Reject
        Amend
    }
    
    DeveloperDecision --> DecisionType
```

## File Formats

### PENDING_RECOMMENDATION.md Format

Each recommendation is stored as a Markdown file with this structure:

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

## MCP Server Data Models

### MCP Request Data Models

Core request models used by the MCP server:

```mermaid
classDiagram
    class DBPGeneralQueryRequest {
        +String|Object query
        +Enum queryType
        +Object scope
        +Enum responseFormat
        +Object context
        +Integer timeout
        +Number maxCost
    }
    
    class DBPCommitMessageRequest {
        +String sinceDiff
        +String sinceCommit
        +Boolean includeImpact
        +Enum format
        +String scope
        +Integer maxLength
        +Number maxCost
    }
    
    class MCPServerConnection {
        +String url
        +String name
        +Enum status
        +Timestamp lastConnected
        +Object capabilities
    }
```

### LLM Coordination Data Models

Models used by the LLM coordination architecture:

```mermaid
classDiagram
    class CoordinatorRequest {
        +UUID requestId
        +String|Object query
        +Object context
        +Object parameters
        +Integer maxExecutionTimeMs
        +Number maxCostBudget
    }
    
    class InternalToolJob {
        +UUID jobId
        +UUID parentRequestId
        +String toolName
        +Object parameters
        +Object context
        +Enum status
        +Integer priority
        +Timestamp creationTimestamp
        +Timestamp startTimestamp
        +Timestamp endTimestamp
        +Integer executionTimeMs
        +Integer maxExecutionTimeMs
        +Number costBudget
        +Number actualCost
        +String resultSummary
        +Object resultPayload
        +Object errorDetails
        +Boolean isPartialResult
        +Object metadata
    }
    
    class CoordinatorResponse {
        +UUID requestId
        +Enum status
        +Object results
        +Object[] jobSummaries
        +Object metadata
        +Object budgetInfo
        +Object errorDetails
    }
```

## Database Implementation

The system supports both SQLite and PostgreSQL databases:

```mermaid
classDiagram
    class DatabaseConnection {
        +connect()
        +disconnect()
        +executeQuery()
        +beginTransaction()
        +commitTransaction()
        +rollbackTransaction()
    }
    
    class SQLiteConnection {
        +String path
        +Boolean walMode
        +connect()
        +disconnect()
        +vacuum()
    }
    
    class PostgreSQLConnection {
        +String connectionString
        +Integer maxConnections
        +connect()
        +disconnect()
    }
    
    class ConnectionPool {
        +Integer poolSize
        +Boolean enablePooling
        +getConnection()
        +releaseConnection()
    }
    
    class Repository {
        +DatabaseConnection connection
        +create()
        +read()
        +update()
        +delete()
    }
    
    DatabaseConnection <|-- SQLiteConnection
    DatabaseConnection <|-- PostgreSQLConnection
    ConnectionPool "1" --> "*" DatabaseConnection
    Repository --> ConnectionPool
```

Key features of the database implementation:
- **SQLite Default**: Local SQLite database for zero-dependency operation
- **PostgreSQL Option**: Advanced deployments can use PostgreSQL
- **Write-Ahead Logging**: WAL mode for optimal concurrent access
- **Connection Pooling**: Efficient connection management
- **Alembic Migrations**: Managed schema evolution

## Change Detection Strategy

The system uses a sophisticated change detection approach:

```mermaid
classDiagram
    class ChangeDetector {
        +detectChanges()
        +compareMetadata()
        +calculateDigest()
    }
    
    class FileMetadata {
        +String path
        +Long size
        +Timestamp modificationTime
        +String contentDigest
        +isChanged()
    }
    
    class FileChange {
        +String path
        +ChangeType type
        +Timestamp detectedAt
        +FileMetadata before
        +FileMetadata after
    }
    
    class ChangeType {
        <<enumeration>>
        Created
        Modified
        Deleted
        Renamed
    }
    
    ChangeDetector --> FileMetadata
    ChangeDetector "1" --> "*" FileChange
    FileChange --> ChangeType
    FileChange --> FileMetadata
```

Key features:
1. **Multiple Indicators**: Uses modification time, file size, and content digest
2. **MD5 Digests**: Calculated for reliable change detection
3. **Cached Metadata**: Stored in database for fast comparison
4. **Efficient Processing**: Only processes actual content changes

## Memory vs. Database Trade-offs

```mermaid
graph TD
    subgraph "Memory Cache"
        inMemoryRecentAccess["Recent Access Metadata"]
        inMemoryRelationships["Relationship Graph"]
        inMemoryRules["Consistency Rules"]
    end
    
    subgraph "Database"
        dbAllMetadata["Complete Metadata"]
        dbHistory["Historical Records"]
        dbDecisions["Developer Decisions"]
    end
    
    inMemoryRecentAccess -->|"Sync"| dbAllMetadata
    inMemoryRelationships -->|"Based on"| dbAllMetadata
    dbAllMetadata -->|"Load"| inMemoryRecentAccess
    dbHistory -->|"Inform"| inMemoryRules
```

Key aspects:
1. **Memory Cache**: Frequently accessed metadata kept in memory
2. **Database Persistence**: Complete metadata stored in SQLite
3. **Lazy Loading**: Rarely accessed items loaded on demand
4. **Memory Pressure Monitoring**: Adaptive cache management
5. **Two-Tier Architecture**: Balances performance and persistence

## Security Model

```mermaid
graph TD
    subgraph "Security Layers"
        L1["Data Locality"]
        L2["Project Isolation"]
        L3["Filesystem Permissions"]
        L4["Resource Constraints"]
        L5["No Code Execution"]
        
        L1 --> L2
        L2 --> L3
        L3 --> L4
        L4 --> L5
    end
    
    subgraph "Protection Mechanisms"
        P1["SQLite WAL Mode"]
        P2["Proper Connection Management"]
        P3["Input Validation"]
        P4["Error Compartmentalization"]
        P5["Local-Only Processing"]
    end
```

Key security features:
1. **Data Locality**: All processing performed locally, nothing leaves the system
2. **Project Isolation**: Complete separation between indexed projects
3. **Filesystem Permissions**: Uses existing file access controls
4. **No Code Execution**: System never executes arbitrary code
5. **Resource Constraints**: Limited CPU and memory usage with throttling

## Next Steps

Continue to the [Development Guide](05_development_guide.md) to learn how to start working with the DBP system.
