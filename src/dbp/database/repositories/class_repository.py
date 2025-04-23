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
# Defines the ClassRepository class for managing Class entities in the database,
# providing operations to create, update, and retrieve class metadata.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides bulk creation/update operations for efficient processing.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Class model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# codebase:- doc/DATA_MODEL.md
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:15:43Z : Created class_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted ClassRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Class entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Class
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Class


logger = logging.getLogger(__name__)


class ClassRepository(BaseRepository):
    """Repository for managing Class entities."""

    def bulk_create_or_update(self, document_id: int, classes_data: list[dict]):
        """
        [Function intent]
        Creates or updates classes for a given document.
        
        [Implementation details]
        Processes a batch of class data for a single document.
        Updates existing classes or creates new ones as needed.
        
        [Design principles]
        Uses a bulk operation for better performance with multiple classes.
        Maps class attributes from the data dictionary to model fields.
        
        Args:
            document_id: ID of the document these classes belong to.
            classes_data: List of dictionaries with class metadata.
        """
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
