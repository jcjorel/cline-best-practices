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
# Implements the StrategySelector class, responsible for selecting the appropriate
# RecommendationStrategy based on the type of inconsistency provided. It maintains
# a registry of available strategies and a mapping from inconsistency types to
# strategy names.
###############################################################################
# [Source file design principles]
# - Centralizes the logic for mapping inconsistency types to recommendation strategies.
# - Allows registration of different strategy implementations.
# - Provides methods to select a strategy based on inconsistency type or directly by name.
# - Includes basic error handling for missing strategies.
# - Design Decision: Mapping-Based Selection (2025-04-15)
#   * Rationale: Provides a clear and configurable way to link specific inconsistency types to the strategies designed to handle them.
#   * Alternatives considered: Complex rule engine for selection (overkill), Hardcoding selection logic (less flexible).
###############################################################################
# [Source file constraints]
# - Depends on `RecommendationStrategy` interface and `InconsistencyType` enum.
# - Requires strategies to be registered before they can be selected.
# - The mapping from inconsistency type to strategy name needs to be maintained.
###############################################################################
# [Dependencies]
# - doc/DESIGN.md
# - src/dbp/recommendation_generator/strategy.py
# - src/dbp/consistency_analysis/data_models.py (InconsistencyType)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:40:20Z : Initial creation of StrategySelector class by CodeAssistant
# * Implemented strategy registration and selection logic based on inconsistency type.
# 2025-04-15T18:10:30Z : Fixed missing List import for type annotation by CodeAssistant
# * Added List to the typing imports to fix NameError in get_registered_strategies method.
###############################################################################

import logging
from typing import Dict, Optional, Any, Type, List

# Assuming necessary imports
try:
    from .strategy import RecommendationStrategy
    from ..consistency_analysis.data_models import InconsistencyType
    # Import config type if defined
    # from ...config import RecommendationGeneratorConfig # Example
    RecommendationGeneratorConfig = Any # Placeholder
except ImportError as e:
    logging.getLogger(__name__).error(f"StrategySelector ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    RecommendationStrategy = object
    InconsistencyType = object
    RecommendationGeneratorConfig = object

logger = logging.getLogger(__name__)

class StrategyNotFoundError(Exception):
    """Custom exception when a required strategy is not found."""
    pass

class StrategySelector:
    """
    Selects the appropriate RecommendationStrategy based on inconsistency type
    or strategy name. Manages a registry of available strategies.
    """

    def __init__(self, config: Optional[RecommendationGeneratorConfig] = None, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the StrategySelector.

        Args:
            config: Configuration object (potentially used for enabling/disabling strategies).
            logger_override: Optional logger instance.
        """
        self.config = config or {}
        self.logger = logger_override or logger
        # strategy_name -> RecommendationStrategy instance
        self._strategies: Dict[str, RecommendationStrategy] = {}
        # InconsistencyType.value -> strategy_name
        self._type_to_strategy_map: Dict[str, str] = self._get_default_type_mapping()
        self.logger.debug("StrategySelector initialized.")

    def _get_default_type_mapping(self) -> Dict[str, str]:
        """Returns the default mapping from inconsistency types to strategy names."""
        # This mapping should align with the implemented strategies
        # It determines which strategy handles which type of problem.
        return {
            InconsistencyType.INTENT_MISMATCH.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.MISSING_CONSTRAINTS.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.DESIGN_PRINCIPLES_MISMATCH.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.MISSING_REFERENCE_DOCS.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.BROKEN_REFERENCE.value: "DocumentationLinkFixStrategy",
            InconsistencyType.MISSING_BIDIRECTIONAL_REFERENCE.value: "DocumentationLinkFixStrategy", # Or a specific strategy
            InconsistencyType.CIRCULAR_REFERENCE.value: "DocumentationLinkFixStrategy", # Or specific strategy
            InconsistencyType.TERMINOLOGY_INCONSISTENCY.value: "DocumentationTerminologyStrategy",
            InconsistencyType.CONFIG_PARAM_MISMATCH.value: "DocumentationContentUpdateStrategy", # Or specific config strategy
            InconsistencyType.CONFIG_PARAM_MISSING_DOC.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.API_ENDPOINT_MISMATCH.value: "DocumentationContentUpdateStrategy", # Or specific API strategy
            InconsistencyType.API_PARAM_MISMATCH.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.API_MISSING_DOC.value: "DocumentationContentUpdateStrategy",
            InconsistencyType.FUNCTION_SIGNATURE_MISMATCH.value: "FunctionSignatureFixStrategy",
            InconsistencyType.CLASS_STRUCTURE_MISMATCH.value: "ClassStructureFixStrategy",
            InconsistencyType.CODE_COMMENT_MISMATCH.value: "CodeCommentUpdateStrategy",
            InconsistencyType.DOC_CODE_LINK_BROKEN.value: "DocumentationLinkFixStrategy", # Or specific code link strategy
            InconsistencyType.CODE_DOC_LINK_BROKEN.value: "CodeCommentUpdateStrategy", # Or specific code link strategy
            # Add mappings for other InconsistencyType members as strategies are implemented
            # InconsistencyType.OTHER.value: None # No default strategy for OTHER
        }

    def register_strategy(self, strategy_name: str, strategy_instance: RecommendationStrategy):
        """
        Registers a concrete recommendation strategy instance.

        Args:
            strategy_name: The unique name for the strategy (should match strategy's `name` property).
            strategy_instance: An instance of a RecommendationStrategy subclass.

        Raises:
            ValueError: If a strategy with the same name is already registered.
            TypeError: If the provided instance is not a RecommendationStrategy.
        """
        if not isinstance(strategy_instance, RecommendationStrategy):
             raise TypeError(f"Object provided for strategy '{strategy_name}' is not a valid RecommendationStrategy instance.")
        if not strategy_name or strategy_instance.name != strategy_name:
             self.logger.warning(f"Registering strategy with mismatched name: provided='{strategy_name}', instance.name='{strategy_instance.name}'. Using provided name.")
             # raise ValueError("Provided strategy_name must match the instance's name property.")

        if strategy_name in self._strategies:
            self.logger.error(f"Strategy with name '{strategy_name}' already registered.")
            raise ValueError(f"Strategy name conflict: '{strategy_name}' is already registered.")

        self.logger.info(f"Registering recommendation strategy: '{strategy_name}' ({type(strategy_instance).__name__})")
        self._strategies[strategy_name] = strategy_instance

    def select_strategy(self, inconsistency_type: InconsistencyType) -> Optional[RecommendationStrategy]:
        """
        Selects the appropriate strategy instance based on the inconsistency type.

        Args:
            inconsistency_type: An InconsistencyType enum member.

        Returns:
            The corresponding RecommendationStrategy instance, or None if no suitable
            strategy is registered or enabled for the given type.
        """
        if not isinstance(inconsistency_type, InconsistencyType):
             self.logger.warning(f"Invalid inconsistency_type provided: {inconsistency_type}")
             return None

        strategy_name = self._type_to_strategy_map.get(inconsistency_type.value)
        if not strategy_name:
            self.logger.debug(f"No strategy mapping defined for inconsistency type: {inconsistency_type.value}")
            return None

        # Check if the strategy is enabled in config (optional)
        enabled_strategies = self.config.get('enabled_strategies', None)
        if enabled_strategies is not None and strategy_name not in enabled_strategies:
             self.logger.debug(f"Strategy '{strategy_name}' is disabled by configuration.")
             return None

        strategy_instance = self._strategies.get(strategy_name)
        if not strategy_instance:
            self.logger.warning(f"Strategy '{strategy_name}' is mapped for type '{inconsistency_type.value}' but not registered.")
            return None

        self.logger.debug(f"Selected strategy '{strategy_name}' for inconsistency type '{inconsistency_type.value}'.")
        return strategy_instance

    def select_strategy_by_name(self, strategy_name: str) -> Optional[RecommendationStrategy]:
        """
        Selects a strategy instance directly by its registered name.

        Args:
            strategy_name: The name of the strategy to retrieve.

        Returns:
            The RecommendationStrategy instance, or None if not found.
        """
        strategy_instance = self._strategies.get(strategy_name)
        if not strategy_instance:
            self.logger.warning(f"Strategy with name '{strategy_name}' not found in registry.")
        return strategy_instance

    def get_registered_strategies(self) -> List[str]:
        """Returns a list of names of all registered strategies."""
        return list(self._strategies.keys())
