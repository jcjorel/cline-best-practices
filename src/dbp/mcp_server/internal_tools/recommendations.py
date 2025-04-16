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
# Implements internal tools for recommendation generation and application.
# These tools support the public dbp_general_query tool but are not directly exposed.
###############################################################################
# [Source file design principles]
# - Prefix class names with 'Internal' to indicate private status
# - Maintain the same functionality as original tools
# - Use common base class and error handling
# - Follow consistent interface pattern
###############################################################################
# [Source file constraints]
# - Not to be used directly by MCP clients
# - Only accessed through the public tools defined in tools.py
# - Must maintain compatibility with existing recommendation tools
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/mcp_tools_refactoring_plan/plan_overview.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T09:21:00Z : Created recommendations internal tools by CodeAssistant
# * Migrated GenerateRecommendationsTool and ApplyRecommendationTool to internal implementations
###############################################################################

import logging
from typing import Dict, Any, Optional, List

from .base import InternalMCPTool, InternalToolValidationError, InternalToolExecutionError

# Import necessary components
try:
    from ...recommendation_generator.component import RecommendationGeneratorComponent
    from ..adapter import SystemComponentAdapter, ComponentNotFoundError
except ImportError as e:
    logging.getLogger(__name__).error(f"Recommendations Tools ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    RecommendationGeneratorComponent = object
    SystemComponentAdapter = object
    ComponentNotFoundError = Exception

logger = logging.getLogger(__name__)

# Define exception that might be raised by the recommendation component
class RecommendationNotFoundError(Exception):
    """Exception raised when a recommendation with a specific ID is not found."""
    pass

class InternalRecommendationsGeneratorTool(InternalMCPTool):
    """
    [Class intent]
    Internal tool for generating recommendations based on inconsistencies.
    Equivalent to the original GenerateRecommendationsTool but designed
    to be used only by the public dbp_general_query tool.
    
    [Implementation details]
    Uses the RecommendationGeneratorComponent to generate recommendations for
    a list of inconsistency IDs.
    
    [Design principles]
    Maintain existing functionality but with clear internal status,
    consistent error handling, and integration with the internal tools framework.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="recommendations_generator", 
            adapter=adapter,
            logger_override=logger_override
        )
    
    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "inconsistency_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of inconsistency IDs to generate recommendations for.",
                    "minItems": 1
                }
            },
            "required": ["inconsistency_ids"]
        }
        
    def _get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "List of generated recommendations."
                }
            },
            "required": ["recommendations"]
        }
        
    def _execute_implementation(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Generate recommendations for a list of inconsistency IDs."""
        inconsistency_ids = data.get("inconsistency_ids")
        
        if not inconsistency_ids or not isinstance(inconsistency_ids, list):
            raise InternalToolValidationError("Missing or invalid required parameter: inconsistency_ids (must be a non-empty list).")
        
        try:
            recommender: RecommendationGeneratorComponent = self.adapter.recommendation_generator
            recommendations = recommender.generate_recommendations_for_inconsistencies(inconsistency_ids)
            
            return {
                "recommendations": [rec.__dict__ for rec in recommendations]
            }
        except ComponentNotFoundError as e:
            self.logger.error(f"Dependency error: {e}")
            raise InternalToolExecutionError(f"Internal component error: {e}") from e
        except Exception as e:
            self.logger.error(f"Error during recommendation generation: {e}", exc_info=True)
            raise InternalToolExecutionError(f"Failed to generate recommendations: {e}") from e


class InternalRecommendationApplicatorTool(InternalMCPTool):
    """
    [Class intent]
    Internal tool for applying recommendations.
    Equivalent to the original ApplyRecommendationTool but designed
    to be used only by the public dbp_general_query tool.
    
    [Implementation details]
    Uses the RecommendationGeneratorComponent to apply a specific recommendation
    identified by its unique ID.
    
    [Design principles]
    Maintain existing functionality but with clear internal status,
    consistent error handling, and integration with the internal tools framework.
    """
    
    def __init__(self, adapter: SystemComponentAdapter, logger_override: Optional[logging.Logger] = None):
        super().__init__(
            name="recommendation_applicator", 
            adapter=adapter,
            logger_override=logger_override
        )
    
    def _get_input_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "recommendation_id": {"type": "string", "description": "The ID of the recommendation to apply."}
            },
            "required": ["recommendation_id"]
        }
        
    def _get_output_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string", "enum": ["applied", "failed", "not_found"]},
                "message": {"type": "string", "description": "Result message."}
            },
            "required": ["status", "message"]
        }
        
    def _execute_implementation(self, data: Dict[str, Any], auth_context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Apply a recommendation identified by its ID."""
        rec_id = data.get("recommendation_id")
        
        if not rec_id:
            raise InternalToolValidationError("Missing required parameter: recommendation_id.")
        
        try:
            recommender: RecommendationGeneratorComponent = self.adapter.recommendation_generator
            success = recommender.apply_recommendation(rec_id)
            
            if success:
                return {"status": "applied", "message": f"Recommendation '{rec_id}' applied successfully."}
            else:
                return {"status": "failed", "message": f"Failed to apply recommendation '{rec_id}'. Check logs."}
        except ComponentNotFoundError as e:
            self.logger.error(f"Dependency error: {e}")
            raise InternalToolExecutionError(f"Internal component error: {e}") from e
        except RecommendationNotFoundError:
            return {"status": "not_found", "message": f"Recommendation '{rec_id}' not found."}
        except Exception as e:
            self.logger.error(f"Error applying recommendation: {e}", exc_info=True)
            raise InternalToolExecutionError(f"Failed to apply recommendation '{rec_id}': {e}") from e
