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
# Defines the ProjectRepository class for managing Project entities in the database,
# providing CRUD operations and specialized queries.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides clear methods for common CRUD operations on projects.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Project model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Reference documentation]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:11:08Z : Created project_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted ProjectRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Project entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Project
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Project


logger = logging.getLogger(__name__)


class ProjectRepository(BaseRepository):
    """Repository for managing Project entities."""

    def create(self, name: str, root_path: str, description: str = None) -> Project | None:
        """
        [Function intent]
        Creates a new project record in the database.
        
        [Implementation details]
        Builds a Project object with provided parameters and adds it to the database.
        
        [Design principles]
        Uses session context manager for proper transaction handling.
        Returns created object for immediate use.
        
        Args:
            name: The name of the project.
            root_path: The root filesystem path for the project.
            description: Optional description of the project.

        Returns:
            The created Project object or None if creation failed.
        """
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
        """
        [Function intent]
        Retrieves a project by its root path.
        
        [Implementation details]
        Performs a database query filtering by the root_path field.
        
        [Design principles]
        Simple read operation with proper error handling.
        
        Args:
            root_path: The root filesystem path of the project.

        Returns:
            The Project object if found, otherwise None.
        """
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
        """
        [Function intent]
        Retrieves a project by its ID.
        
        [Implementation details]
        Uses SQLAlchemy's get() method for primary key lookup.
        
        [Design principles]
        Simple read operation with proper error handling.
        
        Args:
            project_id: The unique ID of the project.

        Returns:
            The Project object if found, otherwise None.
        """
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
        """
        [Function intent]
        Lists all projects in the database.
        
        [Implementation details]
        Simple query to get all Project records.
        
        [Design principles]
        Returns empty list on error rather than None for consistent API.
        
        Returns:
            A list of all Project objects.
        """
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
