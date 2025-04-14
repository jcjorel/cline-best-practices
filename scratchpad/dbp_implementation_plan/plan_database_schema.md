# Database Schema and Structure Implementation Plan

## Overview

This document details the implementation plan for the database layer of the Documentation-Based Programming system. Based on the system documentation, the database will be implemented with SQLite as the default, with optional PostgreSQL support for advanced deployments.

## Database Requirements

From the project documentation, the database system must:

1. Support both SQLite (default) and PostgreSQL
2. Use SQLite's Write-Ahead Logging (WAL) mode for improved safety and concurrency
3. Implement a thread-safe design for all database operations
4. Support migrations via Alembic
5. Maintain complete project isolation
6. Optimize for fast metadata lookups and relationship traversal
7. Implement efficient change detection using file metadata

## Implementation Components

### 1. Database Connection Manager

The Database Connection Manager will handle:

- Connection establishment for SQLite and PostgreSQL
- Connection pooling for improved performance
- Thread-safe access mechanisms
- Transaction management
- Error handling and recovery
- Database version checking and migration

#### Implementation Approach

```python
class DatabaseConnectionManager:
    def __init__(self, config):
        """Initialize connection manager with configuration."""
        self.config = config
        self.engine = None
        self.session_factory = None
        self._setup_database()
        
    def _setup_database(self):
        """Set up database connection based on configuration."""
        if self.config.get('database.type') == 'postgresql':
            self._setup_postgresql()
        else:
            self._setup_sqlite()
            
    def _setup_sqlite(self):
        """Set up SQLite database with WAL mode."""
        # Create directory if it doesn't exist
        # Initialize SQLite with WAL mode
        # Set up connection pooling
        
    def _setup_postgresql(self):
        """Set up PostgreSQL database."""
        # Establish connection to PostgreSQL
        # Verify credentials and access
        # Set up connection pooling
        
    def get_session(self):
        """Get a thread-safe session for database operations."""
        # Return a scoped session from session factory
        
    def close_all_connections(self):
        """Close all connections in the pool."""
        # Clean up resources
```

### 2. Database Schema Definition

The database schema will be defined using SQLAlchemy ORM classes with appropriate indexes for efficient queries. Based on the `DATA_MODEL.md` document, the following tables will be implemented:

#### Document References Table

```python
class DocumentReference(Base):
    __tablename__ = "document_references"
    
    id = Column(Integer, primary_key=True)
    path = Column(String, index=True, unique=True)
    type = Column(Enum("Code", "Markdown", "Header", "Config"))
    last_modified = Column(DateTime)
    size = Column(Integer)
    md5_digest = Column(String)  # For reliable change detection
    
    # Header sections stored as JSON
    header_sections = Column(JSON)
    
    # Relationships
    design_decisions = relationship("DesignDecision", back_populates="document")
    dependencies = relationship(
        "DocumentReference",
        secondary="document_dependencies",
        primaryjoin="DocumentReference.id==document_dependencies.c.source_id",
        secondaryjoin="DocumentReference.id==document_dependencies.c.target_id"
    )
```

#### Document Relationships Table

```python
document_dependencies = Table(
    "document_dependencies",
    Base.metadata,
    Column("source_id", Integer, ForeignKey("document_references.id"), primary_key=True),
    Column("target_id", Integer, ForeignKey("document_references.id"), primary_key=True),
    Column("relation_type", String),
    Column("topic", String),
    Column("scope", String),
)
```

#### Inconsistency Records Table

```python
class InconsistencyRecord(Base):
    __tablename__ = "inconsistency_records"
    
    id = Column(String, primary_key=True)  # UUID
    timestamp = Column(DateTime, index=True)
    severity = Column(Enum("Critical", "Major", "Minor"))
    type = Column(Enum("DocToDoc", "DocToCode", "DesignDecisionViolation"))
    description = Column(String)
    suggested_resolution = Column(String)
    status = Column(Enum("Pending", "InRecommendation", "Resolved"))
    
    # Many-to-many relationship with affected documents
    affected_documents = relationship(
        "DocumentReference",
        secondary="inconsistency_document_map"
    )
```

#### Recommendations Table

```python
class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id = Column(String, primary_key=True)  # UUID
    creation_timestamp = Column(DateTime, index=True)
    title = Column(String)
    suggested_changes = Column(JSON)  # Store structured changes
    status = Column(Enum("Active", "Accepted", "Rejected", "Amended", "Invalidated"))
    developer_feedback = Column(String)
    last_codebase_change_timestamp = Column(DateTime)
    
    # Relationships
    inconsistencies = relationship("InconsistencyRecord")
    affected_documents = relationship(
        "DocumentReference",
        secondary="recommendation_document_map"
    )
```

#### Developer Decisions Table

```python
class DeveloperDecision(Base):
    __tablename__ = "developer_decisions"
    
    id = Column(Integer, primary_key=True)
    recommendation_id = Column(String, ForeignKey("recommendations.id"))
    timestamp = Column(DateTime, index=True)
    decision = Column(Enum("Accept", "Reject", "Amend"))
    comments = Column(String)
    implementation_timestamp = Column(DateTime, nullable=True)
    
    # Relationship
    recommendation = relationship("Recommendation")
```

#### File Metadata Table

```python
class FileMetadata(Base):
    __tablename__ = "file_metadata"
    
    id = Column(Integer, primary_key=True)
    path = Column(String, index=True, unique=True)
    language = Column(String)
    last_modified = Column(DateTime)
    size = Column(Integer)
    md5_digest = Column(String)
    
    # Store extracted metadata as JSON for flexibility
    functions = Column(JSON)
    classes = Column(JSON)
    header_sections = Column(JSON)
```

#### Additional Join Tables

```python
inconsistency_document_map = Table(
    "inconsistency_document_map",
    Base.metadata,
    Column("inconsistency_id", String, ForeignKey("inconsistency_records.id"), primary_key=True),
    Column("document_id", Integer, ForeignKey("document_references.id"), primary_key=True)
)

recommendation_document_map = Table(
    "recommendation_document_map",
    Base.metadata,
    Column("recommendation_id", String, ForeignKey("recommendations.id"), primary_key=True),
    Column("document_id", Integer, ForeignKey("document_references.id"), primary_key=True)
)
```

### 3. Database Migration System

The migration system will use Alembic for schema versioning and migrations:

```python
class DatabaseMigrationManager:
    def __init__(self, connection_manager):
        """Initialize migration manager with connection manager."""
        self.connection_manager = connection_manager
        
    def check_version(self):
        """Check current database version against expected version."""
        # Get current version from database
        # Compare with expected version
        
    def needs_migration(self):
        """Check if migration is needed."""
        # Compare versions to determine if migration is needed
        
    def run_migrations(self):
        """Run pending migrations."""
        # Use Alembic to run migrations
        # Handle errors and rollback if necessary
        
    def initialize_new_database(self):
        """Initialize a new database from scratch."""
        # Create all tables
        # Insert any necessary initial data
```

### 4. Change Detection System

The change detection system will efficiently track file changes:

```python
class FileChangeDetector:
    def __init__(self, db_session):
        """Initialize change detector with database session."""
        self.db_session = db_session
        
    def has_file_changed(self, file_path, mod_time, size):
        """Check if a file has changed based on metadata."""
        # Query file metadata from database
        # Compare modification time and size for quick check
        
    def update_file_metadata(self, file_path, mod_time, size, md5_digest=None):
        """Update file metadata in database."""
        # If md5_digest is not provided, calculate it
        # Update database record
        
    def calculate_md5(self, file_path):
        """Calculate MD5 digest for a file."""
        # Read file content
        # Calculate MD5 hash
        # Return digest
```

### 5. Database Repository Pattern

To abstract database operations and provide a clean interface:

```python
class DocumentReferenceRepository:
    def __init__(self, db_session):
        """Initialize repository with database session."""
        self.db_session = db_session
        
    def get_by_path(self, path):
        """Get document reference by path."""
        # Query database
        
    def save(self, document_reference):
        """Save document reference."""
        # Add or update in database
        
    def delete(self, document_reference):
        """Delete document reference."""
        # Remove from database
        
    def find_by_type(self, type):
        """Find document references by type."""
        # Query database with filter
        
    # Additional query methods
```

Similar repository classes will be implemented for other entity types.

## Error Handling Strategy

Following the "throw on error" principle from the project documentation:

1. All database operations will be wrapped in try/except blocks
2. Errors will be caught, logged, and re-thrown with clear context
3. Error messages will include both what failed and why it failed
4. No silent error handling will be implemented

## Implementation Order

1. Create database connection manager supporting both SQLite and PostgreSQL
2. Define the database schema classes using SQLAlchemy ORM
3. Implement the database migration system using Alembic
4. Create the change detection system for efficient file tracking
5. Implement repository classes for clean data access
6. Add thread-safety mechanisms throughout the database layer
7. Implement automated cleanup for old recommendations and decisions (7-day purge)
8. Add comprehensive logging for all database operations
9. Write unit tests for all database components

## Technical Design Decisions

### SQLite Configuration

SQLite will be configured with:

- Write-Ahead Logging (WAL) mode for improved concurrency
- Journal size limit to prevent excessive disk usage
- Page size optimization based on expected data patterns
- Foreign key constraints enabled
- Busy timeout for concurrent access handling

### PostgreSQL Configuration

PostgreSQL support will include:

- Connection pooling for efficient resource usage
- Prepared statement caching
- Connection timeout handling
- Schema validation on startup
- Appropriate index creation for query patterns

### Thread Safety Implementation

Thread safety will be ensured by:

- Using SQLAlchemy's scoped session pattern
- Implementing proper session management
- Using thread-local storage for session contexts
- Explicit transaction boundaries
- Connection pooling with appropriate pool size

## Integration Points

The database layer will integrate with:

1. **Configuration System**: For database connection parameters
2. **File System Monitor**: For triggering change detection
3. **Metadata Extraction**: For storing extracted metadata
4. **Consistency Analysis**: For retrieving metadata for analysis
5. **Recommendation Generator**: For storing and retrieving recommendations

## Testing Strategy

1. **Unit Tests**: Test individual components with mock dependencies
2. **Integration Tests**: Test database operations with in-memory SQLite
3. **Migration Tests**: Verify schema migrations work properly
4. **Performance Tests**: Ensure query performance meets requirements
5. **Thread Safety Tests**: Verify concurrent operations work correctly

## Security Considerations

As outlined in SECURITY.md:

1. Database file will be protected by filesystem permissions
2. No external connections will be established
3. Input validation will be performed on all queries
4. Project isolation will be strictly enforced
5. Only necessary data will be stored (data minimization)
6. Clean-up processes will remove old data

## Performance Optimization

To meet the performance requirements (<5% CPU, <100MB RAM):

1. Use prepared statements for common queries
2. Implement appropriate indexes based on query patterns
3. Use lazy loading for large datasets
4. Implement query result caching where appropriate
5. Use batch operations for multiple inserts/updates
6. Implement database connection pooling
7. Optimize SQLite page size and cache size
8. Use efficient data serialization for JSON columns
