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
# Implements minimized versions of MCPTool classes for standalone mode testing.
# Each tool class maintains the same interface as the original but returns
# standardized error responses instead of attempting to access unavailable
# components. This enables progressive integration testing.
###############################################################################
# [Source file design principles]
# - Each class inherits from `MCPTool` maintaining the original interface.
# - Input/output schemas match the original implementations.
# - `execute` methods return standardized error responses for tool unavailability.
# - Uses simplified `SystemComponentAdapter` to avoid actual component dependencies.
# - Includes clear logging for standalone mode operation.
# - Design Decision: Standalone Tool Response (2025-04-25)
#   * Rationale: Allows MCP server to provide consistent responses during progressive integration.
#   * Alternatives considered: Dynamic component loading, real component stubs (both more complex).
###############################################################################
# [Source file constraints]
# - Must maintain the same interface as the original tools.
# - Should not attempt to access unavailable components.
# - Must provide standardized error responses.
# - Must provide clear log messages indicating standalone operation.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# other:- src/dbp/mcp_server/mcp_protocols.py
# other:- src/dbp/mcp_server/adapter.py (minimized version)
###############################################################################
# [GenAI tool change history]
# 2025-04-25T00:13:00Z : Created minimized tool implementations by CodeAssistant
# * Created standalone versions of MCPTool implementations for progressive integration testing
# * Implemented standardized error responses for all tools
# * Added clear logging for standalone mode operation
###############################################################################

import logging
import time
from typing import Dict, Any, Optional, List, Tuple

# Import required modules with fallback implementations
try:
    from .mcp_protocols import MCPTool
    from .adapter import SystemComponentAdapter, ComponentNotFoundError
except ImportError as e:
    logging.getLogger(__name__).error(f"MCP Tools ImportError: {e}. Using mock implementations.", exc_info=True)
    # Placeholders
    class MCPTool:
        """Mock MCPTool base class."""
        def __init__(self, name, description, logger_override=None):
            self.name = name
            self.description = description
            self.logger = logger_override or logging.getLogger(__name__)
            
        def _get_input_schema(self):
            return {}
            
        def _get_output_schema(self):
            return {}
            
        def execute(self, data, auth_context=None):
            return {}
            
    class SystemComponentAdapter:
        """Mock SystemComponentAdapter."""
        pass
        
    class ComponentNotFoundError(Exception):
        """Mock ComponentNotFoundError."""
        pass

logger = logging.getLogger(__name__)

# --- Base Exception for Tool Errors ---
class ToolExecutionError(Exception):
    """Custom exception for errors during tool execution."""
    pass

class ValidationError(ValueError):
     """Custom exception for input validation errors."""
     pass

# --- Standard Error Response ---
def create_error_response(tool_name, elapsed_ms=0):
    """
    Creates a standardized error response for tools in standalone mode.
    
    Args:
        tool_name: Name of the tool that was requested
        elapsed_ms: Elapsed time in milliseconds (optional)
        
    Returns:
        A dictionary containing the error response
    """
    return {
        "result": {
            "status": "error",
            "error_code": "STANDALONE_MODE",
            "message": f"Tool '{tool_name}' is running in standalone mode - actual functionality is unavailable",
            "details": "The MCP server is running with minimal dependencies for progressive integration testing."
        },
        "metadata": {
            "execution_path": "standalone_mode",
            "execution_time_ms": elapsed_ms,
            "standalone": True,
            "error_details": {
                "type": "StandaloneOperationError",
                "message": "Component dependencies are not available in standalone mode"
            }
        }
    }

# --- Minimized Tool Implementations ---

class GeneralQueryTool(MCPTool):
    """
    [Class intent]
    Minimized version of the GeneralQueryTool for standalone mode testing.
    
    [Implementation details]
    Returns a standardized error response to indicate standalone mode operation.
    Does not attempt to access any external components.
    
    [Design principles]
    Maintains the same interface as the original tool, provides clear error indication.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        """
        [Function intent]
        Initialize the tool with a SystemComponentAdapter.
        
        [Implementation details]
        Stores adapter reference but doesn't use it for actual component access.
        
        [Design principles]
        Maintains interface compatibility with the original tool.
        """
        super().__init__(
            name="dbp_general_query",
            description="Retrieve various types of codebase metadata and perform document operations.",
            logger_override=logger_override
        )
        self.adapter = adapter
        logger.warning(f"[STANDALONE MODE] {self.name} initialized - will return standardized error responses")

    def _get_input_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define the input schema for general queries.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
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
        """
        [Function intent]
        Define the output schema for general query results.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
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
        """
        [Function intent]
        Execute the general query tool with the provided data.
        
        [Implementation details]
        In standalone mode, just returns a standardized error response.
        
        [Design principles]
        Clear error indication without attempting to access unavailable components.
        """
        self.logger.info(f"[STANDALONE MODE] Executing {self.name}...")
        start_time = time.time()
        
        # Basic validation
        query = data.get("query")
        if not query:
            raise ValidationError("Missing required parameter: query.")
            
        # Log the query but don't attempt to process it
        self.logger.info(f"[STANDALONE MODE] Received query: {query[:100]}...")
        
        # Wait a short time to simulate processing
        time.sleep(0.1)
        
        # Return standardized error response
        elapsed_ms = int((time.time() - start_time) * 1000)
        return create_error_response(self.name, elapsed_ms)


class AnalyzeDocumentConsistencyTool(MCPTool):
    """
    [Class intent]
    Minimized version of the AnalyzeDocumentConsistencyTool for standalone mode testing.
    
    [Implementation details]
    Returns a standardized error response to indicate standalone mode operation.
    Does not attempt to access any external components.
    
    [Design principles]
    Maintains the same interface as the original tool, provides clear error indication.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        """
        [Function intent]
        Initialize the tool with a SystemComponentAdapter.
        
        [Implementation details]
        Stores adapter reference but doesn't use it for actual component access.
        
        [Design principles]
        Maintains interface compatibility with the original tool.
        """
        super().__init__(
            name="dbp_analyze_document_consistency",
            description="Analyze documentation consistency across project files.",
            logger_override=logger_override
        )
        self.adapter = adapter
        logger.warning(f"[STANDALONE MODE] {self.name} initialized - will return standardized error responses")

    def _get_input_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define the input schema for document consistency analysis.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
        return {
            "type": "object",
            "properties": {
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
        Define the output schema for document consistency analysis.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
        return {
            "type": "object",
            "properties": {
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
        """
        [Function intent]
        Execute the document consistency analysis tool with the provided data.
        
        [Implementation details]
        In standalone mode, just returns a standardized error response with additional
        details specific to the document consistency analysis tool.
        
        [Design principles]
        Clear error indication without attempting to access unavailable components.
        """
        self.logger.info(f"[STANDALONE MODE] Executing {self.name}...")
        start_time = time.time()
        
        # Log the request parameters
        document_paths = data.get("document_paths", [])
        self.logger.info(f"[STANDALONE MODE] Requested analysis for {len(document_paths)} document(s)")
        
        # Wait a short time to simulate processing
        time.sleep(0.1)
        
        # Create a more specific error response for this tool
        elapsed_ms = int((time.time() - start_time) * 1000)
        
        # Return a response that's compatible with the expected output schema
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
                "rules_applied": 0,
                "analysis_timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "error": {
                    "status": "error",
                    "error_code": "STANDALONE_MODE",
                    "message": f"Tool '{self.name}' is running in standalone mode - actual functionality is unavailable",
                    "details": "The MCP server is running with minimal dependencies for progressive integration testing."
                }
            }
        }


class CommitMessageTool(MCPTool):
    """
    [Class intent]
    Minimized version of the CommitMessageTool for standalone mode testing.
    
    [Implementation details]
    Returns a standardized error response to indicate standalone mode operation.
    Does not attempt to access any external components.
    
    [Design principles]
    Maintains the same interface as the original tool, provides clear error indication.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        """
        [Function intent]
        Initialize the tool with a SystemComponentAdapter.
        
        [Implementation details]
        Stores adapter reference but doesn't use it for actual component access.
        
        [Design principles]
        Maintains interface compatibility with the original tool.
        """
        super().__init__(
            name="dbp_commit_message",
            description="Generate comprehensive commit messages based on recent changes.",
            logger_override=logger_override
        )
        self.adapter = adapter
        logger.warning(f"[STANDALONE MODE] {self.name} initialized - will return standardized error responses")

    def _get_input_schema(self) -> Dict[str, Any]:
        """
        [Function intent]
        Define the input schema for commit message generation.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
        return {
            "type": "object",
            "properties": {
                "since_commit": {
                    "type": "string",
                    "description": "Optional commit hash to use as base reference for changes."
                },
                "files": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional list of specific files to include in the commit message (if not specified, all changed files are considered)."
                },
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
        Define the output schema for commit message generation.
        
        [Implementation details]
        Identical to the original implementation to maintain interface compatibility.
        
        [Design principles]
        Full compatibility with the original tool's schema.
        """
        return {
            "type": "object",
            "properties": {
                "commit_message": {
                    "type": "string",
                    "description": "Generated commit message."
                },
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
        """
        [Function intent]
        Execute the commit message generation tool with the provided data.
        
        [Implementation details]
        In standalone mode, just returns a standardized error response with additional
        details specific to the commit message generation tool.
        
        [Design principles]
        Clear error indication without attempting to access unavailable components.
        """
        self.logger.info(f"[STANDALONE MODE] Executing {self.name}...")
        start_time = time.time()
        
        # Log the request parameters
        since_commit = data.get("since_commit", "HEAD~1")
        files = data.get("files", [])
        self.logger.info(f"[STANDALONE MODE] Requested commit message since '{since_commit}' for {len(files)} file(s)")
        
        # Wait a short time to simulate processing
        time.sleep(0.1)
        
        # Return a response that's compatible with the expected output schema
        elapsed_ms = int((time.time() - start_time) * 1000)
        return {
            "commit_message": "[STANDALONE MODE] Commit message generation not available",
            "changes_summary": {
                "files_changed": 0,
                "insertions": 0,
                "deletions": 0,
                "file_details": []
            },
            "breaking_changes": [],
            "related_issues": [],
            "metadata": {
                "execution_time_ms": elapsed_ms,
                "base_commit": since_commit,
                "error": {
                    "status": "error",
                    "error_code": "STANDALONE_MODE",
                    "message": f"Tool '{self.name}' is running in standalone mode - actual functionality is unavailable",
                    "details": "The MCP server is running with minimal dependencies for progressive integration testing."
                }
            }
        }
