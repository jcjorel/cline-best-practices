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
# Implements the FeedbackAnalyzer class, responsible for processing user feedback
# provided on generated recommendations. This analysis can be used to track
# strategy effectiveness and potentially improve future recommendation generation
# (though the learning aspect is currently a placeholder).
###############################################################################
# [Source file design principles]
# - Receives Recommendation objects containing user feedback.
# - Aggregates feedback statistics per strategy (acceptance rate, common reasons/improvements).
# - Provides methods to retrieve aggregated feedback statistics.
# - Thread-safe using RLock.
# - Current implementation focuses on tracking; learning logic is deferred.
# - Design Decision: Separate Feedback Analyzer (2025-04-15)
#   * Rationale: Isolates the logic for processing and potentially learning from user feedback.
#   * Alternatives considered: Processing feedback within the main component or repository (mixes concerns).
###############################################################################
# [Source file constraints]
# - Depends on the `Recommendation` and `RecommendationFeedback` data models.
# - The effectiveness of learning from feedback depends on the quality and quantity of feedback received and the sophistication of the analysis logic (currently basic).
# - Statistics are stored in memory and lost on restart unless persisted.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - src/dbp/recommendation_generator/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:42:55Z : Initial creation of FeedbackAnalyzer class by CodeAssistant
# * Implemented basic feedback aggregation and statistics tracking.
###############################################################################

import logging
import threading
from typing import Dict, Any, Optional, DefaultDict
from collections import defaultdict, Counter

# Assuming data_models defines Recommendation and RecommendationFeedback
try:
    from .data_models import Recommendation, RecommendationFeedback
except ImportError:
    logging.getLogger(__name__).error("Failed to import data models for FeedbackAnalyzer.", exc_info=True)
    # Placeholders
    Recommendation = object
    RecommendationFeedback = object

logger = logging.getLogger(__name__)

class FeedbackAnalyzer:
    """
    Analyzes user feedback provided on recommendations to track strategy
    effectiveness and potentially inform future improvements.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the FeedbackAnalyzer."""
        self.logger = logger_override or logger
        # Stores feedback statistics per strategy name
        # strategy_name -> { "total": int, "accepted": int, "rejected": int,
        #                    "acceptance_rate": float, "common_reasons": Counter,
        #                    "common_improvements": Counter }
        self._feedback_stats: DefaultDict[str, Dict[str, Any]] = defaultdict(
            lambda: {
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "acceptance_rate": 0.0,
                "common_reasons": Counter(),
                "common_improvements": Counter()
            }
        )
        self._lock = threading.RLock() # Thread safety
        self.logger.debug("FeedbackAnalyzer initialized.")

    def analyze(self, recommendation: Recommendation):
        """
        Processes the feedback associated with a recommendation and updates statistics.

        Args:
            recommendation: The Recommendation object containing feedback.
        """
        if not recommendation or not recommendation.feedback:
            # self.logger.debug(f"No feedback provided for recommendation ID: {getattr(recommendation, 'id', 'N/A')}. Skipping analysis.")
            return
        if not isinstance(recommendation.feedback, RecommendationFeedback):
             self.logger.warning(f"Invalid feedback type for recommendation ID: {recommendation.id}. Skipping analysis.")
             return

        strategy_name = recommendation.strategy_name
        feedback = recommendation.feedback

        with self._lock:
            self.logger.info(f"Analyzing feedback for recommendation ID: {recommendation.id} (Strategy: {strategy_name}, Accepted: {feedback.accepted})")
            stats = self._feedback_stats[strategy_name] # defaultdict creates if not exists

            # Update counts
            stats["total"] += 1
            if feedback.accepted:
                stats["accepted"] += 1
            else:
                stats["rejected"] += 1

            # Update acceptance rate
            stats["acceptance_rate"] = (stats["accepted"] / stats["total"]) * 100 if stats["total"] > 0 else 0.0

            # Track common reasons for rejection (case-insensitive)
            if not feedback.accepted and feedback.reason:
                reason = feedback.reason.strip().lower()
                if reason:
                    stats["common_reasons"][reason] += 1

            # Track common improvement suggestions (case-insensitive)
            if feedback.improvements:
                for improvement in feedback.improvements:
                    imp_key = improvement.strip().lower()
                    if imp_key:
                        stats["common_improvements"][imp_key] += 1

            self.logger.debug(f"Updated feedback stats for strategy '{strategy_name}': {stats}")

            # TODO: Implement learning logic here?
            # - Adjust strategy selection based on acceptance rates?
            # - Modify prompt generation based on common reasons/improvements?
            # - Requires more sophisticated state management and potentially ML models.
            # For now, just tracking stats.

    def get_feedback_stats(self, strategy_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves aggregated feedback statistics.

        Args:
            strategy_name: If provided, returns stats only for that strategy.
                           Otherwise, returns stats for all strategies.

        Returns:
            A dictionary containing feedback statistics. If strategy_name is specified,
            returns the stats for that strategy or an empty dict if not found.
            If strategy_name is None, returns a dict mapping strategy names to their stats.
        """
        with self._lock:
            if strategy_name:
                # Return a copy of the specific strategy's stats
                stats = self._feedback_stats.get(strategy_name)
                return stats.copy() if stats else {}
            else:
                # Return a copy of the entire stats dictionary
                # Convert Counters back to simple dicts for easier consumption/serialization
                full_stats = {}
                for name, stats_dict in self._feedback_stats.items():
                     full_stats[name] = {
                          **stats_dict, # Copy basic stats
                          "common_reasons": dict(stats_dict["common_reasons"]),
                          "common_improvements": dict(stats_dict["common_improvements"])
                     }
                return full_stats

    def reset_stats(self, strategy_name: Optional[str] = None):
        """
        Resets feedback statistics.

        Args:
            strategy_name: If provided, resets stats only for that strategy.
                           Otherwise, resets stats for all strategies.
        """
        with self._lock:
            if strategy_name:
                if strategy_name in self._feedback_stats:
                    del self._feedback_stats[strategy_name]
                    self.logger.info(f"Reset feedback statistics for strategy: {strategy_name}")
                else:
                    self.logger.warning(f"Attempted to reset stats for unknown strategy: {strategy_name}")
            else:
                self._feedback_stats.clear()
                self.logger.info("Reset all feedback statistics.")
