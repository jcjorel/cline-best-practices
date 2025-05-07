# Phase 2: Scanner

This phase covers the implementation of the HSTC scanner, which is responsible for identifying directories that need HSTC updates and determining the order in which they should be processed.

## Files to Implement

1. `src/dbp/hstc/scanner.py` - HSTC scanner implementation

## Implementation Details

### Scanner Implementation (`scanner.py`)

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
# Implements the HSTCScanner class that locates directories requiring HSTC.md file
# updates or creation. This scanner identifies directories with HSTC_REQUIRES_UPDATE.md
# files and directories without HSTC.md files, and determines the order in which they
# should be processed.
###############################################################################
# [Source file design principles]
# - Efficient directory traversal with minimal resource usage
# - Bottom-up processing of directory hierarchy
# - Clean separation from file processing logic
# - Respect for .gitignore patterns
###############################################################################
# [Source file constraints]
# - Must handle large directory trees efficiently
# - Must determine correct processing order (leaves to root)
# - Must properly identify update markers and missing HSTC files
###############################################################################
# [Dependencies]
# codebase:coding_assistant/scripts/identify_hstc_updates.py
# codebase:src/dbp/hstc/exceptions.py
# system:pathlib
# system:typing
# system:logging
# system:os
# system:re
###############################################################################
# [GenAI tool change history]
# 2025-05-07T11:10:00Z : Initial implementation of HSTCScanner by CodeAssistant
# * Created scanner class with directory traversal
# * Implemented update detection logic
# * Added processing order determination
###############################################################################

import os
import re
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Tuple, Union

from dbp.hstc.exceptions import ScannerError

class HSTCScanner:
    """
    [Class intent]
    Scans a project directory to identify directories requiring HSTC.md file updates
    or creation, and determines the order in which they should be processed to maintain
    hierarchical consistency.
    
    [Design principles]
    Efficient directory tree traversal with minimal resource usage.
    Clear separation between scanning and processing logic.
    Bottom-up processing to ensure child directories are updated before parents.
    Respect for gitignore patterns to avoid processing ignored files.
    
    [Implementation details]
    Uses Path objects for better cross-platform compatibility.
    Implements similar logic to identify_hstc_updates.py but with added processing order.
    Returns structured data about directories needing updates.
    """
    
    def __init__(self, logger=None):
        """
        [Function intent]
        Initializes the HSTC scanner with a logger.
        
        [Design principles]
        Minimal initialization with configuration via constructor parameters.
        
        [Implementation details]
        Sets up logger instance with proper child hierarchy if parent provided.
        
        Args:
            logger: Optional logger instance, creates new logger if None
        """
        self.logger = logger or logging.getLogger("dbp.hstc.scanner")
        # Patterns for identifying files to ignore (similar to gitignore)
        self._ignore_dirs = {'.git', '__pycache__', 'node_modules', 'venv', '.venv', 'dist', 'build'}
        
    def scan_for_updates(self, directory_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
        """
        [Function intent]
        Scans a directory tree to find directories that need HSTC updates.
        
        [Design principles]
        Comprehensive scan with clear categorization of update types.
        Efficient directory traversal with minimal resource usage.
        Clear separation of scan results by category.
        
        [Implementation details]
        Walks the directory tree to find:
        1. Directories with HSTC_REQUIRES_UPDATE.md files
        2. Directories without HSTC.md files
        3. Directories with outdated HSTC.md files (based on child modification times)
        
        Args:
            directory_path: Root directory to scan (defaults to current directory)
            
        Returns:
            dict: Scan results with directories categorized by update type
            
        Raises:
            ScannerError: If the scan fails due to permission issues or other errors
        """
        try:
            # Set default directory if not provided
            if directory_path is None:
                directory_path = Path.cwd()
            elif isinstance(directory_path, str):
                directory_path = Path(directory_path)
                
            self.logger.info(f"Scanning directory: {directory_path}")
            
            # Results containers
            dirs_with_update_required = []  # Has HSTC_REQUIRES_UPDATE.md
            dirs_without_hstc = []          # Missing HSTC.md
            dirs_with_force_update = []     # HSTC.md needs forced update (child is newer)
            
            # Cache of HSTC.md modification times for parent-child comparisons
            hstc_mod_times = {}
            
            # Perform the directory walk
            for current_dir, subdirs, files in os.walk(directory_path):
                # Skip ignored directories
                if any(ignore_dir in current_dir.split(os.sep) for ignore_dir in self._ignore_dirs):
                    continue
                    
                current_path = Path(current_dir)
                
                # Skip empty directories (no files and no non-empty subdirectories)
                if not files and not any(Path(current_dir, subdir).iterdir() for subdir in subdirs):
                    continue
                
                # Check if directory has HSTC_REQUIRES_UPDATE.md
                if 'HSTC_REQUIRES_UPDATE.md' in files:
                    dirs_with_update_required.append(current_path)
                    
                # Check if directory doesn't have HSTC.md
                if 'HSTC.md' not in files:
                    # Only include if not root and not empty
                    if str(current_path) != str(directory_path) and files:
                        dirs_without_hstc.append(current_path)
                else:
                    # Store modification time for later parent-child comparisons
                    hstc_path = current_path / 'HSTC.md'
                    hstc_mod_times[current_path] = hstc_path.stat().st_mtime
            
            # Find directories with HSTC.md files that need forced updates due to newer children
            dirs_with_force_update = self._identify_outdated_parents(hstc_mod_times)
            
            # Get the update order (bottom-up)
            all_dirs_to_update = set(dirs_with_update_required + dirs_without_hstc + dirs_with_force_update)
            update_order = self._get_update_order(list(all_dirs_to_update))
            
            # Return results
            return {
                "dirs_with_update_required": dirs_with_update_required,
                "dirs_without_hstc": dirs_without_hstc,
                "dirs_with_force_update": dirs_with_force_update,
                "update_order": update_order,
                "total_dirs": len(all_dirs_to_update)
            }
            
        except Exception as e:
            self.logger.error(f"Error scanning for HSTC updates: {str(e)}")
            raise ScannerError(f"Failed to scan for HSTC updates: {str(e)}")
    
    def _identify_outdated_parents(self, hstc_mod_times: Dict[Path, float]) -> List[Path]:
        """
        [Function intent]
        Identifies parent directories with HSTC.md files that are older than their children.
        
        [Design principles]
        Clear identification of outdated parent directories.
        Respect for directory hierarchy in modification time comparisons.
        
        [Implementation details]
        Compares modification times of parent and child HSTC.md files.
        Returns list of parent directories needing updates.
        
        Args:
            hstc_mod_times: Dictionary mapping directories to HSTC.md modification times
            
        Returns:
            list: Directories with outdated HSTC.md files
        """
        force_update_dirs = []
        
        # For each parent directory, check if any child has a newer HSTC.md
        for parent_dir in hstc_mod_times:
            parent_mod_time = hstc_mod_times[parent_dir]
            
            # Check each potential child directory
            for child_dir in hstc_mod_times:
                # Skip if same directory
                if parent_dir == child_dir:
                    continue
                
                # Check if child_dir is under parent_dir
                try:
                    rel_path = child_dir.relative_to(parent_dir)
                    
                    # If child has newer HSTC.md, parent needs update
                    if hstc_mod_times[child_dir] > parent_mod_time:
                        force_update_dirs.append(parent_dir)
                        break  # No need to check other children once we know an update is needed
                except ValueError:
                    # Not a child of this parent
                    continue
        
        return force_update_dirs
    
    def get_update_order(self, directories_to_update: List[Path]) -> List[Path]:
        """
        [Function intent]
        Determines the order in which directories should be updated to maintain
        hierarchical consistency.
        
        [Design principles]
        Bottom-up processing to ensure child directories are updated before parents.
        Clear processing order for consistent results.
        
        [Implementation details]
        Sorts directories by path length in descending order to process deepest first.
        
        Args:
            directories_to_update: List of directories requiring updates
            
        Returns:
            list: Directories in the order they should be processed (deepest first)
        """
        return self._get_update_order(directories_to_update)
    
    def _get_update_order(self, directories: List[Path]) -> List[Path]:
        """
        [Function intent]
        Internal method to sort directories in descending path length order.
        
        [Design principles]
        Simple sorting algorithm for consistent ordering.
        
        [Implementation details]
        Sorts directories by string length to prioritize deeper paths.
        
        Args:
            directories: List of directories to sort
            
        Returns:
            list: Sorted list of directories
        """
        # Sort by path length (descending) to prioritize processing deeper directories first
        return sorted(directories, key=lambda p: len(str(p)), reverse=True)
```

## Key Functionality

The HSTCScanner implements several core features:

1. **Identifying Directories Needing Updates**:
   - Directories with `HSTC_REQUIRES_UPDATE.md` files (indicating pending updates)
   - Directories without `HSTC.md` files (indicating missing documentation)
   - Directories with outdated `HSTC.md` files (based on child modification dates)

2. **Determining Update Order**:
   - Sorts directories by depth (path length) to ensure bottom-up processing
   - Ensures child directories are processed before their parents
   - Provides a deterministic order for consistent results

3. **Efficient Directory Traversal**:
   - Uses `os.walk()` for efficient directory traversal
   - Skips ignored directories (like `.git`, `__pycache__`, etc.)
   - Optimizes resource usage for large directory trees

## Integration Points

The Scanner is designed to integrate with:

1. **HSTCManager**: The manager will use the scanner to identify directories that need updates before initiating the update process.

2. **Processing Logic**: The scan results will inform the processing flow, particularly the order in which directories are processed.

## Testing Considerations

When testing the scanner implementation, consider the following scenarios:

1. **Directory Structure Variations**:
   - Directories with `HSTC_REQUIRES_UPDATE.md`
   - Directories without `HSTC.md`
   - Directories with both `HSTC.md` and `HSTC_REQUIRES_UPDATE.md`
   - Nested directories with varying update requirements

2. **Modification Time Scenarios**:
   - Parent `HSTC.md` older than child `HSTC.md`
   - Parent `HSTC.md` newer than child `HSTC.md`
   - Mixed scenarios across multiple levels

3. **Edge Cases**:
   - Empty directories
   - Directories with permission issues
   - Very deep directory hierarchies

## Implementation Steps

1. Create `scanner.py` with the implementation above

2. Test the scanner with various directory structures

3. Verify that the update order is correct (bottom-up)

4. Ensure proper error handling and logging
