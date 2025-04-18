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
# Provides logging utility functions and custom formatters used across different 
# components in the DBP system. Ensures consistent logging format and behavior
# throughout the application.
###############################################################################
# [Source file design principles]
# - Single Responsibility: Focused only on logging-related utilities
# - Consistent Formatting: Provides standard formatters for unified log appearance
# - Reusability: Utilities can be imported by any component requiring logging
# - Design Decision: Centralized Logging Formatters (2025-04-17)
#   * Rationale: Ensures consistent log formatting across all components
#   * Alternatives considered: Per-component formatters (rejected due to inconsistency)
###############################################################################
# [Source file constraints]
# - Must not depend on other DBP components to avoid circular dependencies
# - Must maintain compatibility with Python's standard logging module
# - Should handle different log format requirements flexibly
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T13:54:00Z : Fixed log level name truncation by CodeAssistant
# * Added width specifier to level name format to prevent truncation 
# * Changed '%(levelname)s' to '%(levelname)-8s' to ensure complete level names display
# * Updated formatter in both setup_application_logging and configure_logger for consistency
# 2025-04-17T17:35:32Z : Enhanced root logger configuration for consistent format by CodeAssistant
# * Added explicit root logger configuration with basicConfig
# * Added handler cleanup to prevent inconsistent formats
# * Ensured standardized logging format: 2025-04-17 17:24:30,221 - dbp.core.lifecycle - <LOGLEVEL> - <message>
# 2025-04-17T17:18:15Z : Added centralized setup_application_logging function by CodeAssistant
# * Implemented single function to configure application-wide logging
# * Added support for both console and file logging with rotation
# * Ensured consistent log formatting across all system components
# 2025-04-17T17:09:30Z : Enhanced MillisecondFormatter to remove duplicate level prefixes by CodeAssistant
# * Added format method override to strip redundant "Error:" prefixes from messages
# * Added support for all log levels and case variants in prefix detection
###############################################################################

import logging
import time
import sys
import os
from logging.handlers import RotatingFileHandler
from typing import Optional, List
from pathlib import Path

class MillisecondFormatter(logging.Formatter):
    """
    [Class intent]
    Custom formatter that shows milliseconds (3 digits) instead of microseconds (6 digits)
    and removes duplicate level prefixes from log messages.
    Used to ensure consistent timestamp display across all application logs.
    
    [Implementation details]
    Overrides the formatTime method to format datetime with exactly 3 digits for milliseconds.
    Replaces the '%f' in the date format with exactly 3 digits for milliseconds.
    Also overrides format method to prevent duplication of log level in messages.
    
    [Design principles]
    Maintains consistent logging format while providing precise millisecond timestamps.
    Ensures compatibility with standard logging module formatting.
    Eliminates duplicated log level information for cleaner output.
    """
    def formatTime(self, record, datefmt=None):
        ct = self.converter(record.created)
        if datefmt:
            # Format with standard time formatting
            s = time.strftime(datefmt, ct)
            # Replace the microseconds (%f would be 6 digits) with just 3 digits
            msecs = int(record.msecs)
            s = s.replace('%f', f'{msecs:03d}')
            return s
        else:
            return super().formatTime(record, datefmt)
            
    def format(self, record):
        # First call the parent format method to get the formatted log message
        formatted_message = super().format(record)
        
        # Check if the message starts with a level prefix like "Error: " or "Warning: "
        level_prefixes = {
            logging.ERROR: "Error: ",
            logging.WARNING: "Warning: ",
            logging.CRITICAL: "Critical: ",
            logging.INFO: "Info: ",
            logging.DEBUG: "Debug: "
        }
        
        # If the message starts with the level prefix that matches the record's level,
        # remove the prefix to avoid duplication
        prefix = level_prefixes.get(record.levelno, "")
        if prefix and formatted_message.startswith(prefix):
            formatted_message = formatted_message[len(prefix):]
            
        # Also check for uppercase variants
        prefix_upper = prefix.upper()
        if prefix_upper and formatted_message.startswith(prefix_upper):
            formatted_message = formatted_message[len(prefix_upper):]
            
        return formatted_message

def configure_logger(logger: logging.Logger, level: Optional[int] = None, 
                    add_formatter: bool = True) -> logging.Logger:
    """
    [Function intent]
    Configures a logger with the standard millisecond formatter and optional level.
    
    [Implementation details]
    Sets the log level if provided and attaches the MillisecondFormatter to all handlers
    that don't already have a formatter.
    
    [Design principles]
    Provides a simple way to ensure consistent log formatting across components.
    Respects existing formatter configurations if already present.
    
    Args:
        logger: The logger instance to configure
        level: Optional logging level to set
        add_formatter: Whether to add the millisecond formatter to handlers without formatters
        
    Returns:
        The configured logger instance
    """
    # Set level if provided
    if level is not None:
        logger.setLevel(level)
    
    # Add formatter to handlers that don't have one
    if add_formatter:
        for handler in logger.handlers:
            if isinstance(handler, logging.StreamHandler) and not handler.formatter:
                formatter = MillisecondFormatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S,%f'
                )
                handler.setFormatter(formatter)
    
    return logger

def get_formatted_logger(name: str, level: Optional[int] = None) -> logging.Logger:
    """
    [Function intent]
    Gets a logger with the standard millisecond formatter applied.
    
    [Implementation details]
    Creates a logger with the given name and configures it with the MillisecondFormatter.
    
    [Design principles]
    Convenience function to get properly configured loggers with one call.
    Ensures consistent formatting without repeating setup code.
    
    Args:
        name: The name for the logger
        level: Optional logging level to set
        
    Returns:
        A configured logger instance with millisecond formatting
    """
    logger = logging.getLogger(name)
    return configure_logger(logger, level)

def setup_application_logging(log_level: str = "INFO", log_file: Optional[Path] = None) -> None:
    """
    [Function intent]
    Sets up consistent application-wide logging configuration.
    This function should be called once at application startup to ensure
    homogeneous logging across all components.
    
    [Implementation details]
    Configures the root logger with our custom MillisecondFormatter.
    Handles console output and optional file logging with rotation.
    Ensures that all logging, including from the 'root' logger, uses the standardized format.
    
    [Design principles]
    Provides a single point of configuration for all application logging.
    Ensures consistent formatting and behavior across all components.
    
    Args:
        log_level: Logging level as string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional path to log file for persistent logging
    """
    # Reset any existing logging configuration to avoid format inconsistencies
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)
    
    # Convert string level to numeric level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Standard format and date format - use the officially approved format:
    # 2025-04-17 17:24:30,221 - dbp.core.lifecycle - <LOGLEVEL> - <message>
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    datefmt = '%Y-%m-%d %H:%M:%S,%f'
    
    # Make sure basicConfig is called to configure the root logger early
    # This prevents any default-formatted logs from appearing
    logging.basicConfig(
        format=log_format,
        datefmt=datefmt,
        level=numeric_level,
        handlers=[]  # We'll add handlers explicitly below
    )
    
    # Create handlers list (always include console handler)
    handlers: List[logging.Handler] = [logging.StreamHandler(sys.stderr)]
    
    # Add file handler if log_file is specified
    if log_file:
        # Ensure directory exists
        log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Create a rotating file handler
        file_handler = RotatingFileHandler(
            log_file, 
            mode='a',
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        handlers.append(file_handler)
    
    # Create the formatter once
    formatter = MillisecondFormatter(fmt=log_format, datefmt=datefmt)
    
    # Configure root logger - remove existing handlers first to avoid duplicates
    root_logger = logging.getLogger()
    
    # Remove any existing handlers
    for hdlr in root_logger.handlers[:]:
        root_logger.removeHandler(hdlr)
    
    # Set level and add handlers with formatter
    root_logger.setLevel(numeric_level)
    for handler in handlers:
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
    
    # Log successful setup
    logging.debug(f"Application logging initialized at level {log_level} with consistent formatting")
