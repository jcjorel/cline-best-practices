# MCP Server Integration Implementation Plan

## Overview

This document outlines the implementation plan for the MCP Server Integration component, which exposes the Documentation-Based Programming system's capabilities through the Model Context Protocol (MCP), allowing external clients to interact with the system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - External API Integration section
- [design/MCP_SERVER_ENHANCED_DATA_MODEL.md](../../doc/design/MCP_SERVER_ENHANCED_DATA_MODEL.md) - MCP-specific data models
- [API.md](../../doc/API.md) - API specifications

## Requirements

The MCP Server Integration component must:
1. Implement an MCP server that exposes the system's capabilities
2. Define MCP tools for document analysis and code-documentation consistency checks
3. Define MCP resources for accessing documentation and code metadata
4. Handle authentication and authorization for MCP clients
5. Provide proper error handling and reporting
6. Support both synchronous and asynchronous operations
7. Integrate with the existing component system
8. Include proper logging and monitoring
9. Support scalable deployment options

## Design

### MCP Server Architecture

The MCP Server Integration follows a layered architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  MCP Server         │─────▶│  Tool               │─────▶│  System             │
│    Component        │      │    Registry         │      │    Component        │
│                     │      │                     │      │    Adapter          │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Authentication     │
                               ┌─────────────────────┐    │    Provider         │
                               │                     │    │                     │
                               │  Resource           │    └─────────────────────┘
                               │    Provider         │               │
                               │                     │               │
                               └─────────────────────┘               ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Error              │
                               ┌─────────────────────┐    │    Handler          │
                               │                     │    │                     │
                               │  MCP Server         │    └─────────────────────┘
                               │    Configuration    │
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **MCPServerComponent**

```python
class MCPServerComponent(Component):
    """Component for MCP server integration."""
    
    @property
    def name(self) -> str:
        return "mcp_server"
    
    @property
    def dependencies(self) -> list[str]:
        return [
            "consistency_analysis", 
            "recommendation_generator", 
            "doc_relationships",
            "llm_coordinator"
        ]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the MCP server component."""
        self.config = context.config.mcp_server
        self.logger = context.logger.get_child("mcp_server")
        
        # Get system components
        self.consistency_component = context.get_component("consistency_analysis")
        self.recommendation_component = context.get_component("recommendation_generator")
        self.doc_relationships_component = context.get_component("doc_relationships")
        self.llm_coordinator_component = context.get_component("llm_coordinator")
        
        # Create MCP subcomponents
        self.system_component_adapter = SystemComponentAdapter(context, self.logger)
        self.authentication_provider = AuthenticationProvider(self.config, self.logger)
        self.error_handler = ErrorHandler(self.logger)
        self.tool_registry = ToolRegistry(self.system_component_adapter, self.logger)
        self.resource_provider = ResourceProvider(self.system_component_adapter, self.logger)
        self.server_configuration = MCPServerConfiguration(self.config, self.logger)
        
        # Create and set up MCP server
        self.server = self._create_mcp_server()
        
        # Register tools and resources
        self._register_tools()
        self._register_resources()
        
        self._initialized = True
    
    def _create_mcp_server(self) -> MCPServer:
        """Create an MCP server instance."""
        server = MCPServer(
            host=self.config.host,
            port=self.config.port,
            name=self.config.server_name,
            description=self.config.server_description,
            version=self.config.server_version,
            logger=self.logger
        )
        
        # Set up authentication
        if self.config.auth_enabled:
            server.set_auth_provider(self.authentication_provider)
        
        # Set up error handler
        server.set_error_handler(self.error_handler)
        
        return server
    
    def _register_tools(self) -> None:
        """Register MCP tools."""
        # Consistency Analysis Tools
        self.tool_registry.register_tool(
            AnalyzeDocumentConsistencyTool(
                self.consistency_component, 
                self.system_component_adapter.job_manager,
                self.logger
            )
        )
        
        self.tool_registry.register_tool(
            GenerateRecommendationsTool(
                self.recommendation_component, 
                self.system_component_adapter.job_manager,
                self.logger
            )
        )
        
        self.tool_registry.register_tool(
            ApplyRecommendationTool(
                self.recommendation_component,
                self.logger
            )
        )
        
        # Document Relationship Tools
        self.tool_registry.register_tool(
            AnalyzeDocumentRelationshipsTool(
                self.doc_relationships_component,
                self.logger
            )
        )
        
        self.tool_registry.register_tool(
            GenerateMermaidDiagramTool(
                self.doc_relationships_component,
                self.logger
            )
        )
        
        # LLM Coordination Tools
        self.tool_registry.register_tool(
            ExtractDocumentContextTool(
                self.llm_coordinator_component,
                self.system_component_adapter.job_manager,
                self.logger
            )
        )
        
        self.tool_registry.register_tool(
            ExtractCodebaseContextTool(
                self.llm_coordinator_component,
                self.system_component_adapter.job_manager,
                self.logger
            )
        )
        
        # Register all tools with the MCP server
        for tool in self.tool_registry.get_all_tools():
            self.server.register_tool(tool.name, tool)
    
    def _register_resources(self) -> None:
        """Register MCP resources."""
        # Documentation Resources
        self.resource_provider.register_resource(
            DocumentationResource(
                self.doc_relationships_component,
                self.logger
            )
        )
        
        # Code Metadata Resources
        self.resource_provider.register_resource(
            CodeMetadataResource(
                self.system_component_adapter.metadata_provider,
                self.logger
            )
        )
        
        # Inconsistency Resources
        self.resource_provider.register_resource(
            InconsistencyResource(
                self.consistency_component,
                self.logger
            )
        )
        
        # Recommendation Resources
        self.resource_provider.register_resource(
            RecommendationResource(
                self.recommendation_component,
                self.logger
            )
        )
        
        # Register all resources with the MCP server
        for resource in self.resource_provider.get_all_resources():
            self.server.register_resource(resource.name, resource)
    
    def start_server(self) -> None:
        """Start the MCP server."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.logger.info(f"Starting MCP server on {self.config.host}:{self.config.port}")
        self.server.start()
    
    def stop_server(self) -> None:
        """Stop the MCP server."""
        if not self._initialized:
            return
        
        self.logger.info("Stopping MCP server")
        self.server.stop()
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.stop_server()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
```

2. **ToolRegistry**

```python
class ToolRegistry:
    """Registry for MCP tools."""
    
    def __init__(self, system_component_adapter: SystemComponentAdapter, logger: Logger):
        self.system_component_adapter = system_component_adapter
        self.logger = logger
        self._tools = {}  # type: Dict[str, MCPTool]
    
    def register_tool(self, tool: MCPTool) -> None:
        """
        Register an MCP tool.
        
        Args:
            tool: MCP tool to register
        """
        self.logger.info(f"Registering tool: {tool.name}")
        self._tools[tool.name] = tool
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """
        Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool or None if not found
        """
        return self._tools.get(name)
    
    def get_all_tools(self) -> List[MCPTool]:
        """
        Get all registered tools.
        
        Returns:
            List of tools
        """
        return list(self._tools.values())
```

3. **ResourceProvider**

```python
class ResourceProvider:
    """Provider for MCP resources."""
    
    def __init__(self, system_component_adapter: SystemComponentAdapter, logger: Logger):
        self.system_component_adapter = system_component_adapter
        self.logger = logger
        self._resources = {}  # type: Dict[str, MCPResource]
    
    def register_resource(self, resource: MCPResource) -> None:
        """
        Register an MCP resource.
        
        Args:
            resource: MCP resource to register
        """
        self.logger.info(f"Registering resource: {resource.name}")
        self._resources[resource.name] = resource
    
    def get_resource(self, name: str) -> Optional[MCPResource]:
        """
        Get a resource by name.
        
        Args:
            name: Resource name
            
        Returns:
            Resource or None if not found
        """
        return self._resources.get(name)
    
    def get_all_resources(self) -> List[MCPResource]:
        """
        Get all registered resources.
        
        Returns:
            List of resources
        """
        return list(self._resources.values())
```

4. **SystemComponentAdapter**

```python
class SystemComponentAdapter:
    """Adapter for system components."""
    
    def __init__(self, context: InitializationContext, logger: Logger):
        self.context = context
        self.logger = logger
        
        # Set up job manager for async operations
        self.job_manager = context.get_component("job_management")
        
        # Set up metadata provider
        self.metadata_provider = context.get_component("metadata_extraction")
    
    def get_component(self, name: str) -> Component:
        """
        Get a system component by name.
        
        Args:
            name: Component name
            
        Returns:
            Component
            
        Raises:
            ComponentNotFoundError: If component not found
        """
        component = self.context.get_component(name)
        
        if not component:
            raise ComponentNotFoundError(f"Component not found: {name}")
        
        return component
    
    def submit_async_job(self, spec: JobSpecification) -> str:
        """
        Submit an asynchronous job.
        
        Args:
            spec: Job specification
            
        Returns:
            Job ID
        """
        return self.job_manager.submit_job(spec)
    
    def get_job_status(self, job_id: str) -> JobStatus:
        """
        Get job status.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job status
        """
        return self.job_manager.get_job_status(job_id)
    
    def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """
        Get job result.
        
        Args:
            job_id: Job ID
            
        Returns:
            Job result or None if not completed
        """
        return self.job_manager.get_job_result(job_id)
```

5. **AuthenticationProvider**

```python
class AuthenticationProvider:
    """Provider for authentication services."""
    
    def __init__(self, config: MCPServerConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._api_keys = {}  # type: Dict[str, Dict[str, str]]
        
        # Load API keys
        self._load_api_keys()
    
    def _load_api_keys(self) -> None:
        """Load API keys from configuration."""
        for key_entry in self.config.api_keys:
            self._api_keys[key_entry.key] = {
                "client_id": key_entry.client_id,
                "permissions": key_entry.permissions
            }
        
        self.logger.info(f"Loaded {len(self._api_keys)} API keys")
    
    def authenticate(self, request: MCPRequest) -> Optional[Dict[str, Any]]:
        """
        Authenticate a request.
        
        Args:
            request: MCP request
            
        Returns:
            Authentication context or None if authentication failed
        """
        # Extract API key from request headers
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            self.logger.warning("Authentication failed: No API key provided")
            return None
        
        # Lookup API key
        key_info = self._api_keys.get(api_key)
        
        if not key_info:
            self.logger.warning("Authentication failed: Invalid API key")
            return None
        
        # Return authentication context
        return {
            "client_id": key_info["client_id"],
            "permissions": key_info["permissions"]
        }
    
    def authorize(self, auth_context: Dict[str, Any], resource: str, action: str) -> bool:
        """
        Authorize a request.
        
        Args:
            auth_context: Authentication context
            resource: Resource to access
            action: Action to perform
            
        Returns:
            True if authorized, False otherwise
        """
        if not auth_context:
            return False
        
        # Get permissions
        permissions = auth_context.get("permissions", [])
        
        # Check if client has permission for the requested resource and action
        permission = f"{resource}:{action}"
        wildcard_permission = f"{resource}:*"
        global_permission = "*:*"
        
        if permission in permissions or wildcard_permission in permissions or global_permission in permissions:
            return True
        
        self.logger.warning(f"Authorization failed: {auth_context['client_id']} does not have permission {permission}")
        return False
```

6. **ErrorHandler**

```python
class ErrorHandler:
    """Handler for MCP errors."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
    
    def handle_error(self, error: Exception, request: Optional[MCPRequest] = None) -> MCPError:
        """
        Handle an MCP error.
        
        Args:
            error: Exception that occurred
            request: Original MCP request
            
        Returns:
            MCP error response
        """
        error_type = type(error).__name__
        
        # Log the error
        if request:
            self.logger.error(f"MCP error ({error_type}) for request {request.id}: {error}")
        else:
            self.logger.error(f"MCP error ({error_type}): {error}")
        
        # Map exception types to error codes
        if isinstance(error, ComponentNotFoundError):
            return MCPError(
                code="COMPONENT_NOT_FOUND",
                message=str(error),
                data={"component_name": error.component_name} if hasattr(error, "component_name") else None
            )
        
        if isinstance(error, AuthenticationError):
            return MCPError(
                code="AUTHENTICATION_FAILED",
                message="Authentication failed",
                data=None
            )
        
        if isinstance(error, AuthorizationError):
            return MCPError(
                code="AUTHORIZATION_FAILED",
                message="Not authorized to perform this action",
                data={"required_permission": error.required_permission} if hasattr(error, "required_permission") else None
            )
        
        # Default error
        return MCPError(
            code="INTERNAL_ERROR",
            message=str(error),
            data={"error_type": error_type}
        )
```

7. **MCPServer**

```python
class MCPServer:
    """MCP server implementation."""
    
    def __init__(self, host: str, port: int, name: str, description: str, version: str, logger: Logger):
        self.host = host
        self.port = port
        self.name = name
        self.description = description
        self.version = version
        self.logger = logger
        self._tools = {}  # type: Dict[str, MCPTool]
        self._resources = {}  # type: Dict[str, MCPResource]
        self._auth_provider = None  # type: Optional[AuthenticationProvider]
        self._error_handler = None  # type: Optional[ErrorHandler]
        self._server = None  # type: Optional[Any]  # Server instance
    
    def set_auth_provider(self, auth_provider: AuthenticationProvider) -> None:
        """Set the authentication provider."""
        self._auth_provider = auth_provider
    
    def set_error_handler(self, error_handler: ErrorHandler) -> None:
        """Set the error handler."""
        self._error_handler = error_handler
    
    def register_tool(self, name: str, tool: MCPTool) -> None:
        """
        Register an MCP tool.
        
        Args:
            name: Tool name
            tool: MCP tool to register
        """
        self._tools[name] = tool
    
    def register_resource(self, name: str, resource: MCPResource) -> None:
        """
        Register an MCP resource.
        
        Args:
            name: Resource name
            resource: MCP resource to register
        """
        self._resources[name] = resource
    
    def start(self) -> None:
        """Start the MCP server."""
        # Create uvicorn server
        # In a real implementation, this would use FastAPI, Flask, or similar
        self._server = self._create_server()
        
        # Start server in a separate thread
        server_thread = threading.Thread(target=self._run_server, daemon=True)
        server_thread.start()
        
        self.logger.info(f"MCP server started on {self.host}:{self.port}")
    
    def _create_server(self) -> Any:
        """Create the actual HTTP server."""
        # In a real implementation, this would create a FastAPI or similar app
        # This is just a placeholder
        return {"running": True}
    
    def _run_server(self) -> None:
        """Run the server in a separate thread."""
        # In a real implementation, this would start uvicorn or similar
        while self._server and self._server.get("running", False):
            time.sleep(1)
    
    def stop(self) -> None:
        """Stop the MCP server."""
        if self._server:
            self._server["running"] = False
            self._server = None
            self.logger.info("MCP server stopped")
    
    def handle_request(self, request: MCPRequest) -> MCPResponse:
        """
        Handle an MCP request.
        
        Args:
            request: MCP request
            
        Returns:
            MCP response
        """
        try:
            # Authenticate request
            auth_context = None
            if self._auth_provider:
                auth_context = self._auth_provider.authenticate(request)
                if auth_context is None:
                    return MCPResponse(
                        id=request.id,
                        status="error",
                        error=MCPError(
                            code="AUTHENTICATION_FAILED",
                            message="Authentication failed",
                            data=None
                        ),
                        result=None
                    )
            
            # Route request to appropriate handler
            if request.type == "tool":
                return self._handle_tool_request(request, auth_context)
            elif request.type == "resource":
                return self._handle_resource_request(request, auth_context)
            else:
                return MCPResponse(
                    id=request.id,
                    status="error",
                    error=MCPError(
                        code="INVALID_REQUEST",
                        message=f"Invalid request type: {request.type}",
                        data=None
                    ),
                    result=None
                )
        
        except Exception as e:
            # Handle any unhandled exceptions
            error = self._error_handler.handle_error(e, request) if self._error_handler else MCPError(
                code="INTERNAL_ERROR",
                message=str(e),
                data=None
            )
            
            return MCPResponse(
                id=request.id,
                status="error",
                error=error,
                result=None
            )
    
    def _handle_tool_request(self, request: MCPRequest, auth_context: Optional[Dict[str, Any]]) -> MCPResponse:
        """Handle a tool request."""
        # Get tool
        tool_name = request.target
        tool = self._tools.get(tool_name)
        
        if not tool:
            return MCPResponse(
                id=request.id,
                status="error",
                error=MCPError(
                    code="TOOL_NOT_FOUND",
                    message=f"Tool not found: {tool_name}",
                    data=None
                ),
                result=None
            )
        
        # Authorize request
        if self._auth_provider and auth_context is not None:
            if not self._auth_provider.authorize(auth_context, "tool", tool_name):
                return MCPResponse(
                    id=request.id,
                    status="error",
                    error=MCPError(
                        code="AUTHORIZATION_FAILED",
                        message=f"Not authorized to use tool: {tool_name}",
                        data=None
                    ),
                    result=None
                )
        
        # Execute tool
        try:
            result = tool.execute(request.data, auth_context)
            
            return MCPResponse(
                id=request.id,
                status="success",
                error=None,
                result=result
            )
        
        except Exception as e:
            # Handle tool execution errors
            error = self._error_handler.handle_error(e, request) if self._error_handler else MCPError(
                code="TOOL_EXECUTION_ERROR",
                message=str(e),
                data=None
            )
            
            return MCPResponse(
                id=request.id,
                status="error",
                error=error,
                result=None
            )
    
    def _handle_resource_request(self, request: MCPRequest, auth_context: Optional[Dict[str, Any]]) -> MCPResponse:
        """Handle a resource request."""
        # Parse resource path
        resource_path = request.target
        parts = resource_path.split("/", 1)
        
        resource_name = parts[0]
        resource_id = parts[1] if len(parts) > 1 else None
        
        # Get resource
        resource = self._resources.get(resource_name)
        
        if not resource:
            return MCPResponse(
                id=request.id,
                status="error",
                error=MCPError(
                    code="RESOURCE_NOT_FOUND",
                    message=f"Resource not found: {resource_name}",
                    data=None
                ),
                result=None
            )
        
        # Authorize request
        if self._auth_provider and auth_context is not None:
            if not self._auth_provider.authorize(auth_context, "resource", resource_name):
                return MCPResponse(
                    id=request.id,
                    status="error",
                    error=MCPError(
                        code="AUTHORIZATION_FAILED",
                        message=f"Not authorized to access resource: {resource_name}",
                        data=None
                    ),
                    result=None
                )
        
        # Access resource
        try:
            result = resource.get(resource_id, request.data, auth_context)
            
            return MCPResponse(
                id=request.id,
                status="success",
                error=None,
                result=result
            )
        
        except Exception as e:
            # Handle resource access errors
            error = self._error_handler.handle_error(e, request) if self._error_handler else MCPError(
                code="RESOURCE_ACCESS_ERROR",
                message=str(e),
                data=None
            )
            
            return MCPResponse(
                id=request.id,
                status="error",
                error=error,
                result=None
            )
```

8. **MCPTool (Base Class)**

```python
class MCPTool(ABC):
    """Base class for MCP tools."""
    
    def __init__(self, name: str, description: str, logger: Logger):
        self.name = name
        self.description = description
        self.logger = logger
        self.input_schema = self._get_input_schema()
        self.output_schema = self._get_output_schema()
    
    @abstractmethod
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute the tool.
        
        Args:
            data: Input data
            auth_context: Authentication context
            
        Returns:
            Tool result
        """
        pass
    
    @abstractmethod
    def _get_input_schema(self) -> Dict[str, Any]:
        """
        Get the tool input schema.
        
        Returns:
            JSON schema for tool input
        """
        pass
    
    @abstractmethod
    def _get_output_schema(self) -> Dict[str, Any]:
        """
        Get the tool output schema.
        
        Returns:
            JSON schema for tool output
        """
        pass
```

9. **MCPResource (Base Class)**

```python
class MCPResource(ABC):
    """Base class for MCP resources."""
    
    def __init__(self, name: str, description: str, logger: Logger):
        self.name = name
        self.description = description
        self.logger = logger
    
    @abstractmethod
    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a resource.
        
        Args:
            resource_id: Resource ID
            params: Request parameters
            auth_context: Authentication context
            
        Returns:
            Resource data
        """
        pass
```

10. **Example Tool Implementation: AnalyzeDocumentConsistencyTool**

```python
class AnalyzeDocumentConsistencyTool(MCPTool):
    """Tool for analyzing document consistency."""
    
    def __init__(self, consistency_component: Component, job_manager: Component, logger: Logger):
        super().__init__(
            name="analyze_document_consistency",
            description="Analyze consistency between documentation and code files",
            logger=logger
        )
        self.consistency_component = consistency_component
        self.job_manager = job_manager
    
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the tool."""
        self.logger.info("Executing analyze_document_consistency tool")
        
        # Validate input data against schema
        self._validate_input(data)
        
        # Extract parameters
        code_file_path = data.get("code_file_path")
        doc_file_path = data.get("doc_file_path")
        async_execution = data.get("async", False)
        
        # Execute asynchronously if requested
        if async_execution:
            # Submit job
            job_id = self.job_manager.submit_job(JobSpecification(
                type="consistency_analysis",
                payload={
                    "code_file_path": code_file_path,
                    "doc_file_path": doc_file_path,
                },
                priority=5  # Medium priority
            ))
            
            return {
                "job_id": job_id,
                "status": "submitted",
                "message": "Consistency analysis job submitted"
            }
        
        # Execute synchronously
        try:
            # Analyze consistency
            inconsistencies = self.consistency_component.analyze_code_doc_consistency(
                code_file_path=code_file_path,
                doc_file_path=doc_file_path
            )
            
            # Prepare result
            result = {
                "status": "completed",
                "inconsistencies": [
                    {
                        "id": str(inconsistency.id),
                        "type": inconsistency.inconsistency_type.value,
                        "description": inconsistency.description,
                        "severity": inconsistency.severity.value,
                        "source_file": inconsistency.source_file,
                        "target_file": inconsistency.target_file,
                        "detected_at": inconsistency.detected_at.isoformat()
                    }
                    for inconsistency in inconsistencies
                ],
                "summary": {
                    "total": len(inconsistencies),
                    "by_severity": self._count_by_severity(inconsistencies),
                    "by_type": self._count_by_type(inconsistencies)
                }
            }
            
            return result
        
        except Exception as e:
            self.logger.error(f"Error executing consistency analysis: {e}")
            raise ToolExecutionError(f"Error executing consistency analysis: {e}")
    
    def _validate_input(self, data: Dict[str, Any]) -> None:
        """Validate input data."""
        # Check required parameters
        if "code_file_path" not in data:
            raise ValidationError("Missing required parameter: code_file_path")
        
        if "doc_file_path" not in data:
            raise ValidationError("Missing required parameter: doc_file_path")
        
        # Validate paths
        if not os.path.isfile(data["code_file_path"]):
            raise ValidationError(f"Code file not found: {data['code_file_path']}")
        
        if not os.path.isfile(data["doc_file_path"]):
            raise ValidationError(f"Documentation file not found: {data['doc_file_path']}")
    
    def _count_by_severity(self, inconsistencies: List[InconsistencyRecord]) -> Dict[str, int]:
        """Count inconsistencies by severity."""
        counts = {}
        for inconsistency in inconsistencies:
            severity = inconsistency.severity.value
            counts[severity] = counts.get(severity, 0) + 1
        return counts
    
    def _count_by_type(self, inconsistencies: List[InconsistencyRecord]) -> Dict[str, int]:
        """Count inconsistencies by type."""
        counts = {}
        for inconsistency in inconsistencies:
            inconsistency_type = inconsistency.inconsistency_type.value
            counts[inconsistency_type] = counts.get(inconsistency_type, 0) + 1
        return counts
    
    def _get_input_schema(self) -> Dict[str, Any]:
        """Get input schema for tool."""
        return {
            "type": "object",
            "properties": {
                "code_file_path": {
                    "type": "string",
                    "description": "Path to the code file to analyze"
                },
                "doc_file_path": {
                    "type": "string",
                    "description": "Path to the documentation file to analyze"
                },
                "async": {
                    "type": "boolean",
                    "description": "Whether to execute asynchronously (default: false)",
                    "default": False
                }
            },
            "required": ["code_file_path", "doc_file_path"]
        }
    
    def _get_output_schema(self) -> Dict[str, Any]:
        """Get output schema for tool."""
        return {
            "type": "object",
            "properties": {
                "status": {
                    "type": "string",
                    "enum": ["completed", "submitted"],
                    "description": "Status of the analysis"
                },
                "inconsistencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Inconsistency ID"
                            },
                            "type": {
                                "type": "string",
                                "description": "Type of inconsistency"
                            },
                            "description": {
                                "type": "string",
                                "description": "Description of the inconsistency"
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["high", "medium", "low"],
                                "description": "Severity of the inconsistency"
                            },
                            "source_file": {
                                "type": "string",
                                "description": "Source file path"
                            },
                            "target_file": {
                                "type": "string",
                                "description": "Target file path"
                            },
                            "detected_at": {
                                "type": "string",
                                "format": "date-time",
                                "description": "When the inconsistency was detected"
                            }
                        }
                    },
                    "description": "List of detected inconsistencies"
                },
                "job_id": {
                    "type": "string",
                    "description": "Job ID (for async execution)"
                },
                "message": {
                    "type": "string",
                    "description": "Status message"
                },
                "summary": {
                    "type": "object",
                    "properties": {
                        "total": {
                            "type": "integer",
                            "description": "Total number of inconsistencies"
                        },
                        "by_severity": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "integer"
                            },
                            "description": "Count of inconsistencies by severity"
                        },
                        "by_type": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "integer"
                            },
                            "description": "Count of inconsistencies by type"
                        }
                    },
                    "description": "Summary of inconsistencies"
                }
            }
        }
```

11. **Example Resource Implementation: DocumentationResource**

```python
class DocumentationResource(MCPResource):
    """Resource for accessing documentation metadata."""
    
    def __init__(self, doc_relationships_component: Component, logger: Logger):
        super().__init__(
            name="documentation",
            description="Access documentation metadata and relationships",
            logger=logger
        )
        self.doc_relationships_component = doc_relationships_component
    
    def get(self, resource_id: Optional[str], params: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Get documentation resource."""
        self.logger.info(f"Accessing documentation resource: {resource_id}")
        
        # If no specific resource ID is provided, list available documentation
        if not resource_id:
            return self._list_documentation(params)
        
        # Get specific documentation resource
        if resource_id == "relationships":
            return self._get_relationships(params)
        elif resource_id == "mermaid":
            return self._get_mermaid_diagram(params)
        else:
            # Assume resource_id is a file path
            return self._get_documentation_metadata(resource_id, params)
    
    def _list_documentation(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List available documentation."""
        # Get directory to list
        directory = params.get("directory", "doc")
        
        # List files in directory
        try:
            files = []
            for root, dirs, filenames in os.walk(directory):
                for filename in filenames:
                    if filename.endswith(".md"):
                        file_path = os.path.join(root, filename)
                        files.append({
                            "path": file_path,
                            "name": filename,
                            "modified_at": datetime.fromtimestamp(os.path.getmtime(file_path)).isoformat()
                        })
            
            return {
                "files": files,
                "count": len(files),
                "directory": directory
            }
        
        except Exception as e:
            self.logger.error(f"Error listing documentation: {e}")
            raise ResourceAccessError(f"Error listing documentation: {e}")
    
    def _get_relationships(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get documentation relationships."""
        # Get document path
        document_path = params.get("document_path")
        
        if not document_path:
            raise ValidationError("Missing parameter: document_path")
        
        # Get document relationships
        try:
            relationships = self.doc_relationships_component.get_related_documents(document_path)
            
            return {
                "document_path": document_path,
                "relationships": [
                    {
                        "source": rel.source_document,
                        "target": rel.target_document,
                        "type": rel.relationship_type,
                        "topic": rel.topic,
                        "scope": rel.scope
                    }
                    for rel in relationships
                ],
                "count": len(relationships)
            }
        
        except Exception as e:
            self.logger.error(f"Error getting document relationships: {e}")
            raise ResourceAccessError(f"Error getting document relationships: {e}")
    
    def _get_mermaid_diagram(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get Mermaid diagram of document relationships."""
        # Get document paths
        document_paths = params.get("document_paths")
        
        # Get Mermaid diagram
        try:
            diagram = self.doc_relationships_component.get_mermaid_diagram(document_paths)
            
            return {
                "diagram": diagram,
                "document_paths": document_paths
            }
        
        except Exception as e:
            self.logger.error(f"Error generating Mermaid diagram: {e}")
            raise ResourceAccessError(f"Error generating Mermaid diagram: {e}")
    
    def _get_documentation_metadata(self, document_path: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get metadata for a specific document."""
        try:
            # Check if file exists
            if not os.path.isfile(document_path):
                raise ResourceNotFoundError(f"Documentation file not found: {document_path}")
            
            # Get file metadata
            stat = os.stat(document_path)
            
            # Get file content if requested
            include_content = params.get("include_content", False)
            content = None
            
            if include_content:
                with open(document_path, "r", encoding="utf-8") as f:
                    content = f.read()
            
            # Get document relationships if requested
            include_relationships = params.get("include_relationships", False)
            relationships = None
            
            if include_relationships:
                relationships = [
                    {
                        "source": rel.source_document,
                        "target": rel.target_document,
                        "type": rel.relationship_type,
                        "topic": rel.topic,
                        "scope": rel.scope
                    }
                    for rel in self.doc_relationships_component.get_related_documents(document_path)
                ]
            
            # Return metadata
            result = {
                "path": document_path,
                "name": os.path.basename(document_path),
                "size": stat.st_size,
                "modified_at": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "created_at": datetime.fromtimestamp(stat.st_ctime).isoformat()
            }
            
            # Add content if included
            if content is not None:
                result["content"] = content
            
            # Add relationships if included
            if relationships is not None:
                result["relationships"] = relationships
                result["relationship_count"] = len(relationships)
            
            return result
        
        except ResourceNotFoundError:
            raise
        
        except Exception as e:
            self.logger.error(f"Error getting documentation metadata: {e}")
            raise ResourceAccessError(f"Error getting documentation metadata: {e}")
```

### Data Model Classes

1. **MCPRequest**

```python
@dataclass
class MCPRequest:
    """MCP request model."""
    
    id: str
    type: str  # "tool" or "resource"
    target: str  # Tool name or resource path
    data: Dict[str, Any]
    headers: Dict[str, str]
```

2. **MCPResponse**

```python
@dataclass
class MCPResponse:
    """MCP response model."""
    
    id: str
    status: str  # "success" or "error"
    error: Optional[MCPError]
    result: Optional[Dict[str, Any]]
```

3. **MCPError**

```python
@dataclass
class MCPError:
    """MCP error model."""
    
    code: str
    message: str
    data: Optional[Dict[str, Any]]
```

4. **APIKeyEntry**

```python
@dataclass
class APIKeyEntry:
    """API key entry."""
    
    key: str
    client_id: str
    permissions: List[str]
```

### Configuration Class

```python
@dataclass
class MCPServerConfig:
    """Configuration for MCP server integration."""
    
    host: str
    port: int
    server_name: str
    server_description: str
    server_version: str
    auth_enabled: bool
    api_keys: List[APIKeyEntry]
```

Default configuration values:

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `host` | Server host | `"0.0.0.0"` | Valid IP address |
| `port` | Server port | `3000` | `1-65535` |
| `server_name` | Server name | `"documentation-based-programming-server"` | Non-empty string |
| `server_description` | Server description | `"MCP server for Documentation-Based Programming"` | String |
| `server_version` | Server version | `"1.0.0"` | Semantic version |
| `auth_enabled` | Whether authentication is enabled | `true` | Boolean |
| `api_keys` | List of API keys | `[]` | List of API key entries |

## Implementation Plan

### Phase 1: Core Structure
1. Implement MCPServerComponent as a system component
2. Define data model classes (MCPRequest, MCPResponse, etc.)
3. Create configuration class
4. Implement HTTP server framework

### Phase 2: MCP Protocol Implementation
1. Implement MCPServer for handling requests
2. Create ToolRegistry and ResourceProvider for registration
3. Implement SystemComponentAdapter for accessing system components
4. Implement authentication and authorization

### Phase 3: Tools and Resources
1. Implement MCPTool and MCPResource base classes
2. Create tools for consistency analysis
3. Create tools for recommendation generation
4. Create resources for documentation and metadata

### Phase 4: Error Handling and Logging
1. Implement ErrorHandler for MCP errors
2. Add proper logging and monitoring
3. Implement error response formatting
4. Add validation for requests and responses

## Security Considerations

The MCP Server Integration component implements these security measures:
- API key authentication for all MCP requests
- Permission-based authorization for tool and resource access
- Validation of all request parameters
- Proper error handling to avoid information disclosure
- Resource path validation to prevent path traversal attacks
- Secure handling of sensitive information
- CORS protection for web-based clients
- Rate limiting for API requests
- Proper logging of security events

## Testing Strategy

### Unit Tests
- Test individual tools and resources
- Test authentication and authorization
- Test error handling
- Test request validation

### Integration Tests
- Test integration with system components
- Test end-to-end request handling
- Test asynchronous job handling
- Test authentication flows

### System Tests
- Test performance under load
- Test error recovery
- Test security constraints
- Test API compatibility

## Dependencies on Other Plans

This plan depends on:
- Consistency Analysis plan (for consistency tools)
- Recommendation Generator plan (for recommendation tools)
- Documentation Relationships plan (for documentation resources)
- Job Management plan (for asynchronous operations)
- LLM Coordinator plan (for LLM tools)

## Implementation Timeline

1. Core Structure - 2 days
2. MCP Protocol Implementation - 2 days
3. Tools and Resources - 3 days
4. Error Handling and Logging - 1 day

Total: 8 days
