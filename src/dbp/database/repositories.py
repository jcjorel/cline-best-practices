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
# Defines repository classes that provide a high-level abstraction for database
# operations related to the DBP system. These repositories encapsulate data access
# logic, making it easier to interact with the database models.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Each repository corresponds to a primary data entity or a group of related entities.
# - Uses the DatabaseManager for session handling.
# - Provides clear methods for common CRUD (Create, Read, Update, Delete) operations.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes basic error handling and logging.
# - Design Decision: Repository Pattern (2025-04-14)
#   * Rationale: Decouples business logic from data access details, improves testability, and provides a consistent data access API.
#   * Alternatives considered: Direct model usage in services (rejected for tight coupling), Active Record pattern (rejected as ORM provides similar features).
###############################################################################
# [Source file constraints]
# - Depends on `database.py` for the DatabaseManager instance.
# - Depends on `models.py` for the ORM model definitions.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_database_schema.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:33:05Z : Initial creation of repository classes by CodeAssistant
# * Implemented BaseRepository and DocumentRepository.
###############################################################################

import logging
import datetime
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy.orm import joinedload, subqueryload

# Assuming models.py and database.py are accessible
try:
    from .models import (
        Document, Function, Class, Inconsistency, Recommendation,
        SuggestedChange, DeveloperDecision, DocumentRelationship,
        DesignDecision, ChangeRecord, Project
    )
    from .database import DatabaseManager
except ImportError:
    # Fallback for potential execution context issues
    from models import (
        Document, Function, Class, Inconsistency, Recommendation,
        SuggestedChange, DeveloperDecision, DocumentRelationship,
        DesignDecision, ChangeRecord, Project
    )
    from database import DatabaseManager


logger = logging.getLogger(__name__)

class BaseRepository:
    """Base repository with common helper methods."""

    def __init__(self, db_manager: DatabaseManager):
        """
        Initializes the BaseRepository.

        Args:
            db_manager: An instance of DatabaseManager.
        """
        if not isinstance(db_manager, DatabaseManager):
             raise TypeError("db_manager must be an instance of DatabaseManager")
        self.db_manager = db_manager
        logger.debug(f"{self.__class__.__name__} initialized.")

    def _log_error(self, operation: str, error: Exception):
        """Logs repository errors consistently."""
        logger.error(f"{self.__class__.__name__} error during '{operation}': {error}", exc_info=True)

    def _handle_sqla_error(self, operation: str, error: SQLAlchemyError):
        """Handles SQLAlchemy errors, logs, and re-raises."""
        self._log_error(operation, error)
        # Specific handling can be added here if needed, e.g., for IntegrityError
        if isinstance(error, IntegrityError):
            logger.warning(f"Integrity constraint violation during {operation}.")
        raise # Re-raise the original error after logging

class DocumentRepository(BaseRepository):
    """Repository for managing Document entities."""

    def create(self, path: str, document_type: str, project_id: int, last_modified: datetime.datetime, file_size: int = 0, md5_digest: str = None, content: str = None, header_data: dict = None) -> Document | None:
        """
        Creates a new document record in the database.

        Args:
            path: Full path to the document file.
            document_type: Type of the document (e.g., 'Code', 'Markdown').
            project_id: ID of the project this document belongs to.
            last_modified: The last modified timestamp of the file.
            file_size: Size of the file in bytes.
            md5_digest: MD5 hash of the file content.
            content: Optional file content to store.
            header_data: Optional dictionary with extracted header sections.

        Returns:
            The created Document object or None if creation failed.
        """
        operation = "create_document"
        logger.debug(f"{operation}: Creating document for path '{path}' in project {project_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = Document(
                    path=path,
                    type=document_type,
                    project_id=project_id,
                    last_modified=last_modified,
                    file_size=file_size,
                    md5_digest=md5_digest or "",
                    content=content
                )
                if header_data:
                    document.intent = header_data.get('intent')
                    # Assuming lists are stored as delimited strings or JSON
                    document.design_principles = str(header_data.get('designPrinciples', []))
                    document.constraints = str(header_data.get('constraints', []))
                    document.reference_documentation = str(header_data.get('referenceDocumentation', []))

                session.add(document)
                session.flush() # Flush to get the ID if needed immediately
                logger.info(f"{operation}: Document created with ID {document.id} for path '{path}'.")
                # Eager load relationships if needed, though usually not required on create
                # session.refresh(document, attribute_names=['project'])
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None # Explicitly return None on failure

    def get_by_path(self, path: str) -> Document | None:
        """
        Retrieves a document by its full path.

        Args:
            path: The full path of the document file.

        Returns:
            The Document object if found, otherwise None.
        """
        operation = "get_document_by_path"
        logger.debug(f"{operation}: Getting document for path '{path}'.")
        try:
            with self.db_manager.get_session() as session:
                # Consider adding options like joinedload for relationships if frequently accessed
                document = session.query(Document).filter(Document.path == path).first()
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id} for path '{path}'.")
                else:
                    logger.debug(f"{operation}: No document found for path '{path}'.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_id(self, document_id: int) -> Document | None:
        """
        Retrieves a document by its ID.

        Args:
            document_id: The unique ID of the document.

        Returns:
            The Document object if found, otherwise None.
        """
        operation = "get_document_by_id"
        logger.debug(f"{operation}: Getting document for ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id}.")
                else:
                    logger.debug(f"{operation}: No document found for ID {document_id}.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def update(self, document_id: int, update_data: dict) -> bool:
        """
        Updates an existing document record.

        Args:
            document_id: The ID of the document to update.
            update_data: A dictionary containing fields to update (e.g., 'file_size', 'md5_digest', 'header_data').

        Returns:
            True if the update was successful, False otherwise.
        """
        operation = "update_document"
        logger.debug(f"{operation}: Updating document ID {document_id} with data: {list(update_data.keys())}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if not document:
                    logger.warning(f"{operation}: Document ID {document_id} not found for update.")
                    return False

                # Update fields provided in update_data
                for key, value in update_data.items():
                    if hasattr(document, key):
                        setattr(document, key, value)
                    elif key == 'header_data' and isinstance(value, dict):
                         # Handle nested header data update
                         header_data = value
                         document.intent = header_data.get('intent', document.intent)
                         document.design_principles = str(header_data.get('designPrinciples', document.design_principles))
                         document.constraints = str(header_data.get('constraints', document.constraints))
                         document.reference_documentation = str(header_data.get('referenceDocumentation', document.reference_documentation))
                    else:
                        logger.warning(f"{operation}: Invalid field '{key}' provided for Document update.")

                # Always update the last_modified timestamp on any update
                document.last_modified = datetime.datetime.now()

                session.flush() # Commit happens at the end of the 'with' block
                logger.info(f"{operation}: Document ID {document_id} updated successfully.")
                return True
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def delete(self, document_id: int) -> bool:
        """
        Deletes a document record by its ID.

        Args:
            document_id: The ID of the document to delete.

        Returns:
            True if deletion was successful, False otherwise.
        """
        operation = "delete_document"
        logger.debug(f"{operation}: Deleting document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).get(document_id)
                if document:
                    session.delete(document)
                    session.flush() # Commit happens at the end of the 'with' block
                    logger.info(f"{operation}: Document ID {document_id} deleted successfully.")
                    return True
                else:
                    logger.warning(f"{operation}: Document ID {document_id} not found for deletion.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def list_by_project(self, project_id: int, document_type: str = None) -> list[Document]:
        """
        Lists documents belonging to a specific project, optionally filtered by type.

        Args:
            project_id: The ID of the project.
            document_type: Optional document type to filter by.

        Returns:
            A list of Document objects.
        """
        operation = "list_documents_by_project"
        filter_msg = f" for project ID {project_id}" + (f" and type '{document_type}'" if document_type else "")
        logger.debug(f"{operation}: Listing documents{filter_msg}.")
        try:
            with self.db_manager.get_session() as session:
                query = session.query(Document).filter(Document.project_id == project_id)
                if document_type:
                    query = query.filter(Document.type == document_type)
                documents = query.all()
                logger.debug(f"{operation}: Found {len(documents)} documents{filter_msg}.")
                return documents
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return [] # Return empty list on error

    def find_by_md5(self, md5_digest: str, project_id: int) -> Document | None:
        """ Finds a document by its MD5 digest within a specific project. """
        operation = "find_document_by_md5"
        logger.debug(f"{operation}: Searching for MD5 '{md5_digest}' in project {project_id}.")
        try:
            with self.db_manager.get_session() as session:
                document = session.query(Document).filter(
                    Document.project_id == project_id,
                    Document.md5_digest == md5_digest
                ).first()
                if document:
                    logger.debug(f"{operation}: Found document ID {document.id} with MD5 '{md5_digest}'.")
                else:
                    logger.debug(f"{operation}: No document found with MD5 '{md5_digest}'.")
                return document
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None


class ProjectRepository(BaseRepository):
    """Repository for managing Project entities."""

    def create(self, name: str, root_path: str, description: str = None) -> Project | None:
        """Creates a new project record."""
        operation = "create_project"
        logger.debug(f"{operation}: Creating project '{name}' at path '{root_path}'.")
        try:
            with self.db_manager.get_session() as session:
                project = Project(name=name, root_path=root_path, description=description)
                session.add(project)
                session.flush()
                logger.info(f"{operation}: Project '{name}' created with ID {project.id}.")
                return project
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_root_path(self, root_path: str) -> Project | None:
        """Retrieves a project by its root path."""
        operation = "get_project_by_root_path"
        logger.debug(f"{operation}: Getting project for root path '{root_path}'.")
        try:
            with self.db_manager.get_session() as session:
                project = session.query(Project).filter(Project.root_path == root_path).first()
                if project:
                    logger.debug(f"{operation}: Found project ID {project.id} for path '{root_path}'.")
                else:
                    logger.debug(f"{operation}: No project found for path '{root_path}'.")
                return project
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_id(self, project_id: int) -> Project | None:
        """Retrieves a project by its ID."""
        operation = "get_project_by_id"
        logger.debug(f"{operation}: Getting project for ID {project_id}.")
        try:
            with self.db_manager.get_session() as session:
                project = session.query(Project).get(project_id)
                if project:
                    logger.debug(f"{operation}: Found project ID {project.id}.")
                else:
                    logger.debug(f"{operation}: No project found for ID {project_id}.")
                return project
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def list_all(self) -> list[Project]:
        """Lists all projects."""
        operation = "list_all_projects"
        logger.debug(f"{operation}: Listing all projects.")
        try:
            with self.db_manager.get_session() as session:
                projects = session.query(Project).all()
                logger.debug(f"{operation}: Found {len(projects)} projects.")
                return projects
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []


class RelationshipRepository(BaseRepository):
    """Repository for managing DocumentRelationship entities."""

    def create(self, source_id: int, target_id: int, relationship_type: str, topic: str, scope: str) -> DocumentRelationship | None:
        """Creates a new document relationship."""
        operation = "create_relationship"
        logger.debug(f"{operation}: Creating relationship {relationship_type} from {source_id} to {target_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Check if relationship already exists to avoid duplicates
                existing = session.query(DocumentRelationship).filter_by(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=relationship_type,
                    topic=topic,
                    scope=scope
                ).first()
                if existing:
                    logger.warning(f"{operation}: Relationship already exists (ID: {existing.id}).")
                    return existing

                relationship = DocumentRelationship(
                    source_id=source_id,
                    target_id=target_id,
                    relationship_type=relationship_type,
                    topic=topic,
                    scope=scope
                )
                session.add(relationship)
                session.flush()
                logger.info(f"{operation}: Relationship created with ID {relationship.id}.")
                return relationship
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_relationships_for_document(self, document_id: int) -> list[DocumentRelationship]:
        """Retrieves all relationships where the document is either source or target."""
        operation = "get_relationships_for_document"
        logger.debug(f"{operation}: Getting relationships for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                relationships = session.query(DocumentRelationship).filter(
                    (DocumentRelationship.source_id == document_id) |
                    (DocumentRelationship.target_id == document_id)
                ).options(joinedload(DocumentRelationship.source), joinedload(DocumentRelationship.target)).all()
                logger.debug(f"{operation}: Found {len(relationships)} relationships for document ID {document_id}.")
                return relationships
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []

    def delete_relationships_for_document(self, document_id: int) -> bool:
        """Deletes all relationships associated with a document."""
        operation = "delete_relationships_for_document"
        logger.debug(f"{operation}: Deleting relationships for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                deleted_count = session.query(DocumentRelationship).filter(
                    (DocumentRelationship.source_id == document_id) |
                    (DocumentRelationship.target_id == document_id)
                ).delete(synchronize_session=False)
                session.flush()
                logger.info(f"{operation}: Deleted {deleted_count} relationships for document ID {document_id}.")
                return True
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False


class FunctionRepository(BaseRepository):
    """Repository for managing Function entities."""

    def bulk_create_or_update(self, document_id: int, functions_data: list[dict]):
        """Creates or updates functions for a given document."""
        operation = "bulk_create_or_update_functions"
        logger.debug(f"{operation}: Processing {len(functions_data)} functions for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                existing_functions = {f.name: f for f in session.query(Function).filter_by(document_id=document_id).all()}
                added_count = 0
                updated_count = 0

                for data in functions_data:
                    name = data.get('name')
                    if not name:
                        logger.warning(f"{operation}: Skipping function data with no name: {data}")
                        continue

                    func = existing_functions.get(name)
                    if func:
                        # Update existing function
                        func.intent = data.get('intent', func.intent)
                        func.design_principles = str(data.get('designPrinciples', func.design_principles))
                        func.implementation_details = data.get('implementationDetails', func.implementation_details)
                        func.design_decisions = data.get('designDecisions', func.design_decisions)
                        func.parameters = str(data.get('parameters', func.parameters))
                        func.start_line = data.get('start_line', func.start_line)
                        func.end_line = data.get('end_line', func.end_line)
                        updated_count += 1
                        logger.debug(f"{operation}: Updating function '{name}' for document ID {document_id}.")
                    else:
                        # Create new function
                        func = Function(
                            document_id=document_id,
                            name=name,
                            intent=data.get('intent'),
                            design_principles=str(data.get('designPrinciples', [])),
                            implementation_details=data.get('implementationDetails'),
                            design_decisions=data.get('designDecisions'),
                            parameters=str(data.get('parameters', [])),
                            start_line=data.get('start_line'),
                            end_line=data.get('end_line')
                        )
                        session.add(func)
                        added_count += 1
                        logger.debug(f"{operation}: Adding new function '{name}' for document ID {document_id}.")

                # Optionally delete functions that were in DB but not in new data
                # current_names = {data['name'] for data in functions_data if 'name' in data}
                # for name, func in existing_functions.items():
                #     if name not in current_names:
                #         session.delete(func)
                #         logger.debug(f"{operation}: Deleting obsolete function '{name}' for document ID {document_id}.")

                session.flush()
                logger.info(f"{operation}: Document ID {document_id}: {added_count} functions added, {updated_count} updated.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)


class ClassRepository(BaseRepository):
    """Repository for managing Class entities."""

    def bulk_create_or_update(self, document_id: int, classes_data: list[dict]):
        """Creates or updates classes for a given document."""
        operation = "bulk_create_or_update_classes"
        logger.debug(f"{operation}: Processing {len(classes_data)} classes for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                existing_classes = {c.name: c for c in session.query(Class).filter_by(document_id=document_id).all()}
                added_count = 0
                updated_count = 0

                for data in classes_data:
                    name = data.get('name')
                    if not name:
                        logger.warning(f"{operation}: Skipping class data with no name: {data}")
                        continue

                    cls = existing_classes.get(name)
                    if cls:
                        # Update existing class
                        cls.intent = data.get('intent', cls.intent)
                        cls.design_principles = str(data.get('designPrinciples', cls.design_principles))
                        cls.implementation_details = data.get('implementationDetails', cls.implementation_details)
                        cls.design_decisions = data.get('designDecisions', cls.design_decisions)
                        cls.start_line = data.get('start_line', cls.start_line)
                        cls.end_line = data.get('end_line', cls.end_line)
                        updated_count += 1
                        logger.debug(f"{operation}: Updating class '{name}' for document ID {document_id}.")
                    else:
                        # Create new class
                        cls = Class(
                            document_id=document_id,
                            name=name,
                            intent=data.get('intent'),
                            design_principles=str(data.get('designPrinciples', [])),
                            implementation_details=data.get('implementationDetails'),
                            design_decisions=data.get('designDecisions'),
                            start_line=data.get('start_line'),
                            end_line=data.get('end_line')
                        )
                        session.add(cls)
                        added_count += 1
                        logger.debug(f"{operation}: Adding new class '{name}' for document ID {document_id}.")

                session.flush()
                logger.info(f"{operation}: Document ID {document_id}: {added_count} classes added, {updated_count} updated.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)


class InconsistencyRepository(BaseRepository):
    """Repository for managing Inconsistency entities."""

    def create(self, severity: str, type: str, description: str, affected_document_ids: list[int], suggested_resolution: str = None) -> Inconsistency | None:
        """Creates a new inconsistency record."""
        operation = "create_inconsistency"
        logger.debug(f"{operation}: Creating inconsistency: type='{type}', severity='{severity}'.")
        try:
            with self.db_manager.get_session() as session:
                inconsistency = Inconsistency(
                    timestamp=datetime.datetime.now(),
                    severity=severity,
                    type=type,
                    description=description,
                    suggested_resolution=suggested_resolution,
                    status="Pending"
                )
                # Fetch Document objects for relationships
                affected_docs = session.query(Document).filter(Document.id.in_(affected_document_ids)).all()
                if len(affected_docs) != len(affected_document_ids):
                    logger.warning(f"{operation}: Some affected document IDs not found.")
                    # Decide whether to proceed or raise error
                inconsistency.affected_documents.extend(affected_docs)

                session.add(inconsistency)
                session.flush()
                logger.info(f"{operation}: Inconsistency created with ID {inconsistency.id}.")
                return inconsistency
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_pending(self) -> list[Inconsistency]:
        """Retrieves all inconsistencies with 'Pending' status."""
        operation = "get_pending_inconsistencies"
        logger.debug(f"{operation}: Fetching pending inconsistencies.")
        try:
            with self.db_manager.get_session() as session:
                inconsistencies = session.query(Inconsistency).filter(
                    Inconsistency.status == "Pending"
                ).options(joinedload(Inconsistency.affected_documents)).all()
                logger.debug(f"{operation}: Found {len(inconsistencies)} pending inconsistencies.")
                return inconsistencies
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []

    def update_status(self, inconsistency_id: int, new_status: str) -> bool:
        """Updates the status of an inconsistency."""
        operation = "update_inconsistency_status"
        logger.debug(f"{operation}: Updating status of inconsistency ID {inconsistency_id} to '{new_status}'.")
        try:
            with self.db_manager.get_session() as session:
                inconsistency = session.query(Inconsistency).get(inconsistency_id)
                if inconsistency:
                    inconsistency.status = new_status
                    session.flush()
                    logger.info(f"{operation}: Status updated for inconsistency ID {inconsistency_id}.")
                    return True
                else:
                    logger.warning(f"{operation}: Inconsistency ID {inconsistency_id} not found.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False


class RecommendationRepository(BaseRepository):
    """Repository for managing Recommendation entities."""

    def create(self, title: str, inconsistency_ids: list[int], suggested_changes_data: list[dict]) -> Recommendation | None:
        """Creates a new recommendation and associated suggested changes."""
        operation = "create_recommendation"
        logger.debug(f"{operation}: Creating recommendation '{title}'.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = Recommendation(
                    creation_timestamp=datetime.datetime.now(),
                    title=title,
                    status="Active" # Initial status
                )

                # Link inconsistencies
                inconsistencies = session.query(Inconsistency).filter(Inconsistency.id.in_(inconsistency_ids)).all()
                if len(inconsistencies) != len(inconsistency_ids):
                     logger.warning(f"{operation}: Some inconsistency IDs not found.")
                recommendation.inconsistencies.extend(inconsistencies)

                # Create suggested changes
                for change_data in suggested_changes_data:
                    doc = session.query(Document).get(change_data.get('document_id'))
                    if not doc:
                        logger.warning(f"{operation}: Document ID {change_data.get('document_id')} not found for suggested change.")
                        continue # Skip this change or raise error?

                    change = SuggestedChange(
                        document_id=change_data.get('document_id'),
                        change_type=change_data.get('change_type'),
                        location=change_data.get('location'),
                        before_text=change_data.get('before_text'),
                        after_text=change_data.get('after_text')
                    )
                    recommendation.suggested_changes.append(change)

                session.add(recommendation)

                # Update status of linked inconsistencies
                for inc in inconsistencies:
                    inc.status = "InRecommendation"

                session.flush()
                logger.info(f"{operation}: Recommendation '{title}' created with ID {recommendation.id}.")
                return recommendation
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_active(self) -> Recommendation | None:
        """Retrieves the currently active recommendation (should be only one)."""
        operation = "get_active_recommendation"
        logger.debug(f"{operation}: Fetching active recommendation.")
        try:
            with self.db_manager.get_session() as session:
                # Load relationships eagerly
                recommendation = session.query(Recommendation).filter(
                    Recommendation.status == "Active"
                ).options(
                    joinedload(Recommendation.inconsistencies).joinedload(Inconsistency.affected_documents),
                    joinedload(Recommendation.suggested_changes).joinedload(SuggestedChange.document)
                ).order_by(Recommendation.creation_timestamp).first() # Get the oldest active one

                if recommendation:
                    logger.debug(f"{operation}: Found active recommendation ID {recommendation.id}.")
                else:
                    logger.debug(f"{operation}: No active recommendation found.")
                return recommendation
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def update_status(self, recommendation_id: int, new_status: str, feedback: str = None) -> bool:
        """Updates the status of a recommendation."""
        operation = "update_recommendation_status"
        logger.debug(f"{operation}: Updating status of recommendation ID {recommendation_id} to '{new_status}'.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = session.query(Recommendation).get(recommendation_id)
                if recommendation:
                    recommendation.status = new_status
                    if new_status == "Amended" and feedback:
                        recommendation.developer_feedback = feedback
                    # Reset feedback if status changes from Amended?
                    elif recommendation.status != "Amended":
                         recommendation.developer_feedback = None

                    session.flush()
                    logger.info(f"{operation}: Status updated for recommendation ID {recommendation_id}.")
                    return True
                else:
                    logger.warning(f"{operation}: Recommendation ID {recommendation_id} not found.")
                    return False
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def invalidate_active(self, change_timestamp: datetime.datetime) -> bool:
        """Marks the active recommendation as Invalidated."""
        operation = "invalidate_active_recommendation"
        logger.debug(f"{operation}: Invalidating active recommendation due to change at {change_timestamp}.")
        try:
            with self.db_manager.get_session() as session:
                recommendation = session.query(Recommendation).filter(Recommendation.status == "Active").first()
                if recommendation:
                    recommendation.status = "Invalidated"
                    recommendation.last_codebase_change_timestamp = change_timestamp
                    session.flush()
                    logger.info(f"{operation}: Active recommendation ID {recommendation.id} invalidated.")
                    return True
                else:
                    logger.debug(f"{operation}: No active recommendation to invalidate.")
                    return False # Or True, as there was nothing to do?
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return False

    def delete_old_recommendations(self, days_old: int = 7) -> int:
        """Deletes recommendations older than a specified number of days."""
        operation = "delete_old_recommendations"
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=days_old)
        logger.info(f"{operation}: Deleting recommendations created before {cutoff_date}.")
        try:
            with self.db_manager.get_session() as session:
                # Find old recommendations (excluding Active ones?)
                query = session.query(Recommendation).filter(
                    Recommendation.creation_timestamp < cutoff_date,
                    Recommendation.status != "Active" # Don't delete the active one
                )
                count = query.delete(synchronize_session=False)
                session.flush()
                logger.info(f"{operation}: Deleted {count} old recommendations.")
                return count
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return 0


class DeveloperDecisionRepository(BaseRepository):
    """Repository for managing DeveloperDecision entities."""

    def create(self, recommendation_id: int, decision: str, comments: str = None, implementation_timestamp: datetime.datetime = None) -> DeveloperDecision | None:
        """Creates a new developer decision record."""
        operation = "create_developer_decision"
        logger.debug(f"{operation}: Recording decision '{decision}' for recommendation ID {recommendation_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Ensure recommendation exists
                recommendation = session.query(Recommendation).get(recommendation_id)
                if not recommendation:
                    logger.error(f"{operation}: Recommendation ID {recommendation_id} not found.")
                    return None

                dev_decision = DeveloperDecision(
                    recommendation_id=recommendation_id,
                    timestamp=datetime.datetime.now(),
                    decision=decision,
                    comments=comments,
                    implementation_timestamp=implementation_timestamp
                )
                session.add(dev_decision)
                session.flush()
                logger.info(f"{operation}: Decision '{decision}' recorded with ID {dev_decision.id} for recommendation ID {recommendation_id}.")
                return dev_decision
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return None

    def get_by_recommendation(self, recommendation_id: int) -> list[DeveloperDecision]:
        """Retrieves all decisions for a specific recommendation."""
        operation = "get_decisions_by_recommendation"
        logger.debug(f"{operation}: Fetching decisions for recommendation ID {recommendation_id}.")
        try:
            with self.db_manager.get_session() as session:
                decisions = session.query(DeveloperDecision).filter(
                    DeveloperDecision.recommendation_id == recommendation_id
                ).order_by(DeveloperDecision.timestamp.desc()).all()
                logger.debug(f"{operation}: Found {len(decisions)} decisions for recommendation ID {recommendation_id}.")
                return decisions
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []


class DesignDecisionRepository(BaseRepository):
    """Repository for managing DesignDecision entities."""

    def bulk_create_or_update(self, document_id: int, decisions_data: list[dict]):
        """Creates or updates design decisions for a given document."""
        operation = "bulk_create_or_update_design_decisions"
        logger.debug(f"{operation}: Processing {len(decisions_data)} design decisions for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                # Simple approach: delete existing and add new ones for the document
                session.query(DesignDecision).filter_by(document_id=document_id).delete(synchronize_session=False)
                added_count = 0
                for data in decisions_data:
                    decision = DesignDecision(
                        document_id=document_id,
                        description=data.get('description'),
                        rationale=data.get('rationale'),
                        alternatives=data.get('alternatives'),
                        decision_date=data.get('decision_date') # Assumes datetime object or None
                    )
                    session.add(decision)
                    added_count += 1
                session.flush()
                logger.info(f"{operation}: Added {added_count} design decisions for document ID {document_id}.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)


class ChangeRecordRepository(BaseRepository):
    """Repository for managing ChangeRecord entities."""

    def bulk_create(self, document_id: int, records_data: list[dict]):
        """Bulk creates change records for a document."""
        operation = "bulk_create_change_records"
        logger.debug(f"{operation}: Adding {len(records_data)} change records for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                 # Simple approach: delete existing and add new ones for the document
                session.query(ChangeRecord).filter_by(document_id=document_id).delete(synchronize_session=False)
                added_count = 0
                for data in records_data:
                    record = ChangeRecord(
                        document_id=document_id,
                        timestamp=data.get('timestamp'), # Assumes datetime object
                        summary=data.get('summary'),
                        details=data.get('details')
                    )
                    session.add(record)
                    added_count +=1
                session.flush()
                logger.info(f"{operation}: Added {added_count} change records for document ID {document_id}.")
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)

    def get_by_document(self, document_id: int) -> list[ChangeRecord]:
        """Retrieves change records for a specific document."""
        operation = "get_change_records_by_document"
        logger.debug(f"{operation}: Fetching change records for document ID {document_id}.")
        try:
            with self.db_manager.get_session() as session:
                records = session.query(ChangeRecord).filter(
                    ChangeRecord.document_id == document_id
                ).order_by(ChangeRecord.timestamp.desc()).all()
                logger.debug(f"{operation}: Found {len(records)} change records for document ID {document_id}.")
                return records
        except SQLAlchemyError as e:
            self._handle_sqla_error(operation, e)
            return []
