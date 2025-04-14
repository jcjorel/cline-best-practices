# Internal LLM Tools

This document details the internal LLM tools used by the Documentation-Based Programming MCP server. These specialized tools are orchestrated by the coordinator LLM to process specific types of queries and extract relevant information from the codebase.

## Overview

The Documentation-Based Programming system uses a set of specialized internal LLM tools, each designed to process a specific type of context. These tools are not directly exposed to MCP clients but are invoked by the coordinator LLM based on the nature of incoming requests.

## Internal Tool Architecture

Each internal tool follows a common pattern:

1. **Context Preparation**: A helper function assembles the appropriate context based on the tool's purpose
2. **LLM Invocation**: An instance of the appropriate LLM model is invoked with the prepared context
3. **Result Processing**: The LLM's response is parsed and transformed into the required format
4. **Result Delivery**: The processed result is returned to the coordinator LLM

## Internal Tool Components

### 1. coordinator_get_codebase_context

**Purpose**: Extract relevant file header information based on query context

**Implementation Details**:
- **LLM Model**: Dedicated Amazon Nova Lite instance
- **Context Construction**: 
  - File headers focusing on "[Source file intent]" and "[Reference documentation]" sections
  - Automatically includes statistics on header compliance, file counts, and organization
- **Helper Function Behavior**:
  - Extracts headers from all codebase files
  - Computes metadata about header compliance
  - Filters relevant file headers based on query
- **Typical Queries**:
  - "What files are involved in implementing feature X?"
  - "Where should I implement this new feature?"
  - "How is the codebase organized?"
- **Response Format**: Structured analysis of relevant files with metadata

### 2. coordinator_get_codebase_changelog_context

**Purpose**: Analyze historical code changes across the codebase

**Implementation Details**:
- **LLM Model**: Dedicated Amazon Nova Lite instance
- **Context Construction**: 
  - All "[GenAI tool change history]" sections from file headers
- **Helper Function Behavior**:
  - Automatically adds all change entries to the tool context
  - Sorts entries from newest to oldest
  - Preserves changelog file location with each entry
- **Typical Queries**:
  - "What were the latest codebase changes?"
  - "What parts of the codebase have been most active recently?"
- **Response Format**: Temporal analysis of code changes with relevance rankings

### 3. coordinator_get_documentation_context

**Purpose**: Answer questions about project documentation

**Implementation Details**:
- **LLM Model**: Dedicated Amazon Nova Lite instance
- **Context Construction**: 
  - Content of all documentation markdown files (excluding MARKDOWN_CHANGELOG.md)
- **Helper Function Behavior**:
  - Automatically inserts DOCUMENT_RELATIONSHIPS.md content for document relationship analysis
  - The LLM analyzes this content to discover document relationships
- **Typical Queries**:
  - "If I implement feature X, what document files will be impacted?"
  - "Where is SQL table Y described?"
  - "Generate a dependency graph of documentation files"
  - "Are there inconsistencies in the documentation?"
- **Response Format**: Documentation analysis with reference links

### 4. coordinator_get_documentation_changelog_context

**Purpose**: Analyze historical documentation changes

**Implementation Details**:
- **LLM Model**: Dedicated Amazon Nova Lite instance
- **Context Construction**: 
  - All MARKDOWN_CHANGELOG.md file contents
- **Helper Function Behavior**:
  - Aggregates all changelog entries
  - Sorts entries chronologically
- **Typical Queries**:
  - "What documentation was recently updated?"
  - "What documentation changes relate to feature X?"
- **Response Format**: Temporal analysis of documentation changes

### 5. coordinator_get_expert_architect_advice

**Purpose**: Provide advanced architectural reasoning and guidance

**Implementation Details**:
- **LLM Model**: Anthropic Claude 3.7 Sonnet with 10,000 token context
- **Context Construction**: 
  - All sections from all available file headers
- **Helper Function Behavior**:
  - Constructs comprehensive context from all file headers
  - Enables the read_files tool for additional context retrieval
- **Typical Queries**:
  - "What's the best approach to implement feature X?"
  - "How should we modify the architecture to support requirement Y?"
- **Response Format**: Detailed architectural analysis with rationale

## Common Internal Tool: read_files

All LLM instances have access to a common internal tool:

**Purpose**: Read file contents from the codebase

**Implementation Details**:
- **Operation**: Synchronous
- **Parameters**: 
  - List of files to read
- **Returns**: 
  - JSON with file metadata and content
- **Usage**: 
  - Allows LLMs to dynamically retrieve additional context

## Tool Context Models

### Codebase Context Model

```python
CodebaseContextRequest {
  query: String             // Query about codebase organization
  fileHeaders: [            // List of file headers
    {
      path: String,         // File path
      intent: String,       // Source file intent
      referenceDocumentation: String[] // Referenced documentation
    }
  ]
  fileStats: {              // Statistics about the codebase
    totalFiles: Integer,    // Total number of files
    compliantFiles: Integer, // Files with proper headers
    incompleteHeaderFiles: Integer, // Files with incomplete headers
    missingHeaderFiles: Integer, // Files without headers
    missingHeaderFilesList: String[] // Paths of files without headers
  }
}
```

### Documentation Context Model

```python
DocumentationContextRequest {
  query: String             // Query about documentation
  documentationFiles: [     // List of documentation files
    {
      path: String,         // File path
      content: String,      // File content
      lastModified: Timestamp // Last modification time
    }
  ]
  // Note: The DOCUMENT_RELATIONSHIPS.md content is automatically inserted by the tool helper function
  // Document relationships are discovered by the LLM analyzing this content
}
```

### Expert Architect Context Model

```python
ExpertContextRequest {
  query: String             // Query for architectural advice
  fileHeaders: [            // Complete file headers
    {
      path: String,         // File path
      headerSections: {     // All header sections
        intent: String,
        designPrinciples: String[],
        constraints: String[],
        referenceDocumentation: String[],
        changeHistory: Object[]
      }
    }
  ]
}
```

## Tool Helper Functions

Each internal tool has a dedicated helper function that prepares the appropriate context for the LLM. These helper functions implement specialized logic:

1. **Filtering and Relevance Scoring**: Some helpers filter content to include only what's relevant to the query
2. **Content Transformation**: Some helpers transform content into more easily digestible formats
3. **Automatic Content Inclusion**: Some helpers automatically include content from specific files (like DOCUMENT_RELATIONSHIPS.md)
4. **Metadata Generation**: Some helpers generate metadata about the codebase to provide additional context
5. **Sorting and Ordering**: Some helpers sort content in specific ways (e.g., newest to oldest)

## Integration with LLM Coordination

The internal tools are integrated with the LLM coordination architecture described in [LLM_COORDINATION.md](LLM_COORDINATION.md):

1. The coordinator LLM determines which internal tools to invoke based on the incoming query
2. For each tool, it creates a job with a unique ID and appropriate parameters
3. The job is executed, invoking the internal tool with the prepared context
4. The tool's result is returned to the coordinator for integration into the final response
5. If the tool execution exceeds cost budget or time limits, it returns a partial result

## Design Decisions

- **Design Decision (2025-04-14)**: Use specialized internal tools for different context types
  - **Rationale**: Enables more efficient processing by focusing each LLM instance on a specific type of context
  - **Key Implications**: Requires effective coordination to combine results from multiple tools

- **Design Decision (2025-04-14)**: Use helper functions for context preparation
  - **Rationale**: Separates context preparation logic from LLM invocation, making the system more maintainable
  - **Key Implications**: Helper functions can be individually optimized and tested
