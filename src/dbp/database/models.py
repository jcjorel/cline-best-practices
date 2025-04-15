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
# Defines the SQLAlchemy ORM models for the Documentation-Based Programming system's database.
# These models map Python classes to database tables, enabling structured data storage and retrieval.
###############################################################################
# [Source file design principles]
# - Follows the data structures defined in doc/DATA_MODEL.md.
# - Uses SQLAlchemy declarative base for model definition.
# - Defines relationships between models to represent data connections.
# - Includes timestamp columns for tracking creation and updates.
# - Supports both SQLite and PostgreSQL compatibility where feasible.
# - Design Decision: Use SQLAlchemy ORM (2025-04-13)
#   * Rationale: Provides a high-level abstraction over SQL, improves code readability, and simplifies database interactions.
#   * Alternatives considered: Raw SQL, other ORMs (rejected for complexity or lack of features).
###############################################################################
# [Source file constraints]
# - Requires SQLAlchemy library to be installed.
# - Schema definitions must be kept in sync with doc/DATA_MODEL.md.
# - Table and column names follow snake_case convention.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_database_schema.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:31:30Z : Initial creation of database models by CodeAssistant
# * Created all core and supporting models based on plan_database_schema.md.
###############################################################################

from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Text, func, Boolean
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

# Association table for inconsistency-document many-to-many relationship
inconsistency_documents = Table('inconsistency_documents', Base.metadata,
    Column('inconsistency_id', Integer, ForeignKey('inconsistencies.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True)
)

# Association table for recommendation-inconsistency many-to-many relationship
recommendation_inconsistencies = Table('recommendation_inconsistencies', Base.metadata,
    Column('recommendation_id', Integer, ForeignKey('recommendations.id'), primary_key=True),
    Column('inconsistency_id', Integer, ForeignKey('inconsistencies.id'), primary_key=True)
)

class Project(Base):
    """Represents a project being monitored by the DBP system."""
    __tablename__ = 'projects'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    root_path = Column(String, nullable=False, unique=True)
    description = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    documents = relationship("Document", back_populates="project", cascade="all, delete-orphan")

class Document(Base):
    """Represents a file (code or documentation) within a project."""
    __tablename__ = 'documents'

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # Code, Markdown, Header, Config
    last_modified = Column(DateTime, nullable=False)
    file_size = Column(Integer, nullable=False)
    md5_digest = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'))
    content = Column(Text) # Optional: Store content for faster access? Consider size implications.

    # Header sections (nullable for non-code files)
    intent = Column(Text)
    design_principles = Column(Text) # Store as JSON string or delimited?
    constraints = Column(Text) # Store as JSON string or delimited?
    reference_documentation = Column(Text) # Store as JSON string or delimited?

    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    project = relationship("Project", back_populates="documents")
    functions = relationship("Function", back_populates="document", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="document", cascade="all, delete-orphan")
    change_records = relationship("ChangeRecord", back_populates="document", cascade="all, delete-orphan")
    design_decisions = relationship("DesignDecision", back_populates="document", cascade="all, delete-orphan")

    # Document relationships (many-to-many self-referential)
    source_relationships = relationship("DocumentRelationship",
                                       foreign_keys="DocumentRelationship.source_id",
                                       back_populates="source", cascade="all, delete-orphan")
    target_relationships = relationship("DocumentRelationship",
                                       foreign_keys="DocumentRelationship.target_id",
                                       back_populates="target", cascade="all, delete-orphan")

    # Inconsistency relationships (many-to-many)
    inconsistencies = relationship("Inconsistency",
                                  secondary=inconsistency_documents,
                                  back_populates="affected_documents")

    # Suggested changes (one-to-many)
    suggested_changes = relationship("SuggestedChange", back_populates="document")

class DocumentRelationship(Base):
    """Represents a relationship between two documents."""
    __tablename__ = 'document_relationships'

    id = Column(Integer, primary_key=True)
    source_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    target_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    relationship_type = Column(String, nullable=False)  # DependsOn, Impacts, Implements, Extends
    topic = Column(String, nullable=False)
    scope = Column(String, nullable=False)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    source = relationship("Document", foreign_keys=[source_id], back_populates="source_relationships")
    target = relationship("Document", foreign_keys=[target_id], back_populates="target_relationships")

class Function(Base):
    """Represents a function or method within a code file."""
    __tablename__ = 'functions'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    name = Column(String, nullable=False)

    # Documentation sections
    intent = Column(Text)
    design_principles = Column(Text) # Store as JSON string or delimited?
    implementation_details = Column(Text)
    design_decisions = Column(Text)
    parameters = Column(Text) # Store as JSON string or delimited?

    start_line = Column(Integer)
    end_line = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    document = relationship("Document", back_populates="functions")

class Class(Base):
    """Represents a class within a code file."""
    __tablename__ = 'classes'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    name = Column(String, nullable=False)

    # Documentation sections
    intent = Column(Text)
    design_principles = Column(Text) # Store as JSON string or delimited?
    implementation_details = Column(Text)
    design_decisions = Column(Text)

    start_line = Column(Integer)
    end_line = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships
    document = relationship("Document", back_populates="classes")

class Inconsistency(Base):
    """Represents a detected inconsistency between documents or code."""
    __tablename__ = 'inconsistencies'

    id = Column(Integer, primary_key=True)
    timestamp = Column(DateTime, nullable=False)
    severity = Column(String, nullable=False)  # Critical, Major, Minor
    type = Column(String, nullable=False)  # DocToDoc, DocToCode, DesignDecisionViolation
    description = Column(Text, nullable=False)
    suggested_resolution = Column(Text)
    status = Column(String, nullable=False)  # Pending, InRecommendation, Resolved
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships (many-to-many)
    affected_documents = relationship("Document", secondary=inconsistency_documents, back_populates="inconsistencies")
    recommendations = relationship("Recommendation",
                                 secondary=recommendation_inconsistencies,
                                 back_populates="inconsistencies")

class Recommendation(Base):
    """Represents a generated recommendation to resolve inconsistencies."""
    __tablename__ = 'recommendations'

    id = Column(Integer, primary_key=True)
    creation_timestamp = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)  # Active, Accepted, Rejected, Amended, Invalidated
    developer_feedback = Column(Text)
    last_codebase_change_timestamp = Column(DateTime) # Used for auto-invalidation
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())

    # Relationships (many-to-many)
    inconsistencies = relationship("Inconsistency",
                                 secondary=recommendation_inconsistencies,
                                 back_populates="recommendations")
    # Relationships (one-to-many)
    suggested_changes = relationship("SuggestedChange", back_populates="recommendation", cascade="all, delete-orphan")
    developer_decisions = relationship("DeveloperDecision", back_populates="recommendation", cascade="all, delete-orphan")

class SuggestedChange(Base):
    """Represents a specific change suggested within a recommendation."""
    __tablename__ = 'suggested_changes'

    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'))
    document_id = Column(Integer, ForeignKey('documents.id'))
    change_type = Column(String, nullable=False)  # Addition, Deletion, Modification
    location = Column(String, nullable=False) # e.g., line number range, section header
    before_text = Column(Text) # For Modification/Deletion
    after_text = Column(Text) # For Modification/Addition
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    recommendation = relationship("Recommendation", back_populates="suggested_changes")
    document = relationship("Document", back_populates="suggested_changes")

class DeveloperDecision(Base):
    """Records a developer's decision on a recommendation."""
    __tablename__ = 'developer_decisions'

    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'))
    timestamp = Column(DateTime, nullable=False)
    decision = Column(String, nullable=False)  # Accept, Reject, Amend
    comments = Column(Text) # Primarily for Amend
    implementation_timestamp = Column(DateTime) # For Accept
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    recommendation = relationship("Recommendation", back_populates="developer_decisions")

class DesignDecision(Base):
    """Represents a design decision extracted from documentation."""
    __tablename__ = 'design_decisions'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    description = Column(Text, nullable=False)
    rationale = Column(Text)
    alternatives = Column(Text)
    decision_date = Column(DateTime)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    document = relationship("Document", back_populates="design_decisions")

class ChangeRecord(Base):
    """Represents a historical change recorded in a file's header."""
    __tablename__ = 'change_records'

    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    timestamp = Column(DateTime, nullable=False)
    summary = Column(String, nullable=False)
    details = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())

    # Relationships
    document = relationship("Document", back_populates="change_records")

class SchemaVersion(Base):
    """Tracks the current version of the database schema."""
    __tablename__ = 'schema_version'

    id = Column(Integer, primary_key=True)
    version = Column(String, nullable=False)
    applied_at = Column(DateTime, default=func.current_timestamp())

class DocRelationshipORM(Base):
    """ORM model for storing document relationships."""
    __tablename__ = 'doc_relationships' # Renamed table from plan for clarity

    id = Column(Integer, primary_key=True) # Use standard integer PK
    source_document = Column(String, nullable=False, index=True) # Indexed for lookups
    target_document = Column(String, nullable=False, index=True) # Indexed for lookups
    relationship_type = Column(String, nullable=False, index=True) # Indexed
    topic = Column(String, nullable=True)
    scope = Column(String, nullable=True)
    metadata = Column(Text, nullable=True) # Store as JSON string
    created_at = Column(DateTime, default=func.current_timestamp(), nullable=False)
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp(), nullable=False)

    # Add unique constraint? Maybe not, allow multiple relationships of different types/topics
    # __table_args__ = (UniqueConstraint('source_document', 'target_document', 'relationship_type', name='uq_doc_relationship'),)

class InconsistencyORM(Base):
    """ORM model for storing detected inconsistency records."""
    __tablename__ = 'inconsistencies' # Matches table name in plan

    id = Column(Integer, primary_key=True) # Auto-incrementing primary key
    # Link back to documents involved (using paths for simplicity, could use foreign keys to documents table)
    source_file = Column(String, nullable=False, index=True)
    target_file = Column(String, nullable=True, index=True) # Target might not always apply
    # Store enums as strings
    inconsistency_type = Column(String, nullable=False, index=True)
    description = Column(String, nullable=False)
    details = Column(Text, nullable=True) # Store details dict as JSON string
    severity = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False, index=True)
    confidence_score = Column(Float, nullable=False, default=1.0)
    detected_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    resolved_at = Column(DateTime, nullable=True)
    metadata = Column(Text, nullable=True) # Store additional metadata as JSON string

class RecommendationORM(Base):
    """ORM model for storing generated recommendations."""
    __tablename__ = 'recommendations' # Matches table name in plan

    id = Column(Integer, primary_key=True) # Auto-incrementing primary key
    title = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    strategy_name = Column(String, nullable=False, index=True) # Strategy that generated it
    fix_type = Column(String, nullable=False) # Store RecommendationFixType enum value
    severity = Column(String, nullable=False, index=True) # Store RecommendationSeverity enum value
    status = Column(String, nullable=False, index=True) # Store RecommendationStatus enum value
    # Link to inconsistency records (store as JSON list of IDs for simplicity)
    # A many-to-many table might be better for complex querying.
    inconsistency_ids = Column(Text, nullable=False) # JSON array of inconsistency IDs as text
    # Files involved (can be inferred from inconsistencies, but store for quick access?)
    source_file = Column(String, nullable=True, index=True)
    target_file = Column(String, nullable=True, index=True)
    # Snippets for the proposed fix
    code_snippet = Column(Text, nullable=True)
    doc_snippet = Column(Text, nullable=True)
    # Timestamps
    created_at = Column(DateTime, nullable=False, default=func.current_timestamp())
    updated_at = Column(DateTime, nullable=False, default=func.current_timestamp(), onupdate=func.current_timestamp())
    applied_at = Column(DateTime, nullable=True) # When the recommendation was applied
    # Additional data
    metadata = Column(Text, nullable=True) # Store extra metadata as JSON string
    feedback = Column(Text, nullable=True) # Store RecommendationFeedback as JSON string
