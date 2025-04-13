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

<!-- Do not modify above this line -->

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

<!-- For AMEND option only, add comments below -->
## Amendment Requests:

[Developer feedback here]
```

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

## Database Implementation

The Documentation-Based Programming system uses a pure in-memory data store with the following characteristics:

- **No Persistence**: All data is stored in memory only
- **Efficient Representation**: Compressed data structures minimize memory usage
- **Fast Access Patterns**: Optimized for quick lookups and relationship traversal
- **Change Detection**: Direct references to file system for change detection
- **Isolated Projects**: Complete separation between multiple projects

The in-memory structure is organized as a series of indexed collections:

1. **Document Store**: All document references indexed by path
2. **Relationship Graph**: Bidirectional graph of document relationships
3. **Inconsistency Index**: Active inconsistencies indexed by status
4. **Recommendation Queue**: FIFO queue of pending recommendations
5. **Decision History**: Record of all developer decisions
