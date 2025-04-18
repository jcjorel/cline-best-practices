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
# Implements the RecommendationGeneratorComponent class, the main entry point for
# the recommendation generation subsystem. It conforms to the Component protocol,
# initializes and manages its internal parts (repository, strategies, engine, etc.),
# registers strategies, and provides the public API for generating, formatting,
# applying, and managing recommendations based on detected inconsistencies.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Encapsulates the recommendation generation logic.
# - Declares dependencies ('database', 'consistency_analysis', 'llm_coordinator').
# - Initializes sub-components (repository, selector, engine, etc.) in `initialize`.
# - Registers concrete recommendation strategies.
# - Provides high-level methods delegating to internal services.
# - Manages its own initialization state.
# - Design Decision: Component Facade for Recommendations (2025-04-15)
#   * Rationale: Groups recommendation logic into a single component.
#   * Alternatives considered: Distributing logic across other components (less cohesive).
###############################################################################
# [Source file constraints]
# - Depends on core framework and other components ('database', 'consistency_analysis', 'llm_coordinator').
# - Requires all helper classes within `recommendation_generator` package.
# - Assumes configuration is available via InitializationContext.
# - Relies on placeholder implementations in strategies and LLM integration.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/core/component.py
# - All other files in src/dbp/recommendation_generator/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:43:30Z : Initial creation of RecommendationGeneratorComponent by CodeAssistant
# * Implemented Component protocol, initialization, strategy registration, and public API.
###############################################################################

import logging
from typing import List, Optional, Any, Dict

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    Config = Any # Placeholder
    RecommendationGeneratorConfig = Any # Placeholder
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for RecommendationGeneratorComponent.", exc_info=True)
    class Component: pass
    class InitializationContext: pass
    Config = Any
    RecommendationGeneratorConfig = Any

# Imports for internal services
try:
    from .data_models import Recommendation, RecommendationFeedback
    from .repository import RecommendationRepository, RepositoryError, RecommendationNotFoundError
    from .strategy import (
        RecommendationStrategy, DocumentationLinkFixStrategy, DocumentationTerminologyStrategy,
        DocumentationContentUpdateStrategy, CodeCommentUpdateStrategy, CodeHeaderFixStrategy,
        FunctionSignatureFixStrategy, ClassStructureFixStrategy
    )
    from .selector import StrategySelector, StrategyNotFoundError
    from .engine import GeneratorEngine
    from .llm_integration import LLMIntegration, LLMIntegrationError
    from .formatter import FormattingEngine
    from .feedback import FeedbackAnalyzer
    # Import dependencies
    from ..consistency_analysis.component import ConsistencyAnalysisComponent
    from ..consistency_analysis.data_models import InconsistencyRecord # For type hint
    from ..llm_coordinator.component import LLMCoordinatorComponent
    from ..database.database import DatabaseManager # For type hint
except ImportError as e:
    logging.getLogger(__name__).error(f"RecommendationGeneratorComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    Recommendation, RecommendationFeedback = object, object
    RecommendationRepository, RepositoryError, RecommendationNotFoundError = object, Exception, Exception
    RecommendationStrategy, DocumentationLinkFixStrategy, DocumentationTerminologyStrategy = object, object, object
    DocumentationContentUpdateStrategy, CodeCommentUpdateStrategy, CodeHeaderFixStrategy = object, object, object
    FunctionSignatureFixStrategy, ClassStructureFixStrategy = object, object
    StrategySelector, StrategyNotFoundError = object, Exception
    GeneratorEngine = object
    LLMIntegration, LLMIntegrationError = object, Exception
    FormattingEngine = object
    FeedbackAnalyzer = object
    ConsistencyAnalysisComponent = object
    InconsistencyRecord = object
    LLMCoordinatorComponent = object
    DatabaseManager = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class RecommendationGeneratorComponent(Component):
    """
    DBP system component responsible for generating actionable recommendations
    based on detected inconsistencies.
    """
    _initialized: bool = False
    _repository: Optional[RecommendationRepository] = None
    _strategy_selector: Optional[StrategySelector] = None
    _generator_engine: Optional[GeneratorEngine] = None
    _llm_integration: Optional[LLMIntegration] = None
    _formatter: Optional[FormattingEngine] = None
    _feedback_analyzer: Optional[FeedbackAnalyzer] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "recommendation_generator"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Needs database, consistency analysis results, and potentially LLM coordinator
        return ["database", "consistency_analysis", "llm_coordinator"]

    def initialize(self, context: InitializationContext):
        """
        [Function intent]
        Initializes the Recommendation Generator component and its sub-components.
        
        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Creates internal sub-components and registers recommendation strategies.
        Sets the _initialized flag when initialization succeeds.
        
        [Design principles]
        Explicit initialization with strong typing.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with typed configuration and resources
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get strongly-typed configuration
            config = context.get_typed_config()
            component_config = getattr(config, self.name)

            # Get dependent components
            db_component = context.get_component("database")
            self.consistency_component = context.get_component("consistency_analysis") # Keep ref if needed
            self.llm_component = context.get_component("llm_coordinator") # Keep ref

            # Get database manager using the method instead of accessing attribute
            db_manager = db_component.get_manager()

            # Instantiate sub-components
            self._repository = RecommendationRepository(db_manager=db_manager, logger_override=self.logger.getChild("repository"))
            self._strategy_selector = StrategySelector(config=component_config, logger_override=self.logger.getChild("selector"))
            self._generator_engine = GeneratorEngine(strategy_selector=self._strategy_selector, logger_override=self.logger.getChild("engine"))
            self._llm_integration = LLMIntegration(llm_component=self.llm_component, logger_override=self.logger.getChild("llm_integration"))
            self._formatter = FormattingEngine(logger_override=self.logger.getChild("formatter"))
            self._feedback_analyzer = FeedbackAnalyzer(logger_override=self.logger.getChild("feedback"))

            # Register available strategies
            self._register_strategies()

            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _register_strategies(self):
        """Instantiates and registers all concrete RecommendationStrategy implementations."""
        if not self._strategy_selector or not self._llm_integration:
             self.logger.error("Cannot register strategies: Selector or LLMIntegration not initialized.")
             return

        self.logger.debug("Registering recommendation strategies...")
        strategies_to_register = [
            DocumentationLinkFixStrategy(self._llm_integration, self.logger.getChild("DocLinkFix")),
            DocumentationTerminologyStrategy(self._llm_integration, self.logger.getChild("DocTerm")),
            DocumentationContentUpdateStrategy(self._llm_integration, self.logger.getChild("DocContent")),
            CodeCommentUpdateStrategy(self._llm_integration, self.logger.getChild("CodeComment")),
            CodeHeaderFixStrategy(self._llm_integration, self.logger.getChild("CodeHeader")),
            FunctionSignatureFixStrategy(self._llm_integration, self.logger.getChild("FuncSig")),
            ClassStructureFixStrategy(self._llm_integration, self.logger.getChild("ClassStruct")),
        ]

        count = 0
        for strategy_instance in strategies_to_register:
             try:
                  # Use the name property from the strategy instance itself
                  self._strategy_selector.register_strategy(strategy_instance.name, strategy_instance)
                  count += 1
             except (ValueError, TypeError) as e:
                  self.logger.error(f"Failed to register strategy '{strategy_instance.name}': {e}")
             except Exception as e:
                  self.logger.error(f"Unexpected error registering strategy '{strategy_instance.name}': {e}", exc_info=True)
        self.logger.info(f"Registered {count}/{len(strategies_to_register)} recommendation strategies.")


    def shutdown(self) -> None:
        """Performs cleanup for the recommendation generator component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        # Add cleanup logic if needed
        self._repository = None
        self._strategy_selector = None
        self._generator_engine = None
        self._llm_integration = None
        self._formatter = None
        self._feedback_analyzer = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Methods ---

    def generate_recommendations_for_inconsistencies(self, inconsistency_ids: List[str]) -> List[Recommendation]:
        """
        Generates recommendations for a specific list of inconsistency IDs.

        Args:
            inconsistency_ids: List of IDs for inconsistencies to address.

        Returns:
            A list of generated Recommendation objects.
        """
        if not self.is_initialized or not self.consistency_component or not self._generator_engine or not self._repository:
            raise ComponentNotInitializedError(self.name)

        self.logger.info(f"Requesting recommendations for {len(inconsistency_ids)} inconsistencies.")
        # Fetch inconsistency records from the ConsistencyAnalysis component's repository
        inconsistencies_to_process: List[InconsistencyRecord] = []
        if hasattr(self.consistency_component, 'get_inconsistencies'):
             # Assuming get_inconsistencies can take a list of IDs, or filter one by one
             # For simplicity, get one by one (less efficient)
             for inc_id in inconsistency_ids:
                  inc = self.consistency_component.get_inconsistencies(id=inc_id, limit=1) # Hypothetical method
                  if inc:
                       inconsistencies_to_process.append(inc[0])
                  else:
                       self.logger.warning(f"Inconsistency ID '{inc_id}' not found.")
        else:
             self.logger.error("ConsistencyAnalysisComponent does not have expected 'get_inconsistencies' method.")
             return []


        if not inconsistencies_to_process:
             self.logger.info("No valid inconsistencies found for the provided IDs.")
             return []

        # Generate recommendations using the engine
        recommendations = self._generator_engine.generate(inconsistencies_to_process)

        # Persist the generated recommendations
        saved_recommendations = []
        for rec in recommendations:
            try:
                self._repository.save(rec) # Save and update ID in rec object
                saved_recommendations.append(rec)
            except RepositoryError as e:
                self.logger.error(f"Failed to save generated recommendation '{rec.title}': {e}")

        return saved_recommendations

    def format_recommendations(self, recommendations: List[Recommendation], format_type: str = "markdown") -> str:
        """Formats a list of recommendations into a string."""
        if not self.is_initialized or not self._formatter:
            raise ComponentNotInitializedError(self.name)
        return self._formatter.format(recommendations, format_type)

    def apply_recommendation(self, recommendation_id: str) -> bool:
        """Attempts to automatically apply a specific recommendation."""
        if not self.is_initialized or not self._repository or not self._strategy_selector:
            raise ComponentNotInitializedError(self.name)

        self.logger.info(f"Attempting to apply recommendation ID: {recommendation_id}")
        try:
            recommendation = self._repository.get(recommendation_id)
            if not recommendation:
                raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found.")
            if recommendation.status == RecommendationStatus.APPLIED:
                 self.logger.info(f"Recommendation {recommendation_id} has already been applied.")
                 return True # Consider already applied as success
            if recommendation.status != RecommendationStatus.PENDING and recommendation.status != RecommendationStatus.ACCEPTED:
                 self.logger.warning(f"Cannot apply recommendation {recommendation_id} with status {recommendation.status.value}.")
                 return False

            strategy = self._strategy_selector.select_strategy_by_name(recommendation.strategy_name)
            if not strategy:
                raise StrategyNotFoundError(f"Strategy '{recommendation.strategy_name}' not found for recommendation {recommendation_id}.")

            # Delegate application to the strategy
            applied = strategy.apply(recommendation)

            # Update status in repository
            if applied:
                recommendation.status = RecommendationStatus.APPLIED
                recommendation.applied_at = datetime.now(timezone.utc)
                self.logger.info(f"Successfully applied recommendation: {recommendation_id}")
            else:
                recommendation.status = RecommendationStatus.FAILED # Mark as failed if apply returns False
                self.logger.warning(f"Failed to apply recommendation: {recommendation_id}")
            self._repository.update(recommendation)

            # If applied successfully, mark related inconsistencies as resolved
            if applied and hasattr(self.consistency_component, 'mark_inconsistency_resolved'):
                 for inc_id in recommendation.inconsistency_ids:
                      try:
                           self.consistency_component.mark_inconsistency_resolved(inc_id)
                      except Exception as e:
                           self.logger.warning(f"Error marking inconsistency {inc_id} as resolved after applying recommendation {recommendation_id}: {e}")

            return applied

        except (RecommendationNotFoundError, StrategyNotFoundError) as e:
             self.logger.error(f"Cannot apply recommendation {recommendation_id}: {e}")
             return False
        except Exception as e:
            self.logger.error(f"Unexpected error applying recommendation {recommendation_id}: {e}", exc_info=True)
            # Optionally update status to FAILED in DB here too
            return False

    def provide_feedback(self, recommendation_id: str, feedback_data: Dict[str, Any]):
        """Records user feedback for a recommendation."""
        if not self.is_initialized or not self._repository or not self._feedback_analyzer:
            raise ComponentNotInitializedError(self.name)

        self.logger.info(f"Recording feedback for recommendation ID: {recommendation_id}")
        try:
            recommendation = self._repository.get(recommendation_id)
            if not recommendation:
                raise RecommendationNotFoundError(f"Recommendation {recommendation_id} not found.")

            # Create feedback object
            feedback = RecommendationFeedback.from_dict(feedback_data)
            recommendation.feedback = feedback
            # Update status based on feedback
            recommendation.status = RecommendationStatus.ACCEPTED if feedback.accepted else RecommendationStatus.REJECTED
            recommendation.updated_at = datetime.now(timezone.utc)

            # Save updated recommendation
            self._repository.update(recommendation)

            # Analyze feedback
            self._feedback_analyzer.analyze(recommendation)
            self.logger.info(f"Feedback recorded for recommendation ID: {recommendation_id}")

        except (RecommendationNotFoundError, ValueError) as e: # ValueError from from_dict
             self.logger.error(f"Failed to record feedback for {recommendation_id}: {e}")
        except Exception as e:
             self.logger.error(f"Unexpected error recording feedback for {recommendation_id}: {e}", exc_info=True)


    def get_recommendations(self, **filters) -> List[Recommendation]:
        """Retrieves stored recommendations, optionally applying filters."""
        if not self.is_initialized or not self._repository:
            raise ComponentNotInitializedError(self.name)
        # Pass filters directly to the repository method
        return self._repository.get_recommendations(**filters)
