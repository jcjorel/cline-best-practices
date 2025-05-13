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
# This file provides utility functions for the HSTC implementation using the Agno
# framework. It includes functionality for AWS client configuration, file operations,
# and comment parsing utilities needed by the HSTC feature components.
###############################################################################
# [Source file design principles]
# - Separation of concerns between AWS configuration and file processing
# - Clean abstractions for file and code parsing
# - Consistent error handling
# - Type annotations for improved code quality
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with both local and cloud environments
# - Should avoid dependencies outside of boto3, agno, and standard library
# - File operations should be path-agnostic (work with both string and Path objects)
###############################################################################
# [Dependencies]
# system:boto3
# system:os
# system:typing
# system:pathlib
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:06:00Z : Initial implementation by CodeAssistant
# * Created utility for Bedrock client initialization
# * Added AWS credential handling
###############################################################################

import os
import boto3
from typing import Dict, List, Optional, Any, Tuple, Union
from pathlib import Path
from datetime import datetime


def get_bedrock_client(region: Optional[str] = None) -> boto3.Session:
    """
    [Function intent]
    Get a Bedrock client session with proper configuration.
    
    [Design principles]
    Uses environment variables for credential configuration with fallbacks to defaults.
    Centralizes AWS client creation for consistent configuration.
    
    [Implementation details]
    Reads AWS region from function parameter or environment variable with default fallback.
    Creates a boto3 session configured with the specified region.
    
    Args:
        region: AWS region (optional, defaults to environment variable or 'us-west-2')
        
    Returns:
        boto3.Session: Configured Bedrock session
    """
    region = region or os.environ.get('AWS_REGION', 'us-west-2')
    
    # Create a Boto3 session with the specified region
    session = boto3.Session(region_name=region)
    
    return session


# Timestamp Utility

def get_current_timestamp() -> str:
    """
    [Function intent]
    Get current timestamp in the format required for HSTC history.
    
    [Design principles]
    Provides standardized timestamp format for consistent documentation.
    Centralizes timestamp generation to ensure format consistency.
    
    [Implementation details]
    Uses ISO 8601 format with Zulu timezone indicator.
    Format: YYYY-MM-DDThh:mm:ssZ
    
    Returns:
        str: Formatted timestamp string (YYYY-MM-DDThh:mm:ssZ)
    """
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")


# Dependency Parsing Utilities

def parse_dependency_string(dep_str: str) -> Dict[str, str]:
    """
    [Function intent]
    Parse a dependency string into its components.
    
    [Design principles]
    Extracts structured information from dependency notation.
    Follows HSTC dependency string format conventions.
    
    [Implementation details]
    Handles dependency strings in the format "<kind>:<dependency>".
    Falls back to "unknown" kind if format is not followed.
    
    Args:
        dep_str: Dependency string in the format "<kind>:<dependency>"
        
    Returns:
        Dict containing parsed dependency information with "kind" and "dependency" keys
    """
    if ":" in dep_str:
        parts = dep_str.split(":", 1)
        if len(parts) == 2:
            kind = parts[0].strip().strip("<>")
            path = parts[1].strip()
            return {
                "kind": kind,
                "dependency": path
            }
    # Default to unknown kind
    return {
        "kind": "unknown",
        "dependency": dep_str.strip()
    }


def format_dependency_string(dep: Dict[str, str]) -> str:
    """
    [Function intent]
    Format a dependency dict into a string.
    
    [Design principles]
    Provides consistent representation of dependency information.
    Inverse operation to parse_dependency_string for round-trip conversions.
    
    [Implementation details]
    Creates a dependency string in the format "<kind>:<dependency>".
    Uses default values if required keys are missing.
    
    Args:
        dep: Dependency dict with "kind" and "dependency" keys
        
    Returns:
        Formatted dependency string in the format "<kind>:<dependency>"
    """
    kind = dep.get("kind", "unknown")
    dependency = dep.get("dependency", "")
    return f"<{kind}>:{dependency}"


# Comment Extraction Utilities

def extract_comment_blocks(file_content: str, comment_formats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    [Function intent]
    Extract comment blocks from file content.
    
    [Design principles]
    Uses language-specific comment formats for accurate extraction.
    Preserves comment position information for source mapping.
    
    [Implementation details]
    Supports both block and inline comment formats.
    Tracks position information for each extracted comment.
    Avoids false positives by checking for comment markers in string literals.
    
    Args:
        file_content: Content of the file
        comment_formats: Comment format information
        
    Returns:
        List of extracted comment blocks with position information
    """
    result = []
    
    # Different extraction strategies based on comment formats
    if comment_formats.get("block_comment_start") and comment_formats.get("block_comment_end"):
        block_start = comment_formats.get("block_comment_start")
        block_end = comment_formats.get("block_comment_end")
        
        # Find all block comments
        start_pos = 0
        while True:
            start_pos = file_content.find(block_start, start_pos)
            if start_pos == -1:
                break
                
            end_pos = file_content.find(block_end, start_pos + len(block_start))
            if end_pos == -1:
                break
                
            comment_block = file_content[start_pos:end_pos + len(block_end)]
            result.append({
                "type": "block",
                "content": comment_block,
                "start_pos": start_pos,
                "end_pos": end_pos + len(block_end)
            })
            
            start_pos = end_pos + len(block_end)
    
    # Extract inline comments if applicable
    if comment_formats.get("inline_comment"):
        inline_marker = comment_formats.get("inline_comment")
        lines = file_content.split("\n")
        pos = 0
        
        for i, line in enumerate(lines):
            if inline_marker in line:
                comment_start = line.find(inline_marker)
                if comment_start >= 0:
                    # Make sure it's not inside a string
                    if not _is_in_string(line, comment_start):
                        comment = line[comment_start:]
                        result.append({
                            "type": "inline",
                            "content": comment,
                            "start_pos": pos + comment_start,
                            "end_pos": pos + len(line),
                            "line_number": i + 1
                        })
            pos += len(line) + 1  # +1 for newline
    
    return result


def _is_in_string(line: str, pos: int) -> bool:
    """
    [Function intent]
    Helper to check if a position is inside a string literal.
    
    [Design principles]
    Supports accurate comment detection by avoiding false positives.
    Provides simple but effective string detection heuristic.
    
    [Implementation details]
    Checks for balanced quote characters before the position.
    Works with both single and double quotes.
    
    Args:
        line: Line of code
        pos: Position to check
        
    Returns:
        bool: True if position is inside a string, False otherwise
    """
    # A simplified check - in a real implementation, this would be more robust
    quote_chars = ['"', "'"]
    for quote_char in quote_chars:
        # Count quotes before this position
        quotes_before = line[:pos].count(quote_char)
        # If odd number of quotes, we're in a string
        if quotes_before % 2 == 1:
            return True
    return False


# LLM Prompt Logging Utility

def log_prompt_to_file(model_id: str, agent_name: str, prompt: str, response: str) -> str:
    """
    [Function intent]
    Log LLM prompt and response to a debug file for visibility and tracking.
    
    [Design principles]
    Provides a persistent record of LLM interactions for debugging.
    Creates human-readable output with clear prompt/response separation.
    
    [Implementation details]
    Creates a log directory if it doesn't exist.
    Appends to a log file with timestamps, model information, and conversation.
    Each entry is clearly delimited for easy parsing.
    Returns the path to the created log file for reference.
    
    Args:
        model_id: ID of the model used
        agent_name: Name of the agent using the model
        prompt: The prompt sent to the model
        response: The response received from the model
        
    Returns:
        str: Path to the log file that was written
    """
    # Create log directory if it doesn't exist
    log_dir = Path.cwd() / "scratchpad" / "hstc_agno_logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Create log filename based on date
    date_str = datetime.utcnow().strftime("%Y%m%d")
    log_file = log_dir / f"agno_prompts_{date_str}.log"
    
    # Format the log entry
    timestamp = get_current_timestamp()
    log_entry = f"""
==========================================================================
TIMESTAMP: {timestamp}
AGENT: {agent_name}
MODEL: {model_id}
==========================================================================
PROMPT:
--------------------------------------------------------------------------
{prompt}
--------------------------------------------------------------------------
RESPONSE:
--------------------------------------------------------------------------
{response}
==========================================================================

"""
    
    # Append to log file
    with open(log_file, "a") as f:
        f.write(log_entry)
        
    # Return the log file path for reference
    return str(log_file)


# File Path Utilities

def resolve_relative_path(base_path: str, relative_path: str) -> str:
    """
    [Function intent]
    Resolve a relative path relative to a base path.
    
    [Design principles]
    Handles path resolution consistently across platforms.
    Supports dependency resolution with relative paths.
    
    [Implementation details]
    Converts relative paths to absolute paths based on a reference path.
    Preserves absolute paths without modification.
    Normalizes path separators for platform compatibility.
    
    Args:
        base_path: Base path (usually the current file)
        relative_path: Path relative to the base path
        
    Returns:
        str: Resolved absolute path
    """
    if os.path.isabs(relative_path):
        return relative_path
        
    base_dir = os.path.dirname(os.path.abspath(base_path))
    return os.path.normpath(os.path.join(base_dir, relative_path))


def is_binary_file(content: bytes) -> bool:
    """
    [Function intent]
    Check if file content appears to be binary.
    
    [Design principles]
    Provides reliable binary file detection without external dependencies.
    Prevents processing of non-text files that would cause errors.
    
    [Implementation details]
    Uses two detection methods:
    1. Checks for null bytes in the file header, common in binary files
    2. Attempts UTF-8 decoding as a fallback test
    
    Args:
        content: File content as bytes
        
    Returns:
        bool: True if file appears to be binary, False otherwise
    """
    # Check for null bytes, which usually indicate binary content
    if b'\x00' in content[:1024]:
        return True
    
    # Try to decode as text
    try:
        content.decode('utf-8')
        return False
    except UnicodeDecodeError:
        return True


# Implementation Plan Utilities

def append_to_implementation_plan(plan_dir: Path, filename: str, content: str) -> None:
    """
    [Function intent]
    Append content to an implementation plan file.
    
    [Design principles]
    Supports iterative implementation plan generation.
    Ensures file exists before appending content.
    
    [Implementation details]
    Creates directories if they don't exist.
    Opens file in append mode to preserve existing content.
    
    Args:
        plan_dir: Directory containing implementation plan files
        filename: Name of the file to append to
        content: Content to append
    """
    file_path = plan_dir / filename
    
    # Create directory if it doesn't exist
    plan_dir.mkdir(parents=True, exist_ok=True)
    
    # Append to file
    with file_path.open("a") as f:
        f.write(content)


def generate_implementation_progress_markdown(definitions: List[Dict[str, Any]]) -> str:
    """
    [Function intent]
    Generate markdown for tracking implementation progress.
    
    [Design principles]
    Provides standardized progress tracking format.
    Supports visualization of implementation status.
    
    [Implementation details]
    Creates a markdown document with status indicators.
    Includes all definitions with their initial status.
    
    Args:
        definitions: List of function/class definitions
        
    Returns:
        str: Markdown content for progress tracking
    """
    md = """# HSTC Implementation Progress

## Status Legend

- ❌ Not started
- 🔄 In progress
- ✅ Completed

## Tasks

- ❌ Update file header
- ❌ Update function/class documentation
"""
    
    # Add each definition
    for definition in definitions:
        name = definition.get("name", "unknown")
        def_type = definition.get("type", "function")
        md += f"  - ❌ {name} ({def_type})\n"
    
    md += "- ❌ Final validation\n"
    return md


# File IO Utilities

def read_file_content(file_path: str) -> Tuple[str, bool]:
    """
    [Function intent]
    Read file content, handling binary vs text detection.
    
    [Design principles]
    Provides safe file reading with appropriate error handling.
    Automatically handles binary vs text file detection.
    
    [Implementation details]
    First reads file as binary to detect content type.
    Returns decoded content as text if the file is not binary.
    Handles errors gracefully with clear error messages.
    
    Args:
        file_path: Path to the file
        
    Returns:
        tuple: (file_content, is_binary) with empty content for binary files
    """
    try:
        # First try to read as binary to check if it's a binary file
        with open(file_path, 'rb') as f:
            content_bytes = f.read()
            
        binary = is_binary_file(content_bytes)
        
        if binary:
            return "", True
        
        # If not binary, return as text
        return content_bytes.decode('utf-8'), False
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return "", True


# Testing Utilities

def verify_models_and_utils(verbose: bool = False) -> bool:
    """
    [Function intent]
    Verify that models and utilities are functioning correctly.
    
    [Design principles]
    Provides sanity check for basic functionality.
    Supports debugging with verbose output option.
    
    [Implementation details]
    Tests key utility functions with simple test cases.
    Reports success/failure with detailed messages in verbose mode.
    
    Args:
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if all checks pass, False otherwise
    """
    try:
        # Test timestamp generation
        timestamp = get_current_timestamp()
        if verbose:
            print(f"Generated timestamp: {timestamp}")
        
        # Test dependency string parsing
        dep_str = "<codebase>:path/to/file.py"
        dep_dict = parse_dependency_string(dep_str)
        if dep_dict["kind"] != "codebase" or dep_dict["dependency"] != "path/to/file.py":
            if verbose:
                print(f"Error parsing dependency string: {dep_str} -> {dep_dict}")
            return False
        
        # Test prompt logging
        try:
            log_prompt_to_file("test-model", "TestAgent", "Test prompt", "Test response")
            if verbose:
                print("Prompt logging test passed")
        except Exception as e:
            if verbose:
                print(f"Error testing prompt logging: {e}")
            return False
        
        if verbose:
            print("All model and utility checks passed")
        
        return True
    except Exception as e:
        if verbose:
            print(f"Error during verification: {e}")
        return False
