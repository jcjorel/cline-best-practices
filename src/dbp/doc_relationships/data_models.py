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
# Defines the core data structures (using dataclasses) for representing
# relationships between documentation files, the impact of changes, and the
# details of those changes within the DBP system.
###############################################################################
# [Source file design principles]
# - Uses standard Python dataclasses for clear and lightweight data representation.
# - Defines structures for relationships, impacts, and change impacts.
# - Includes type hints for clarity and static analysis.
# - Aligns with the data models specified in the Documentation Relationships design plan.
###############################################################################
# [Source file constraints]
# - Requires Python 3.7+ for dataclasses.
# - Assumes consistency in usage across the documentation relationships components.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/DOCUMENT_RELATIONSHIPS.md
# - scratchpad/dbp_implementation_plan/plan_doc_relationships.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:17:40Z : Initial creation of doc relationships data models by CodeAssistant
# * Defined DocumentRelationship, DocImpact, and DocChangeImpact dataclasses.
###############################################################################

from dataclasses import dataclass, field
from typing import Optional, Dict, Any, List
from datetime import datetime

@dataclass
class DocumentRelationship:
    """
    Represents a directed relationship between two documents.
    """
    source_document: str # Path of the document where the relationship originates
    target_document: str # Path of the document the relationship points to
    relationship_type: str # Type of relationship (e.g., "depends on", "impacts", "references")
    topic: Optional[str] = None # Subject matter of the relationship (e.g., link text, section title)
    scope: Optional[str] = None # Scope of the relationship (e.g., "narrow", "broad")
    metadata: Dict[str, Any] = field(default_factory=dict) # Additional metadata about the relationship
    # Fields typically populated by the repository/database
    id: Optional[str] = None # Unique ID assigned by the database
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DocImpact:
    """
    Represents the potential impact of a change in a source document
    on a target document.
    """
    source_document: str # The document that changed (or is being analyzed)
    target_document: str # The document potentially impacted
    impact_type: str # How the target is impacted (e.g., "direct", "reverse", "indirect", "transitive")
    impact_level: str # Estimated severity of the impact (e.g., "high", "medium", "low")
    relationship_type: str # The type of relationship linking the documents
    topic: Optional[str] = None # Topic of the relationship causing the impact
    scope: Optional[str] = None # Scope of the relationship causing the impact

@dataclass
class DocChangeImpact:
    """
    Represents the specific impact on a target document caused by a detected
    change in a source document.
    """
    source_document: str # Document where the change occurred
    target_document: str # Document potentially impacted by the change
    change_type: str # Type of change detected (e.g., "section_added", "link_modified")
    change_section: Optional[str] # Section within the source document where change occurred
    change_content: Optional[str] # Snippet or description of the change content
    impact_type: str # Type of impact on the target document
    impact_level: str # Estimated severity of the impact
    relationship_type: str # Relationship linking the source and target
    topic: Optional[str] = None # Topic of the relationship
    scope: Optional[str] = None # Scope of the relationship
