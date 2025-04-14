# LLM Coordination Architecture

This document details the architecture and data models for the LLM coordination system that powers the Documentation-Based Programming MCP server.

## Overview

The LLM coordination architecture enables efficient processing of queries by orchestrating multiple LLM instances working in parallel. This hierarchical system consists of:

1. **Coordinator LLM**: An instance of Amazon Nova Lite that manages incoming requests and orchestrates internal tools
2. **Internal Tool LLMs**: Specialized LLM instances for processing specific types of context (code, documentation, etc.)
3. **Asynchronous Job Management**: UUID-based tracking system for parallel execution of internal tools
4. **Standardized Prompt Templates**: Structured templates in `doc/llm/prompts/` that define each tool's input/output format

## Request Processing Workflow

1. **Request Ingestion**: The coordinator LLM receives an incoming MCP request
2. **Context Assembly**: Basic context is assembled including PR-FAQ.md, WORKING_BACKWARDS.md, and codebase file listings
3. **Tool Orchestration**: 
   - The coordinator LLM determines which internal tools are required
   - For each tool, it selects the appropriate prompt template from `doc/llm/prompts/`
   - It generates a unique UUID and queues a job internally for each tool
   - Multiple tools can execute in parallel across different LLM instances
4. **Result Collection**:
   - The coordinator waits for job completion notifications
   - Each internal tool reports success/error status along with execution context and results
5. **Response Formation**: Once all internal jobs complete, the coordinator formats a structured response
6. **Response Delivery**: The formatted response is sent to the MCP client

## Core Data Models

### Coordinator Request Model

```python
CoordinatorRequest {
  requestId: UUID           // Unique identifier for the request
  query: String | Object    // User query (natural language or structured)
  context: {                // Context information for processing
    projectFiles: String[], // List of all files in the project
    currentDateTime: String, // Current date and time
    businessContext: String  // Content from PR-FAQ.md and WORKING_BACKWARDS.md
  }
  parameters: Object        // Additional parameters for request processing
  maxExecutionTimeMs: Integer // Maximum execution time for the entire request
  maxCostBudget: Number     // Maximum allowed cost for the entire request
}
```

### Internal Tool Job Model

```python
InternalToolJob {
  jobId: UUID               // Unique identifier for the job
  parentRequestId: UUID     // ID of the parent coordinator request
  toolName: String          // Name of the internal tool to execute
  parameters: Object        // Parameters for the tool
  context: Object           // Context information for processing
  status: Enum              // Queued, Running, Completed, Failed, Aborted
  priority: Integer         // Job priority (higher values = higher priority)
  creationTimestamp: Timestamp // When job was created
  startTimestamp: Timestamp // When job execution started
  endTimestamp: Timestamp   // When job execution completed
  executionTimeMs: Integer  // Actual execution time in milliseconds
  maxExecutionTimeMs: Integer // Maximum allowed execution time
  costBudget: Number        // Maximum allowed cost for this job
  actualCost: Number        // Actual cost incurred by job execution
  resultSummary: String     // Brief summary of job result
  resultPayload: Object     // Complete result data
  errorDetails: {           // Present only if status is Failed or Aborted
    code: String,           // Error code
    message: String,        // Error message
    reason: Enum            // Timeout, BudgetExceeded, InternalError, LLMError
  }
  isPartialResult: Boolean  // Whether result is incomplete due to constraints
  metadata: {               // Additional metadata about execution
    modelUsed: String,      // LLM model used for this job
    tokenUsage: {           // Token usage information
      input: Integer,       // Number of input tokens
      output: Integer,      // Number of output tokens
      total: Integer        // Total token usage
    },
    fileProcessingStats: {  // Information about file processing
      filesProcessed: Integer, // Number of files processed
      totalFilesToProcess: Integer // Total number of files to process
    }
  }
}
```

### Coordinator Response Model

```python
CoordinatorResponse {
  requestId: UUID           // Matching the original request ID
  status: Enum              // Success, PartialSuccess, Failed
  results: Object           // Consolidated results from all jobs
  jobSummaries: [           // Summary of all jobs executed
    {
      jobId: UUID,          // Job ID
      toolName: String,     // Tool name
      status: Enum,         // Job status
      executionTimeMs: Integer, // Execution time
      costIncurred: Number, // Cost incurred
      isPartialResult: Boolean // Whether result is incomplete
    }
  ]
  metadata: {               // Information about the request execution
    totalExecutionTimeMs: Integer, // Total execution time
    totalCostIncurred: Number,     // Total cost incurred
    modelsUsed: String[],   // All LLM models used
    tokenUsage: {           // Aggregated token usage
      input: Integer,
      output: Integer,
      total: Integer
    }
  }
  budgetInfo: {             // Information about budget utilization
    costBudgetExceeded: Boolean, // Whether cost budget was exceeded
    timeBudgetExceeded: Boolean, // Whether time budget was exceeded
    costUtilizationPercent: Number, // Percentage of cost budget used
    timeUtilizationPercent: Number  // Percentage of time budget used
  }
  errorDetails: {           // Present only if status is Failed
    message: String,        // Error message
    failedJobs: [           // List of failed jobs
      {
        jobId: UUID,        // Job ID
        toolName: String,   // Tool name
        errorCode: String,  // Error code
        errorMessage: String // Error message
      }
    ]
  }
}
```

### Common Tool Interfaces

All internal LLM tools share common interface structures:

```python
ReadFilesRequest {
  filePaths: String[]       // List of file paths to read
}

ReadFilesResponse {
  files: [                  // List of files read
    {
      path: String,         // File path
      content: String,      // File content
      exists: Boolean,      // Whether file exists
      size: Integer,        // File size in bytes
      lastModified: Timestamp, // Last modification timestamp
      error: String         // Error message if read failed
    }
  ]
  missing: String[]         // List of files that couldn't be read
}
```

## Budget and Resource Management

To ensure responsible resource utilization:

1. **Per-Tool Cost Budgeting**:
   - Each internal tool execution has a maximum cost budget
   - When budget is reached, the LLM is instructed to conclude the task
   - Responses include "incomplete result" markers with appropriate metadata
   - Response metadata includes budget utilization information

2. **Timeout Management**:
   - Each tool execution has a maximum allowed execution time
   - Timeouts trigger graceful termination of the tool execution
   - LLM is instructed to provide partial results with timeout indication
   - Coordination ensures overall system stability despite individual timeouts

## Security Considerations

The LLM coordination architecture implements several security measures:

1. **Isolated Execution Contexts**: Each LLM instance operates in its own isolated context
2. **Input Validation**: Strict validation of inputs passed between LLM instances
3. **Rate Limiting**: Prevention of resource exhaustion through rate limits on internal tool calls
4. **Response Validation**: Validation of responses from internal LLM tools before passing to coordinator
5. **Audit Logging**: Detailed logs of all inter-LLM communications
6. **Resource Quotas**: Token usage limits for each LLM instance
7. **Error Compartmentalization**: Errors in one LLM component don't compromise the entire workflow
8. **Secure Credential Management**: Secure handling of AWS Bedrock credentials

## Relationship to Other Components

- Integrates with the dbp_general_query and dbp_commit_message MCP tools
- Leverages the SQLite database for retrieving metadata about the codebase
- Adheres to the security principles defined in SECURITY.md
- Uses standardized prompt templates from `doc/llm/prompts/` directory
- Coordinates with internal tools as detailed in [INTERNAL_LLM_TOOLS.md](INTERNAL_LLM_TOOLS.md)

## Design Decisions

- **Design Decision (2025-04-14)**: Implement an asynchronous job-based architecture for LLM tool coordination
  - **Rationale**: Enables parallel execution of multiple LLM tools, improving overall response times and making efficient use of AWS Bedrock resources
  - **Key Implications**: Requires robust job tracking, error handling, and result aggregation mechanisms

- **Design Decision (2025-04-14)**: Use cost budget constraints for each tool execution
  - **Rationale**: Prevents runaway costs while allowing for graceful degradation when budgets are reached
  - **Key Implications**: Tools must be designed to provide useful partial results when budget constraints are hit
