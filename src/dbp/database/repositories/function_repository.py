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
# Defines the FunctionRepository class for managing Function entities in the database,
# providing operations to create, update, and retrieve function metadata.
###############################################################################
# [Source file design principles]
# - Follows the Repository pattern to separate data access logic.
# - Provides bulk creation/update operations for efficient processing.
# - Encapsulates SQLAlchemy-specific query logic.
# - Includes proper error handling and logging.
###############################################################################
# [Source file constraints]
# - Depends on BaseRepository from base_repository.py.
# - Depends on Function model from models.py.
# - Assumes a properly initialized DatabaseManager is provided.
###############################################################################
# [Dependencies]
# - doc/DATA_MODEL.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T22:14:25Z : Created function_repository.py as part of repositories.py refactoring by CodeAssistant
# * Extracted FunctionRepository class from original repositories.py
###############################################################################

"""
Repository implementation for Function entity operations.
"""

import logging
from sqlalchemy.exc import SQLAlchemyError

# Import required dependencies
try:
    from .base_repository import BaseRepository
    from ..models import Function
except ImportError:
    # Fallback for potential execution context issues
    from base_repository import BaseRepository
    from models import Function


logger = logging.getLogger(__name__)


class FunctionRepository(BaseRepository):
    """Repository for managing Function entities."""

    def bulk_create_or_update(self, document_id: int, functions_data: list[dict]):
        """
        [Function intent]
        Creates or updates functions for a given document.
        
        [Implementation details]
        Processes a batch of function data for a single document.
        Updates existing functions or creates new ones as needed.
        
        [Design principles]
        Uses a bulk operation for better performance with multiple functions.
        Maps function attributes from the data dictionary to model fields.
        
        Args:
            document_id: ID of the document these functions belong to.
            functions_data: List of dictionaries with function metadata.
        """
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
