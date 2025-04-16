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
# Implements internal tools for consistency analysis between code and documentation.
# These tools support the public dbp_general_query tool but are not directly exposed.
###############################################################################
# [Source file design principles]
# - Prefix class names with 'Internal' to indicate private status
# - Maintain the same functionality as original tool
# - Use common base class and error handling
# - Follow consistent interface pattern
###############################################################################
# [Source file constraints]
# - Not to be used directly by MCP clients
# - Only accessed through the public tools defined in tools.py
# - Must maintain compatibility with existing AnalyzeDocumentConsistencyTool
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T08:55:00Z : Created consistency analysis internal tool by CodeAssistant
# * Migrated AnalyzeDocumentConsistencyTool to internal implementation
###############################################################################

import logging
from typing import Dict, Any, Optional, List

from .base import InternalMCPTool, InternalToolValidationError, InternalToolExecutionError

# Import necessary components
try:
    from ...consistency_analysis.component import ConsistencyAnalysisComponent
    from ..adapter import SystemComponentAdapter, ComponentNotFoundError
except ImportError as e:
    logging.getLogger(__name__).error(f"Consistency Tools ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    ConsistencyAnalysisComponent = object
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception

logger = logging.getLogger(__name__)

class InternalConsistencyAnalysisTool(InternalMCPTool):
    """
    [Class intent]
    Internal tool for analyzing consistency between code and documentation.
    Equivalent to the original AnalyzeDocumentConsistencyTool but designed
    to be used only by the public dbp_general_query tool.
    
    [Implementation details]
    Uses the ConsistencyAnalysisComponent to analyze consistency between
    specified code and documentation files.
    
    [Design principles]
    Maintain existing functionality but with clear internal status,
    consistent error handling, and integration with the internal tools framework.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="consistency_analysis", 
            adapter=adapter,
            logger_override=logger_override
        )
    
    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "code_file_path": {"type": "string", "description": "Relative or absolute path to the code file."},
                "doc_file_path": {"type": "string", "description": "Relative or absolute path to the documentation file."},
                "analysis_level": {"type": "string", "enum": ["metadata", "full"], "default": "metadata", "description": "Level of analysis."}
            },
            "required": ["code_file_path", "doc_file_path"]
        }
        
    def _get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "inconsistencies": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of detected inconsistencies."
                },
                "summary": {"type": "object", "description": "Summary of inconsistencies."}
            },
            "required": ["inconsistencies", "summary"]
        }
        
    def _execute_implementation(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Analyze consistency between a code file and a documentation file."""
        code_path = data.get("code_file_path")
        doc_path = data.get("doc_file_path")
        
        if not code_path or not doc_path:
            raise InternalToolValidationError("Missing required parameters: code_file_path and doc_file_path.")
        
        try:
            consistency_component: ConsistencyAnalysisComponent = self.adapter.consistency_analysis
            inconsistencies = consistency_component.analyze_code_doc_consistency(code_path, doc_path)
            
            # Format result
            summary = {"count": len(inconsistencies)}
            return {
                "inconsistencies": [inc.__dict__ for inc in inconsistencies],
                "summary": summary
            }
        except ComponentNotFoundError as e:
            self.logger.error(f"Dependency error: {e}")
            raise InternalToolExecutionError(f"Internal component error: {e}") from e
        except Exception as e:
            self.logger.error(f"Error during consistency analysis: {e}", exc_info=True)
            raise InternalToolExecutionError(f"Failed to analyze consistency: {e}") from e
