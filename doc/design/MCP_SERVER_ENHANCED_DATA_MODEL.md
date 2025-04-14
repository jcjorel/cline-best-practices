# MCP Server Enhanced Data Model

This document provides detailed data models for the MCP server tools with enhanced features for budget management, partial results, and standardized input/output validation.

## Overview

The MCP server exposes tools to clients that leverage the LLM coordination architecture described in [LLM_COORDINATION.md](LLM_COORDINATION.md). This document focuses on the specific data models for the MCP-exposed tools, including their enhanced features for resource management and validation.

These MCP-exposed tools utilize the internal LLM tools detailed in [INTERNAL_LLM_TOOLS.md](INTERNAL_LLM_TOOLS.md), which in turn use the standardized prompt templates defined in the `doc/llm/prompts/` directory. While this document focuses on the interface between clients and the MCP server, the actual processing leverages the complete LLM coordination architecture.

## MCP-Exposed Tool Data Models

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
  maxCost: Number           // Maximum allowed cost for query execution
}

DBPGeneralQueryResponse {
  results: Object           // Query results (format depends on request)
  metadata: {               // Information about the query execution
    executionTimeMs: Integer, // Time taken to execute the query in milliseconds
    modelsUsed: String[],   // LLMs utilized for this query
    filesProcessed: Integer, // Number of files processed
    tools: {                // Tools used to fulfill the query
      name: String,         // Tool name
      executionTimeMs: Integer, // Time taken by this tool in milliseconds
      isPartialResult: Boolean, // Whether result is incomplete due to constraints
      budgetExceeded: Boolean   // Whether budget was exceeded for this tool
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
  maxCost: Number           // Maximum allowed cost for generation
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
    isPartialResult: Boolean, // Whether result is incomplete due to constraints
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

## Input and Response Validation

The MCP server implements standardized input and response validation for all exposed tools:

### Input Validation

1. **Schema Validation**: All requests are validated against JSON schemas that define required fields, data types, and value constraints
2. **Content Type Validation**: Ensures all request fields contain appropriate data types
3. **Size Limit Validation**: Enforces limits on request size to prevent resource exhaustion
4. **Scope Validation**: Validates that requested file paths are within allowed project boundaries
5. **Budget Validation**: Ensures requested cost budgets are within allowed ranges

### Response Validation

1. **Schema Validation**: All responses are validated against JSON schemas before being returned to clients
2. **Sanitization**: Responses are sanitized to remove any sensitive information
3. **Size Limit Enforcement**: Responses exceeding size limits are truncated with appropriate indicators
4. **Error Standardization**: All errors follow a consistent format with appropriate error codes
5. **Budget Reporting**: All responses include accurate budget utilization information

### Implementation Status

Currently, the input and response validation components are implemented as placeholders that will be expanded in future development:

1. **Request Validation**: Basic structure validation is in place
2. **Response Validation**: Basic structure validation is in place
3. **Error Handling**: Standard error codes and messages are defined
4. **Future Work**: Enhanced validation with more comprehensive rule sets is planned

## Budget Management

The MCP server implements budget management for all exposed tools:

### Cost Tracking

1. **Per-Request Budgets**: Each request can specify a maximum cost budget
2. **Default Budgets**: System-wide default budgets are applied if not specified
3. **Actual Cost Tracking**: Costs are tracked in real-time during request processing
4. **Budget Enforcement**: Requests exceeding their budget are gracefully terminated

### Partial Results

When a request exceeds its budget or timeout:

1. **Result Marking**: Responses include `isPartialResult: true` in metadata
2. **Completion Status**: Individual tool results include completion status indicators
3. **Missing Information**: Response includes information about what could not be completed
4. **Suggestion Handling**: Suggestions for handling incomplete results are provided

## Security Considerations

The enhanced data model includes several security features:

1. **Resource Limits**: Explicit budget and timeout parameters prevent resource exhaustion attacks
2. **Content Validation**: All inputs and outputs are validated to prevent injection attacks
3. **Error Compartmentalization**: Errors in one component do not affect others
4. **Safe Default Values**: All optional parameters have safe default values

## Design Decisions

- **Design Decision (2025-04-14)**: Add explicit budget parameters to all MCP tool requests
  - **Rationale**: Enables clients to control costs and prevents runaway API usage
  - **Key Implications**: All tools must support graceful termination and partial results

- **Design Decision (2025-04-14)**: Implement standardized input and response validation
  - **Rationale**: Improves security and provides consistent error handling
  - **Key Implications**: All tools must conform to validation schemas and handle validation errors gracefully
