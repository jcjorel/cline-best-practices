# Database Schema Implementation Plan

## Overview

This plan details the database schema design and implementation for the Documentation-Based Programming system. The schema will support metadata storage, document relationships, consistency tracking, and recommendation management.

## Documentation Context

The database schema design is informed by these key documentation files:
- [doc/DATA_MODEL.md](../../doc/DATA_MODEL.md) - Defines core data entities and structures
- [doc/DESIGN.md](../../doc/DESIGN.md) - Provides architectural principles affecting database design
- [doc/SECURITY.md](../../doc/SECURITY.md) - Outlines security considerations for data storage
- [doc/CONFIGURATION.md](../../doc/CONFIGURATION.md) - Specifies database configuration parameters

## Implementation Requirements

### Functional Requirements

1. Support for storing file metadata including header sections and function/class documentation
2. Document relationship tracking with bidirectional graph capabilities
3. Inconsistency detection and storage
4. Recommendation lifecycle management
5. File change detection with efficient comparison mechanisms
6. Support for both SQLite and PostgreSQL database backends
7. Thread-safe database operations
8. Efficient querying for common access patterns
9. Project isolation (separate metadata for different projects)

### Non-Functional Requirements

1. Low memory footprint (<100MB for SQLite database)
2. Fast query response (<50ms for common queries)
3. Filesystem permission adherence
4. Protection against data corruption
5. Schema migration support
6. Efficient storage representation
7. Zero external data transmission

## Database Models

### Core Models

1. **DocumentReference**
   - Represents any file containing documentation or code
   - Contains metadata about the file (path, type, last modified)
   - Includes extracted header sections if applicable

2. **DocumentRelationship**
   - Tracks relationships between document references
   - Supports bidirectional edges (DependsOn, Impacts, Implements, Extends)
   - Includes topic and scope information

3. **InconsistencyRecord**
   - Stores detected inconsistencies between documents
   - Includes severity, type, and resolution suggestions
   - Links to affected documents

4. **Recommendation**
   - Represents actionable suggestions based on inconsistencies
   - Contains suggested changes with before/after content
   - Tracks status and developer feedback

5. **DeveloperDecision**
   - Records decisions on recommendations (Accept, Reject, Amend)
   - Includes timestamp and comments
   - Tracks implementation status

6. **FileMetadata**
   - Stores low-level file tracking data
   - Includes file size, modification time, MD5 digest
   - Used for efficient change detection

### Supporting Models

1. **DesignDecision**
   - Represents individual design decisions extracted from files
   - Includes rationale and alternatives considered

2. **FunctionMetadata**
   - Stores metadata about functions/methods in code files
   - Includes documentation sections, parameters, line ranges

3. **ClassMetadata**
   - Contains metadata about classes in code files
   - Includes documentation sections and line ranges

4. **ChangeRecord**
   - Tracks historical changes to files
   - Stores timestamp, summary, and details

5. **ProjectMetadata**
   - Contains project-level information
   - Supports multi-project isolation

## Database Schema

### Tables and Relationships

1. **documents**
   ```sql
   CREATE TABLE documents (
       id INTEGER PRIMARY KEY,
       path TEXT UNIQUE NOT NULL,
       type TEXT NOT NULL, -- Code, Markdown, Header, Config
       last_modified TIMESTAMP NOT NULL,
       file_size INTEGER NOT NULL,
       md5_digest TEXT NOT NULL,
       project_id INTEGER REFERENCES projects(id),
       content TEXT,
       -- Header sections (nullable for non-code files)
       intent TEXT,
       design_principles TEXT,
       constraints TEXT,
       reference_documentation TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

2. **document_relationships**
   ```sql
   CREATE TABLE document_relationships (
       id INTEGER PRIMARY KEY,
       source_id INTEGER NOT NULL REFERENCES documents(id),
       target_id INTEGER NOT NULL REFERENCES documents(id),
       relationship_type TEXT NOT NULL, -- DependsOn, Impacts, Implements, Extends
       topic TEXT NOT NULL,
       scope TEXT NOT NULL,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

3. **functions**
   ```sql
   CREATE TABLE functions (
       id INTEGER PRIMARY KEY,
       document_id INTEGER REFERENCES documents(id),
       name TEXT NOT NULL,
       -- Documentation sections
       intent TEXT,
       design_principles TEXT,
       implementation_details TEXT,
       design_decisions TEXT,
       parameters TEXT,
       start_line INTEGER,
       end_line INTEGER,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

4. **classes**
   ```sql
   CREATE TABLE classes (
       id INTEGER PRIMARY KEY,
       document_id INTEGER REFERENCES documents(id),
       name TEXT NOT NULL,
       -- Documentation sections
       intent TEXT,
       design_principles TEXT,
       implementation_details TEXT,
       design_decisions TEXT,
       start_line INTEGER,
       end_line INTEGER,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

5. **inconsistencies**
   ```sql
   CREATE TABLE inconsistencies (
       id INTEGER PRIMARY KEY,
       timestamp TIMESTAMP NOT NULL,
       severity TEXT NOT NULL, -- Critical, Major, Minor
       type TEXT NOT NULL, -- DocToDoc, DocToCode, DesignDecisionViolation
       description TEXT NOT NULL,
       suggested_resolution TEXT,
       status TEXT NOT NULL, -- Pending, InRecommendation, Resolved
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

6. **inconsistency_documents**
   ```sql
   CREATE TABLE inconsistency_documents (
       inconsistency_id INTEGER REFERENCES inconsistencies(id),
       document_id INTEGER REFERENCES documents(id),
       PRIMARY KEY (inconsistency_id, document_id)
   );
   ```

7. **recommendations**
   ```sql
   CREATE TABLE recommendations (
       id INTEGER PRIMARY KEY,
       creation_timestamp TIMESTAMP NOT NULL,
       title TEXT NOT NULL,
       status TEXT NOT NULL, -- Active, Accepted, Rejected, Amended, Invalidated
       developer_feedback TEXT,
       last_codebase_change_timestamp TIMESTAMP,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

8. **recommendation_inconsistencies**
   ```sql
   CREATE TABLE recommendation_inconsistencies (
       recommendation_id INTEGER REFERENCES recommendations(id),
       inconsistency_id INTEGER REFERENCES inconsistencies(id),
       PRIMARY KEY (recommendation_id, inconsistency_id)
   );
   ```

9. **suggested_changes**
   ```sql
   CREATE TABLE suggested_changes (
       id INTEGER PRIMARY KEY,
       recommendation_id INTEGER REFERENCES recommendations(id),
       document_id INTEGER REFERENCES documents(id),
       change_type TEXT NOT NULL, -- Addition, Deletion, Modification
       location TEXT NOT NULL,
       before_text TEXT,
       after_text TEXT,
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
   );
   ```

10. **developer_decisions**
    ```sql
    CREATE TABLE developer_decisions (
        id INTEGER PRIMARY KEY,
        recommendation_id INTEGER REFERENCES recommendations(id),
        timestamp TIMESTAMP NOT NULL,
        decision TEXT NOT NULL, -- Accept, Reject, Amend
        comments TEXT,
        implementation_timestamp TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

11. **design_decisions**
    ```sql
    CREATE TABLE design_decisions (
        id INTEGER PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id),
        description TEXT NOT NULL,
        rationale TEXT,
        alternatives TEXT,
        decision_date TIMESTAMP,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

12. **change_records**
    ```sql
    CREATE TABLE change_records (
        id INTEGER PRIMARY KEY,
        document_id INTEGER REFERENCES documents(id),
        timestamp TIMESTAMP NOT NULL,
        summary TEXT NOT NULL,
        details TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

13. **projects**
    ```sql
    CREATE TABLE projects (
        id INTEGER PRIMARY KEY,
        name TEXT NOT NULL,
        root_path TEXT NOT NULL UNIQUE,
        description TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

14. **schema_version**
    ```sql
    CREATE TABLE schema_version (
        id INTEGER PRIMARY KEY,
        version TEXT NOT NULL,
        applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ```

### Indexes

```sql
-- Efficient file path lookup
CREATE INDEX idx_documents_path ON documents(path);

-- Project-based filtering
CREATE INDEX idx_documents_project_id ON documents(project_id);

-- Document type filtering
CREATE INDEX idx_documents_type ON documents(type);

-- Relationship navigation
CREATE INDEX idx_document_relationships_source ON document_relationships(source_id);
CREATE INDEX idx_document_relationships_target ON document_relationships(target_id);
CREATE INDEX idx_document_relationships_type ON document_relationships(relationship_type);

-- Function lookup by name
CREATE INDEX idx_functions_name ON functions(name);
CREATE INDEX idx_functions_document_id ON functions(document_id);

-- Class lookup by name
CREATE INDEX idx_classes_name ON classes(name);
CREATE INDEX idx_classes_document_id ON classes(document_id);

-- Inconsistency filtering
CREATE INDEX idx_inconsistencies_status ON inconsistencies(status);
CREATE INDEX idx_inconsistencies_severity ON inconsistencies(severity);

-- Recommendation status filtering
CREATE INDEX idx_recommendations_status ON recommendations(status);

-- Change record timestamps
CREATE INDEX idx_change_records_timestamp ON change_records(timestamp);
```

## SQLAlchemy ORM Models

The database schema will be implemented using SQLAlchemy ORM with the following models:

```python
# models.py
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Table, Text, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class Project(Base):
    __tablename__ = 'projects'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    root_path = Column(String, nullable=False, unique=True)
    description = Column(String)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    documents = relationship("Document", back_populates="project")

class Document(Base):
    __tablename__ = 'documents'
    
    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, nullable=False)
    type = Column(String, nullable=False)  # Code, Markdown, Header, Config
    last_modified = Column(DateTime, nullable=False)
    file_size = Column(Integer, nullable=False)
    md5_digest = Column(String, nullable=False)
    project_id = Column(Integer, ForeignKey('projects.id'))
    content = Column(Text)
    
    # Header sections
    intent = Column(Text)
    design_principles = Column(Text)
    constraints = Column(Text)
    reference_documentation = Column(Text)
    
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    project = relationship("Project", back_populates="documents")
    functions = relationship("Function", back_populates="document", cascade="all, delete-orphan")
    classes = relationship("Class", back_populates="document", cascade="all, delete-orphan")
    change_records = relationship("ChangeRecord", back_populates="document", cascade="all, delete-orphan")
    design_decisions = relationship("DesignDecision", back_populates="document", cascade="all, delete-orphan")
    
    # Document relationships
    source_relationships = relationship("DocumentRelationship", 
                                       foreign_keys="DocumentRelationship.source_id",
                                       back_populates="source")
    target_relationships = relationship("DocumentRelationship", 
                                       foreign_keys="DocumentRelationship.target_id",
                                       back_populates="target")
    
    # Inconsistency relationships
    inconsistencies = relationship("Inconsistency", 
                                  secondary="inconsistency_documents",
                                  back_populates="affected_documents")
    
    # Suggested changes
    suggested_changes = relationship("SuggestedChange", back_populates="document")

class DocumentRelationship(Base):
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
    __tablename__ = 'functions'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    name = Column(String, nullable=False)
    
    # Documentation sections
    intent = Column(Text)
    design_principles = Column(Text)
    implementation_details = Column(Text)
    design_decisions = Column(Text)
    parameters = Column(Text)
    
    start_line = Column(Integer)
    end_line = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    document = relationship("Document", back_populates="functions")

class Class(Base):
    __tablename__ = 'classes'
    
    id = Column(Integer, primary_key=True)
    document_id = Column(Integer, ForeignKey('documents.id'))
    name = Column(String, nullable=False)
    
    # Documentation sections
    intent = Column(Text)
    design_principles = Column(Text)
    implementation_details = Column(Text)
    design_decisions = Column(Text)
    
    start_line = Column(Integer)
    end_line = Column(Integer)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    document = relationship("Document", back_populates="classes")

# Association table for inconsistency-document many-to-many relationship
inconsistency_documents = Table('inconsistency_documents', Base.metadata,
    Column('inconsistency_id', Integer, ForeignKey('inconsistencies.id'), primary_key=True),
    Column('document_id', Integer, ForeignKey('documents.id'), primary_key=True)
)

class Inconsistency(Base):
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
    
    # Relationships
    affected_documents = relationship("Document", secondary=inconsistency_documents, back_populates="inconsistencies")
    recommendations = relationship("Recommendation", 
                                 secondary="recommendation_inconsistencies",
                                 back_populates="inconsistencies")

# Association table for recommendation-inconsistency many-to-many relationship
recommendation_inconsistencies = Table('recommendation_inconsistencies', Base.metadata,
    Column('recommendation_id', Integer, ForeignKey('recommendations.id'), primary_key=True),
    Column('inconsistency_id', Integer, ForeignKey('inconsistencies.id'), primary_key=True)
)

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    creation_timestamp = Column(DateTime, nullable=False)
    title = Column(String, nullable=False)
    status = Column(String, nullable=False)  # Active, Accepted, Rejected, Amended, Invalidated
    developer_feedback = Column(Text)
    last_codebase_change_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=func.current_timestamp())
    updated_at = Column(DateTime, default=func.current_timestamp(), onupdate=func.current_timestamp())
    
    # Relationships
    inconsistencies = relationship("Inconsistency", 
                                 secondary=recommendation_inconsistencies,
                                 back_populates="recommendations")
    suggested_changes = relationship("SuggestedChange", back_populates="recommendation", cascade="all, delete-orphan")
    developer_decisions = relationship("DeveloperDecision", back_populates="recommendation", cascade="all, delete-orphan")

class SuggestedChange(Base):
    __tablename__ = 'suggested_changes'
    
    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'))
    document_id = Column(Integer, ForeignKey('documents.id'))
    change_type = Column(String, nullable=False)  # Addition, Deletion, Modification
    location = Column(String, nullable=False)
    before_text = Column(Text)
    after_text = Column(Text)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="suggested_changes")
    document = relationship("Document", back_populates="suggested_changes")

class DeveloperDecision(Base):
    __tablename__ = 'developer_decisions'
    
    id = Column(Integer, primary_key=True)
    recommendation_id = Column(Integer, ForeignKey('recommendations.id'))
    timestamp = Column(DateTime, nullable=False)
    decision = Column(String, nullable=False)  # Accept, Reject, Amend
    comments = Column(Text)
    implementation_timestamp = Column(DateTime)
    created_at = Column(DateTime, default=func.current_timestamp())
    
    # Relationships
    recommendation = relationship("Recommendation", back_populates="developer_decisions")

class DesignDecision(Base):
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
    __tablename__ = 'schema_version'
    
    id = Column(Integer, primary_key=True)
    version = Column(String, nullable=False)
    applied_at = Column(DateTime, default=func.current_timestamp())
```

## Database Connection Management

The database connection will be managed through a `DatabaseManager` class that:

1. Establishes connections based on configuration
2. Supports both SQLite and PostgreSQL
3. Provides thread-safe access through connection pooling
4. Implements connection retry logic
5. Handles schema migration

```python
# database.py
import os
import logging
import time
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError, OperationalError

from .models import Base, SchemaVersion

logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, config):
        self.config = config
        self.engine = None
        self.Session = None
        self.initialized = False
        
    def initialize(self):
        """Initialize the database connection."""
        db_type = self.config.get('database.type', 'sqlite')
        
        if db_type == 'sqlite':
            self._initialize_sqlite()
        elif db_type == 'postgresql':
            self._initialize_postgresql()
        else:
            raise ValueError(f"Unsupported database type: {db_type}")
            
        # Create scoped session factory
        self.Session = scoped_session(sessionmaker(bind=self.engine))
        
        # Initialize schema
        self._initialize_schema()
        
        self.initialized = True
        logger.info("Database initialized successfully")
        
    def _initialize_sqlite(self):
        """Initialize SQLite database connection."""
        db_path = self.config.get('database.path', '~/.dbp/metadata.db')
        db_path = os.path.expanduser(db_path)
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        
        # Create engine with connection pooling and WAL mode
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            poolclass=QueuePool,
            pool_size=self.config.get('database.max_connections', 4),
            max_overflow=2,
            pool_timeout=self.config.get('database.connection_timeout', 5),
            connect_args={'timeout': self.config.get('database.connection_timeout', 5)}
        )
        
        # Enable WAL mode
        if self.config.get('database.use_wal_mode', True):
            with self.engine.connect() as conn:
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute("PRAGMA synchronous=NORMAL")
                
        logger.info(f"SQLite database initialized at {db_path}")
                
    def _initialize_postgresql(self):
        """Initialize PostgreSQL database connection."""
        connection_string = self.config.get('database.connection_string')
        
        if not connection_string:
            raise ValueError("PostgreSQL connection string not provided")
            
        # Create engine with connection pooling
        self.engine = create_engine(
            connection_string,
            poolclass=QueuePool,
            pool_size=self.config.get('database.max_connections', 4),
            max_overflow=2,
            pool_timeout=self.config.get('database.connection_timeout', 5),
            pool_pre_ping=True
        )
        
        logger.info("PostgreSQL database initialized")
        
    def _initialize_schema(self):
        """Create schema if it doesn't exist or verify version."""
        # Try to create all tables
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database schema created")
            
            # Insert initial schema version
            with self.get_session() as session:
                if not session.query(SchemaVersion).first():
                    session.add(SchemaVersion(version="1.0.0"))
                    session.commit()
            
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database schema: {e}")
            raise
            
    @contextmanager
    def get_session(self):
        """Get a database session."""
        if not self.initialized:
            raise RuntimeError("Database not initialized")
            
        session = self.Session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def execute_with_retry(self, operation, max_retries=3, retry_interval=1):
        """Execute database operation with retry logic."""
        retries = 0
        while retries <= max_retries:
            try:
                return operation()
            except OperationalError as e:
                retries += 1
                if retries > max_retries:
                    logger.error(f"Operation failed after {max_retries} retries: {e}")
                    raise
                logger.warning(f"Database operation failed, retrying ({retries}/{max_retries}): {e}")
                time.sleep(retry_interval * retries)  # Exponential backoff
    
    def vacuum(self):
        """Perform database vacuum operation (SQLite only)."""
        if self.config.get('database.type') != 'sqlite':
            logger.warning("Vacuum operation only supported for SQLite")
            return
            
        try:
            # VACUUM cannot run in transaction
            self.engine.execute("VACUUM")
            logger.info("Database vacuum completed")
        except SQLAlchemyError as e:
            logger.error(f"Failed to vacuum database: {e}")
    
    def check_vacuum_needed(self):
        """Check if vacuum is needed based on free space threshold."""
        if self.config.get('database.type') != 'sqlite':
            return False
            
        threshold = self.config.get('database.vacuum_threshold', 20)
        
        try:
            # Calculate free space percentage
            result = self.engine.execute("PRAGMA page_count").scalar()
            page_count = int(result) if result else 0
            
            result = self.engine.execute("PRAGMA free_page_count").scalar()
            free_page_count = int(result) if result else 0
            
            if page_count > 0:
                free_percent = (free_page_count / page_count) * 100
                logger.debug(f"Database free space: {free_percent:.2f}%")
                return free_percent >= threshold
                
        except SQLAlchemyError as e:
            logger.error(f"Failed to check free space: {e}")
            
        return False
    
    def close(self):
        """Close all connections."""
        if self.Session:
            self.Session.remove()
            
        if self.engine:
            self.engine.dispose()
            
        logger.info("Database connections closed")
```

## Database Repository Classes

The database schema will be accessed through repository classes that provide a high-level API for database operations:

```python
# repositories.py
import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError

from .models import (
    Document, Function, Class, Inconsistency, Recommendation, 
    SuggestedChange, DeveloperDecision, DocumentRelationship,
    DesignDecision, ChangeRecord, Project
)

logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository with common operations."""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
    
    def _log_error(self, operation, error):
        """Log repository errors."""
        logger.error(f"{self.__class__.__name__} error during {operation}: {error}")

class DocumentRepository(BaseRepository):
    """Repository for document operations."""
    
    def create(self, path, document_type, project_id, file_size=0, md5_digest=None):
        """Create a new document record."""
        try:
            with self.db_manager.get_session() as session:
                document = Document(
                    path=path,
                    type=document_type,
                    project_id=project_id,
                    last_modified=datetime.datetime.now(),
                    file_size=file_size,
                    md5_digest=md5_digest or ""
                )
                session.add(document)
                session.commit()
                return document.id
        except SQLAlchemyError as e:
            self._log_error("create", e)
            raise
    
    def get_by_path(self, path):
        """Get document by path."""
        try:
            with self.db_manager.get_session() as session:
                return session.query(Document).filter(Document.path == path).first()
        except SQLAlchemyError as e:
            self._log_error("get_by_path", e)
            raise
    
    def update_metadata(self, document_id, metadata):
        """Update document metadata."""
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    if "intent" in metadata:
                        document.intent = metadata["intent"]
                    if "design_principles" in metadata:
                        document.design_principles = metadata["design_principles"]
                    if "constraints" in metadata:
                        document.constraints = metadata["constraints"]
                    if "reference_documentation" in metadata:
                        document.reference_documentation = metadata["reference_documentation"]
                    if "file_size" in metadata:
                        document.file_size = metadata["file_size"]
                    if "md5_digest" in metadata:
                        document.md5_digest = metadata["md5_digest"]
                    document.last_modified = datetime.datetime.now()
                    return True
                return False
        except SQLAlchemyError as e:
            self._log_error("update_metadata", e)
            raise
    
    def delete(self, document_id):
        """Delete document by ID."""
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    session.delete(document)
                    return True
                return False
        except SQLAlchemyError as e:
            self._log_error("delete", e)
            raise
    
    def list_by_project(self, project_id, document_type=None):
        """List documents by project and optional type."""
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Document).filter(Document.project_id == project_id)
                if document_type:
                    query = query.filter(Document.type == document_type)
                return query.all()
        except SQLAlchemyError as e:
            self._log_error
