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
# 2025-05-07T11:46:30Z : Initial implementation of HSTC exceptions by CodeAssistant
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


class FileAccessError(HSTCError):
    """
    [Class intent]
    Raised when there's an error accessing a file, such as permission issues,
    or file not found.
    
    [Design principles]
    Clear identification of file access errors.
    Includes file path for contextual error information.
    
    [Implementation details]
    Extends HSTCError with specific file access error details.
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
            file_path: Path to the file that caused the error
        """
        self.file_path = file_path
        if file_path:
            full_message = f"{message} (file: {file_path})"
        else:
            full_message = message
        super().__init__(full_message)
