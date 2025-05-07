# Phase 1: Component Structure

This phase covers the base component architecture and interfaces for the HSTC module.

## Files to Implement

1. `src/dbp/hstc/__init__.py` - Package initialization
2. `src/dbp/hstc/component.py` - Main component class
3. `src/dbp/hstc/exceptions.py` - Custom exceptions

## Implementation Details

### 1. Package Initialization (`__init__.py`)

```python
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
# Package initialization for the HSTC module that manages Hierarchical Semantic Tree 
# Context (HSTC) files. Provides public imports for key components and functions.
###############################################################################
# [Source file design principles]
# - Minimal imports to avoid circular dependencies
# - Clear public interface through explicit exports
# - Version information for module tracking
###############################################################################
# [Source file constraints]
# - Must not contain implementation details, only imports and version
###############################################################################
# [Dependencies]
# codebase:src/dbp/hstc/component.py
###############################################################################
# [GenAI tool change history]
# 2025-05-07T11:08:00Z : Initial creation of HSTC module package by CodeAssistant
# * Created package initialization file
# * Added version information and imports
# * Established public interface
###############################################################################

"""
HSTC (Hierarchical Semantic Tree Context) module for managing HSTC.md files.
"""

__version__ = '0.1.0'

# Public imports
from .component import HSTCComponent
```

### 2. Component Class (`component.py`)

```python
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
# Implements the HSTCComponent class that integrates with the DBP component system
# to provide HSTC.md file management capabilities. This component acts as the entry
# point for HSTC operations and manages the underlying services.
###############################################################################
# [Source file design principles]
# - Clean component lifecycle management (initialization, shutdown)
# - Delegation to specialized services for core functionality
# - Simple public API for HSTC operations
# - Explicit dependency declaration and management
###############################################################################
# [Source file constraints]
# - Must comply with DBP component system requirements
# - Must handle initialization and shutdown correctly
# - Must manage dependencies on other components
###############################################################################
# [Dependencies]
# codebase:src/dbp/core/component.py
# codebase:src/dbp/hstc/manager.py
###############################################################################
# [GenAI tool change history]
# 2025-05-07T11:08:00Z : Initial implementation of HSTCComponent by CodeAssistant
# * Created component class with initialization and shutdown
# * Added public methods for HSTC operations
# * Set up dependency management
###############################################################################

import logging
from typing import Dict, Any, Optional, List, Union
from pathlib import Path

from dbp.core.component import Component, InitializationContext


class HSTCComponent(Component):
    """
    [Class intent]
    Provides HSTC (Hierarchical Semantic Tree Context) file management capabilities
    as a component in the DBP system. Coordinates operations for updating source
    code documentation and HSTC.md files.
    
    [Design principles]
    Follows the component pattern of the DBP system with clean initialization and shutdown.
    Delegates complex processing to specialized service classes.
    Provides a simple API for HSTC operations.
    
    [Implementation details]
    Uses HSTCManager for most functionality and handles component lifecycle.
    Manages dependencies on other components required for operation.
    """

    def __init__(self):
        """
        [Function intent]
        Initializes the HSTC component with default state.
        
        [Design principles]
        Minimal initialization with manager creation deferred to initialize().
        
        [Implementation details]
        Sets up logger and component state variables.
        """
        super().__init__()
        self.logger = logging.getLogger(__name__)
        self._manager = None

    @property
    def name(self) -> str:
        """
        [Function intent]
        Returns the unique name of this component for registration and dependency references.
        
        [Design principles]
        Clear, descriptive name following DBP component naming conventions.
        
        [Implementation details]
        Returns a simple string identifier for this component.
        
        Returns:
            str: Component name
        """
        return "hstc"

    def initialize(self, context: InitializationContext, dependencies: Optional[Dict[str, 'Component']] = None) -> None:
        """
        [Function intent]
        Initializes the component with the provided context and dependencies.
        
        [Design principles]
        Clean component initialization following DBP component pattern.
        Explicit dependency handling.
        Clear error handling and logging.
        
        [Implementation details]
        Creates the HSTCManager and initializes it.
        Sets up references to required dependencies.
        
        Args:
            context: Initialization context with configuration and resources
            dependencies: Dictionary of pre-resolved dependencies
            
        Raises:
            ComponentInitializationError: If initialization fails
        """
        try:
            self.logger = context.logger.getChild("hstc")
            self.logger.info("Initializing HSTC component")

            # Import here to avoid circular imports
            from dbp.hstc.manager import HSTCManager

            # Create and initialize the manager
            self._manager = HSTCManager(logger=self.logger)

            # Set initialization flag
            self._initialized = True
            
            self.logger.info("HSTC component initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize HSTC component: {str(e)}")
            self.set_initialization_error(e)
            raise

    def shutdown(self) -> None:
        """
        [Function intent]
        Gracefully shuts down the component and releases all resources.
        
        [Design principles]
        Clean resource release pattern.
        Proper handling of manager shutdown.
        
        [Implementation details]
        Calls shutdown on the manager if it exists.
        Sets initialization flag to False.
        
        Raises:
            ComponentShutdownError: If shutdown fails
        """
        if self._initialized:
            try:
                self.logger.info("Shutting down HSTC component")
                
                # Shutdown manager if it exists
                if self._manager:
                    # No shutdown needed for the manager currently
                    pass
                
                # Clear resources
                self._manager = None
                self._initialized = False
                
                self.logger.info("HSTC component shutdown complete")
            except Exception as e:
                self.logger.error(f"Error during HSTC component shutdown: {str(e)}")
                raise

    def update_hstc(self, directory_path: Optional[Union[str, Path]] = None, dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates HSTC.md files for a directory tree, starting from the specified directory.
        
        [Design principles]
        Simple delegation to the manager.
        Clear parameter validation and error handling.
        
        [Implementation details]
        Validates initialization state.
        Delegates to the manager's update_hstc method.
        
        Args:
            directory_path: Root directory to update (defaults to project root)
            dry_run: If True, show changes without applying them
            
        Returns:
            dict: Summary of update operations
            
        Raises:
            ComponentNotInitializedError: If component is not initialized
        """
        if not self._initialized:
            raise RuntimeError("HSTC component is not initialized")
        
        # Convert string path to Path object if needed
        if directory_path and isinstance(directory_path, str):
            directory_path = Path(directory_path)
            
        return self._manager.update_hstc(directory_path, dry_run)

    def update_source_file(self, file_path: Union[str, Path], dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates a source file's documentation to match project standards.
        
        [Design principles]
        Simple delegation to the manager.
        Clear parameter validation and error handling.
        
        [Implementation details]
        Validates initialization state.
        Delegates to the manager's update_source_file method.
        
        Args:
            file_path: Path to the source file
            dry_run: If True, return changes without applying them
            
        Returns:
            dict: Result of the operation
            
        Raises:
            ComponentNotInitializedError: If component is not initialized
        """
        if not self._initialized:
            raise RuntimeError("HSTC component is not initialized")
        
        # Convert string path to Path object if needed
        if isinstance(file_path, str):
            file_path = Path(file_path)
            
        return self._manager.update_source_file(file_path, dry_run)

    def query_hstc(self, query: str) -> Dict[str, Any]:
        """
        [Function intent]
        Queries HSTC files based on the provided query string. This is a placeholder
        for future functionality.
        
        [Design principles]
        Simple delegation to the manager.
        Clear parameter validation and error handling.
        
        [Implementation details]
        Validates initialization state.
        Delegates to the manager's query_hstc method (will be implemented in future).
        
        Args:
            query: Query string
            
        Returns:
            dict: Query results
            
        Raises:
            ComponentNotInitializedError: If component is not initialized
            NotImplementedError: As this is a placeholder for future functionality
        """
        if not self._initialized:
            raise RuntimeError("HSTC component is not initialized")
            
        # This is a placeholder for future functionality
        raise NotImplementedError("HSTC querying is not yet implemented")
```

### 3. Custom Exceptions (`exceptions.py`)

```python
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
# Defines custom exceptions for the HSTC module to provide clear error information
# and enable specific error handling.
###############################################################################
# [Source file design principles]
# - Descriptive exception names for clear error identification
# - Hierarchical exception structure with base class
# - Descriptive error messages for troubleshooting
###############################################################################
# [Source file constraints]
# - Must derive from base Exception class
# - Must include descriptive docstrings for each exception
###############################################################################
# [Dependencies]
# system:typing
###############################################################################
# [GenAI tool change history]
# 2025-05-07T11:08:00Z : Initial implementation of HSTC exceptions by CodeAssistant
# * Created base HSTCError exception
# * Added specialized exceptions for different error scenarios
# * Added complete documentation for each exception class
###############################################################################

from typing import Optional


class HSTCError(Exception):
    """
    [Class intent]
    Base exception class for all HSTC-related errors, providing a common
    type for catching any error raised by the HSTC module.
    
    [Design principles]
    Serves as a parent class for all HSTC exceptions.
    Provides a consistent error message format.
    
    [Implementation details]
    Extends the standard Exception class with additional context.
    """


class SourceProcessingError(HSTCError):
    """
    [Class intent]
    Raised when there's an error processing a source file for documentation
    standards compliance.
    
    [Design principles]
    Clear identification of source file processing errors.
    Includes file path for contextual error information.
    
    [Implementation details]
    Includes file path in the error message for easier troubleshooting.
    """
    def __init__(self, message: str, file_path: Optional[str] = None):
        """
        [Function intent]
        Initializes the exception with a message and optional file path.
        
        [Design principles]
        Includes contextual information for better error identification.
        
        [Implementation details]
        Stores file path and includes it in the formatted message.
        
        Args:
            message: Error message
            file_path: Path to the source file that caused the error
        """
        self.file_path = file_path
        if file_path:
            full_message = f"{message} (file: {file_path})"
        else:
            full_message = message
        super().__init__(full_message)


class HSTCProcessingError(HSTCError):
    """
    [Class intent]
    Raised when there's an error processing an HSTC.md file.
    
    [Design principles]
    Clear identification of HSTC file processing errors.
    Includes directory path for contextual error information.
    
    [Implementation details]
    Includes directory path in the error message for easier troubleshooting.
    """
    def __init__(self, message: str, directory_path: Optional[str] = None):
        """
        [Function intent]
        Initializes the exception with a message and optional directory path.
        
        [Design principles]
        Includes contextual information for better error identification.
        
        [Implementation details]
        Stores directory path and includes it in the formatted message.
        
        Args:
            message: Error message
            directory_path: Path to the directory that caused the error
        """
        self.directory_path = directory_path
        if directory_path:
            full_message = f"{message} (directory: {directory_path})"
        else:
            full_message = message
        super().__init__(full_message)


class ScannerError(HSTCError):
    """
    [Class intent]
    Raised when there's an error scanning directories for HSTC updates.
    
    [Design principles]
    Clear identification of scanner errors.
    
    [Implementation details]
    Extends HSTCError with specific error type.
    """


class LLMError(HSTCError):
    """
    [Class intent]
    Raised when there's an error with LLM processing, such as API errors,
    rate limiting, or invalid responses.
    
    [Design principles]
    Clear identification of LLM-related errors.
    
    [Implementation details]
    Extends HSTCError with specific error type.
    """
    def __init__(self, message: str, model_id: Optional[str] = None):
        """
        [Function intent]
        Initializes the exception with a message and optional model ID.
        
        [Design principles]
        Includes LLM model information for better error identification.
        
        [Implementation details]
        Stores model ID and includes it in the formatted message.
        
        Args:
            message: Error message
            model_id: ID of the LLM model that caused the error
        """
        self.model_id = model_id
        if model_id:
            full_message = f"{message} (model: {model_id})"
        else:
            full_message = message
        super().__init__(full_message)
```

## Interfaces for Other Classes

The component phase establishes the interfaces for the other key classes that will be implemented in later phases:

### Manager Interface

```python
class HSTCManager:
    """Interface for the HSTC manager."""
    
    def __init__(self, logger=None):
        pass
    
    def update_hstc(self, directory_path=None, dry_run=False):
        """Updates HSTC.md files for a directory tree."""
        raise NotImplementedError()
    
    def update_source_file(self, file_path, dry_run=False):
        """Updates a source file's documentation."""
        raise NotImplementedError()
    
    def query_hstc(self, query):
        """Queries HSTC files based on the provided query string."""
        raise NotImplementedError()
```

### Scanner Interface

```python
class HSTCScanner:
    """Interface for the HSTC scanner."""
    
    def __init__(self, logger=None):
        pass
    
    def scan_for_updates(self, directory_path):
        """Scans for directories that need HSTC updates."""
        raise NotImplementedError()
    
    def get_update_order(self, directories_to_update):
        """Gets the order in which directories should be updated."""
        raise NotImplementedError()
```

### Source Processor Interface

```python
class SourceCodeProcessor:
    """Interface for the source code processor."""
    
    def __init__(self, logger=None, llm_model_id=None):
        pass
    
    def update_source_file(self, file_path, dry_run=False):
        """Updates a source file's documentation."""
        raise NotImplementedError()
```

### HSTC Processor Interface

```python
class HSTCFileProcessor:
    """Interface for the HSTC file processor."""
    
    def __init__(self, logger=None, llm_model_id=None):
        pass
    
    def update_hstc_file(self, directory_path, dry_run=False):
        """Updates an HSTC.md file."""
        raise NotImplementedError()
    
    def create_hstc_file(self, directory_path, dry_run=False):
        """Creates a new HSTC.md file."""
        raise NotImplementedError()
```

## Implementation Steps

1. Create the module directory structure:
   ```bash
   mkdir -p src/dbp/hstc/prompts
   ```

2. Implement `__init__.py` with package initialization

3. Implement `component.py` with the HSTCComponent class

4. Implement `exceptions.py` with custom exceptions

5. Create placeholder files for interfaces that will be implemented in later phases:
   ```
   src/dbp/hstc/manager.py
   src/dbp/hstc/scanner.py
   src/dbp/hstc/source_processor.py
   src/dbp/hstc/hstc_processor.py
   ```

## Testing Steps

1. Verify that the component can be initialized without errors
2. Check that the component properly delegates to the manager
3. Ensure that exceptions are properly defined and raised as expected
4. Confirm that the component interface matches the requirements
