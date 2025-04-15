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
# Consistency Analysis package for the Documentation-Based Programming system.
# Provides functionality to analyze consistency between documentation and code.
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


# src/dbp/consistency_analysis/__init__.py

"""
Consistency Analysis package for the Documentation-Based Programming system.

Detects inconsistencies between documentation and code artifacts using a
rule-based engine and specialized analyzers.

Key components:
- ConsistencyAnalysisComponent: The main component conforming to the core framework.
- RuleEngine: Executes consistency rules.
- AnalysisRegistry: Manages available analyzers and rules.
- ConsistencyAnalyzer: Abstract base class for specific analysis logic.
- InconsistencyRepository: Persists detected inconsistencies.
- ReportGenerator: Creates summary reports of analysis results.
- Data Models: Defines structures like InconsistencyRecord, ConsistencyRule, etc.
"""

# Expose key classes, data models, and exceptions for easier import
from .data_models import (
    InconsistencyRecord,
    ConsistencyReport,
    ConsistencyRule,
    InconsistencyType,
    InconsistencySeverity,
    InconsistencyStatus
)
from .repository import InconsistencyRepository, RepositoryError
from .registry import AnalysisRegistry, AnalysisError
from .engine import RuleEngine
from .analyzer import ConsistencyAnalyzer # Expose ABC
# Concrete analyzers are likely internal details, but can be exposed if needed
# from .analyzer import CodeDocMetadataAnalyzer, ...
from .report_generator import ReportGenerator
from .component import ConsistencyAnalysisComponent, ComponentNotInitializedError
# ImpactAnalyzer might belong here or in doc_relationships depending on final design
# from .impact_analyzer import ConsistencyImpactAnalyzer

__all__ = [
    # Main Component
    "ConsistencyAnalysisComponent",
    # Core Classes (Expose interfaces/facades)
    "RuleEngine",
    "AnalysisRegistry",
    "ConsistencyAnalyzer", # ABC
    "InconsistencyRepository",
    "ReportGenerator",
    # "ConsistencyImpactAnalyzer", # Decide if this should be public
    # Data Models & Enums
    "InconsistencyRecord",
    "ConsistencyReport",
    "ConsistencyRule",
    "InconsistencyType",
    "InconsistencySeverity",
    "InconsistencyStatus",
    # Exceptions
    "RepositoryError",
    "AnalysisError",
    "ComponentNotInitializedError",
]
