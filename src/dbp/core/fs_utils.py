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
# Provides filesystem utility functions used across different components in the DBP system.
# Functions for directory creation, path manipulation, and file operations that maintain
# consistency across the application and handle common error cases.
###############################################################################
# [Source file design principles]
# - Single Responsibility: Each function does one thing well and handles its error cases.
# - Defensive Programming: Functions validate inputs and handle edge cases gracefully.
# - Comprehensive Logging: All operations are logged with appropriate detail level.
# - Error Transparency: Filesystem errors are caught, logged, and re-raised with context.
# - Design Decision: Centralized Filesystem Operations (2025-04-17)
#   * Rationale: Ensures consistent directory creation and path handling across components
#   * Alternatives considered: Component-specific implementations (rejected due to duplication)
###############################################################################
# [Source file constraints]
# - Must not depend on other DBP components to avoid circular dependencies
# - Must handle relative/absolute paths consistently
# - Should not modify any global state
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-17T12:03:38Z : Updated path resolution to be Git root-relative by CodeAssistant
# * Added find_git_root and resolve_path functions
# * Updated all path handling to resolve relative to Git project root
# * Added error handling when Git root cannot be found
# 2025-04-17T11:46:24Z : Initial creation by CodeAssistant
# * Created centralized filesystem utility functions
# * Implemented ensure_directory_exists and other helper functions
###############################################################################

import os
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Union, List, Optional

logger = logging.getLogger(__name__)

def find_git_root() -> Optional[Path]:
    """
    [Function intent]
    Finds the Git root directory (the directory containing .git/) for the current project.
    Used to resolve relative paths from the project root rather than the current working directory.
    
    [Implementation details]
    Tries first using git command, then falls back to searching for .git directory upward
    from the current working directory.
    
    [Design principles]
    Provides consistent path resolution regardless of the working directory within the project.
    
    Returns:
        Path: Path to the Git root directory, or None if not found
    """
    try:
        # First approach: Use git command to find the root
        git_root = subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], 
                                         stderr=subprocess.DEVNULL,
                                         universal_newlines=True).strip()
        return Path(git_root)
    except (subprocess.SubprocessError, FileNotFoundError):
        # Git command failed, try manual search
        logger.debug("Git command failed, searching manually for .git directory")
        
    # Fall back to manually searching for .git directory
    current_path = Path.cwd().absolute()
    
    # Traverse up the directory tree
    while current_path.parent != current_path:  # Stop at filesystem root
        if (current_path / '.git').exists() and (current_path / '.git').is_dir():
            return current_path
        current_path = current_path.parent
        
    # No Git repository found
    logger.warning("Could not find Git root directory")
    return None

def resolve_path(path: Union[str, Path]) -> Path:
    """
    [Function intent]
    Resolves a path, handling user home expansion and relative paths from Git root.
    
    [Implementation details]
    For relative paths, resolves them from the Git root directory.
    If Git root can't be found, raises an error since paths must be resolved relative to project root.
    
    [Design principles]
    Consistent path resolution regardless of working directory within project.
    Fails explicitly rather than using potentially incorrect paths.
    
    Args:
        path: The path to resolve (string or Path object)
        
    Returns:
        Path: The fully resolved path
        
    Raises:
        RuntimeError: If Git root directory cannot be found for resolving relative paths
    """
    if isinstance(path, str):
        # Handle home directory expansion
        path = os.path.expanduser(path)
        path_obj = Path(path)
    else:
        path_obj = path
        
    # If it's an absolute path, just return it
    if path_obj.is_absolute():
        return path_obj
        
    # For relative paths, resolve from Git root
    git_root = find_git_root()
    if git_root is not None:
        return git_root / path_obj
    else:
        # Error if Git root not found - relative paths must be resolved from project root
        error_msg = f"Git root not found, cannot resolve relative path '{path}'"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

def ensure_directory_exists(path: Union[str, Path], create_parents: bool = True) -> bool:
    """
    [Function intent]
    Ensures a directory exists, creating it if necessary, and verifies write permissions.
    Used across components to guarantee that all required directories are available.
    
    [Implementation details]
    Handles both string and Path objects, resolves paths relative to Git root,
    creates parent directories when needed, and verifies write access after creation.
    
    [Design principles]
    Defensive programming with comprehensive error handling and detailed logging.
    Single responsibility - only handles directory existence, not file operations.
    
    Args:
        path: Directory path to ensure exists (string or Path object)
        create_parents: Whether to create parent directories if they don't exist
        
    Returns:
        bool: True if directory exists and is writable, False otherwise
        
    Raises:
        OSError: If directory cannot be created or write permissions cannot be obtained
        RuntimeError: If Git root cannot be found for resolving relative paths
    """
    try:
        # Resolve path properly from Git root if relative
        dir_path = resolve_path(path)
            
        # Log the operation
        logger.debug(f"Ensuring directory exists: {dir_path}")
        
        # Create directory if it doesn't exist
        if not dir_path.exists():
            if create_parents:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info(f"Created directory with parents: {dir_path}")
            else:
                dir_path.mkdir(exist_ok=True)
                logger.info(f"Created directory: {dir_path}")
                
        # Verify the directory exists now
        if not dir_path.exists():
            logger.error(f"Failed to create directory: {dir_path}")
            return False
            
        # Verify the directory is actually a directory
        if not dir_path.is_dir():
            logger.error(f"Path exists but is not a directory: {dir_path}")
            return False
            
        # Verify directory is writable
        if not os.access(dir_path, os.W_OK):
            logger.error(f"Directory exists but is not writable: {dir_path}")
            return False
            
        logger.debug(f"Directory exists and is writable: {dir_path}")
        return True
        
    except PermissionError as e:
        logger.error(f"Permission error creating directory {path}: {e}")
        raise OSError(f"Permission denied while creating directory {path}: {e}") from e
        
    except OSError as e:
        logger.error(f"OS error creating directory {path}: {e}")
        raise OSError(f"Failed to create directory {path}: {e}") from e
        
    except Exception as e:
        logger.error(f"Unexpected error creating directory {path}: {e}", exc_info=True)
        raise OSError(f"Unexpected error creating directory {path}: {e}") from e

def ensure_directories_exist(paths: List[Union[str, Path]]) -> bool:
    """
    [Function intent]
    Ensures multiple directories exist, creating them if necessary.
    
    [Implementation details]
    Iterates through the list of paths, ensuring each one exists.
    Logs results and returns overall success.
    
    [Design principles]
    Convenience function to ensure multiple directories exist in a single call.
    
    Args:
        paths: List of directory paths to ensure exist
        
    Returns:
        bool: True if all directories exist and are writable, False otherwise
    """
    all_successful = True
    
    for path in paths:
        try:
            success = ensure_directory_exists(path)
            if not success:
                all_successful = False
        except OSError as e:
            logger.error(f"Failed to create directory {path}: {e}")
            all_successful = False
            
    return all_successful

def ensure_path_for_file(file_path: Union[str, Path]) -> bool:
    """
    [Function intent]
    Ensures the directory path for a file exists, creating it if necessary.
    
    [Implementation details]
    Resolves the path relative to Git root if necessary, then extracts the directory
    and ensures it exists.
    
    [Design principles]
    Convenience function for ensuring directory exists before file operations.
    Properly handles paths relative to Git root.
    
    Args:
        file_path: Path to the file (the file itself doesn't need to exist)
        
    Returns:
        bool: True if directory exists and is writable, False otherwise
        
    Raises:
        RuntimeError: If Git root cannot be found for resolving relative paths
    """
    # First resolve the path properly
    resolved_path = resolve_path(file_path)
    
    # Extract the parent directory
    dir_path = resolved_path.parent
        
    # Ensure the directory exists
    return ensure_directory_exists(dir_path)


def create_dbp_gitignore(dbp_dir: Union[str, Path] = '.dbp') -> bool:
    """
    [Function intent]
    Creates a .gitignore file in the DBP data directory to exclude database files
    and logs directory from Git version control.
    
    [Implementation details]
    Resolves the path to the DBP directory relative to Git root,
    checks if a .gitignore file exists, and if not, creates one with
    appropriate exclusion patterns.
    
    [Design principles]
    Ensures sensitive and large data files are not inadvertently committed to Git.
    
    Args:
        dbp_dir: Path to the DBP data directory, defaults to '.dbp'
        
    Returns:
        bool: True if gitignore file was created or already exists, False otherwise
        
    Raises:
        RuntimeError: If Git root cannot be found for resolving relative paths
    """
    try:
        # Resolve the DBP directory path
        resolved_dbp_dir = resolve_path(dbp_dir)
        
        # Ensure the directory exists
        if not ensure_directory_exists(resolved_dbp_dir):
            logger.error(f"Failed to create DBP directory: {resolved_dbp_dir}")
            return False
            
        # Path to .gitignore file
        gitignore_path = resolved_dbp_dir / '.gitignore'
        
        # Check if .gitignore already exists
        if gitignore_path.exists():
            logger.debug(f".gitignore already exists in {resolved_dbp_dir}")
            return True
            
        # Define gitignore content
        gitignore_content = """# DBP system files to ignore
*.sqlite
*.sqlite-*
logs/
*.log
*.pid
"""

        # Write the gitignore file
        with open(gitignore_path, 'w') as f:
            f.write(gitignore_content)
            
        logger.info(f"Created .gitignore file in {resolved_dbp_dir}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to create .gitignore file in DBP directory: {e}", exc_info=True)
        return False
