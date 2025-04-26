###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements the GeneralQueryMCPTool class, which provides a Model Context Protocol 
# (MCP) compliant interface for the LLM coordinator's general query functionality.
# This tool allows LLM assistants to access various codebase metadata and perform
# operations through a standardized interface.
###############################################################################
# [Source file design principles]
# - MCP-compliant implementation with proper schema validation
# - Streaming response support for long-running queries
# - Proper error handling according to MCP specifications
# - Clear separation between MCP protocol concerns and internal tool execution
# - Support for cost and time budgets to prevent runaway resources consumption
# - Asynchronous job management for parallel processing
###############################################################################
# [Source file constraints]
# - Must comply with the MCP specification
# - Must implement streaming responses for long-running operations
# - Must handle cancellation requests appropriately
# - Must provide accurate progress reporting
# - Must properly validate all inputs against schema
###############################################################################
# [Dependencies]
# system:typing
# system:logging
# system:json
# system:uuid
# system:pydantic
# codebase:src/dbp/mcp_server/mcp/tool.py
# codebase:src/dbp/mcp_server/mcp/streaming_tool.py
# codebase:src/dbp/llm_coordinator/job_manager.py
# codebase:src/dbp/core/exceptions.py
# codebase:doc/design/LLM_COORDINATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-26T00:58:00Z : Initial implementation by CodeAssistant
# * Created GeneralQueryMCPTool class
# * Added streaming response support
# * Implemented proper MCP schema validation
# * Added integration with LLM coordinator job management
###############################################################################

import json
import logging
import time
import uuid
from typing import Dict, Any, Optional, List, Type, AsyncGenerator, Tuple, Union
from pydantic import BaseModel, Field, ValidationError

# MCP imports
from src.dbp.mcp_server.mcp.tool import MCPTool
from src.dbp.mcp_server.mcp.streaming_tool import MCPStreamingTool
from src.dbp.mcp_server.mcp.progress import MCPProgressReporter
from src.dbp.mcp_server.mcp.cancellation import MCPCancellationToken
from src.dbp.mcp_server.mcp.error import MCPError, MCPErrorCode

# LLM coordinator imports
from src.dbp.llm_coordinator.job_manager import JobManager, Job, JobStatus
from src.dbp.core.exceptions import DBPBaseException

logger = logging.getLogger(__name__)


class QueryInputSchema(BaseModel):
    """
    [Class intent]
    Defines the input schema for the general query MCP tool.
    
    [Design principles]
    Uses Pydantic for schema validation and strong typing.
    Provides clear field descriptions following MCP best practices.
    
    [Implementation details]
    Includes all fields needed for general queries with proper validation.
    """
    query: str = Field(
        description="Natural language query text to be processed by the LLM coordinator."
    )
    context: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional additional context information for query processing."
    )
    parameters: Optional[Dict[str, Any]] = Field(
        default=None, 
        description="Optional parameters to control query execution behavior."
    )
    max_execution_time_ms: Optional[int] = Field(
        default=None, 
        description="Maximum query execution time in milliseconds."
    )
    max_cost_budget: Optional[float] = Field(
        default=None, 
        description="Maximum cost budget for query execution."
    )
    force_llm_processing: Optional[bool] = Field(
        default=False, 
        description="Force processing via LLM coordinator instead of using internal tools."
    )

    class Config:
        schema_extra = {
            "example": {
                "query": "What are the key design principles in the DATA_MODEL.md file?",
                "context": {"file_paths": ["doc/DATA_MODEL.md"]},
                "max_execution_time_ms": 30000,
                "max_cost_budget": 0.5,
                "force_llm_processing": False
            }
        }


class QueryResultSchema(BaseModel):
    """
    [Class intent]
    Defines the output schema for the general query MCP tool.
    
    [Design principles]
    Uses Pydantic for schema validation and strong typing.
    Provides a structured way to return query results with metadata.
    
    [Implementation details]
    Separates actual result data from execution metadata for clarity.
    """
    result: Dict[str, Any] = Field(
        description="The result data from the query execution."
    )
    metadata: Dict[str, Any] = Field(
        description="Metadata about the query execution."
    )

    class Config:
        schema_extra = {
            "example": {
                "result": {
                    "answer": "The key design principles in DATA_MODEL.md include...",
                    "relevant_sections": [
                        {"heading": "Database Schema", "content": "..."}
                    ],
                    "references": ["doc/DATA_MODEL.md", "doc/DESIGN.md"]
                },
                "metadata": {
                    "execution_path": "llm_coordinator",
                    "confidence": 0.95,
                    "execution_time_ms": 2500,
                    "token_usage": {"input": 1024, "output": 512, "total": 1536}
                }
            }
        }


class GeneralQueryMCPTool(MCPStreamingTool):
    """
    [Class intent]
    Implements an MCP-compliant tool for handling general queries to the DBP system.
    Provides both synchronous and streaming response capabilities.
    
    [Design principles]
    - Fully compliant with MCP specifications
    - Supports streaming for long-running operations
    - Integrates with LLM coordinator for query processing
    - Handles proper cancellation and progress reporting
    - Supports both synchronous and asynchronous execution
    
    [Implementation details]
    - Uses asynchronous job management from LLM coordinator
    - Implements Pydantic models for input/output schema validation
    - Provides compatibility with both streaming and non-streaming clients
    - Handles JSON-RPC protocol requirements for both modes
    """

    def __init__(self, 
                 job_manager: Optional[JobManager] = None, 
                 logger_override: Optional[logging.Logger] = None):
        """
        [Class method intent]
        Initializes the GeneralQueryMCPTool with job manager and logging setup.
        
        [Design principles]
        Clear separation of concerns with dependency injection for job management.
        
        [Implementation details]
        Sets up the tool with proper name and description following MCP standards.
        
        Args:
            job_manager: Optional JobManager for handling async operations
            logger_override: Optional logger instance
        """
        super().__init__(
            name="dbp_general_query",
            description="Retrieve various types of codebase metadata and perform document operations.",
            logger_override=logger_override
        )
        self.job_manager = job_manager or JobManager()
        self.logger = logger_override or logger.getChild(f"MCPTool.{self.name}")

    def _get_input_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Defines the input schema for the tool using Pydantic models.
        
        [Design principles]
        Strong typing and validation through Pydantic.
        
        [Implementation details]
        Returns the QueryInputSchema class for validation.
        
        Returns:
            A Pydantic model class for validating input data
        """
        return QueryInputSchema

    def _get_output_schema(self) -> Type[BaseModel]:
        """
        [Function intent]
        Defines the output schema for the tool using Pydantic models.
        
        [Design principles]
        Strong typing and validation through Pydantic.
        
        [Implementation details]
        Returns the QueryResultSchema class for validation.
        
        Returns:
            A Pydantic model class for validating output data
        """
        return QueryResultSchema

    def execute(self, 
                data: QueryInputSchema,
                cancellation_token: Optional[MCPCancellationToken] = None,
                progress_reporter: Optional[MCPProgressReporter] = None,
                auth_context: Optional[Dict[str, Any]] = None) -> QueryResultSchema:
        """
        [Function intent]
        Executes the query synchronously and returns the result.
        
        [Design principles]
        Handles synchronous execution with proper error handling and progress reporting.
        
        [Implementation details]
        Creates and manages a job using the JobManager and waits for completion.
        
        Args:
            data: A Pydantic model containing validated query parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context
            
        Returns:
            A QueryResultSchema containing the query results
            
        Raises:
            MCPError: For tool-specific execution errors
        """
        if not self.job_manager:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                "Job manager not initialized"
            )
            
        self.logger.info(f"Processing query: {data.query[:100]}...")
        
        try:
            # Create a job for the query
            job_id = str(uuid.uuid4())
            job = self._create_query_job(job_id, data, auth_context)
            
            # Start the job
            start_time = time.time()
            self.job_manager.submit_job(job)
            
            # Setup progress reporting
            last_reported_progress = 0
            if progress_reporter:
                progress_reporter.report(0, 100)
                
            # Monitor job for completion, cancellation, or progress updates
            while True:
                if cancellation_token and cancellation_token.is_cancelled():
                    self.job_manager.cancel_job(job_id)
                    self.logger.warning(f"Job {job_id} cancelled by request")
                    raise MCPError(
                        MCPErrorCode.CANCELLED,
                        "Operation cancelled by user request"
                    )
                
                job_status = self.job_manager.get_job_status(job_id)
                
                # Update progress if changed
                if progress_reporter and job_status.progress != last_reported_progress:
                    last_reported_progress = job_status.progress
                    progress_reporter.report(job_status.progress, 100)
                
                # Check if job completed
                if job_status.status == JobStatus.COMPLETED:
                    result = self.job_manager.get_job_result(job_id)
                    self.logger.info(f"Job {job_id} completed successfully")
                    return self._format_job_result(result)
                
                # Check if job failed
                elif job_status.status == JobStatus.FAILED:
                    error = self.job_manager.get_job_error(job_id)
                    self.logger.error(f"Job {job_id} failed: {error}")
                    raise MCPError(
                        MCPErrorCode.TOOL_EXECUTION_ERROR,
                        f"Query execution failed: {error}"
                    )
                
                # Check for timeout
                if data.max_execution_time_ms and \
                   (time.time() - start_time) * 1000 > data.max_execution_time_ms:
                    self.job_manager.cancel_job(job_id)
                    self.logger.warning(f"Job {job_id} timed out after {data.max_execution_time_ms}ms")
                    raise MCPError(
                        MCPErrorCode.DEADLINE_EXCEEDED,
                        f"Query execution timed out after {data.max_execution_time_ms}ms"
                    )
                
                # Sleep briefly to avoid CPU spin
                time.sleep(0.1)
                
        except MCPError:
            # Re-raise MCPError exceptions
            raise
        except Exception as e:
            # Convert other exceptions to MCPError
            self.logger.error(f"Error executing query: {str(e)}", exc_info=True)
            raise MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Error executing query: {str(e)}"
            )

    async def execute_streaming(self, 
                               data: QueryInputSchema,
                               cancellation_token: Optional[MCPCancellationToken] = None,
                               progress_reporter: Optional[MCPProgressReporter] = None,
                               auth_context: Optional[Dict[str, Any]] = None
                               ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        [Function intent]
        Executes the query asynchronously with streaming response support.
        
        [Design principles]
        Implements MCP streaming protocol for incremental result delivery.
        
        [Implementation details]
        Creates and manages a streaming job with the JobManager and yields results incrementally.
        
        Args:
            data: A Pydantic model containing validated query parameters
            cancellation_token: Optional token to check for cancellation
            progress_reporter: Optional reporter to update progress
            auth_context: Optional authentication context
            
        Yields:
            Incremental query results as they become available
            
        Raises:
            MCPError: For tool-specific execution errors
        """
        if not self.job_manager:
            raise MCPError(
                MCPErrorCode.INTERNAL_ERROR,
                "Job manager not initialized"
            )
            
        self.logger.info(f"Processing streaming query: {data.query[:100]}...")
        
        try:
            # Create a job for the query with streaming enabled
            job_id = str(uuid.uuid4())
            job = self._create_query_job(job_id, data, auth_context, streaming=True)
            
            # Start the job
            start_time = time.time()
            self.job_manager.submit_job(job)
            
            # Setup progress reporting
            last_reported_progress = 0
            if progress_reporter:
                progress_reporter.report(0, 100)
            
            # Get streaming results iterator
            streaming_results = self.job_manager.get_streaming_results(job_id)
            
            # Process streaming results until completion
            last_chunk_time = time.time()
            async for result_chunk in streaming_results:
                # Check for cancellation
                if cancellation_token and cancellation_token.is_cancelled():
                    self.job_manager.cancel_job(job_id)
                    self.logger.warning(f"Streaming job {job_id} cancelled by request")
                    raise MCPError(
                        MCPErrorCode.CANCELLED,
                        "Operation cancelled by user request"
                    )
                
                # Update progress if available in chunk
                if progress_reporter and 'progress' in result_chunk:
                    progress = min(int(result_chunk['progress'] * 100), 100)
                    if progress != last_reported_progress:
                        last_reported_progress = progress
                        progress_reporter.report(progress, 100)
                
                # Check for timeout between chunks
                if data.max_execution_time_ms:
                    elapsed_ms = (time.time() - start_time) * 1000
                    if elapsed_ms > data.max_execution_time_ms:
                        self.job_manager.cancel_job(job_id)
                        self.logger.warning(f"Streaming job {job_id} timed out after {data.max_execution_time_ms}ms")
                        raise MCPError(
                            MCPErrorCode.DEADLINE_EXCEEDED,
                            f"Query execution timed out after {data.max_execution_time_ms}ms"
                        )
                
                # Format and yield the chunk
                formatted_chunk = self._format_streaming_chunk(result_chunk)
                yield formatted_chunk
                last_chunk_time = time.time()
                
            # Final progress update if needed
            if progress_reporter and last_reported_progress < 100:
                progress_reporter.report(100, 100)
                
        except MCPError:
            # Re-raise MCPError exceptions
            raise
        except Exception as e:
            # Convert other exceptions to MCPError
            self.logger.error(f"Error executing streaming query: {str(e)}", exc_info=True)
            raise MCPError(
                MCPErrorCode.TOOL_EXECUTION_ERROR,
                f"Error executing streaming query: {str(e)}"
            )

    def _create_query_job(self, 
                         job_id: str, 
                         data: QueryInputSchema,
                         auth_context: Optional[Dict[str, Any]] = None,
                         streaming: bool = False) -> Job:
        """
        [Function intent]
        Creates a Job object for processing by the JobManager.
        
        [Design principles]
        Encapsulates job creation logic separately from execution.
        
        [Implementation details]
        Builds a Job with all necessary parameters from the query input.
        
        Args:
            job_id: Unique ID for the job
            data: Query input data from the MCP tool request
            auth_context: Optional authentication context
            streaming: Whether this job should produce streaming results
            
        Returns:
            A Job object ready for submission to JobManager
        """
        # In a real implementation, this would integrate with LLMCoordinator
        # to process the query. Here, we're providing a placeholder implementation.
        
        # Create parameters dictionary for the job
        job_params = {
            "query": data.query,
            "context": data.context or {},
            "parameters": data.parameters or {},
            "max_execution_time_ms": data.max_execution_time_ms,
            "max_cost_budget": data.max_cost_budget,
            "force_llm_processing": data.force_llm_processing,
            "auth_context": auth_context,
            "streaming": streaming
        }
        
        # Create and return the job
        job = Job(
            job_id=job_id,
            job_type="general_query",
            parameters=job_params,
            priority=1,  # Default priority
            max_execution_time_ms=data.max_execution_time_ms
        )
        
        return job

    def _format_job_result(self, result: Dict[str, Any]) -> QueryResultSchema:
        """
        [Function intent]
        Formats the job result into the expected MCP response format.
        
        [Design principles]
        Ensures consistent response formatting that complies with schema.
        
        [Implementation details]
        Transforms internal job result format into QueryResultSchema.
        
        Args:
            result: Raw result from job execution
            
        Returns:
            A QueryResultSchema formatted response
        """
        # In a real implementation, this would properly format the LLMCoordinator
        # response. Here, we provide a placeholder implementation.
        
        if not result:
            result = {}
            
        # Ensure we have the base structure
        if "result" not in result:
            result["result"] = {}
        
        if "metadata" not in result:
            result["metadata"] = {}
        
        # Add default metadata if not present
        metadata = result["metadata"]
        if "execution_time_ms" not in metadata:
            metadata["execution_time_ms"] = 0
        
        if "execution_path" not in metadata:
            metadata["execution_path"] = "placeholder"
        
        # Validate against schema
        try:
            return QueryResultSchema(
                result=result["result"],
                metadata=metadata
            )
        except ValidationError as e:
            self.logger.error(f"Error validating result: {str(e)}")
            # Return a minimal valid response
            return QueryResultSchema(
                result={"error": "Result validation failed"},
                metadata={"execution_path": "error", "execution_time_ms": 0}
            )

    def _format_streaming_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Formats a streaming result chunk into the expected MCP streaming format.
        
        [Design principles]
        Ensures streaming chunks comply with MCP streaming protocol.
        
        [Implementation details]
        Transforms internal streaming format into MCP-compatible chunks.
        
        Args:
            chunk: Raw streaming chunk from job execution
            
        Returns:
            A properly formatted MCP streaming chunk
        """
        # In a real implementation, this would format streaming chunks properly.
        # Here, we provide a placeholder implementation.
        
        # Basic validation and formatting
        formatted_chunk = {}
        
        # Content is required for most chunks
        if "content" in chunk:
            formatted_chunk["content"] = chunk["content"]
        
        # Add metadata if present
        if "metadata" in chunk:
            formatted_chunk["metadata"] = chunk["metadata"]
        
        # Add progress if present (0.0 to 1.0)
        if "progress" in chunk:
            formatted_chunk["progress"] = min(max(chunk["progress"], 0.0), 1.0)
        
        # Handle special chunk types
        if chunk.get("type") == "end":
            formatted_chunk["end"] = True
        
        if chunk.get("type") == "error":
            formatted_chunk["error"] = {
                "code": chunk.get("error_code", "UNKNOWN_ERROR"),
                "message": chunk.get("error_message", "Unknown error occurred")
            }
        
        return formatted_chunk
