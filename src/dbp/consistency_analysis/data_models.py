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
# Defines the core data structures (enums and dataclasses) used by the
# Consistency Analysis component. This includes representations for inconsistency
# types, severities, statuses, individual inconsistency records, analysis rules,
# and the final consistency report.
###############################################################################
# [Source file design principles]
# - Uses Enums for controlled vocabularies (Type, Severity, Status).
# - Uses standard Python dataclasses for structured data representation.
# - Defines clear fields for each data structure based on the design plan.
# - Includes type hints for clarity and static analysis.
###############################################################################
# [Source file constraints]
# - Requires Python 3.7+ for dataclasses and Enum.
# - Enum values should be kept consistent with their usage in analyzers and reports.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:27:45Z : Initial creation of consistency analysis data models by CodeAssistant
# * Defined Enums and Dataclasses for rules, records, and reports.
# 2025-04-15T17:53:10Z : Fixed parameter ordering and missing import by CodeAssistant
# * Moved source_file parameter before status parameter in InconsistencyRecord
# * Added missing uuid import for ID generation
###############################################################################

import logging
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# --- Enumerations ---

class InconsistencyType(Enum):
    """Defines the types of inconsistencies that can be detected."""
    # Code <-> Doc
    INTENT_MISMATCH = "intent_mismatch"
    MISSING_CONSTRAINTS = "missing_constraints"
    DESIGN_PRINCIPLES_MISMATCH = "design_principles_mismatch"
    MISSING_REFERENCE_DOCS = "missing_reference_docs"
    FUNCTION_SIGNATURE_MISMATCH = "function_signature_mismatch"
    CLASS_STRUCTURE_MISMATCH = "class_structure_mismatch"
    CODE_COMMENT_MISMATCH = "code_comment_mismatch" # e.g., docstring vs implementation
    DOC_CODE_LINK_BROKEN = "doc_code_link_broken" # Link from doc to code is invalid
    CODE_DOC_LINK_BROKEN = "code_doc_link_broken" # Link from code to doc is invalid
    # Doc <-> Doc
    BROKEN_REFERENCE = "broken_reference"
    MISSING_BIDIRECTIONAL_REFERENCE = "missing_bidirectional_reference"
    CIRCULAR_REFERENCE = "circular_reference"
    TERMINOLOGY_INCONSISTENCY = "terminology_inconsistency"
    # Config <-> Doc/Code
    CONFIG_PARAM_MISMATCH = "config_parameter_mismatch" # Value/default differs
    CONFIG_PARAM_MISSING_DOC = "config_parameter_missing_doc"
    # API <-> Doc/Code
    API_ENDPOINT_MISMATCH = "api_endpoint_mismatch" # Route/method differs
    API_PARAM_MISMATCH = "api_parameter_mismatch" # Request/response param differs
    API_MISSING_DOC = "api_missing_doc"
    # General
    OTHER = "other"

class InconsistencySeverity(Enum):
    """Defines the severity levels for detected inconsistencies."""
    HIGH = "high"     # Significant issue, likely breaks functionality or understanding
    MEDIUM = "medium" # Important issue, may lead to confusion or minor problems
    LOW = "low"       # Minor issue, suggestion, or potential improvement area

class InconsistencyStatus(Enum):
    """Defines the lifecycle status of a detected inconsistency."""
    OPEN = "open"           # Newly detected
    ACKNOWLEDGED = "acknowledged" # Reviewed, but not yet fixed
    IN_PROGRESS = "in_progress" # Being worked on
    RESOLVED = "resolved"     # Fixed
    IGNORED = "ignored"       # Intentionally not fixing (e.g., false positive, won't fix)

# --- Dataclasses ---

@dataclass
class ConsistencyRule:
    """Represents a single rule used for consistency checking."""
    rule_id: str # Unique identifier for the rule (e.g., "check_broken_markdown_links")
    analysis_type: str # Category of analysis (e.g., "code_doc", "doc_doc", "full_project")
    description: str # Human-readable description of what the rule checks

@dataclass
class InconsistencyRecord:
    """Represents a single detected inconsistency."""
    # Core Information
    inconsistency_type: InconsistencyType
    description: str # Human-readable description of the specific inconsistency found
    severity: InconsistencySeverity
    source_file: str # The primary file where the inconsistency originates or is most evident
    status: InconsistencyStatus = InconsistencyStatus.OPEN # Default status

    # Location Information
    target_file: Optional[str] = None # The related file involved (if applicable)
    source_location: Optional[str] = None # E.g., line number, section header, function name in source_file
    target_location: Optional[str] = None # E.g., line number, section header in target_file

    # Details and Context
    details: Dict[str, Any] = field(default_factory=dict) # Specific data about the inconsistency (e.g., expected vs actual values)
    confidence_score: float = 1.0 # Confidence score (0.0 to 1.0) from the analyzer
    metadata: Dict[str, Any] = field(default_factory=dict) # Additional metadata (e.g., impact analysis results)

    # Timestamps and ID
    detected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4())) # Unique ID for tracking

    def __post_init__(self):
        # Ensure enums are used correctly if initialized with strings
        if isinstance(self.inconsistency_type, str):
            self.inconsistency_type = InconsistencyType(self.inconsistency_type)
        if isinstance(self.severity, str):
            self.severity = InconsistencySeverity(self.severity)
        if isinstance(self.status, str):
            self.status = InconsistencyStatus(self.status)

@dataclass
class ConsistencyReport:
    """Represents a summary report of a consistency analysis run."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    report_version: str = "1.0"
    summary: Dict[str, Any] = field(default_factory=dict) # Aggregated stats (total, by type, by severity)
    inconsistencies: List[InconsistencyRecord] = field(default_factory=list) # List of detected inconsistencies
    metadata: Dict[str, Any] = field(default_factory=dict) # Metadata about the analysis run (e.g., duration, scope)
