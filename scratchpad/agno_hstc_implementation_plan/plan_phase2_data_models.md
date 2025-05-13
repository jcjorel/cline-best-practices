# HSTC Implementation with Agno - Phase 2: Data Models and Utilities

This document outlines the detailed steps to implement the core data models and utility functions for the HSTC implementation using the Agno framework.

## Overview

In this phase, we'll implement:

1. Data models that represent the structure of the information we'll be working with
2. Utility functions for processing files, comments, and dependencies
3. Helper functions for common operations across the codebase

These components will serve as the foundation for the agent implementations in later phases.

## Step 1: Implement Basic Data Models

Create the data classes that represent the core data structures needed for HSTC processing:

```python
# src/dbp_cli/commands/hstc_agno/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any


@dataclass
class CommentFormat:
    """Comment format information for a programming language"""
    inline_comment: Optional[str] = None
    block_comment_start: Optional[str] = None
    block_comment_end: Optional[str] = None
    docstring_format: Optional[str] = None
    docstring_start: Optional[str] = None
    docstring_end: Optional[str] = None
    has_documentation_comments: bool = False


@dataclass
class Dependency:
    """Dependency information"""
    name: str
    kind: str  # One of "codebase", "system", "external"
    path_or_package: str
    function_names: List[str] = field(default_factory=list)


@dataclass
class Definition:
    """Function, method or class definition"""
    name: str
    type: str  # One of "function", "method", "class"
    line_number: int
    comments: str = ""
    updated_comment: str = ""


@dataclass
class FileMetadata:
    """Metadata about a source file"""
    path: str
    size: int
    last_modified: float
    file_type: str
    is_binary: bool = False
    language: str = ""
    confidence: int = 0
    file_extension: str = ""
    comment_formats: Optional[CommentFormat] = None
    header_comment: str = ""
    dependencies: List[Dependency] = field(default_factory=list)
    definitions: List[Definition] = field(default_factory=list)


@dataclass
class HeaderDocumentation:
    """Documentation for a file header"""
    intent: str
    design_principles: str
    constraints: str
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    change_history: List[str] = field(default_factory=list)
    raw_header: str = ""


@dataclass
class DefinitionDocumentation:
    """Documentation for a function, method or class"""
    name: str
    type: str
    original_comment: str
    updated_comment: str


@dataclass
class Documentation:
    """Complete documentation for a file"""
    path: str
    file_type: str
    language: str = ""
    file_header: Optional[HeaderDocumentation] = None
    definitions: List[DefinitionDocumentation] = field(default_factory=list)
    documentation_updated: bool = False
    analysis: str = ""
    reason: str = ""


@dataclass
class ValidationResult:
    """Result of documentation validation"""
    valid: bool
    issues: List[str] = field(default_factory=list)
    file_path: str = ""
    reason: str = ""
```

## Step 2: Implement Timestamp Utility

Add a utility function to generate timestamps in the required format for HSTC documentation:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

from datetime import datetime

def get_current_timestamp() -> str:
    """
    Get current timestamp in the format required for HSTC history
    
    Returns:
        str: Formatted timestamp string (YYYY-MM-DDThh:mm:ssZ)
    """
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")
```

## Step 3: Implement Dependency String Parsing

Add utilities for parsing and formatting dependency strings:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

from typing import Dict, Any, List, Optional

def parse_dependency_string(dep_str: str) -> Dict[str, str]:
    """
    Parse a dependency string into its components
    
    Args:
        dep_str: Dependency string in the format "<kind>:<dependency>"
        
    Returns:
        Dict containing parsed dependency information
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
    Format a dependency dict into a string
    
    Args:
        dep: Dependency dict with "kind" and "dependency" keys
        
    Returns:
        Formatted dependency string
    """
    kind = dep.get("kind", "unknown")
    dependency = dep.get("dependency", "")
    return f"<{kind}>:{dependency}"
```

## Step 4: Implement Comment Extraction Utilities

Add utilities for extracting comments from file content:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

def extract_comment_blocks(file_content: str, comment_formats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract comment blocks from file content
    
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
    Helper to check if a position is inside a string literal
    
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
```

## Step 5: Implement Language Detection Utilities

Add utilities to help with language detection:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

def get_language_by_extension(file_path: str) -> str:
    """
    Get programming language by file extension
    
    Args:
        file_path: Path to the file
        
    Returns:
        str: Detected programming language or "unknown"
    """
    extension_map = {
        '.py': 'python',
        '.js': 'javascript',
        '.ts': 'typescript',
        '.jsx': 'javascript',
        '.tsx': 'typescript',
        '.java': 'java',
        '.c': 'c',
        '.cpp': 'c++',
        '.h': 'c',
        '.hpp': 'c++',
        '.cs': 'csharp',
        '.go': 'go',
        '.rb': 'ruby',
        '.php': 'php',
        '.swift': 'swift',
        '.kt': 'kotlin',
        '.rs': 'rust',
        '.sh': 'shell',
        '.bash': 'shell',
        '.md': 'markdown',
        '.html': 'html',
        '.css': 'css',
        '.xml': 'xml',
        '.json': 'json',
        '.yml': 'yaml',
        '.yaml': 'yaml',
    }
    
    import os
    _, ext = os.path.splitext(file_path.lower())
    return extension_map.get(ext, "unknown")


def get_default_comment_format(language: str) -> Dict[str, Any]:
    """
    Get default comment format for a programming language
    
    Args:
        language: Programming language name
        
    Returns:
        Dict containing default comment format information
    """
    formats = {
        'python': {
            'inline_comment': '#',
            'block_comment_start': '"""',
            'block_comment_end': '"""',
            'docstring_format': 'triple quotes',
            'docstring_start': '"""',
            'docstring_end': '"""',
            'has_documentation_comments': True
        },
        'javascript': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'JSDoc',
            'docstring_start': '/**',
            'docstring_end': '*/',
            'has_documentation_comments': True
        },
        'typescript': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'JSDoc',
            'docstring_start': '/**',
            'docstring_end': '*/',
            'has_documentation_comments': True
        },
        'java': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'JavaDoc',
            'docstring_start': '/**',
            'docstring_end': '*/',
            'has_documentation_comments': True
        },
        'c': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'block comment',
            'docstring_start': '/**',
            'docstring_end': '*/',
            'has_documentation_comments': True
        },
        'c++': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'block comment',
            'docstring_start': '/**',
            'docstring_end': '*/',
            'has_documentation_comments': True
        },
        'csharp': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'XML comments',
            'docstring_start': '///',
            'docstring_end': None,
            'has_documentation_comments': True
        },
        'ruby': {
            'inline_comment': '#',
            'block_comment_start': '=begin',
            'block_comment_end': '=end',
            'docstring_format': 'RDoc',
            'docstring_start': '#',
            'docstring_end': None,
            'has_documentation_comments': True
        },
        'go': {
            'inline_comment': '//',
            'block_comment_start': '/*',
            'block_comment_end': '*/',
            'docstring_format': 'GoDoc',
            'docstring_start': '//',
            'docstring_end': None,
            'has_documentation_comments': True
        },
    }
    
    return formats.get(language.lower(), {
        'inline_comment': None,
        'block_comment_start': None,
        'block_comment_end': None,
        'docstring_format': None,
        'docstring_start': None,
        'docstring_end': None,
        'has_documentation_comments': False
    })
```

## Step 6: Implement File Path Utilities

Add utilities for handling file paths and file content:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

import os
from pathlib import Path

def resolve_relative_path(base_path: str, relative_path: str) -> str:
    """
    Resolve a relative path relative to a base path
    
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
    Check if file content appears to be binary
    
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
```

## Step 7: Implement Implementation Plan Utilities

Add utilities for generating implementation plans:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

def append_to_implementation_plan(plan_dir: Path, filename: str, content: str) -> None:
    """
    Append content to an implementation plan file
    
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
    Generate markdown for tracking implementation progress
    
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
```

## Step 8: Update Model Imports

Ensure the model classes are properly imported in the agent implementation files:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (update imports)

from .models import (
    CommentFormat,
    Dependency,
    Definition,
    FileMetadata,
    HeaderDocumentation,
    DefinitionDocumentation,
    Documentation,
    ValidationResult
)
```

## Step 9: Integration with File IO

Add utilities for file IO operations:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

def read_file_content(file_path: str) -> tuple[str, bool]:
    """
    Read file content, handling binary vs text detection
    
    Args:
        file_path: Path to the file
        
    Returns:
        tuple: (file_content, is_binary)
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
```

## Step 10: Testing Utilities

Create a simple function to verify that the models and utilities are functioning correctly:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (add to existing file)

def verify_models_and_utils(verbose: bool = False) -> bool:
    """
    Verify that models and utilities are functioning correctly
    
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
        
        # Test language detection
        lang = get_language_by_extension("test.py")
        if lang != "python":
            if verbose:
                print(f"Error detecting language for test.py: {lang}")
            return False
        
        # Test comment format retrieval
        comment_format = get_default_comment_format("python")
        if comment_format["inline_comment"] != "#":
            if verbose:
                print(f"Error getting comment format for python: {comment_format}")
            return False
        
        # Test data classes
        file_meta = FileMetadata(
            path="test.py",
            size=100,
            last_modified=1620000000.0,
            file_type="source_code",
            language="python"
        )
        if file_meta.path != "test.py" or file_meta.language != "python":
            if verbose:
                print(f"Error creating FileMetadata: {file_meta}")
            return False
        
        if verbose:
            print("All model and utility checks passed")
        
        return True
    except Exception as e:
        if verbose:
            print(f"Error during verification: {e}")
        return False
```

## Expected Output

After completing this phase, you should have:

1. A complete set of data model classes that represent the HSTC data structures
2. Utility functions for common operations like timestamp generation and comment extraction
3. Helper functions for language detection and file type identification
4. Integration points for later phases of the implementation

## Next Steps

After completing this phase, proceed to Phase 3 (File Analyzer Agent) to implement the Nova Micro-based agent for analyzing source code files.
