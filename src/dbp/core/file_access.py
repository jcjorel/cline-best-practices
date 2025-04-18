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
# Implements the FileAccessService class, which provides a standard interface
# for accessing file content across the DBP system. This service is used by 
# components like doc_relationships to read file contents without having to
# implement their own file access logic.
###############################################################################
# [Source file design principles]
# - Simple, focused interface for file operations
# - Error handling with clear reporting
# - Minimal dependencies to ensure wide reusability
# - Follows a service pattern for consistent file access across components
###############################################################################
# [Source file constraints]
# - Must handle file read errors gracefully with appropriate logging
# - Should support basic file encoding detection
# - Does not handle writing to files (read-only service)
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T15:40:30Z : Initial creation of FileAccessService by CodeAssistant
# * Implemented file access service with standard methods for reading file content
###############################################################################

import logging
import os
import chardet
from typing import Optional, Tuple, Dict, Any

logger = logging.getLogger(__name__)

class FileAccessService:
    """
    [Class intent]
    Provides a unified interface for file access operations across the DBP system,
    focusing primarily on reading file content with appropriate error handling.
    
    [Implementation details]
    Handles file reading with encoding detection, caching options, and error reporting.
    
    [Design principles]
    Simple, focused service interface for consistent file operations.
    """
    
    def __init__(self, config: Any = None, logger_override: Optional[logging.Logger] = None):
        """
        [Function intent]
        Initializes the FileAccessService with configuration and logging.
        
        [Implementation details]
        Sets up logging and optional configuration parameters.
        
        [Design principles]
        Minimal initialization with clear dependency management.
        
        Args:
            config: Optional configuration for file access parameters
            logger_override: Optional logger instance to use instead of the default
        """
        self.logger = logger_override if logger_override else logger.getChild('file_access')
        self.config = config
        self._content_cache: Dict[str, Tuple[str, float]] = {}  # path -> (content, timestamp)
        self.logger.debug("FileAccessService initialized")
    
    def read_file_content(self, file_path: str, use_cache: bool = False) -> Optional[str]:
        """
        [Function intent]
        Reads the content of a file with encoding detection.
        
        [Implementation details]
        Attempts to detect the file encoding and read the content.
        Optionally uses a cache to improve performance for frequently accessed files.
        
        [Design principles]
        Robust error handling with useful logging.
        Encoding detection for better text handling.
        
        Args:
            file_path: Path to the file to read
            use_cache: Whether to use/update the content cache
            
        Returns:
            The file content as a string, or None if reading failed
        """
        if not os.path.isfile(file_path):
            self.logger.warning(f"File not found: {file_path}")
            return None
            
        # Check cache if enabled
        if use_cache and file_path in self._content_cache:
            cached_content, cached_time = self._content_cache[file_path]
            file_mtime = os.path.getmtime(file_path)
            
            # Use cache if file hasn't been modified
            if file_mtime <= cached_time:
                self.logger.debug(f"Using cached content for {file_path}")
                return cached_content
                
        try:
            # Read the file in binary mode first for encoding detection
            with open(file_path, 'rb') as f:
                raw_content = f.read()
                
            if not raw_content:
                self.logger.debug(f"Empty file: {file_path}")
                if use_cache:
                    self._content_cache[file_path] = ('', os.path.getmtime(file_path))
                return ''
                
            # Detect encoding
            result = chardet.detect(raw_content)
            encoding = result['encoding'] if result['confidence'] > 0.7 else 'utf-8'
            
            # Decode content
            try:
                content = raw_content.decode(encoding)
            except UnicodeDecodeError:
                # Fallback to utf-8 if detected encoding fails
                self.logger.warning(f"Failed to decode with detected encoding {encoding}, falling back to utf-8 for {file_path}")
                content = raw_content.decode('utf-8', errors='replace')
            
            # Update cache if enabled
            if use_cache:
                self._content_cache[file_path] = (content, os.path.getmtime(file_path))
                
            return content
            
        except Exception as e:
            self.logger.error(f"Error reading file {file_path}: {str(e)}")
            return None
            
    def clear_cache(self):
        """
        [Function intent]
        Clears the content cache.
        
        [Implementation details]
        Resets the internal cache dictionary.
        
        [Design principles]
        Simple resource management for memory efficiency.
        """
        self._content_cache.clear()
        self.logger.debug("File content cache cleared")
        
    def file_exists(self, file_path: str) -> bool:
        """
        [Function intent]
        Checks if a file exists.
        
        [Implementation details]
        Uses os.path.isfile for checking.
        
        [Design principles]
        Simple utility method for consistent file existence checking.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if the file exists, False otherwise
        """
        return os.path.isfile(file_path)
