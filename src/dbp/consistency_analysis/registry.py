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
# Implements the AnalysisRegistry class, responsible for managing and providing
# access to various specialized ConsistencyAnalyzer instances and their associated
# ConsistencyRules. It allows the RuleEngine to discover and invoke relevant analyzers.
###############################################################################
# [Source file design principles]
# - Central registry for all consistency analyzers and their rules.
# - Analyzers are registered with unique IDs.
# - Rules are grouped by the type of analysis they perform (e.g., "code_doc", "doc_doc").
# - Provides methods to retrieve analyzers by ID and rules by analysis type.
# - Thread-safe using RLock.
# - Design Decision: Registry for Analyzers/Rules (2025-04-15)
#   * Rationale: Decouples the RuleEngine from specific analyzer implementations, allowing easy addition/removal of analyzers and rules.
#   * Alternatives considered: Hardcoding rules in the engine (less flexible), Discovering analyzers dynamically (more complex).
###############################################################################
# [Source file constraints]
# - Depends on `analyzer.py` for `ConsistencyAnalyzer` and `ConsistencyRule` definitions.
# - Assumes analyzer IDs and rule IDs are unique.
# - Relies on analyzers correctly reporting their rules via `get_rules()`.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_consistency_analysis.md
# - src/dbp/consistency_analysis/analyzer.py (Interface definition)
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:29:35Z : Initial creation of AnalysisRegistry class by CodeAssistant
# * Implemented registration and retrieval logic for analyzers and rules.
###############################################################################

import logging
import threading
from typing import Dict, List, Tuple, Optional, Any
from collections import defaultdict

# Assuming analyzer defines ConsistencyAnalyzer and ConsistencyRule
try:
    from .analyzer import ConsistencyAnalyzer, ConsistencyRule
except ImportError:
    logging.getLogger(__name__).error("Failed to import ConsistencyAnalyzer/Rule for AnalysisRegistry.")
    # Placeholders
    ConsistencyRule = object
    class ConsistencyAnalyzer:
        def get_rules(self) -> List[ConsistencyRule]: return []

logger = logging.getLogger(__name__)

class AnalysisError(Exception):
    """Custom exception for analysis registry errors."""
    pass

class AnalysisRegistry:
    """
    Manages the registration and retrieval of consistency analyzers and their rules.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """Initializes the AnalysisRegistry."""
        self.logger = logger_override or logger
        # analyzer_id -> ConsistencyAnalyzer instance
        self._analyzers: Dict[str, ConsistencyAnalyzer] = {}
        # analysis_type -> List[(ConsistencyAnalyzer, ConsistencyRule)]
        self._rules_by_type: Dict[str, List[Tuple[ConsistencyAnalyzer, ConsistencyRule]]] = defaultdict(list)
        self._lock = threading.RLock() # Thread safety
        self.logger.debug("AnalysisRegistry initialized.")

    def register_analyzer(self, analyzer_id: str, analyzer: ConsistencyAnalyzer):
        """
        Registers a consistency analyzer instance and its associated rules.

        Args:
            analyzer_id: A unique string identifier for the analyzer.
            analyzer: An instance of a class implementing the ConsistencyAnalyzer interface.

        Raises:
            ValueError: If an analyzer with the same ID is already registered.
            TypeError: If the provided analyzer is not a valid ConsistencyAnalyzer instance.
        """
        if not isinstance(analyzer_id, str) or not analyzer_id:
            raise TypeError("analyzer_id must be a non-empty string.")
        # Basic check for interface compliance - relies on abstract methods
        if not isinstance(analyzer, ConsistencyAnalyzer) or not callable(getattr(analyzer, 'get_rules', None)) or not callable(getattr(analyzer, 'apply_rule', None)):
             raise TypeError(f"Object provided for ID '{analyzer_id}' does not conform to the ConsistencyAnalyzer protocol.")

        with self._lock:
            if analyzer_id in self._analyzers:
                self.logger.error(f"Analyzer with ID '{analyzer_id}' already registered.")
                raise ValueError(f"Analyzer ID conflict: '{analyzer_id}' is already registered.")

            self.logger.info(f"Registering consistency analyzer: '{analyzer_id}' ({type(analyzer).__name__})")
            self._analyzers[analyzer_id] = analyzer

            # Extract and register rules provided by this analyzer
            try:
                rules = analyzer.get_rules()
                if not isinstance(rules, list):
                     self.logger.error(f"Analyzer '{analyzer_id}' get_rules() did not return a list.")
                     # Optionally remove the analyzer registration or proceed without rules?
                     # Let's proceed without its rules for now.
                     rules = []

                rule_count = 0
                for rule in rules:
                    if not isinstance(rule, ConsistencyRule):
                         self.logger.warning(f"Analyzer '{analyzer_id}' provided an invalid rule object: {type(rule)}. Skipping.")
                         continue
                    if not rule.analysis_type or not rule.rule_id:
                         self.logger.warning(f"Analyzer '{analyzer_id}' provided a rule with missing ID or type: {rule}. Skipping.")
                         continue

                    self._rules_by_type[rule.analysis_type].append((analyzer, rule))
                    rule_count += 1
                self.logger.info(f"Registered {rule_count} rules for analyzer '{analyzer_id}'.")

            except Exception as e:
                 self.logger.error(f"Error getting or registering rules for analyzer '{analyzer_id}': {e}", exc_info=True)
                 # Optionally unregister the analyzer if rule retrieval fails critically?
                 # del self._analyzers[analyzer_id]
                 # raise AnalysisError(f"Failed to process rules for analyzer '{analyzer_id}'") from e


    def get_analyzer(self, analyzer_id: str) -> ConsistencyAnalyzer:
        """
        Retrieves a registered consistency analyzer by its ID.

        Args:
            analyzer_id: The unique ID of the analyzer.

        Returns:
            The ConsistencyAnalyzer instance.

        Raises:
            AnalysisError: If no analyzer with the given ID is registered.
        """
        with self._lock:
            analyzer = self._analyzers.get(analyzer_id)
            if analyzer is None:
                self.logger.error(f"Consistency analyzer with ID '{analyzer_id}' not found.")
                raise AnalysisError(f"Analyzer not found: {analyzer_id}")
            return analyzer

    def get_rules_for_analysis_type(self, analysis_type: str) -> List[Tuple[ConsistencyAnalyzer, ConsistencyRule]]:
        """
        Retrieves all rules associated with a specific analysis type.

        Args:
            analysis_type: The type of analysis (e.g., "code_doc", "doc_doc").

        Returns:
            A list of tuples, where each tuple contains (analyzer_instance, rule_object).
            Returns an empty list if no rules are registered for the type.
        """
        with self._lock:
            # Return a copy to prevent external modification
            return list(self._rules_by_type.get(analysis_type, []))

    def get_all_analyzers(self) -> Dict[str, ConsistencyAnalyzer]:
        """Returns a dictionary of all registered analyzers (ID -> instance)."""
        with self._lock:
            # Return a copy
            return self._analyzers.copy()

    def get_all_rules(self) -> Dict[str, List[Tuple[ConsistencyAnalyzer, ConsistencyRule]]]:
         """Returns a dictionary of all registered rules, grouped by analysis type."""
         with self._lock:
              # Return a deep copy? Or just copy the lists? Copying lists is usually sufficient.
              return {k: list(v) for k, v in self._rules_by_type.items()}

    def clear(self):
         """Clears all registered analyzers and rules."""
         with self._lock:
              self._analyzers.clear()
              self._rules_by_type.clear()
              self.logger.info("AnalysisRegistry cleared.")
