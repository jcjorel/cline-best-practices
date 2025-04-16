###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Implements concrete MCPTool classes that expose the DBP system's functionality
# via the Model Context Protocol. Each tool class defines its input/output schema
# and implements the execution logic by interacting with the core DBP components
# through the SystemComponentAdapter.
###############################################################################
# [Source file design principles]
# - Each class inherits from `MCPTool`.
# - Each class defines specific input and output JSON schemas.
# - `execute` methods contain the logic to handle tool invocation.
# - Uses `SystemComponentAdapter` to access underlying DBP functionality.
# - Includes basic input validation and error handling.
# - Supports asynchronous execution where appropriate by interacting with a JobManager (via adapter).
# - Placeholder logic used for complex interactions.
###############################################################################
# [Source file constraints]
# - Depends on `mcp_protocols.py` for `MCPTool` base class.
# - Depends on `adapter.py` for `SystemComponentAdapter`.
# - Depends on various core DBP components and data models (e.g., ConsistencyAnalysisComponent, Recommendation).
# - Input/output schemas must be kept consistent with tool functionality.
# - Placeholder execution logic needs to be replaced with actual component interactions.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/API.md
# - scratchpad/dbp_implementation_plan/plan_mcp_integration.md
# - src/dbp/mcp_server/mcp_protocols.py
# - src/dbp/mcp_server/adapter.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T09:26:00Z : Refactored to use internal tools by CodeAssistant
# * Removed directly exposed tools that aren't documented in DESIGN.md
# * Added placeholder for CommitMessageTool
# * Updated imports to use new internal tools package
# 2025-04-15T10:51:25Z : Initial creation of MCP tool classes by CodeAssistant
# * Implemented placeholder tools for consistency analysis, recommendations, relationships, and LLM coordination.
###############################################################################

import logging
import time
import re
from typing import Dict, Any, Optional, List, Tuple

# Import internal tools
try:
    from .internal_tools import (
        InternalConsistencyAnalysisTool,
        InternalRecommendationsGeneratorTool,
        InternalRecommendationApplicatorTool,
        InternalDocumentRelationshipsTool,
        InternalMermaidDiagramTool,
    )
    from .mcp_protocols import MCPTool
    from .adapter import SystemComponentAdapter, ComponentNotFoundError
    from ..llm_coordinator.component import LLMCoordinatorComponent
    from ..llm_coordinator.data_models import CoordinatorRequest
except ImportError as e:
    logging.getLogger(__name__).error(f"MCP Tools ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    class MCPTool:
        def __init__(self, name, description, logger): self.name=name; self.description=description; self.logger=logger
        def _get_input_schema(self): return {}
        def _get_output_schema(self): return {}
        def execute(self, data, auth_context): return {}
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception
    LLMCoordinatorComponent = object
    CoordinatorRequest = object
    # Placeholder internal tool classes
    InternalConsistencyAnalysisTool = object
    InternalRecommendationsGeneratorTool = object
    InternalRecommendationApplicatorTool = object
    InternalDocumentRelationshipsTool = object
    InternalMermaidDiagramTool = object


logger = logging.getLogger(__name__)

# --- Base Exception for Tool Errors ---
class ToolExecutionError(Exception):
    """Custom exception for errors during tool execution."""
    pass

class ValidationError(ValueError):
     """Custom exception for input validation errors."""
     pass

# --- Documented Public Tool Implementations ---

class QueryClassifier:
    """
    [Class intent]
    Analyzes queries to determine which internal tool should handle them.
    
    [Implementation details]
    Uses a combination of keyword matching, pattern recognition, and context
    analysis to classify incoming queries.
    
    [Design principles]
    Focused responsibility, extensible classification patterns, transparent
    decision-making with confidence scores.
    """
    
    # Query types that can be identified
    CONSISTENCY_ANALYSIS = "consistency_analysis"
    RECOMMENDATION_GENERATION = "recommendation_generation"
    RECOMMENDATION_APPLICATION = "recommendation_application"
    DOCUMENT_RELATIONSHIP = "document_relationship"
    VISUALIZATION = "visualization"
    GENERAL_QUERY = "general_query"  # Default fallback
    
    def __init__(self, logger=None):
        """Initialize the query classifier."""
        self.logger = logger or logging.getLogger(__name__)
        # Define classification patterns
        self._patterns = self._build_classification_patterns()
        
    def _build_classification_patterns(self):
        """Build the patterns used for classification."""
        patterns = {
            self.CONSISTENCY_ANALYSIS: {
                "keywords": ["consistency", "analyze", "check", "compare", "alignment"],
                "context_indicators": ["code", "documentation", "doc", "inconsistency"]
            },
            self.RECOMMENDATION_GENERATION: {
                "keywords": ["recommend", "suggestion", "propose", "generate", "fix"],
                "context_indicators": ["inconsistency", "issue", "problem"]
            },
            self.RECOMMENDATION_APPLICATION: {
                "keywords": ["apply", "implement", "accept", "execute"],
                "context_indicators": ["recommendation", "change", "fix"]
            },
            self.DOCUMENT_RELATIONSHIP: {
                "keywords": ["relationship", "relate", "connection", "dependency", "impact"],
                "context_indicators": ["document", "documentation", "doc", "files"]
            },
            self.VISUALIZATION: {
                "keywords": ["visualize", "diagram", "graph", "mermaid", "chart"],
                "context_indicators": ["relationship", "structure", "hierarchy"]
            }
        }
        return patterns
    
    def classify(self, query_text: str, context: Optional[Dict[str, Any]] = None) -> Tuple[str, float]:
        """
        Classify a query to determine which internal tool should handle it.
        
        Args:
            query_text: The query text to classify
            context: Optional additional context for classification
            
        Returns:
            Tuple of (query_type, confidence_score)
        """
        self.logger.debug(f"Classifying query: {query_text[:50]}...")
        
        # Initialize scores
        scores = {query_type: 0.0 for query_type in self._patterns}
        
        # Simple classification based on keywords and context
        query_lower = query_text.lower()
        
        for query_type, pattern in self._patterns.items():
            # Check for keywords
            keyword_score = self._calculate_keyword_score(query_lower, pattern["keywords"])
            context_score = self._calculate_keyword_score(query_lower, pattern["context_indicators"])
            
            # Calculate final score (weighted combination)
            scores[query_type] = (keyword_score * 0.7) + (context_score * 0.3)
            
        # Check for explicit mentions of tools
        if "consistency" in query_lower and "analyze" in query_lower:
            scores[self.CONSISTENCY_ANALYSIS] += 0.3
            
        if "generate recommendation" in query_lower:
            scores[self.RECOMMENDATION_GENERATION] += 0.3
            
        if "apply recommendation" in query_lower:
            scores[self.RECOMMENDATION_APPLICATION] += 0.3
            
        # Consider context if provided
        if context:
            # If specific file paths are provided, likely consistency analysis
            if context.get("code_file_path") and context.get("doc_file_path"):
                scores[self.CONSISTENCY_ANALYSIS] += 0.4
                
            # If recommendation IDs are provided, likely recommendation-related
            if context.get("recommendation_id"):
                scores[self.RECOMMENDATION_APPLICATION] += 0.5
                
            if context.get("inconsistency_ids"):
                scores[self.RECOMMENDATION_GENERATION] += 0.5
        
        # Get the highest scoring query type
        best_match = max(scores.items(), key=lambda x: x[1])
        query_type, confidence = best_match
        
        # If confidence is too low, fall back to general query
        if confidence < 0.2:
            query_type = self.GENERAL_QUERY
            confidence = 0.1  # Low confidence indicates fallback
            
        self.logger.debug(f"Query classified as {query_type} with confidence {confidence:.2f}")
        return query_type, confidence
    
    def _calculate_keyword_score(self, query_text: str, keywords: List[str]) -> float:
        """Calculate a score based on keyword presence."""
        matches = sum(1 for keyword in keywords if keyword in query_text)
        return min(matches / max(len(keywords) / 2, 1), 1.0)


class GeneralQueryTool(MCPTool):
    """
    [Class intent]
    Public tool for handling all types of queries about the codebase and documentation.
    
    [Implementation details]
    Uses a query classifier to determine which internal tool should handle the query,
    then routes the request appropriately. Acts as a facade for all internal tools.
    
    [Design principles]
    Single entry point for queries, intelligent routing, uniform response format,
    detailed execution metadata.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="dbp_general_query",
            description="Retrieve various types of codebase metadata and perform document operations.",
            logger_override=logger_override
        )
        self.adapter = adapter
        self.query_classifier = QueryClassifier(self.logger)
        
        # Initialize internal tools (will be created on first use)
        self._internal_tools = {}
    
    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": ["string", "object"], "description": "The natural language query or structured query."},
                "context": {"type": "object", "description": "Optional additional context."},
                "parameters": {"type": "object", "description": "Optional parameters."},
                "max_execution_time_ms": {"type": "integer", "description": "Optional time budget override."},
                "max_cost_budget": {"type": "number", "description": "Optional cost budget override."},
                "force_llm_processing": {"type": "boolean", "description": "Force processing via LLM coordinator instead of internal tool."}
            },
            "required": ["query"]
        }
    
    def _get_output_schema(self) -> Dict[str, Any]:
        # Unified schema that can represent all internal tool outputs
        return {
            "type": "object",
            "properties": {
                "result": {"type": "object", "description": "The result data."},
                "metadata": {
                    "type": "object",
                    "properties": {
                        "execution_path": {"type": "string", "description": "Internal tool or LLM that handled the query."},
                        "confidence": {"type": "number", "description": "Confidence score for query classification."},
                        "execution_time_ms": {"type": "integer", "description": "Execution time in milliseconds."},
                        "error_details": {"type": "object", "description": "Error details, if any."}
                    }
                }
            },
            "required": ["result", "metadata"]
        }
        
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the general query tool with the provided data."""
        self.logger.info(f"Executing {self.name}...")
        start_time = time.time()
        
        query = data.get("query")
        if not query:
            raise ValidationError("Missing required parameter: query.")
        
        context = data.get("context", {})
        parameters = data.get("parameters", {})
        force_llm = data.get("force_llm_processing", False)
        
        try:
            # Determine if we should use direct internal tool routing or LLM coordinator
            if not force_llm:
                # Check if this is a natural language query or a structured query
                if isinstance(query, str):
                    # Natural language query - use classifier
                    query_type, confidence = self.query_classifier.classify(query, context)
                    self.logger.info(f"Query classified as {query_type} with confidence {confidence:.2f}")
                    
                    # If confidence is high enough, use internal tool
                    if confidence > 0.4:
                        return self._route_to_internal_tool(query_type, query, context, parameters, auth_context, start_time)
                else:
                    # Structured query - might have explicit tool information
                    if isinstance(query, dict) and query.get("tool"):
                        query_type = query.get("tool")
                        return self._route_to_internal_tool(query_type, query, context, parameters, auth_context, start_time)
            
            # Fall back to LLM coordinator for all other cases
            return self._route_to_llm_coordinator(query, context, parameters, data, auth_context, start_time)
                
        except Exception as e:
            self.logger.error(f"Error executing {self.name}: {e}", exc_info=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "result": {"error": str(e)},
                "metadata": {
                    "execution_path": "error",
                    "confidence": 0.0,
                    "execution_time_ms": elapsed_ms,
                    "error_details": {
                        "type": type(e).__name__,
                        "message": str(e)
                    }
                }
            }
    
    def _get_internal_tool(self, tool_type: str) -> Optional[InternalMCPTool]:
        """Get or create an internal tool instance for the specified type."""
        if tool_type not in self._internal_tools:
            self.logger.debug(f"Creating internal tool for type: {tool_type}")
            
            # Create tool instance based on type
            if tool_type == QueryClassifier.CONSISTENCY_ANALYSIS:
                self._internal_tools[tool_type] = InternalConsistencyAnalysisTool(self.adapter)
            elif tool_type == QueryClassifier.RECOMMENDATION_GENERATION:
                self._internal_tools[tool_type] = InternalRecommendationsGeneratorTool(self.adapter)
            elif tool_type == QueryClassifier.RECOMMENDATION_APPLICATION:
                self._internal_tools[tool_type] = InternalRecommendationApplicatorTool(self.adapter)
            elif tool_type == QueryClassifier.DOCUMENT_RELATIONSHIP:
                self._internal_tools[tool_type] = InternalDocumentRelationshipsTool(self.adapter)
            elif tool_type == QueryClassifier.VISUALIZATION:
                self._internal_tools[tool_type] = InternalMermaidDiagramTool(self.adapter)
                
        return self._internal_tools.get(tool_type)
    
    def _route_to_internal_tool(self, tool_type: str, query: Any, context: Dict[str, Any], 
                              parameters: Dict[str, Any], auth_context: Optional[Dict[str, Any]],
                              start_time: float) -> Dict[str, Any]:
        """Route a query to the appropriate internal tool."""
        self.logger.info(f"Routing query to internal tool: {tool_type}")
        
        internal_tool = self._get_internal_tool(tool_type)
        if not internal_tool:
            # No tool available for this type, fall back to LLM coordinator
            self.logger.info(f"No internal tool implementation for {tool_type}, falling back to LLM coordinator")
            return self._route_to_llm_coordinator(query, context, parameters, {
                "query": query,
                "context": context,
                "parameters": parameters
            }, auth_context, start_time)
        
        # Prepare input for the internal tool
        tool_input = self._prepare_internal_tool_input(tool_type, query, context, parameters)
        
        # Execute the internal tool
        try:
            result = internal_tool.execute(tool_input, auth_context)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Format the result according to our unified schema
            return {
                "result": result,
                "metadata": {
                    "execution_path": f"internal_tool:{tool_type}",
                    "confidence": 1.0,  # Internal tool execution is deterministic
                    "execution_time_ms": elapsed_ms
                }
            }
        except Exception as e:
            self.logger.error(f"Error in internal tool {tool_type}: {e}", exc_info=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "result": {"error": str(e)},
                "metadata": {
                    "execution_path": f"internal_tool:{tool_type}",
                    "confidence": 1.0,
                    "execution_time_ms": elapsed_ms,
                    "error_details": {
                        "type": type(e).__name__,
                        "message": str(e)
                    }
                }
            }
    
    def _prepare_internal_tool_input(self, tool_type: str, query: Any, context: Dict[str, Any], 
                                    parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare input for an internal tool based on tool type."""
        # Start with context and parameters
        tool_input = {**context, **parameters}
        
        # Add tool-specific parameters based on query content
        if tool_type == QueryClassifier.CONSISTENCY_ANALYSIS:
            # Extract or infer code_file_path and doc_file_path
            if isinstance(query, dict):
                tool_input["code_file_path"] = query.get("code_file_path") or context.get("code_file_path")
                tool_input["doc_file_path"] = query.get("doc_file_path") or context.get("doc_file_path")
            elif isinstance(query, str):
                # Try to extract file paths from query text
                code_match = re.search(r'code\s+file[:\s]+([^\s,]+)', query, re.IGNORECASE)
                if code_match:
                    tool_input["code_file_path"] = code_match.group(1)
                    
                doc_match = re.search(r'doc(?:umentation)?\s+file[:\s]+([^\s,]+)', query, re.IGNORECASE)
                if doc_match:
                    tool_input["doc_file_path"] = doc_match.group(1)
        
        elif tool_type == QueryClassifier.RECOMMENDATION_GENERATION:
            # Extract or infer inconsistency_ids
            if isinstance(query, dict):
                tool_input["inconsistency_ids"] = query.get("inconsistency_ids", [])
            elif isinstance(query, str):
                # Try to extract inconsistency IDs from query text
                id_matches = re.findall(r'inconsistency\s+ids?[:\s]+([a-zA-Z0-9\-_,\s]+)', query, re.IGNORECASE)
                if id_matches:
                    # Parse comma-separated IDs
                    ids_text = id_matches[0]
                    tool_input["inconsistency_ids"] = [id.strip() for id in ids_text.split(',')]
        
        elif tool_type == QueryClassifier.RECOMMENDATION_APPLICATION:
            # Extract or infer recommendation_id
            if isinstance(query, dict):
                tool_input["recommendation_id"] = query.get("recommendation_id")
            elif isinstance(query, str):
                # Try to extract recommendation ID from query text
                rec_match = re.search(r'recommendation\s+id[:\s]+([a-zA-Z0-9\-_]+)', query, re.IGNORECASE)
                if rec_match:
                    tool_input["recommendation_id"] = rec_match.group(1)
        
        elif tool_type == QueryClassifier.DOCUMENT_RELATIONSHIP:
            # Extract or infer doc_file_path or analysis_type
            if isinstance(query, dict):
                tool_input["doc_file_path"] = query.get("doc_file_path")
                tool_input["analysis_type"] = query.get("analysis_type", "all")
            elif isinstance(query, str):
                # Try to extract document path from query text
                doc_match = re.search(r'document[:\s]+([^\s,]+)', query, re.IGNORECASE)
                if doc_match:
                    tool_input["doc_file_path"] = doc_match.group(1)
                
                # Try to determine analysis type from query text
                if "dependencies" in query.lower():
                    tool_input["analysis_type"] = "dependencies"
                elif "impacts" in query.lower():
                    tool_input["analysis_type"] = "impacts"
                else:
                    tool_input["analysis_type"] = "all"  # Default
        
        elif tool_type == QueryClassifier.VISUALIZATION:
            # Extract or infer diagram_type and related parameters
            if isinstance(query, dict):
                tool_input["diagram_type"] = query.get("diagram_type", "relationships")
                tool_input["doc_file_path"] = query.get("doc_file_path")
            elif isinstance(query, str):
                # Try to determine diagram type from query text
                if "class" in query.lower():
                    tool_input["diagram_type"] = "class"
                elif "sequence" in query.lower():
                    tool_input["diagram_type"] = "sequence"
                elif "flowchart" in query.lower():
                    tool_input["diagram_type"] = "flowchart"
                else:
                    tool_input["diagram_type"] = "relationships"  # Default
                
                # Try to extract document path for relationship diagrams
                doc_match = re.search(r'document[:\s]+([^\s,]+)', query, re.IGNORECASE)
                if doc_match:
                    tool_input["doc_file_path"] = doc_match.group(1)
        
        return tool_input
    
    def _route_to_llm_coordinator(self, query: Any, context: Dict[str, Any], parameters: Dict[str, Any], 
                                 data: Dict[str, Any], auth_context: Optional[Dict[str, Any]],
                                 start_time: float) -> Dict[str, Any]:
        """Route a query to the LLM coordinator."""
        self.logger.info("Routing query to LLM coordinator")
        
        try:
            coordinator: LLMCoordinatorComponent = self.adapter.llm_coordinator
            request = CoordinatorRequest(
                query=query,
                context=context,
                parameters=parameters,
                max_execution_time_ms=data.get("max_execution_time_ms"),
                max_cost_budget=data.get("max_cost_budget")
            )
            
            coordinator_response = coordinator.process_request(request)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            # Format the result according to our unified schema
            return {
                "result": coordinator_response.results,
                "metadata": {
                    "execution_path": "llm_coordinator",
                    "confidence": 0.0,  # No confidence measure for LLM coordinator
                    "execution_time_ms": elapsed_ms,
                    "llm_metadata": coordinator_response.metadata,
                    "budget_info": coordinator_response.budget_info
                }
            }
        except Exception as e:
            self.logger.error(f"Error in LLM coordinator: {e}", exc_info=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            return {
                "result": {"error": str(e)},
                "metadata": {
                    "execution_path": "llm_coordinator",
                    "confidence": 0.0,
                    "execution_time_ms": elapsed_ms,
                    "error_details": {
                        "type": type(e).__name__,
                        "message": str(e)
                    }
                }
            }

class CommitMessageTool(MCPTool):
    """
    [Class intent]
    Public tool for generating comprehensive commit messages based on code changes.
    
    [Implementation details]
    Analyzes code changes to generate descriptive and structured commit messages
    following configurable formats and conventions.
    
    [Design principles]
    Comprehensive analysis - identifies and summarizes all relevant changes
    Configurable output - supports different commit message formats
    Context-aware - provides change context and impact analysis
    
    [Example usage]
    1. Basic usage with default parameters:
    ```python
    response = commit_message_tool.execute({})
    print(response["commit_message"])
    ```

    2. With a specific base commit:
    ```python
    response = commit_message_tool.execute({
        "since_commit": "a1b2c3d"
    })
    ```

    3. With format customization:
    ```python
    response = commit_message_tool.execute({
        "format": "conventional",
        "include_scope": True,
        "max_length": 72
    })
    ```
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="dbp_commit_message",
            description="Generate comprehensive commit messages based on recent changes.",
            logger_override=logger_override
        )
        self.adapter = adapter
        
    def _get_input_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define a comprehensive input schema for generating commit messages.
        
        [Implementation details]
        Supports various parameters to control commit message generation.
        
        [Design principles]
        Flexibility - supports multiple options for commit message generation
        Clarity - clearly documents all possible parameters
        """
        return {
            "type": "object",
            "properties": {
                # Core parameters
                "since_commit": {
                    "type": "string",
                    "description": "Optional commit hash to use as base reference for changes."
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific files to include in the commit message (if not specified, all changed files are considered)."
                },
                
                # Format control parameters
                "format": {
                    "type": "string",
                    "enum": ["conventional", "detailed", "simple"],
                    "default": "conventional",
                    "description": "Format style for the commit message."
                },
                "include_scope": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include scope information in conventional commit format."
                },
                "max_length": {
                    "type": "integer",
                    "description": "Maximum length for the commit message subject line."
                },
                
                # Content control parameters
                "include_breaking_changes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to highlight breaking changes in the commit message."
                },
                "include_tests": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include test changes in the commit message."
                },
                "include_issues": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include references to issue numbers."
                }
            }
        }
        
    def _get_output_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define a comprehensive output schema for commit message generation.
        
        [Implementation details]
        Provides both the generated commit message and additional metadata about the changes.
        
        [Design principles]
        Completeness - provides both the message and supporting information
        Usefulness - includes information that helps understand the commit scope
        """
        return {
            "type": "object",
            "properties": {
                # Primary output
                "commit_message": {
                    "type": "string",
                    "description": "Generated commit message."
                },
                
                # Supporting metadata
                "changes_summary": {
                    "type": "object",
                    "properties": {
                        "files_changed": {
                            "type": "integer",
                            "description": "Number of files changed."
                        },
                        "insertions": {
                            "type": "integer",
                            "description": "Number of lines inserted."
                        },
                        "deletions": {
                            "type": "integer",
                            "description": "Number of lines deleted."
                        },
                        "file_details": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "path": {
                                        "type": "string",
                                        "description": "File path."
                                    },
                                    "changes": {
                                        "type": "string",
                                        "description": "Summary of changes to this file."
                                    },
                                    "impact": {
                                        "type": "string",
                                        "description": "Impact analysis of changes to this file."
                                    }
                                }
                            },
                            "description": "Details about each changed file."
                        }
                    }
                },
                
                # Analysis results
                "breaking_changes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of detected breaking changes."
                },
                "related_issues": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of related issue references detected in the changes."
                },
                
                # Execution metadata
                "metadata": {
                    "type": "object",
                    "properties": {
                        "execution_time_ms": {
                            "type": "integer",
                            "description": "Execution time in milliseconds."
                        },
                        "base_commit": {
                            "type": "string",
                            "description": "Base commit used for comparison."
                        },
                        "llm_metadata": {
                            "type": "object",
                            "description": "Metadata from LLM processing."
                        }
                    }
                }
            },
            "required": ["commit_message"]
        }
        
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute the commit message generator with the provided data."""
        self.logger.info(f"Executing {self.name}...")
        start_time = time.time()
        
        try:
            # For now, return a placeholder implementation
            # In a real implementation, we would:
            # 1. Validate the input against the schema
            # 2. Determine the base commit to compare against
            # 3. Analyze the changes
            # 4. Generate the commit message
            # 5. Format the results according to the schema
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return {
                "commit_message": "feat(mcp): implement enhanced schema standardization",
                "changes_summary": {
                    "files_changed": 3,
                    "insertions": 150,
                    "deletions": 30,
                    "file_details": [
                        {
                            "path": "src/dbp/mcp_server/tools.py",
                            "changes": "Updated schema definitions",
                            "impact": "Improved API documentation and validation"
                        }
                    ]
                },
                "breaking_changes": [],
                "related_issues": ["GH-123"],
                "metadata": {
                    "execution_time_ms": elapsed_ms,
                    "base_commit": data.get("since_commit", "HEAD~1"),
                    "llm_metadata": {}
                }
            }
        except Exception as e:
            self.logger.error(f"Error generating commit message: {e}", exc_info=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return {
                "commit_message": "Error generating commit message",
                "changes_summary": {"files_changed": 0},
                "metadata": {
                    "execution_time_ms": elapsed_ms,
                    "error": str(e)
                }
            }
