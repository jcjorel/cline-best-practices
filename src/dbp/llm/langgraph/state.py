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
# Provides state management functionality for LangGraph workflows. This includes
# state creation, persistence, tracking, and transitions, enabling stateful agent
# workflows with proper history tracking and typed state models.
###############################################################################
# [Source file design principles]
# - Clean state management interface
# - Support for typed state models
# - Efficient state transitions and history tracking
# - Thread-safe state operations
# - Support for both in-memory and persistent state
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with LangGraph's state model
# - Must support concurrent state access
# - Must efficiently handle state history without excessive memory usage
# - Must provide type safety for state operations
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/common/exceptions.py
# system:uuid
# system:logging
# system:threading
# system:typing
# system:pydantic
###############################################################################
# [GenAI tool change history]
# 2025-05-02T11:32:00Z : Initial creation for LangChain/LangGraph integration by CodeAssistant
# * Created StateManager class for workflow state management
# * Implemented state creation, retrieval, and update operations
# * Added history tracking and type validation for state
###############################################################################

"""
State management for LangGraph workflows.
"""

import logging
import uuid
import threading
from typing import Dict, Any, List, Optional, TypeVar, Generic, Type, Union
from pydantic import BaseModel, create_model, ValidationError

# Custom exception for state operations
class StateError(Exception):
    """Base exception for state management errors."""
    pass

class StateManager:
    """
    [Class intent]
    Manages state for LangGraph workflows. This class provides a central
    repository for state management, enabling stateful agent workflows
    with proper persistence and retrieval.
    
    [Design principles]
    - Clean state management interface
    - Support for typed state models
    - Efficient state transitions
    - Support for state persistence
    
    [Implementation details]
    - Uses Pydantic models for type-safe state
    - Manages state creation and transitions
    - Provides history tracking
    - Supports state serialization
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """
        [Method intent]
        Initialize the state manager.
        
        [Design principles]
        - Minimal initialization
        - Support for customization
        
        [Implementation details]
        - Sets up logging
        - Initializes state storage
        - Creates thread safety lock
        
        Args:
            logger: Optional custom logger instance
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self._states = {}
        self._history = {}
        self._state_models = {}
        self._lock = threading.RLock()  # Reentrant lock for thread safety
    
    def create_state(
        self, 
        state_id: Optional[str] = None, 
        initial_values: Optional[Dict[str, Any]] = None,
        state_schema: Optional[Type[BaseModel]] = None
    ) -> str:
        """
        [Method intent]
        Create a new state instance with optional initial values.
        
        [Design principles]
        - Simple state creation
        - Support for initial values
        - Unique state identification
        
        [Implementation details]
        - Generates unique ID if not provided
        - Initializes state with provided values
        - Sets up history tracking
        
        Args:
            state_id: Optional ID for the state
            initial_values: Optional initial state values
            state_schema: Optional Pydantic model for state validation
            
        Returns:
            str: State ID
            
        Raises:
            StateError: If state creation fails
        """
        with self._lock:
            # Generate UUID if not provided
            if state_id is None:
                state_id = str(uuid.uuid4())
            elif state_id in self._states:
                raise StateError(f"State with ID {state_id} already exists")
            
            # Initialize state values
            state_values = {}
            if initial_values:
                state_values.update(initial_values)
            
            # Store state schema if provided
            if state_schema is not None:
                self._state_models[state_id] = state_schema
                
                # Validate initial values if schema provided
                try:
                    state_values = state_schema(**state_values).dict()
                except ValidationError as e:
                    raise StateError(f"Initial values don't match schema: {e}")
            
            # Create initial state
            self._states[state_id] = state_values
            
            # Initialize history
            self._history[state_id] = []
            
            self.logger.debug(f"Created state {state_id}")
            return state_id
    
    def get_state(self, state_id: str) -> Dict[str, Any]:
        """
        [Method intent]
        Get the current state for a given state ID.
        
        [Design principles]
        - Simple state access
        - Error handling
        
        [Implementation details]
        - Validates state existence
        - Returns state copy to prevent untracked modification
        
        Args:
            state_id: State ID to retrieve
            
        Returns:
            Dict[str, Any]: Current state
            
        Raises:
            StateError: If state_id doesn't exist
        """
        with self._lock:
            if state_id not in self._states:
                raise StateError(f"State {state_id} not found")
            
            # Return copy to prevent untracked modification
            return self._states[state_id].copy()
    
    def update_state(
        self, 
        state_id: str, 
        updates: Dict[str, Any], 
        track_history: bool = True
    ) -> Dict[str, Any]:
        """
        [Method intent]
        Update an existing state with new values.
        
        [Design principles]
        - Clean state transition
        - Optional history tracking
        - Support for partial updates
        
        [Implementation details]
        - Validates state existence
        - Tracks previous state in history if enabled
        - Merges updates with existing state
        - Validates against schema if available
        
        Args:
            state_id: State ID to update
            updates: State updates to apply
            track_history: Whether to record this update in history
            
        Returns:
            Dict[str, Any]: Updated state
            
        Raises:
            StateError: If state_id doesn't exist or validation fails
        """
        with self._lock:
            if state_id not in self._states:
                raise StateError(f"State {state_id} not found")
            
            # Track history if enabled
            if track_history:
                self._history[state_id].append(self._states[state_id].copy())
            
            # Create new state with updates
            new_state = self._states[state_id].copy()
            new_state.update(updates)
            
            # Validate against schema if available
            if state_id in self._state_models:
                try:
                    model = self._state_models[state_id]
                    new_state = model(**new_state).dict()
                except ValidationError as e:
                    raise StateError(f"Updated state doesn't match schema: {e}")
            
            # Update state
            self._states[state_id] = new_state
            
            self.logger.debug(f"Updated state {state_id}")
            return new_state.copy()
    
    def get_history(self, state_id: str) -> List[Dict[str, Any]]:
        """
        [Method intent]
        Get the history of state transitions for a given state ID.
        
        [Design principles]
        - Support for state debugging
        - Complete history access
        
        [Implementation details]
        - Validates state existence
        - Returns history copy to prevent modification
        
        Args:
            state_id: State ID to retrieve history for
            
        Returns:
            List[Dict[str, Any]]: List of historical states
            
        Raises:
            StateError: If state_id doesn't exist
        """
        with self._lock:
            if state_id not in self._history:
                raise StateError(f"State {state_id} not found")
            
            # Return copy to prevent modification
            return self._history[state_id].copy()
    
    def delete_state(self, state_id: str) -> None:
        """
        [Method intent]
        Delete a state and its history.
        
        [Design principles]
        - Support for state cleanup
        - Complete removal of state data
        
        [Implementation details]
        - Validates state existence
        - Removes state, history, and schema
        
        Args:
            state_id: State ID to delete
            
        Raises:
            StateError: If state_id doesn't exist
        """
        with self._lock:
            if state_id not in self._states:
                raise StateError(f"State {state_id} not found")
            
            # Remove state, history, and schema
            del self._states[state_id]
            del self._history[state_id]
            if state_id in self._state_models:
                del self._state_models[state_id]
            
            self.logger.debug(f"Deleted state {state_id}")
    
    def create_state_model(
        self, 
        name: str, 
        field_types: Dict[str, Type]
    ) -> Type[BaseModel]:
        """
        [Method intent]
        Create a Pydantic model for state validation.
        
        [Design principles]
        - Dynamic model creation
        - Type safety for state
        - Clean interface
        
        [Implementation details]
        - Uses Pydantic to create model dynamically
        - Returns model class for use with state
        
        Args:
            name: Name for the model class
            field_types: Dictionary of field names and types
            
        Returns:
            Type[BaseModel]: Created Pydantic model class
            
        Raises:
            ValueError: If model creation fails
        """
        try:
            # Create model dynamically
            model = create_model(name, **field_types)
            return model
        except Exception as e:
            raise ValueError(f"Failed to create state model: {e}")
    
    def serialize_state(self, state_id: str) -> Dict[str, Any]:
        """
        [Method intent]
        Serialize a state for persistence or transmission.
        
        [Design principles]
        - Support for state persistence
        - Complete state representation
        
        [Implementation details]
        - Includes state values and metadata
        - Excludes history for efficiency
        
        Args:
            state_id: State ID to serialize
            
        Returns:
            Dict[str, Any]: Serialized state
            
        Raises:
            StateError: If state_id doesn't exist
        """
        with self._lock:
            if state_id not in self._states:
                raise StateError(f"State {state_id} not found")
            
            # Get model name if available
            model_name = None
            if state_id in self._state_models:
                model_name = self._state_models[state_id].__name__
                
            # Create serialized representation
            serialized = {
                "state_id": state_id,
                "values": self._states[state_id],
                "model_name": model_name
            }
            
            return serialized
    
    def get_all_state_ids(self) -> List[str]:
        """
        [Method intent]
        Get all currently managed state IDs.
        
        [Design principles]
        - Support for state enumeration
        - Clean interface
        
        [Implementation details]
        - Returns list of state IDs
        - Thread-safe access
        
        Returns:
            List[str]: List of state IDs
        """
        with self._lock:
            return list(self._states.keys())
