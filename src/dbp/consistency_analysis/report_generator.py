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
# Implements the ReportGenerator class, responsible for taking a list of
# InconsistencyRecord objects and generating a structured ConsistencyReport
# containing aggregated summary statistics and the detailed list of inconsistencies.
###############################################################################
# [Source file design principles]
# - Consumes a list of inconsistency records.
# - Calculates summary statistics (total count, counts by type, counts by severity).
# - Groups inconsistencies by the source file for easier review.
# - Populates the ConsistencyReport data model.
# - Design Decision: Dedicated Report Generator (2025-04-15)
#   * Rationale: Separates the logic for summarizing and structuring the final report from the analysis/detection logic.
#   * Alternatives considered: Generating summary within the RuleEngine or main component (less modular).
###############################################################################
# [Source file constraints]
# - Depends on the `InconsistencyRecord` and `ConsistencyReport` data models.
# - Assumes input list contains valid `InconsistencyRecord` objects.
# - Summary statistics are based solely on the provided list of inconsistencies.
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# other:- src/dbp/consistency_analysis/data_models.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:31:35Z : Initial creation of ReportGenerator class by CodeAssistant
# * Implemented logic to generate summary statistics and populate the report object.
###############################################################################

import logging
from typing import List, Dict, Any, Optional
from collections import Counter
from datetime import datetime, timezone
import uuid

# Assuming data_models defines the necessary structures
try:
    from .data_models import InconsistencyRecord, ConsistencyReport, InconsistencySeverity, InconsistencyType, InconsistencyStatus
except ImportError:
    logging.getLogger(__name__).error("Failed to import data models for ReportGenerator.", exc_info=True)
    # Placeholders
    InconsistencyRecord = object
    ConsistencyReport = object
    # Dummy Enum for placeholder
    class Enum:
        def __init__(self, value): self.value = value
    class InconsistencySeverity(Enum): HIGH="high"; MEDIUM="medium"; LOW="low"
    class InconsistencyType(Enum): OTHER="other"
    class InconsistencyStatus(Enum): OPEN="open"


logger = logging.getLogger(__name__)

class ReportGenerator:
    """
    Generates a structured consistency report from a list of detected inconsistencies.
    """

    def __init__(self, logger_override: Optional[logging.Logger] = None):
        """
        Initializes the ReportGenerator.

        Args:
            logger_override: Optional logger instance.
        """
        self.logger = logger_override or logger
        self.logger.debug("ReportGenerator initialized.")

    def generate(self, inconsistencies: List[InconsistencyRecord], analysis_metadata: Optional[Dict[str, Any]] = None) -> ConsistencyReport:
        """
        Generates a ConsistencyReport object summarizing the provided inconsistencies.

        Args:
            inconsistencies: A list of InconsistencyRecord objects.
            analysis_metadata: Optional metadata about the analysis run (e.g., duration, scope).

        Returns:
            A ConsistencyReport object.
        """
        self.logger.info(f"Generating consistency report for {len(inconsistencies)} inconsistencies.")

        # Validate input
        if not isinstance(inconsistencies, list):
             self.logger.error("Invalid input: inconsistencies must be a list.")
             # Return an empty report or raise error? Let's return empty.
             return ConsistencyReport(summary={"error": "Invalid input"}, inconsistencies=[])

        valid_inconsistencies = [inc for inc in inconsistencies if isinstance(inc, InconsistencyRecord)]
        if len(valid_inconsistencies) != len(inconsistencies):
             self.logger.warning(f"Some invalid items found in the input inconsistency list ({len(inconsistencies) - len(valid_inconsistencies)} items skipped).")

        # Calculate summary statistics
        total_count = len(valid_inconsistencies)
        type_counts = Counter(inc.inconsistency_type.value for inc in valid_inconsistencies)
        severity_counts = Counter(inc.severity.value for inc in valid_inconsistencies)
        status_counts = Counter(inc.status.value for inc in valid_inconsistencies)

        # Group by source file
        file_inconsistencies: Dict[str, int] = defaultdict(int)
        for inc in valid_inconsistencies:
            file_inconsistencies[inc.source_file] += 1

        summary = {
            "total_inconsistencies": total_count,
            "by_type": dict(type_counts),
            "by_severity": dict(severity_counts),
            "by_status": dict(status_counts),
            "by_file": dict(file_inconsistencies),
            # Add specific severity counts for convenience
            "high_severity_count": severity_counts.get(InconsistencySeverity.HIGH.value, 0),
            "medium_severity_count": severity_counts.get(InconsistencySeverity.MEDIUM.value, 0),
            "low_severity_count": severity_counts.get(InconsistencySeverity.LOW.value, 0),
        }

        # Create the report object
        report = ConsistencyReport(
            # id generated by default factory
            summary=summary,
            inconsistencies=valid_inconsistencies, # Include the validated list
            generated_at=datetime.now(timezone.utc),
            report_version="1.0",
            metadata=analysis_metadata or {} # Include any metadata about the run
        )

        self.logger.info(f"Consistency report generated with ID: {report.id}")
        return report
