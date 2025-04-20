# Hierarchical Semantic Tree Context - Internal Tools Module

This directory contains components for the LLM-powered internal tools system of the Document-Based Programming (DBP) framework. It provides context assemblage, execution, and response handling for specialized LLM tools used by the LLM Coordinator.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'component.py':
**Intent:** Implements the InternalToolsComponent class, conforming to the core Component protocol. This component encapsulates the specialized internal LLM tools, initializing their dependencies (context assemblers, LLM interfaces, response handlers, execution engine) and registering the tool execution functions with the LLM Coordinator's ToolRegistry.

**Design principles:**
- Conforms to the Component protocol (`src/dbp/core/component.py`).
- Declares dependency on the `llm_coordinator` component to access its ToolRegistry.
- Initializes all internal tool parts (assemblers, LLMs, handlers, engine).
- Registers the actual tool execution methods from the engine with the coordinator's registry.
- Acts as a container and initializer for the internal tools subsystem.
- Design Decision: Dedicated Component for Internal Tools (2025-04-15)
  * Rationale: Groups the implementation of all specialized tools under a single manageable component within the application framework.
  * Alternatives considered: Implementing tools directly within the coordinator (less modular).

**Constraints:**
- Depends on the core component framework and the `llm_coordinator` component.
- Requires all helper classes within the `internal_tools` package to be implemented.
- Assumes configuration for internal tools is available via InitializationContext.
- Placeholder logic exists in the execution engine and LLM interfaces.

**Change History:**
- 2025-04-20T01:49:11Z : Completed dependency injection refactoring
- 2025-04-15T10:15:55Z : Initial creation of InternalToolsComponent

### Filename 'execution_engine.py':
**Intent:** Implements the InternalToolExecutionEngine class, which is responsible for executing the specific logic of each internal LLM tool. It coordinates the context assembly, LLM invocation (using the appropriate instance), response parsing, and result formatting for each tool type.

**Design principles:**
- Provides distinct methods for executing each internal tool.
- Injects dependencies for context assemblers, LLM instances, parsers, and formatters.
- Orchestrates the step-by-step execution flow for a given tool job.
- Includes error handling for each step of the tool execution process.
- Placeholder methods return mock data until full implementation.
- Design Decision: Central Execution Engine (2025-04-15)
  * Rationale: Consolidates the execution logic for all internal tools, making it easier to manage the workflow and dependencies.
  * Alternatives considered: Implementing execution logic within each tool's definition (less organized), Direct calls from JobManager (mixes concerns).

**Constraints:**
- Requires instances of all assemblers, LLM interfaces, parsers, and formatters.
- Placeholder methods need to be replaced with actual logic involving dependency calls.
- Error handling needs to be robust to failures in any step (context, LLM, parsing, formatting).
- Needs access to configuration for LLM parameters (passed via job or config).

**Change History:**
- 2025-04-15T10:15:10Z : Initial creation of InternalToolExecutionEngine

### Filename 'context_assemblers.py':
**Intent:** Implements context assemblers for the various internal LLM tools. Each assembler is responsible for gathering the specific information (e.g., file contents, headers, changelogs) required as context for its corresponding LLM tool, using the FileAccessService.

**Design principles:**
- Abstract base class `ContextAssembler` defines the common interface.
- Each concrete assembler implements the logic for gathering context specific to one tool.
- Uses `FileAccessService` to interact with the filesystem.
- Includes basic error handling and logging.
- Placeholder logic used for complex parsing (header/changelog extraction).
- Design Decision: Separate Assembler Classes (2025-04-15)
  * Rationale: Isolates the context gathering logic for each tool, making it easier to manage and modify individual tool contexts.
  * Alternatives considered: Single assembler with conditional logic (less modular).

**Constraints:**
- Depends on `FileAccessService`.
- Placeholder logic for header/changelog extraction needs replacement with robust parsing.
- Performance depends on filesystem access speed and the number of files accessed.
- Assumes file paths and directory structures are consistent.

**Change History:**
- 2025-04-15T10:12:30Z : Initial creation of Context Assembler classes

### Filename 'file_access.py':
**Intent:** Implements the FileAccessService that provides standardized methods for accessing files and directories within the project. It abstracts the file system operations needed by the context assemblers and other components.

**Design principles:**
- Provides a simple interface for common file operations (read, list)
- Handles file system errors consistently with appropriate logging
- Uses path normalization for project-relative path handling
- Includes configuration options for path limitations and filters
- Design Decision: Dedicated File Access Service (2025-04-15)
  * Rationale: Centralizes file access logic with proper error handling and logging
  * Alternatives considered: Direct file system access in assemblers (less consistent)

**Constraints:**
- Must handle file reading errors gracefully with fallbacks
- Performance affected by file system characteristics
- Security considerations for path traversal and access limits
- Path handling must work consistently across platforms

**Change History:**
- 2025-04-16T09:45:00Z : Added file filtering capabilities
- 2025-04-15T15:36:30Z : Enhanced error handling for file access operations
- 2025-04-15T10:11:15Z : Initial implementation of FileAccessService

### Filename 'llm_interface.py':
**Intent:** Implements the interfaces to different LLM models (NovaLite and Claude) used by the internal tools. It provides a consistent way to invoke the models with appropriate parameters and prompt handling.

**Design principles:**
- Abstracts LLM-specific API details behind a common interface
- Manages authentication, rate limiting, and error handling
- Provides model-specific prompt formatting and parameter tuning
- Includes logging for monitoring and debugging
- Design Decision: Model-Specific Implementations (2025-04-15)
  * Rationale: Different models have unique API requirements and optimal settings
  * Alternatives considered: Generic interface (less optimized for each model)

**Constraints:**
- Requires API credentials for each LLM provider
- Subject to rate limits and quotas from LLM services
- Must handle various error conditions from external services
- Latency considerations for synchronous tool execution

**Change History:**
- 2025-04-16T11:23:30Z : Added temperature and sampling parameters
- 2025-04-16T09:15:00Z : Implemented retry logic for API failures
- 2025-04-15T10:13:45Z : Initial implementation of LLM interfaces

### Filename 'prompt_loader.py':
**Intent:** Implements the PromptLoader class that loads and manages prompt templates used by internal tools. It handles template loading from files, caching, and parameter replacement.

**Design principles:**
- Centralizes prompt template management in a single service
- Loads templates from configurable directories
- Implements caching to avoid redundant file operations
- Provides consistent error handling for missing templates
- Design Decision: File-based Templates (2025-04-15)
  * Rationale: Enables version control and easier editing of prompts
  * Alternatives considered: Embedded prompts in code (less flexible)

**Constraints:**
- Requires templates to follow a consistent format
- Must handle file access errors gracefully
- Caching strategy must balance memory usage and performance
- Should support template updates without application restart

**Change History:**
- 2025-04-16T14:18:00Z : Added template caching with auto-refresh
- 2025-04-15T22:04:30Z : Enhanced template parameter validation
- 2025-04-15T10:14:15Z : Initial implementation of PromptLoader

### Filename 'response_handlers.py':
**Intent:** Implements parser and formatter classes for processing LLM responses from each internal tool. Parsers extract structured data from raw LLM output, and formatters transform this data into the final format expected by clients.

**Design principles:**
- Separate classes for parsing and formatting to maintain single responsibility
- Tool-specific implementations to handle unique response structures
- Robust error handling for unexpected LLM outputs
- Consistent logging for debugging and monitoring
- Design Decision: Two-Step Processing (2025-04-15)
  * Rationale: Separates parsing logic from formatting for better maintainability
  * Alternatives considered: Combined parser-formatter classes (less flexible)

**Constraints:**
- Must handle variations and inconsistencies in LLM outputs
- Parsers should extract as much valid data as possible even from partial responses
- Formatters must adhere to strict output schemas for tool API compatibility
- Error handling should provide actionable diagnostics

**Change History:**
- 2025-04-16T16:37:00Z : Enhanced error recovery in parsers
- 2025-04-16T10:42:30Z : Added structured response validation
- 2025-04-15T10:14:45Z : Initial implementation of response handlers
