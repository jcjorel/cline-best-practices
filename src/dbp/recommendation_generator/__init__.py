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
# Recommendation Generator package for the Documentation-Based Programming system.
# Generates recommendations for maintaining documentation consistency.
###############################################################################
# [Source file design principles]
# - Exports only the essential classes and functions needed by other components
# - Maintains a clean public API with implementation details hidden
# - Uses explicit imports rather than wildcard imports
###############################################################################
# [Source file constraints]
# - Must avoid circular imports
# - Should maintain backward compatibility for public interfaces
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T21:58:23Z : Added GenAI header to comply with documentation standards by CodeAssistant
# * Added complete header template with appropriate sections
###############################################################################


# src/dbp/recommendation_generator/__init__.py

"""
Recommendation Generator package for the Documentation-Based Programming system.

Generates actionable recommendations to fix inconsistencies detected between
documentation and code, utilizing various strategies and potentially LLMs.

Key components:
- RecommendationGeneratorComponent: The main component conforming to the core framework.
- RecommendationStrategy: Abstract base class for different fix generation approaches.
- StrategySelector: Selects the appropriate strategy based on inconsistency type.
- GeneratorEngine: Orchestrates recommendation generation using selected strategies.
- LLMIntegration: Handles interaction with LLMs for generating fix suggestions.
- FormattingEngine: Formats recommendations for display.
- FeedbackAnalyzer: Processes user feedback on recommendations.
- RecommendationRepository: Persists recommendation data.
- Data Models: Defines structures like Recommendation, RecommendationFeedback, etc.
"""

# Expose key classes, data models, and exceptions for easier import
from .data_models import (
    Recommendation,
    RecommendationFeedback,
    RecommendationFixType,
    RecommendationSeverity,
    RecommendationStatus
)
from .repository import RecommendationRepository, RepositoryError, RecommendationNotFoundError
from .strategy import RecommendationStrategy # ABC
# Expose concrete strategies only if needed externally
# from .strategy import DocumentationLinkFixStrategy, ...
from .selector import StrategySelector, StrategyNotFoundError
from .engine import GeneratorEngine
from .llm_integration import LLMIntegration, LLMIntegrationError
from .formatter import FormattingEngine
from .feedback import FeedbackAnalyzer
from .component import RecommendationGeneratorComponent, ComponentNotInitializedError

__all__ = [
    # Main Component
    "RecommendationGeneratorComponent",
    # Core Classes (Expose interfaces/facades)
    "RecommendationRepository",
    "StrategySelector",
    "GeneratorEngine",
    "LLMIntegration",
    "FormattingEngine",
    "FeedbackAnalyzer",
    "RecommendationStrategy", # ABC
    # Data Models & Enums
    "Recommendation",
    "RecommendationFeedback",
    "RecommendationFixType",
    "RecommendationSeverity",
    "RecommendationStatus",
    # Exceptions
    "RepositoryError",
    "RecommendationNotFoundError",
    "StrategyNotFoundError",
    "LLMIntegrationError",
    "ComponentNotInitializedError",
]
