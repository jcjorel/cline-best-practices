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
# Implements the GeneratorEngine class, which orchestrates the process of
# generating recommendations. It takes detected inconsistencies, uses the
# StrategySelector to find appropriate strategies, and invokes those strategies
# to produce a list of Recommendation objects.
###############################################################################
# [Source file design principles]
# - Coordinates the recommendation generation process.
# - Groups inconsistencies by type to apply the correct strategy efficiently.
# - Uses the StrategySelector to decouple the engine from specific strategy implementations.
# - Delegates the actual recommendation generation logic to the selected strategies.
# - Aggregates results from multiple strategies if necessary.
# - Includes error handling for strategy selection and execution.
# - Design Decision: Strategy-Driven Generation Engine (2025-04-15)
#   * Rationale: Provides a clear workflow where the engine selects and invokes the right tool (strategy) for the job (inconsistency type).
#   * Alternatives considered: Monolithic generator (less flexible), Rule-based selection within the engine (duplicates selector logic).
###############################################################################
# [Source file constraints]
# - Depends on `StrategySelector` and the `RecommendationStrategy` interface.
# - Relies on `InconsistencyRecord` and `Recommendation` data models.
# - Performance depends on the number of inconsistencies and the complexity of the selected strategies.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_recommendation_generator.md
# - src/dbp/recommendation_generator/selector.py
# - src/dbp/recommendation_generator/strategy.py
# - src/dbp/consistency_analysis/data_models.py (InconsistencyRecord)
# - src/dbp/recommendation_generator/data_models.py (Recommendation)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:41:00Z : Initial creation of GeneratorEngine class by CodeAssistant
# * Implemented logic to group inconsistencies, select strategies, and invoke generation.
###############################################################################

import logging
from typing import List, Dict, Optional, Any
from collections import defaultdict

# Assuming necessary imports
try:
    from .selector import StrategySelector, StrategyNotFoundError
    from .strategy import RecommendationStrategy # ABC for type hint
    from ..consistency_analysis.data_models import InconsistencyRecord, InconsistencyType
    from .data_models import Recommendation
except ImportError as e:
    logging.getLogger(__name__).error(f"GeneratorEngine ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    StrategySelector = object
    StrategyNotFoundError = Exception
    RecommendationStrategy = object
    InconsistencyRecord = object
    InconsistencyType = object
    Recommendation = object

logger = logging.getLogger(__name__)

class GeneratorEngine:
    """
    Orchestrates the generation of recommendations by selecting and invoking
    appropriate strategies based on detected inconsistencies.
    """

    def __init__(self, strategy_selector: StrategySelector, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the GeneratorEngine.

        Args:
            strategy_selector: The StrategySelector instance used to find strategies.
            logger_override: Optional logger instance.
        """
        if not isinstance(strategy_selector, StrategySelector):
             logger.warning("GeneratorEngine initialized with potentially incorrect selector type.")
        self.strategy_selector = strategy_selector
        self.logger = logger_override or logger
        self.logger.debug("GeneratorEngine initialized.")

    def generate(self, inconsistencies: List[InconsistencyRecord]) -> List[Recommendation]:
        """
        Generates recommendations for a given list of inconsistencies.

        It groups inconsistencies by type, selects the appropriate strategy for each type,
        invokes the strategy, and aggregates the resulting recommendations.

        Args:
            inconsistencies: A list of InconsistencyRecord objects to process.

        Returns:
            A list of generated Recommendation objects.
        """
        if not inconsistencies:
            self.logger.info("No inconsistencies provided, skipping recommendation generation.")
            return []

        self.logger.info(f"Generating recommendations for {len(inconsistencies)} inconsistencies.")
        all_recommendations: List[Recommendation] = []

        # 1. Group inconsistencies by their type
        grouped_inconsistencies: Dict[InconsistencyType, List[InconsistencyRecord]] = defaultdict(list)
        for inc in inconsistencies:
            if isinstance(inc, InconsistencyRecord) and hasattr(inc, 'inconsistency_type'):
                 grouped_inconsistencies[inc.inconsistency_type].append(inc)
            else:
                 self.logger.warning(f"Skipping invalid inconsistency object: {inc}")


        # 2. Process each group with the appropriate strategy
        for inconsistency_type, group in grouped_inconsistencies.items():
            self.logger.debug(f"Processing group for inconsistency type: {inconsistency_type.value} ({len(group)} items)")

            # Select strategy based on type
            strategy = self.strategy_selector.select_strategy(inconsistency_type)

            if not strategy:
                self.logger.warning(f"No registered or enabled strategy found for inconsistency type: {inconsistency_type.value}. Skipping this group.")
                continue

            # Invoke the selected strategy's generate method
            try:
                self.logger.info(f"Invoking strategy '{strategy.name}' for {len(group)} inconsistencies of type '{inconsistency_type.value}'.")
                generated_recs = strategy.generate(group)

                if generated_recs:
                    # Validate results are Recommendation objects
                    valid_recs = [rec for rec in generated_recs if isinstance(rec, Recommendation)]
                    if len(valid_recs) != len(generated_recs):
                         self.logger.warning(f"Strategy '{strategy.name}' returned non-Recommendation objects.")
                    all_recommendations.extend(valid_recs)
                    self.logger.info(f"Strategy '{strategy.name}' generated {len(valid_recs)} recommendations.")
                else:
                     self.logger.debug(f"Strategy '{strategy.name}' generated no recommendations for this group.")

            except Exception as e:
                self.logger.error(f"Error executing strategy '{strategy.name}' for type '{inconsistency_type.value}': {e}", exc_info=True)
                # Continue processing other groups even if one strategy fails

        self.logger.info(f"Recommendation generation complete. Total recommendations generated: {len(all_recommendations)}")
        return all_recommendations
