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
# - src/dbp/mcp_server/mcp_protocols.py
# - src/dbp/mcp_server/adapter.py
###############################################################################
# [GenAI tool change history]
# 2025-04-16T14:33:45Z : Renamed GenerateRecommendationsTool to CommitMessageTool by CodeAssistant
# * Renamed class per DESIGN.md specifications while preserving all functionality
# * Ensured the tool continues to use dbp_commit_message name in its initialization
# 2025-04-16T14:17:04Z : Added AnalyzeDocumentConsistencyTool class by CodeAssistant
# * Implemented missing AnalyzeDocumentConsistencyTool class that was referenced but not implemented
# * Added comprehensive input/output schemas with detailed documentation 
# * Added placeholder execution logic for consistency analysis
# 2025-04-16T10:50:00Z : Removed all manual classification code by CodeAssistant
# * Removed QueryClassifier class and all related code
# * Removed internal tool initialization, routing and input preparation methods
# * Simplified imports to only essential modules
# * Updated GeneralQueryTool class documentation to reflect direct LLM routing
# 2025-04-16T10:47:00Z : Enforced LLM coordinator processing for all queries by CodeAssistant
# * Removed manual classification fallback in GeneralQueryTool
# * Updated GeneralQueryTool to route all queries directly to LLM coordinator
# * Ensured consistent natural language handling across MCP tools
###############################################################################

import logging
import time
import re
from typing import Dict, Any, Optional, List, Tuple

# Import required modules
try:
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


logger = logging.getLogger(__name__)

# --- Base Exception for Tool Errors ---
class ToolExecutionError(Exception):
    """Custom exception for errors during tool execution."""
    pass

class ValidationError(ValueError):
     """Custom exception for input validation errors."""
     pass

# --- Documented Public Tool Implementations ---


class GeneralQueryTool(MCPTool):
    """
    [Class intent]
    Public tool for handling all types of queries about the codebase and documentation.
    
    [Implementation details]
    Routes all natural language queries to the LLM coordinator without any manual classification.
    The LLM coordinator is responsible for understanding query intent and invoking the appropriate
    internal tools.
    
    [Design principles]
    Single entry point for queries, consistent natural language interface, uniform response format,
    detailed execution metadata.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="dbp_general_query",
            description="Retrieve various types of codebase metadata and perform document operations.",
            logger_override=logger_override
        )
        self.adapter = adapter
    
    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The natural language query."},
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
        
        if not isinstance(query, str):
            raise ValidationError("Query must be a natural language string, not a structured object.")
        
        context = data.get("context", {})
        parameters = data.get("parameters", {})
        
        try:
            # All queries must go through the LLM coordinator for classification
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

class AnalyzeDocumentConsistencyTool(MCPTool):
    """
    [Class intent]
    Public tool for analyzing documentation consistency across project files.
    
    [Implementation details]
    Leverages the consistency analysis engine to detect inconsistencies between
    documentation files, source code, and associated metadata. Supports analyzing
    specific documents or entire document sets against predefined consistency rules.
    
    [Design principles]
    Comprehensive analysis - checks multiple consistency aspects
    Detailed reporting - provides actionable inconsistency details
    Configurable scope - allows focusing on specific documents or rules
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="dbp_analyze_document_consistency",
            description="Analyze documentation consistency across project files.",
            logger_override=logger_override
        )
        self.adapter = adapter
        
    def _get_input_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define the input schema for document consistency analysis requests.
        
        [Implementation details]
        Supports parameters to control the scope and depth of analysis.
        
        [Design principles]
        Flexibility - allows focusing on specific documents or rules
        Clarity - clearly documents all analysis parameters
        """
        return {
            "type": "object",
            "properties": {
                # Core parameters
                "document_paths": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific document paths to analyze. If not provided, analyzes all indexed documents."
                },
                "rule_categories": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of rule categories to apply. If not provided, applies all rule categories."
                },
                "include_source_code": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include source code files in the analysis."
                },
                
                # Analysis control parameters
                "max_depth": {
                    "type": "integer",
                    "default": 2,
                    "description": "Maximum depth for relationship analysis."
                },
                "severity_threshold": {
                    "type": "string",
                    "enum": ["info", "warning", "error", "critical"],
                    "default": "warning",
                    "description": "Minimum severity level to include in results."
                },
                "include_context": {
                    "type": "boolean",
                    "default": True,
                    "description": "Whether to include surrounding context for inconsistencies."
                }
            }
        }
        
    def _get_output_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define the output schema for document consistency analysis results.
        
        [Implementation details]
        Provides detailed inconsistency information with context and recommendations.
        
        [Design principles]
        Actionability - includes specific locations and recommendations
        Comprehensiveness - provides multiple views of inconsistency data
        """
        return {
            "type": "object",
            "properties": {
                # Primary output
                "inconsistencies": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {
                                "type": "string",
                                "description": "Unique identifier for the inconsistency."
                            },
                            "severity": {
                                "type": "string",
                                "enum": ["info", "warning", "error", "critical"],
                                "description": "Severity level of the inconsistency."
                            },
                            "rule_category": {
                                "type": "string",
                                "description": "Category of the rule that detected the inconsistency."
                            },
                            "rule_id": {
                                "type": "string",
                                "description": "Identifier of the specific rule that was violated."
                            },
                            "description": {
                                "type": "string",
                                "description": "Human-readable description of the inconsistency."
                            },
                            "locations": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "document_path": {
                                            "type": "string",
                                            "description": "Path to the document containing the inconsistency."
                                        },
                                        "line_number": {
                                            "type": "integer",
                                            "description": "Line number where the inconsistency occurs."
                                        },
                                        "context": {
                                            "type": "string",
                                            "description": "Context surrounding the inconsistency."
                                        }
                                    }
                                },
                                "description": "Locations where the inconsistency appears."
                            },
                            "recommendation": {
                                "type": "string",
                                "description": "Recommended action to resolve the inconsistency."
                            }
                        }
                    },
                    "description": "List of detected inconsistencies."
                },
                
                # Summary statistics
                "summary": {
                    "type": "object",
                    "properties": {
                        "total_documents_analyzed": {
                            "type": "integer",
                            "description": "Total number of documents analyzed."
                        },
                        "total_inconsistencies": {
                            "type": "integer",
                            "description": "Total number of inconsistencies found."
                        },
                        "by_severity": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "integer"
                            },
                            "description": "Count of inconsistencies by severity level."
                        },
                        "by_rule_category": {
                            "type": "object",
                            "additionalProperties": {
                                "type": "integer"
                            },
                            "description": "Count of inconsistencies by rule category."
                        }
                    },
                    "description": "Summary statistics about the analysis results."
                },
                
                # Execution metadata
                "metadata": {
                    "type": "object",
                    "properties": {
                        "execution_time_ms": {
                            "type": "integer",
                            "description": "Execution time in milliseconds."
                        },
                        "rules_applied": {
                            "type": "integer",
                            "description": "Number of consistency rules applied."
                        },
                        "analysis_timestamp": {
                            "type": "string",
                            "description": "ISO timestamp when analysis was performed."
                        }
                    }
                }
            },
            "required": ["inconsistencies", "summary", "metadata"]
        }
        
    def execute(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute document consistency analysis with the provided parameters."""
        self.logger.info(f"Executing {self.name}...")
        start_time = time.time()
        
        try:
            # Extract and validate parameters
            document_paths = data.get("document_paths", [])
            rule_categories = data.get("rule_categories", [])
            include_source_code = data.get("include_source_code", True)
            max_depth = data.get("max_depth", 2)
            severity_threshold = data.get("severity_threshold", "warning")
            include_context = data.get("include_context", True)
            
            # For now, return a placeholder implementation
            # In a real implementation, we would:
            # 1. Access the consistency_analysis component via self.adapter
            # 2. Invoke the appropriate analysis method
            # 3. Format the results according to the schema
            
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            severity_levels = ["info", "warning", "error", "critical"]
            severity_counts = {level: 0 for level in severity_levels}
            severity_counts["warning"] = 2  # Example data
            severity_counts["error"] = 1    # Example data
            
            rule_categories_counts = {
                "header_compliance": 1,
                "documentation_content": 1,
                "cross_references": 1
            }
            
            return {
                "inconsistencies": [
                    {
                        "id": "inc-001",
                        "severity": "warning",
                        "rule_category": "header_compliance",
                        "rule_id": "header-complete-sections",
                        "description": "Missing design principles section in file header",
                        "locations": [
                            {
                                "document_path": "src/dbp/consistency_analysis/analyzer.py",
                                "line_number": 10,
                                "context": "# [Source file intent]\n# Implements the core analysis logic...\n# [Source file constraints]"
                            }
                        ],
                        "recommendation": "Add the missing [Source file design principles] section between intent and constraints."
                    },
                    {
                        "id": "inc-002",
                        "severity": "warning",
                        "rule_category": "documentation_content",
                        "rule_id": "function-doc-sections",
                        "description": "Function missing required documentation sections",
                        "locations": [
                            {
                                "document_path": "src/dbp/consistency_analysis/analyzer.py",
                                "line_number": 142,
                                "context": "def analyze_documents(self, document_paths):\n    \"\"\"Analyze documents for consistency issues.\"\"\"\n    # Implementation..."
                            }
                        ],
                        "recommendation": "Add the missing [Implementation details] and [Design principles] sections to the function documentation."
                    },
                    {
                        "id": "inc-003",
                        "severity": "error",
                        "rule_category": "cross_references",
                        "rule_id": "broken-doc-references",
                        "description": "Broken reference to non-existent documentation file",
                        "locations": [
                            {
                                "document_path": "src/dbp/consistency_analysis/analyzer.py",
                                "line_number": 22,
                                "context": "# [Reference documentation]\n# - doc/DESIGN.md\n# - doc/ANALYSIS_RULES.md  # This file doesn't exist"
                            }
                        ],
                        "recommendation": "Either create the referenced file at 'doc/ANALYSIS_RULES.md' or remove the reference."
                    }
                ],
                "summary": {
                    "total_documents_analyzed": 10,
                    "total_inconsistencies": 3,
                    "by_severity": severity_counts,
                    "by_rule_category": rule_categories_counts
                },
                "metadata": {
                    "execution_time_ms": elapsed_ms,
                    "rules_applied": 15,
                    "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
                }
            }
        except Exception as e:
            self.logger.error(f"Error analyzing document consistency: {e}", exc_info=True)
            elapsed_ms = int((time.time() - start_time) * 1000)
            
            return {
                "inconsistencies": [],
                "summary": {
                    "total_documents_analyzed": 0,
                    "total_inconsistencies": 0,
                    "by_severity": {},
                    "by_rule_category": {}
                },
                "metadata": {
                    "execution_time_ms": elapsed_ms,
                    "error": str(e)
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
            # Validate important parameters to ensure they're strings if provided
            if "since_commit" in data and not isinstance(data["since_commit"], str):
                raise ValidationError("Since commit must be a string, not a structured object.")
                
            # Validate that any other string parameters are actually strings
            for param_name in ["format"]:
                if param_name in data and not isinstance(data[param_name], str):
                    raise ValidationError(f"Parameter '{param_name}' must be a string, not a structured object.")
            
            # For now, return a placeholder implementation
            # In a real implementation, we would:
            # 1. Further validate the input against the schema
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
