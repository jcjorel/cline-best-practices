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
# 2025-05-07T12:56:53Z : Added direct console debugging to update_source_file by CodeAssistant
# * Added direct stderr debug output to bypass logging system
# * Implemented file existence checking at the component level
# * Added timing metrics to track execution duration
# * Enhanced error reporting with exception type information
# 2025-05-07T11:47:00Z : Initial implementation of HSTCComponent by CodeAssistant
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
        self.logger = None
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
        # Direct console output for debugging
        import sys
        print(f"[COMPONENT:DEBUG] update_source_file called with file_path={file_path}, dry_run={dry_run}", file=sys.stderr)
        sys.stderr.flush()
        
        # Check if file exists directly at this level
        import os
        if isinstance(file_path, str):
            file_exists = os.path.exists(file_path)
        else:
            file_exists = file_path.exists()
            
        print(f"[COMPONENT:DEBUG] File exists check: {file_exists}", file=sys.stderr)
        sys.stderr.flush()
        
        if not self._initialized:
            print(f"[COMPONENT:ERROR] Component not initialized", file=sys.stderr)
            sys.stderr.flush()
            raise RuntimeError("HSTC component is not initialized")
        else:
            print(f"[COMPONENT:DEBUG] Component is initialized", file=sys.stderr)
            sys.stderr.flush()
        
        # Convert string path to Path object if needed
        if isinstance(file_path, str):
            file_path = Path(file_path)
            print(f"[COMPONENT:DEBUG] Converted string path to Path object: {file_path}", file=sys.stderr)
            sys.stderr.flush()
        
        try:
            print(f"[COMPONENT:DEBUG] Calling manager.update_source_file()", file=sys.stderr)
            sys.stderr.flush()
            
            start_time = __import__('time').time()
            result = self._manager.update_source_file(file_path, dry_run)
            elapsed_time = __import__('time').time() - start_time
            
            print(f"[COMPONENT:DEBUG] Manager call completed in {elapsed_time:.2f} seconds with status: {result.get('status', 'unknown')}", file=sys.stderr)
            
            # Check if this is a dry run with updated content for debugging
            if dry_run and "updated_content" in result:
                print(f"[COMPONENT:DEBUG] Dry run result includes updated_content field of {len(result['updated_content'])} characters", file=sys.stderr)
            
            sys.stderr.flush()
            
            return result
        except Exception as e:
            print(f"[COMPONENT:ERROR] Manager call failed: {str(e)}", file=sys.stderr)
            print(f"[COMPONENT:ERROR] Exception type: {type(e).__name__}", file=sys.stderr)
            sys.stderr.flush()
            raise

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
