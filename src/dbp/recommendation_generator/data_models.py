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
# Recommendation Generator component. This includes representations for
# recommendation types, severities, statuses, feedback, and the main
# Recommendation object itself.
###############################################################################
# [Source file design principles]
# - Uses Enums for controlled vocabularies (FixType, Severity, Status).
# - Uses standard Python dataclasses for structured data representation.
# - Defines clear fields for each data structure based on the design plan.
# - Includes type hints for clarity and static analysis.
# - RecommendationFeedback includes a method to convert to dict for easier storage.
###############################################################################
# [Source file constraints]
# - Requires Python 3.7+ for dataclasses and Enum.
# - Enum values should be kept consistent with their usage throughout the system.
# - Assumes consistency in the structure of Recommendation objects.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_recommendation_generator.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:34:15Z : Initial creation of recommendation data models by CodeAssistant
# * Defined Enums and Dataclasses for recommendations and feedback.
###############################################################################

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import uuid

logger = logging.getLogger(__name__)

# --- Enumerations ---

class RecommendationFixType(Enum):
    """Categorizes the type of fix proposed by a recommendation."""
    DOCUMENTATION = "documentation" # Change only documentation files
    CODE = "code"                   # Change only code files
    COMBINED = "combined"           # Change both code and documentation

class RecommendationSeverity(Enum):
    """Defines the severity or importance of addressing a recommendation."""
    HIGH = "high"     # Strongly recommended, addresses critical inconsistency
    MEDIUM = "medium" # Recommended, addresses significant inconsistency
    LOW = "low"       # Suggestion or minor improvement

class RecommendationStatus(Enum):
    """Defines the lifecycle status of a generated recommendation."""
    PENDING = "pending"     # Generated, awaiting user review/action
    ACCEPTED = "accepted"   # User indicated they will apply the fix manually or accepted auto-apply
    REJECTED = "rejected"   # User rejected the recommendation
    APPLIED = "applied"     # The recommended change was successfully applied (automatically or manually confirmed)
    FAILED = "failed"       # An attempt to automatically apply the recommendation failed
    SUPERSEDED = "superseded" # A newer recommendation addresses the same underlying issue
    INVALIDATED = "invalidated" # Underlying code/doc changed, making recommendation obsolete

# --- Dataclasses ---

@dataclass
class RecommendationFeedback:
    """Stores user feedback provided for a specific recommendation."""
    accepted: bool # Did the user accept the recommendation's validity?
    reason: Optional[str] = None # Reason if rejected, or comments if accepted
    improvements: Optional[List[str]] = field(default_factory=list) # Suggested improvements if amended/rejected
    provided_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Converts feedback to a dictionary suitable for JSON serialization."""
        return {
            "accepted": self.accepted,
            "reason": self.reason,
            "improvements": self.improvements,
            "provided_at": self.provided_at.isoformat() if self.provided_at else None
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'RecommendationFeedback':
        """Creates feedback from a dictionary (e.g., loaded from DB)."""
        ts = data.get("provided_at")
        return cls(
            accepted=data.get("accepted", False),
            reason=data.get("reason"),
            improvements=data.get("improvements", []),
            provided_at=datetime.fromisoformat(ts) if ts else None
        )


@dataclass
class Recommendation:
    """
    Represents an actionable recommendation generated to address one or more
    detected inconsistencies.
    """
    # Core Info
    title: str # Concise title summarizing the recommendation
    description: str # Detailed explanation of the issue and the proposed fix
    strategy_name: str # Identifier of the strategy that generated this recommendation
    fix_type: RecommendationFixType # What kind of files does this fix target?
    severity: RecommendationSeverity
    status: RecommendationStatus = RecommendationStatus.PENDING

    # Context / Location
    # List of inconsistency IDs this recommendation addresses
    inconsistency_ids: List[str] = field(default_factory=list)
    # Primary file where change originates or should be applied
    source_file: Optional[str] = None
    # Other relevant file(s) involved
    target_file: Optional[str] = None # Kept singular for simplicity, use metadata for multiple?

    # Proposed Fix Details
    # Specific code snippet suggestion (e.g., diff format or replacement block)
    code_snippet: Optional[str] = None
    # Specific documentation snippet suggestion
    doc_snippet: Optional[str] = None

    # Lifecycle & Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4())) # Unique ID
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    applied_at: Optional[datetime] = None # Timestamp when applied
    metadata: Dict[str, Any] = field(default_factory=dict) # For strategy-specific data, confidence, etc.
    feedback: Optional[RecommendationFeedback] = None # User feedback on this recommendation

    def __post_init__(self):
        # Ensure enums are used correctly if initialized with strings
        if isinstance(self.fix_type, str):
            self.fix_type = RecommendationFixType(self.fix_type)
        if isinstance(self.severity, str):
            self.severity = RecommendationSeverity(self.severity)
        if isinstance(self.status, str):
            self.status = RecommendationStatus(self.status)
