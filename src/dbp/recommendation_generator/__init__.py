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
