# HSTC Implementation Details with Agno - Part 2C: Utilities and Integration

## Key Classes and Interfaces (continued)

### 5. Utility Functions Implementation

```python
# src/dbp_cli/commands/hstc_agno/utils.py

import os
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

def get_current_timestamp() -> str:
    """Get current timestamp in the format required for HSTC history"""
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

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

def extract_comment_blocks(file_content: str, comment_formats: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extract comment blocks from file content
    
    Args:
        file_content: Content of the file
        comment_formats: Comment format information
        
    Returns:
        List of extracted comment blocks with position information
    """
    # This is a simplified implementation that would be expanded in a real implementation
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
    """Helper to check if position is inside a string"""
    # A simplified check - in a real implementation, this would be more robust
    quote_chars = ['"', "'"]
    for quote_char in quote_chars:
        # Count quotes before this position
        quotes_before = line[:pos].count(quote_char)
        # If odd number of quotes, we're in a string
        if quotes_before % 2 == 1:
            return True
    return False

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
```

### 6. CLI Integration

To integrate the HSTC feature into the existing CLI framework, we need to add our command group to the CLI:

```python
# src/dbp_cli/commands/__init__.py (modified part)

from .hstc_agno.cli import hstc_agno  # Import our new command group

def register_commands(cli_group):
    """Register all CLI commands with the main cli_group"""
    # Register existing command groups...
    
    # Register our new HSTC Agno command group
    cli_group.add_command(hstc_agno)
```

## Data Models and Structures

For better organization and type safety, we can define dedicated data models for the HSTC components:

```python
# src/dbp_cli/commands/hstc_agno/models.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, List, Optional

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
    kind: str
    path_or_package: str
    function_names: List[str] = field(default_factory=list)

@dataclass
class Definition:
    """Function, method or class definition"""
    name: str
    type: str
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

## Performance Considerations

When implementing the HSTC feature with Agno, several performance factors should be considered:

1. **Token Usage Optimization**:
   - For Nova Micro, limit file content to necessary portions (first 1000-5000 chars)
   - Use structured output formats (JSON) to minimize LLM parsing errors
   - Break large files into smaller chunks for analysis

2. **Parallel Processing**:
   - Implement concurrent processing for multiple files
   - Process dependencies in parallel when applicable
   - Use async/await pattern for I/O-bound operations

3. **Caching Strategy**:
   - Cache file analysis results to avoid reprocessing
   - Implement checksums for detecting file changes
   - Cache dependencies to avoid circular dependency issues
   - Use session state to persist data between calls

4. **Model Selection**:
   - Use Nova Micro for quick classification tasks
   - Reserve Claude 3.7 for complex reasoning tasks
   - Dynamically select models based on task complexity

## Error Handling Strategy

Implement a robust error handling strategy that accounts for:

1. **File Access Errors**:
   - File not found
   - Permission issues
   - Encoding problems

2. **LLM Response Errors**:
   - JSON parsing failures
   - Rate limits
   - Token limits
   - Connection issues

3. **Dependency Analysis Errors**:
   - Circular dependencies
   - Missing dependencies
   - Invalid imports

4. **Recovery Mechanisms**:
   - Partial results handling
   - Graceful degradation
   - Automatic retries with exponential backoff
   - Detailed error reporting in implementation plans

## Example Command Usage

The implemented HSTC feature can be used from the command line as follows:

```bash
# Basic usage - process a single file
python -m dbp_cli hstc_agno update path/to/file.py

# Specify output directory
python -m dbp_cli hstc_agno update path/to/file.py --output path/to/output

# Process dependencies recursively
python -m dbp_cli hstc_agno update path/to/file.py --recursive
```

## Integration with Existing HSTC Implementation

This Agno-based implementation is designed to work alongside the existing LangChain-based implementation. Key differences include:

1. **Different Command Group**: Uses `hstc_agno` instead of `hstc`
2. **Focused Scope**: Processes a single file at a time instead of directories
3. **Model Selection**: Uses Nova Micro and Claude 3.7 specifically
4. **In-Memory Data Store**: Uses Agno's session state for data persistence

The two implementations can coexist, allowing for gradual migration as needed.
