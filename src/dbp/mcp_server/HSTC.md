# Hierarchical Semantic Tree Context - MCP Server Module

This directory contains the Model Context Protocol (MCP) server implementation for the Document-Based Programming (DBP) system, which provides API access to DBP functionalities.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'adapter.py':
**Intent:** Implements the SystemComponentAdapter class, which acts as a facade or bridge between the MCP server layer (tools, resources) and the core DBP system components (consistency analysis, recommendation generator, etc.). It uses the InitializationContext to retrieve initialized component instances safely.

**Design principles:**
- Provides a single point of access to underlying system components for MCP handlers.
- Uses the InitializationContext's component registry to retrieve components by name.
- Ensures that requested components are initialized before returning them.
- Includes error handling for cases where components are missing or not ready.
- Design Decision: Adapter Facade (2025-04-15)
  * Rationale: Decouples the MCP server implementation from the specific details of how core components are structured and accessed, promoting modularity.
  * Alternatives considered: MCP tools/resources directly accessing the component registry (tighter coupling).

**Constraints:**
- Depends on the core component framework (`InitializationContext`, `Component`).
- Relies on components being correctly registered and initialized by the core framework.
- Assumes component names used for retrieval match the names used during registration.

**Change History:**
- 2025-04-16T22:55:41Z : Fixed import path for component registry
- 2025-04-15T16:42:09Z : Updated adapter to use centralized exceptions
- 2025-04-15T10:49:00Z : Initial creation of SystemComponentAdapter

### Filename 'auth.py':
**Intent:** Implements the AuthenticationProvider class for the MCP Server. This class handles the authentication of incoming MCP requests based on API keys defined in the server configuration and performs authorization checks based on the permissions associated with the authenticated client.

**Design principles:**
- Loads API keys and permissions from the MCPServerConfig.
- Provides methods to authenticate a request (based on headers) and authorize an action (based on resource and action strings).
- Uses a dictionary for efficient API key lookup.
- Implements basic wildcard permission checking (*).
- Design Decision: API Key Authentication (2025-04-15)
  * Rationale: Simple and common method for securing server-to-server APIs like MCP.
  * Alternatives considered: OAuth (more complex), No auth (insecure).
- Design Decision: String-Based Permissions (2025-04-15)
  * Rationale: Flexible way to define access control (e.g., "tool:analyze", "resource:*").
  * Alternatives considered: Role-based access (could be built on top).

**Constraints:**
- Depends on `MCPServerConfig` and `APIKeyEntry` from `config_schema.py`.
- Depends on `MCPRequest` from `data_models.py`.
- Security relies on keeping API keys confidential.
- Assumes API keys are passed in a specific header (`X-API-Key`).
- Permission matching logic is basic (exact match or wildcard).

**Change History:**
- 2025-04-15T16:40:59Z : Updated auth to use centralized exceptions
- 2025-04-15T10:49:30Z : Initial creation of AuthenticationProvider

### Filename 'component.py':
**Intent:** Implements the MCPServerComponent class, the main entry point for the MCP server integration within the DBP application framework. It conforms to the Component protocol, initializes the MCP server and its dependencies (adapter, auth, registries, handlers), registers tools and resources, and manages the server's lifecycle (start/stop).

**Design principles:**
- Conforms to the Component protocol (`src/dbp/core/component.py`).
- Encapsulates the entire MCP server logic.
- Declares dependencies on core DBP components needed by its tools/resources.
- Initializes and wires together internal MCP server parts in `initialize`.
- Registers concrete MCP tools and resources.
- Provides methods to start and stop the actual server process.
- Design Decision: Component Facade for MCP Server (2025-04-15)
  * Rationale: Integrates the MCP server functionality cleanly into the application's component lifecycle.
  * Alternatives considered: Running the MCP server as a separate process (harder integration).

**Constraints:**
- Depends on the core component framework and various DBP system components.
- Requires all helper classes within the `mcp_server` package.
- Assumes configuration for the MCP server is available via InitializationContext.
- Relies on placeholder implementations for the actual web server and tool/resource logic.

**Change History:**
- 2025-04-20T01:35:42Z : Completed dependency injection refactoring
- 2025-04-20T00:31:26Z : Added dependency injection support
- 2025-04-17T23:39:00Z : Updated to use strongly-typed configuration
- 2025-04-17T11:54:21Z : Added directory creation for required paths

### Filename 'data_models.py':
**Intent:** Defines the core data structures (using dataclasses) for the Model Context Protocol (MCP) server integration. This includes representations for MCP requests, responses, and error objects, aligning with MCP specifications.

**Design principles:**
- Uses standard Python dataclasses for data representation.
- Defines structures closely matching the expected MCP message formats.
- Includes type hints for clarity.
- Provides a clear structure for handling errors within the MCP framework.

**Constraints:**
- Requires Python 3.7+ for dataclasses.
- Assumes adherence to the basic principles of the Model Context Protocol.

**Change History:**
- 2025-04-15T22:56:00Z : Fixed Pydantic v2 compatibility issues
- 2025-04-15T19:32:00Z : Added FastAPI Pydantic models for request/response validation
- 2025-04-15T10:48:30Z : Initial creation of MCP data models

### Filename 'error_handler.py':
**Intent:** Implements the ErrorHandler class for the MCP Server. This class catches exceptions raised during request processing (authentication, authorization, tool execution, resource access) and translates them into standardized MCPError objects suitable for inclusion in an MCPResponse.

**Design principles:**
- Centralizes error handling logic for MCP requests.
- Maps specific Python exceptions (e.g., ComponentNotFoundError, Auth errors) to predefined MCP error codes and messages.
- Provides a default handler for unexpected exceptions.
- Logs errors appropriately.
- Design Decision: Centralized Error Handler (2025-04-15)
  * Rationale: Ensures consistent error reporting format across all MCP tools and resources. Simplifies error handling in individual tool/resource implementations.
  * Alternatives considered: Handling errors within each tool/resource (inconsistent, boilerplate).

**Constraints:**
- Depends on `MCPError` and `MCPRequest` data models.
- Depends on custom exception types defined elsewhere (e.g., `ComponentNotFoundError`, `AuthenticationError`).
- The mapping between Python exceptions and MCP error codes needs to be maintained.

**Change History:**
- 2025-04-15T16:36:30Z : Updated error handler to use centralized exceptions
- 2025-04-15T10:50:15Z : Initial creation of ErrorHandler class

### Filename 'exceptions.py':
**Intent:** Defines all exception classes used throughout the MCP server implementation. Centralizes exception definitions to avoid circular imports and ensure a consistent error handling approach across the MCP server codebase.

**Design principles:**
- Defines custom exceptions for the MCP server component.
- Uses descriptive class names that indicate the error type.
- Includes docstrings for all exceptions with clear error descriptions.
- Inherits appropriately from standard exception types.
- Allows for additional context in exception instances via attributes.

**Constraints:**
- Must only use standard library imports to avoid circular dependencies.
- Must be importable by all other MCP server modules.

**Change History:**
- 2025-04-15T16:31:15Z : Created exceptions.py file

### Filename 'mcp_protocols.py':
**Intent:** Defines the abstract base classes (ABCs) for Model Context Protocol (MCP) tools and resources. These classes establish the required interface that all concrete tools and resources exposed by the DBP MCP server must implement.

**Design principles:**
- Uses `abc.ABC` and `abc.abstractmethod` to define clear interfaces.
- `MCPTool` defines the structure for executable actions, including input/output schemas.
- `MCPResource` defines the structure for accessing data sources via URIs.
- Provides a consistent foundation for building MCP capabilities.
- Design Decision: Abstract Base Classes (2025-04-15)
  * Rationale: Enforces a standard contract for all tools and resources, ensuring they integrate correctly with the MCP server framework.
  * Alternatives considered: Protocol classes (less explicit inheritance), Duck typing (no formal contract).

**Constraints:**
- Concrete implementations must inherit from these base classes and implement abstract methods.
- Input/output schemas should ideally follow JSON Schema standards.

**Change History:**
- 2025-04-15T10:51:20Z : Initial creation of MCP protocol base classes

### Filename '__main__.py':
**Intent:** Entry point for running the MCP server module directly. Parses command-line arguments, sets up logging, initializes components, and starts the server. This file is executed when the module is run with python -m dbp.mcp_server.

**Design principles:**
- Provides a clean entry point for the MCP server.
- Processes command-line arguments for server configuration.
- Sets up proper logging with configurable verbosity.
- Initializes the server component and handles lifecycle.
- Implements comprehensive error handling and detailed reporting.
- Acts as a bridge between CLI and the actual MCP server implementation.

**Constraints:**
- Must work with the existing server implementation and component model.
- Logging must be properly configured before server initialization.
- Error handling must be detailed enough to diagnose startup issues.
- Exit codes must be meaningful for the calling process.

**Change History:**
- 2025-04-20T19:23:00Z : Fixed watchdog deadlock detection
- 2025-04-20T10:53:00Z : Moved watchdog implementation to dedicated core module
- 2025-04-20T03:52:00Z : Fixed startup timeout parameter to use configuration values
- 2025-04-20T03:48:00Z : Updated argument parser to use ConfigurationManager

### Filename 'registry.py':
**Intent:** Implements the ToolRegistry and ResourceProvider classes for the MCP Server. These registries manage the collection of tools and resources that the DBP MCP server exposes to clients, allowing for dynamic registration and lookup.

**Design principles:**
- Provides separate, thread-safe registries for MCP tools and resources.
- Uses dictionaries for efficient lookup by name (for tools) or URI prefix (for resources).
- Allows registration of tool/resource handler instances.
- Provides methods for retrieving handlers based on request targets.
- Design Decision: Separate Registries for Tools/Resources (2025-04-15)
  * Rationale: Clear separation between executable actions (tools) and data access points (resources) as per MCP concepts.
  * Alternatives considered: Single combined registry (less clear distinction).

**Constraints:**
- Depends on base classes/interfaces for `MCPTool` and `MCPResource`.
- Assumes tool names and resource URI prefixes are unique within their respective registries.
- Thread safety ensured by RLock.

**Change History:**
- 2025-04-15T10:50:45Z : Initial creation of MCP ToolRegistry and ResourceProvider

### Filename 'resources.py':
**Intent:** Implements concrete MCPResource classes that expose DBP system data via the Model Context Protocol. Each resource class handles requests for specific data URIs (e.g., documentation, code metadata, inconsistencies) by interacting with the core DBP components through the SystemComponentAdapter.

**Design principles:**
- Each class inherits from `MCPResource`.
- Each class defines logic within its `get` method to retrieve and format data.
- Uses `SystemComponentAdapter` to access underlying DBP functionality and data.
- Handles `resource_id` and `params` to filter or specify the requested data.
- Includes basic error handling.
- Placeholder logic used for complex data retrieval and formatting.

**Constraints:**
- Depends on `mcp_protocols.py` for `MCPResource` base class.
- Depends on `adapter.py` for `SystemComponentAdapter`.
- Depends on various core DBP components and data models.
- Placeholder `get` methods need to be replaced with actual data retrieval logic.

**Change History:**
- 2025-04-15T16:39:48Z : Updated resources to use centralized exceptions
- 2025-04-15T10:53:00Z : Initial creation of MCP resource classes

### Filename 'server.py':
**Intent:** Implements the main MCPServer class, responsible for running the actual server process using FastAPI/Uvicorn. It receives MCP requests, routes them to registered tools or resources, handles authentication/authorization via providers, formats responses, and manages the server lifecycle (start/stop).

**Design principles:**
- Acts as the entry point for MCP communication.
- Integrates with FastAPI and Uvicorn to handle HTTP requests.
- Parses incoming requests into MCPRequest objects.
- Uses ToolRegistry and ResourceProvider to find handlers for requests.
- Uses AuthenticationProvider and ErrorHandler for request processing middleware.
- Formats results or errors into MCPResponse objects.
- Manages the server's running state.
- Design Decision: Placeholder Web Framework (2025-04-15)
  * Rationale: Focuses on the MCP logic rather than specific web framework details. A concrete implementation would replace placeholders with FastAPI/Flask/etc. routes and handlers.
  * Alternatives considered: Implementing full FastAPI/Flask server (adds significant complexity and dependencies).

**Constraints:**
- Requires concrete implementations of MCPTool, MCPResource, AuthenticationProvider, ErrorHandler, ToolRegistry, ResourceProvider.
- Placeholder server logic needs replacement with a real web framework implementation (e.g., FastAPI, Uvicorn).
- Threading model for handling requests depends on the chosen web framework.

**Change History:**
- 2025-04-15T21:37:00Z : Implemented FastAPI/Uvicorn integration
- 2025-04-15T16:35:58Z : Updated server to use centralized exceptions

### Filename 'tools.py':
**Intent:** Implements concrete MCPTool classes that expose the DBP system's functionality via the Model Context Protocol. Each tool class defines its input/output schema and implements the execution logic by interacting with the core DBP components through the SystemComponentAdapter.

**Design principles:**
- Each class inherits from `MCPTool`.
- Each class defines specific input and output JSON schemas.
- `execute` methods contain the logic to handle tool invocation.
- Uses `SystemComponentAdapter` to access underlying DBP functionality.
- Includes basic input validation and error handling.
- Supports asynchronous execution where appropriate by interacting with a JobManager (via adapter).
- Placeholder logic used for complex interactions.

**Constraints:**
- Depends on `mcp_protocols.py` for `MCPTool` base class.
- Depends on `adapter.py` for `SystemComponentAdapter`.
- Depends on various core DBP components and data models (e.g., ConsistencyAnalysisComponent, Recommendation).
- Input/output schemas must be kept consistent with tool functionality.
- Placeholder execution logic needs to be replaced with actual component interactions.

**Change History:**
- 2025-04-16T14:33:45Z : Renamed GenerateRecommendationsTool to CommitMessageTool
- 2025-04-16T14:17:04Z : Added AnalyzeDocumentConsistencyTool class
- 2025-04-16T10:50:00Z : Removed all manual classification code
- 2025-04-16T10:47:00Z : Enforced LLM coordinator processing for all queries
