#!/usr/bin/env python3
"""
[Source file intent]
Identifies directories that require HSTC.md file updates or creation based on project requirements.
This script helps maintain the Hierarchical Semantic Tree Context by finding directories that:
1. Contain HSTC_REQUIRES_UPDATE.md files (indicating pending updates)
2. Do not contain HSTC.md files (indicating missing HSTC documentation)
The script respects .gitignore patterns to avoid processing ignored files and directories.

[Source file design principles]
- Single responsibility: Focus solely on identifying directories needing HSTC updates
- Non-destructive: Read-only operations, no modifications to filesystem
- Respect project configuration: Honor .gitignore patterns
- Prioritize by complexity: Sort results by path length to handle more complex directories first

[Source file constraints]
- Must work on Unix-like and Windows systems
- Should handle large directory structures efficiently
- Must parse and respect all .gitignore files in the directory tree
"""

import os
import sys
from pathlib import Path
import re
from typing import List, Set, Dict, Tuple
import datetime


class GitIgnoreParser:
    """
    [Class intent]
    Parses .gitignore files and checks if paths match any ignore patterns.
    
    [Design principles]
    Uses path-based matching similar to Git to determine if files should be ignored.
    Follows git pattern matching rules: patterns ending with / match directories only,
    leading / restricts pattern to current directory.
    
    [Implementation details]
    Converts gitignore patterns to regex patterns for efficient matching.
    Caches compiled regex patterns for better performance.
    """
    
    def __init__(self):
        """
        [Class method intent]
        Initializes the GitIgnoreParser with empty patterns.
        
        [Design principles]
        Start with clean state, patterns added incrementally.
        
        [Implementation details]
        Creates empty sets for storing patterns and compiled regex objects.
        """
        self.patterns = []
        self._regex_cache = {}
    
    def add_patterns_from_file(self, gitignore_path: Path) -> None:
        """
        [Function intent]
        Reads and adds patterns from a .gitignore file.
        
        [Design principles]
        Processes one gitignore file at a time, validates patterns.
        
        [Implementation details]
        Reads the file line by line, skipping comments and empty lines.
        Stores base directory along with pattern for correct path matching.
        
        Args:
            gitignore_path: Path to the .gitignore file
        """
        if not gitignore_path.exists():
            return
            
        base_dir = gitignore_path.parent
        
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.rstrip()
                if not line or line.startswith('#'):
                    continue
                    
                # Remove leading ! for negated patterns (we don't handle negation in this script)
                if line.startswith('!'):
                    continue
                
                self.patterns.append((base_dir, line))
    
    def _pattern_to_regex(self, pattern: str) -> re.Pattern:
        """
        [Function intent]
        Converts a gitignore pattern to a regex pattern.
        
        [Design principles]
        Follows Git pattern matching rules while translating to Python regex.
        
        [Implementation details]
        Handles special characters, directory-only patterns, and wildcards.
        Caches compiled regex patterns for performance.
        
        Args:
            pattern: Gitignore pattern
            
        Returns:
            Compiled regex pattern
        """
        if pattern in self._regex_cache:
            return self._regex_cache[pattern]
        
        # Special case for comments and empty lines
        if not pattern or pattern.startswith('#'):
            regex = re.compile(r'^$')
            self._regex_cache[pattern] = regex
            return regex
        
        # Start with an exact match
        regex_pattern = pattern
        
        # Handle directory-only pattern (trailing slash)
        dir_only = False
        if regex_pattern.endswith('/'):
            dir_only = True
            regex_pattern = regex_pattern[:-1]
        
        # Escape special regex chars except those with special gitignore meaning
        regex_pattern = re.escape(regex_pattern)
        
        # Handle gitignore wildcards
        regex_pattern = regex_pattern.replace(r'\*\*/', '(.*?/)?')  # **/ -> match any directory depth
        regex_pattern = regex_pattern.replace(r'/\*\*', '(/.*)?')   # /** -> match anything after
        regex_pattern = regex_pattern.replace(r'\*\*', '.*?')       # ** -> match anything
        regex_pattern = regex_pattern.replace(r'\*', '[^/]*?')      # * -> match anything except /
        regex_pattern = regex_pattern.replace(r'\?', '[^/]')        # ? -> match single character except /
        
        # Handle the start-of-path marker
        if regex_pattern.startswith(r'\^'):
            regex_pattern = '^' + regex_pattern[2:]
        elif regex_pattern.startswith('/'):
            regex_pattern = '^' + regex_pattern[1:]
        else:
            regex_pattern = '.*?' + regex_pattern
        
        # Add end-of-path condition
        if dir_only:
            regex_pattern = regex_pattern + '/?$'
        else:
            regex_pattern = regex_pattern + '$'
            
        # Compile and cache the regex
        regex = re.compile(regex_pattern)
        self._regex_cache[pattern] = regex
        return regex
    
    def is_ignored(self, path: Path, is_dir: bool = None) -> bool:
        """
        [Function intent]
        Determines if a path should be ignored based on gitignore patterns.
        
        [Design principles]
        Efficient path checking by trying only relevant patterns.
        
        [Implementation details]
        Converts path to relative form for each gitignore pattern.
        Checks if path matches any ignore pattern considering its context.
        
        Args:
            path: Path to check
            is_dir: Whether the path is a directory (auto-detected if None)
            
        Returns:
            True if path should be ignored, False otherwise
        """
        if is_dir is None:
            is_dir = path.is_dir()
            
        path = path.resolve()
        
        for base_dir, pattern in self.patterns:
            # Skip patterns from unrelated directories
            if not str(path).startswith(str(base_dir)):
                continue
                
            # Get the relative path for matching
            rel_path = path.relative_to(base_dir)
            rel_str = str(rel_path).replace('\\', '/')
            
            # Add trailing slash for directories
            if is_dir and not rel_str.endswith('/'):
                rel_dir_str = rel_str + '/'
            else:
                rel_dir_str = rel_str
                
            # Try to match the pattern
            regex = self._pattern_to_regex(pattern)
            
            if regex.match(rel_str) or (is_dir and regex.match(rel_dir_str)):
                return True
                
        return False


class HSTCUpdatesScanner:
    """
    [Class intent]
    Scans a project directory to find directories that need HSTC updates.
    
    [Design principles]
    Efficiently traverses directory tree while respecting gitignore patterns.
    Organizes results by priority (path length) to handle complex directories first.
    Excludes empty directories (no files, no subdirectories) from results.
    
    [Implementation details]
    Uses Path objects for better cross-platform compatibility.
    Caches gitignore rules to avoid repeated parsing.
    """
    
    def __init__(self, root_dir: Path):
        """
        [Class method intent]
        Sets up the scanner with the root directory to scan.
        
        [Design principles]
        Initialize with minimal required state.
        
        [Implementation details]
        Creates a gitignore parser and initializes result containers.
        
        Args:
            root_dir: Root directory to start scanning from
        """
        self.root_dir = root_dir.resolve()
        self.gitignore_parser = GitIgnoreParser()
        self.dirs_with_update_required = []
        self.dirs_without_hstc = []
        self.dirs_with_force_update = []
        
        # Load all gitignore files from the root directory
        self._load_gitignore_files()
        
    def _load_gitignore_files(self) -> None:
        """
        [Function intent]
        Finds and loads all .gitignore files in the project.
        
        [Design principles]
        Load all gitignore files up front for complete rule coverage.
        
        [Implementation details]
        Uses Path.glob to find all .gitignore files and adds them to the parser.
        """
        for gitignore_path in self.root_dir.glob('**/.gitignore'):
            self.gitignore_parser.add_patterns_from_file(gitignore_path)
    
    def _should_process_directory(self, dir_path: Path) -> bool:
        """
        [Function intent]
        Determines if a directory should be processed based on gitignore rules and special exclusions.
        
        [Design principles]
        Respects project configuration to avoid processing ignored directories.
        Explicitly excludes .git directories which should not be part of HSTC tracking.
        
        [Implementation details]
        Uses gitignore parser to check if directory should be ignored.
        Also has explicit checks for specific directories that should always be ignored.
        
        Args:
            dir_path: Path to directory to check
            
        Returns:
            True if directory should be processed, False otherwise
        """
        # Explicitly exclude .git directories
        if '.git' in dir_path.parts:
            return False
            
        return not self.gitignore_parser.is_ignored(dir_path, is_dir=True)
    
    def _is_directory_empty(self, dir_path: Path) -> bool:
        """
        [Function intent]
        Determines if a directory is empty (no files and no subdirectories).
        
        [Design principles]
        Provides a simple check for empty directories to avoid processing them.
        
        [Implementation details]
        Checks if a directory contains any files or subdirectories.
        
        Args:
            dir_path: Path to directory to check
            
        Returns:
            True if directory is empty, False otherwise
        """
        # Check if directory exists
        if not dir_path.exists() or not dir_path.is_dir():
            return True
            
        # Check if directory has any contents
        has_contents = any(dir_path.iterdir())
        return not has_contents
    
    def _find_hstc_files_for_forced_update(self) -> List[Path]:
        """
        [Function intent]
        Identifies HSTC.md files that need to be forcibly updated based on child HSTC.md files having
        more recent modification dates.
        
        [Design principles]
        Ensures hierarchical consistency by identifying outdated parent HSTC.md files.
        
        [Implementation details]
        Builds a dictionary of all HSTC.md files and their modification times.
        Compares each HSTC.md file's modification time with its child HSTC.md files.
        Identifies parents that have older modification dates than their children.
        Ensures the root HSTC.md is also checked against its direct children.
        
        Returns:
            List of directories containing HSTC.md files that need forced updates
        """
        # Dictionary to store all HSTC.md files and their modification times
        hstc_files = {}
        
        # First pass: collect all HSTC.md files and their modification times
        for current_dir, _, files in os.walk(self.root_dir):
            current_path = Path(current_dir)
            
            # Skip ignored directories
            if not self._should_process_directory(current_path):
                continue
            
            # Check if directory has HSTC.md
            if 'HSTC.md' in files:
                hstc_path = current_path / 'HSTC.md'
                mod_time = datetime.datetime.fromtimestamp(hstc_path.stat().st_mtime)
                hstc_files[current_path] = mod_time
        
        # Directories needing forced updates
        force_update_dirs = []
        
        # Second pass: for each directory, check if ANY child HSTC.md file is newer
        force_update_dirs = []
        
        # Process all directories - for each parent, check if any child HSTC.md is newer
        
        # Process all directories
        for parent_dir in hstc_files:
            parent_mod_time = hstc_files[parent_dir]
            
            # Check each potential child directory at any depth
            for child_dir in hstc_files:
                # Skip if it's the same directory
                if parent_dir == child_dir:
                    continue
                
                # Check if child_dir is a subdirectory of parent_dir
                try:
                    # This will succeed if child_dir is under parent_dir
                    rel_path = child_dir.relative_to(parent_dir)
                    
                    # If rel_path exists, it's a child of some depth
                    # Check if the child's HSTC.md is newer than the parent's
                    if hstc_files[child_dir] > parent_mod_time:
                        force_update_dirs.append(parent_dir)
                        # No need to check other children once we know an update is needed
                        break
                except ValueError:
                    # Not a child of this parent
                    continue
        
        return force_update_dirs
    
    def scan(self) -> Tuple[List[Path], List[Path], List[Path]]:
        """
        [Function intent]
        Scans the directory tree to find directories needing HSTC updates.
        
        [Design principles]
        Complete but efficient traversal prioritizing important results.
        
        [Implementation details]
        Finds directories with HSTC_REQUIRES_UPDATE.md and directories without HSTC.md.
        Also identifies HSTC.md files that need forced updates based on child modification dates.
        Sorts results by path length (descending) to handle complex directories first.
        
        Returns:
            Tuple of (dirs with update required, dirs without HSTC, dirs needing forced updates)
        """
        self.dirs_with_update_required = []
        self.dirs_without_hstc = []
        
        # Traverse the directory tree
        for current_dir, subdirs, files in os.walk(self.root_dir):
            current_path = Path(current_dir)
            
            # Skip ignored directories
            if not self._should_process_directory(current_path):
                # Prevent os.walk from descending into ignored directories
                subdirs[:] = [d for d in subdirs if not self.gitignore_parser.is_ignored(
                    current_path / d, is_dir=True)]
                continue
            
            # Check if directory has HSTC_REQUIRES_UPDATE.md
            if 'HSTC_REQUIRES_UPDATE.md' in files:
                self.dirs_with_update_required.append(current_path)
                
            # Check if directory doesn't have HSTC.md
            if 'HSTC.md' not in files:
                # Only include directories, not root, and not empty directories
                if str(current_path) != str(self.root_dir) and current_path.is_dir() and not self._is_directory_empty(current_path):
                    self.dirs_without_hstc.append(current_path)
        
        # Find directories with HSTC.md files that need forced updates
        self.dirs_with_force_update = self._find_hstc_files_for_forced_update()
        
        # Sort results by path length, descending
        self.dirs_with_update_required.sort(key=lambda p: len(str(p)), reverse=True)
        self.dirs_without_hstc.sort(key=lambda p: len(str(p)), reverse=True)
        self.dirs_with_force_update.sort(key=lambda p: len(str(p)), reverse=True)
        
        return self.dirs_with_update_required, self.dirs_without_hstc, self.dirs_with_force_update


def main() -> None:
    """
    [Function intent]
    Main entry point for the script that initiates scanning and outputs results.
    
    [Design principles]
    Provides clear, organized output of scan results.
    
    [Implementation details]
    Uses the project root directory as the scanning starting point.
    Outputs results in a format useful for humans and scripts.
    Includes forced update directories when no directories require updates or are missing HSTC.md.
    """
    # Use current working directory as root if not specified
    root_dir = Path.cwd()
    
    # Create scanner and scan for updates
    scanner = HSTCUpdatesScanner(root_dir)
    dirs_with_update_required, dirs_without_hstc, dirs_with_force_update = scanner.scan()
    
    # Output directories with HSTC_REQUIRES_UPDATE.md
    if dirs_with_update_required:
        print("\n=== Directories with HSTC_REQUIRES_UPDATE.md (sorted by path length DESC) ===")
        for dir_path in dirs_with_update_required:
            print(dir_path)
    else:
        print("No directories with HSTC_REQUIRES_UPDATE.md found.")
    
    # Output directories without HSTC.md
    if dirs_without_hstc:
        print("\n=== Directories without HSTC.md (sorted by path length DESC) ===")
        for dir_path in dirs_without_hstc:
            print(dir_path)
    else:
        print("No directories without HSTC.md found.")
        
    # Always output directories with HSTC.md files that need forced updates
    if dirs_with_force_update and (not dirs_with_update_required and not dirs_without_hstc):
        print("\n=== HSTC.md files requiring forced updates (child HSTC.md files are newer) ===")
        for dir_path in dirs_with_force_update:
            print(dir_path)
    elif not dirs_with_update_required and not dirs_without_hstc:
        print("No HSTC.md files requiring forced updates found.")
        print("HSTC structure do not need any updates.")


if __name__ == "__main__":
    main()
