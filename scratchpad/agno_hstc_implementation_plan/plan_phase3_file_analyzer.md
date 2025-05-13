# HSTC Implementation with Agno - Phase 3: File Analyzer Agent

This document outlines the detailed steps to implement the File Analyzer Agent for the HSTC implementation using the Agno framework and Amazon Bedrock's Nova Micro model.

## Overview

The File Analyzer Agent is responsible for:

1. Analyzing source files to determine their type
2. Detecting the programming language used
3. Identifying comment formats for the language
4. Extracting header comments and function/class documentation
5. Identifying dependencies on other files or packages

This agent uses the Nova Micro model for efficient analysis of code files.

## Prerequisites

Ensure that Phases 1 and 2 are completed:
- The basic project structure is in place
- Data models and utility functions are implemented

## Step 1: Extend the File Analyzer Agent Class

Expand the skeleton agent class created in Phase 1:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (File Analyzer part)

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from agno.agent import Agent
from agno.models import BedrockNovaModel
from agno.tools import FileTools

from .models import (
    CommentFormat,
    Dependency,
    Definition,
    FileMetadata
)
from .utils import (
    get_current_timestamp,
    get_language_by_extension,
    get_default_comment_format,
    is_binary_file,
    read_file_content
)

class FileAnalyzerAgent(Agent):
    """Agent for analyzing source files using Nova Micro."""
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        base_dir: Optional[Path] = None,
        **kwargs
    ):
        # Initialize Nova model for file analysis
        model = BedrockNovaModel(id=model_id)
        super().__init__(model=model, **kwargs)
        
        # Add file tools for reading source files
        base_dir = base_dir or Path.cwd()
        self.file_tools = FileTools(base_dir=base_dir)
        self.add_toolkit(self.file_tools)
        
        # Initialize state for storing analysis results
        self.file_metadata = {}
```

## Step 2: Implement File Analysis Entry Point

Add the main analysis method that coordinates the entire analysis process:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def analyze_file(self, file_path: str) -> Dict[str, Any]:
    """
    Perform comprehensive analysis of a source file
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dict containing all analysis results
    """
    # Get file metadata
    file_stat = os.stat(file_path)
    metadata = {
        "path": file_path,
        "size": file_stat.st_size,
        "last_modified": file_stat.st_mtime,
    }
    
    # Read file content for analysis
    file_content, is_binary = read_file_content(file_path)
    if is_binary:
        metadata["file_type"] = "binary"
        metadata["is_binary"] = True
        return metadata
    
    if not file_content:
        metadata["file_type"] = "empty"
        metadata["error"] = "Empty file"
        return metadata
    
    # Detect file type
    file_type_info = self.analyze_file_type(file_content)
    metadata.update(file_type_info)
    
    # For source code files, perform deeper analysis
    if file_type_info["file_type"] == "source_code":
        # Detect language
        language_info = self.detect_language(file_content, file_path)
        metadata.update(language_info)
        
        # Identify comment formats for this language
        comment_formats = self.identify_comment_formats(language_info["language"])
        metadata["comment_formats"] = comment_formats
        
        # Extract header comment
        header_comment = self.extract_header_comment(file_content, comment_formats)
        if header_comment:
            metadata["header_comment"] = header_comment
        
        # Extract dependencies
        dependency_info = self.extract_dependencies(file_content, language_info["language"])
        metadata["dependencies"] = dependency_info.get("dependencies", [])
        
        # Extract function comments
        function_info = self.extract_function_comments(file_content, language_info["language"], comment_formats)
        metadata["definitions"] = function_info.get("definitions", [])
    
    # Store results in agent state
    self.file_metadata[file_path] = metadata
    
    return metadata
```

## Step 3: Implement File Type Detection

Add a method to detect the file type:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def analyze_file_type(self, file_content: str) -> Dict[str, Any]:
    """
    Analyze content to determine file type
    
    Args:
        file_content: Content of the file to analyze
        
    Returns:
        Dict containing file type information
    """
    # Build prompt for file type detection
    prompt = f"""
    Examine the following file content and determine its type.
    Return a JSON structure with:
    - file_type: The general type of file (e.g., "source_code", "markdown", "data", "configuration")
    - is_binary: Whether the file appears to be binary (true/false)
    
    File content (first 1000 chars):
    ```
    {file_content[:1000]}
    ```
    
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"file_type": "unknown", "is_binary": False}
```

## Step 4: Implement Language Detection

Add a method to detect the programming language:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def detect_language(self, file_content: str, file_path: str) -> Dict[str, Any]:
    """
    Determine the programming language with confidence score
    
    Args:
        file_content: Content of the file to analyze
        file_path: Path to the file (for extension-based detection)
        
    Returns:
        Dict containing language information and confidence score
    """
    # Try extension-based detection first
    extension_language = get_language_by_extension(file_path)
    if extension_language != "unknown":
        return {
            "language": extension_language,
            "confidence": 90,  # High confidence for extension-based detection
            "file_extension": os.path.splitext(file_path)[1]
        }
    
    # If extension-based detection fails, use LLM to analyze content
    prompt = f"""
    Analyze this source code and determine:
    1. The primary programming language
    2. Your confidence level (0-100%)
    
    Source code (first 2000 chars):
    ```
    {file_content[:2000]}
    ```
    
    Return a JSON object with these fields:
    - language: The primary programming language
    - confidence: Your confidence as an integer percentage
    - file_extension: The typical file extension for this language
    
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"language": "unknown", "confidence": 0, "file_extension": ""}
```

## Step 5: Implement Comment Format Identification

Add a method to identify comment formats for the detected language:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def identify_comment_formats(self, language: str) -> Dict[str, Any]:
    """
    Identify comment formats for the detected language
    
    Args:
        language: The detected programming language
        
    Returns:
        Dict containing comment syntax information
    """
    # Try to get default comment format from utilities
    default_format = get_default_comment_format(language)
    if default_format["inline_comment"] is not None:
        # We have a known format for this language
        return default_format
    
    # If language is not in our defaults, use LLM to determine comment format
    prompt = f"""
    For the {language} programming language, provide a JSON object with these fields:
    - inline_comment: The syntax for inline comments (e.g., "//", "#")
    - block_comment_start: The syntax to start a block comment (e.g., "/*")
    - block_comment_end: The syntax to end a block comment (e.g., "*/")
    - docstring_format: The syntax for docstrings or documentation comments
    - docstring_start: The syntax to start a docstring
    - docstring_end: The syntax to end a docstring
    - has_documentation_comments: Whether the language has special documentation comments
    
    Include null for any syntax that doesn't apply to this language.
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {
            "inline_comment": None,
            "block_comment_start": None,
            "block_comment_end": None,
            "docstring_format": None,
            "docstring_start": None,
            "docstring_end": None,
            "has_documentation_comments": False
        }
```

## Step 6: Implement Header Comment Extraction

Add a method to extract header comment from file content:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def extract_header_comment(self, file_content: str, comment_formats: Dict[str, Any]) -> Optional[str]:
    """
    Extract header comment from file content
    
    Args:
        file_content: Content of the file
        comment_formats: Comment format information
        
    Returns:
        Header comment or None if not found
    """
    # First try simple extraction - check for block comment at start of file
    if comment_formats.get("block_comment_start") and comment_formats.get("block_comment_end"):
        block_start = comment_formats.get("block_comment_start")
        block_end = comment_formats.get("block_comment_end")
        
        # Check if file starts with a block comment
        if file_content.strip().startswith(block_start):
            end_pos = file_content.find(block_end, len(block_start))
            if end_pos != -1:
                return file_content[:end_pos + len(block_end)].strip()
    
    # If simple extraction fails, use LLM to extract header
    prompt = f"""
    Extract the header comment from this file. A header comment appears at the very beginning of the file before any code.
    
    File content (first 2000 chars):
    ```
    {file_content[:2000]}
    ```
    
    Comment formats for this file:
    {json.dumps(comment_formats, indent=2)}
    
    Return only the raw header comment text without any additional formatting or explanation.
    If no header comment is found, return an empty string.
    """
    
    response = self.query(prompt)
    return response.strip() if response.strip() else None
```

## Step 7: Implement Dependency Extraction

Add a method to extract dependencies from the source file:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def extract_dependencies(self, file_content: str, language: str) -> Dict[str, Any]:
    """
    Extract dependencies from the source file
    
    Args:
        file_content: Content of the file
        language: The detected programming language
        
    Returns:
        Dict containing dependency information
    """
    # Determine how much content to analyze based on file size
    content_to_analyze = file_content[:5000]  # First 5000 chars for dependency detection
    
    # Build prompt for dependency extraction
    prompt = f"""
    Analyze this {language} code and identify all external dependencies:
    1. Other source file imports or includes
    2. External libraries or packages
    3. System dependencies
    
    Source code:
    ```
    {content_to_analyze}
    ```
    
    For each dependency, identify:
    - name: The name of the dependency
    - kind: One of "codebase" (internal project file), "system" (system package), "external" (third-party library)
    - path_or_package: The import path or package name
    - function_names: Array of specific functions/classes/methods imported from this dependency
    
    Return a JSON object with a "dependencies" field containing an array of these dependencies.
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"dependencies": []}
```

## Step 8: Implement Function/Class Comment Extraction

Add a method to extract comments associated with functions and classes:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def extract_function_comments(self, file_content: str, language: str, comment_formats: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract comments associated with functions and classes
    
    Args:
        file_content: Content of the file
        language: The detected programming language
        comment_formats: Comment format information
        
    Returns:
        Dict containing function comment information
    """
    # Build prompt for function comment extraction
    docstring_info = ""
    if comment_formats.get("docstring_format"):
        docstring_info = f"Docstrings in this language are denoted by {comment_formats.get('docstring_format')}."
    
    # For large files, let's analyze in smaller chunks to stay within token limits
    if len(file_content) > 8000:
        # Split into chunks of approximately 8000 chars
        chunks = [file_content[i:i+8000] for i in range(0, len(file_content), 8000)]
        all_definitions = []
        
        for i, chunk in enumerate(chunks):
            chunk_prompt = f"""
            Analyze this chunk {i+1}/{len(chunks)} of {language} code and extract all function/method/class definitions
            along with their associated comments.
            {docstring_info}
            
            Source code chunk:
            ```
            {chunk}
            ```
            
            For each function/method/class, provide:
            - name: The name of the function/method/class
            - type: "function", "method", or "class"
            - line_number: Approximate starting line number (relative to this chunk)
            - comments: All comments associated with this definition, including any special documentation comments
            
            Return a JSON object with a "definitions" field containing an array of these items.
            Return only the JSON object with no other text.
            """
            
            response = self.query(chunk_prompt)
            try:
                chunk_result = json.loads(response)
                # Adjust line numbers for chunk position
                for def_item in chunk_result.get("definitions", []):
                    def_item["line_number"] = def_item.get("line_number", 0) + i * 8000 // 40  # Rough approximation of lines
                all_definitions.extend(chunk_result.get("definitions", []))
            except json.JSONDecodeError:
                # If parsing fails, we continue with other chunks
                continue
                
        return {"definitions": all_definitions}
    else:
        # For smaller files, analyze the whole file at once
        prompt = f"""
        Analyze this {language} code and extract all function/method/class definitions along with their associated comments.
        {docstring_info}
        
        Source code:
        ```
        {file_content}
        ```
        
        For each function/method/class, provide:
        - name: The name of the function/method/class
        - type: "function", "method", or "class"
        - line_number: Approximate starting line number
        - comments: All comments associated with this definition, including any special documentation comments
        
        Return a JSON object with a "definitions" field containing an array of these items.
        Return only the JSON object with no other text.
        """
        
        response = self.query(prompt)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"definitions": []}
```

## Step 9: Add State Management Methods

Add methods to access the stored metadata:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
    """
    Get the stored metadata for a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict containing metadata or None if not available
    """
    return self.file_metadata.get(file_path)

def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
    """
    Get all stored file metadata
    
    Returns:
        Dict mapping file paths to their metadata
    """
    return self.file_metadata

def clear_metadata(self, file_path: Optional[str] = None) -> None:
    """
    Clear stored metadata
    
    Args:
        file_path: Path to clear metadata for, or None to clear all
    """
    if file_path:
        if file_path in self.file_metadata:
            del self.file_metadata[file_path]
    else:
        self.file_metadata = {}
```

## Step 10: Add Test Method

Create a test method to verify the agent's functionality:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Add to FileAnalyzerAgent class)

def test_on_file(self, file_path: str, verbose: bool = False) -> bool:
    """
    Run a test analysis on a file to verify functionality
    
    Args:
        file_path: Path to the file to analyze
        verbose: Whether to print verbose output
        
    Returns:
        bool: True if analysis succeeded, False otherwise
    """
    try:
        if verbose:
            print(f"Testing analyzer on {file_path}...")
            
        # Run analysis
        metadata = self.analyze_file(file_path)
        
        if verbose:
            print(f"File type: {metadata.get('file_type', 'unknown')}")
            print(f"Language: {metadata.get('language', 'unknown')}")
            print(f"Definitions found: {len(metadata.get('definitions', []))}")
            print(f"Dependencies found: {len(metadata.get('dependencies', []))}")
            
        return True
    except Exception as e:
        if verbose:
            print(f"Error analyzing {file_path}: {e}")
        return False
```

## Step 11: Add Example Usage to `__main__`

Create an example usage that can be run as a standalone script:

```python
# Add to the bottom of src/dbp_cli/commands/hstc_agno/agents.py

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        analyzer = FileAnalyzerAgent()
        
        print(f"Analyzing {file_path}...")
        metadata = analyzer.analyze_file(file_path)
        
        print("Analysis complete!")
        print(f"File type: {metadata.get('file_type', 'unknown')}")
        print(f"Language: {metadata.get('language', 'unknown')}")
        print(f"Confidence: {metadata.get('confidence', 0)}%")
        print(f"Definitions found: {len(metadata.get('definitions', []))}")
        
        if metadata.get('definitions'):
            print("\nDefinitions:")
            for definition in metadata.get('definitions', []):
                print(f"- {definition.get('name')} ({definition.get('type')})")
        
        if metadata.get('dependencies'):
            print("\nDependencies:")
            for dependency in metadata.get('dependencies', []):
                print(f"- {dependency.get('name')} ({dependency.get('kind')})")
    else:
        print("Usage: python -m src.dbp_cli.commands.hstc_agno.agents <file_path>")
```

## Step 12: Testing the File Analyzer Agent

To test the agent implementation:

1. Create a test file with various functions and classes:

```python
# test_file.py

"""
Test file for demonstrating the File Analyzer Agent.
This file contains various functions and classes to test extraction capabilities.
"""

import os
import sys
from typing import List, Dict, Any

# Global variable
VERSION = "1.0.0"

def main_function(arg1: str, arg2: int = 0) -> bool:
    """
    [Function intent]
    This is the main function that does important things.
    
    [Design principles]
    Follows single responsibility principle.
    
    [Implementation details]
    Uses optimized algorithm for processing input.
    
    Args:
        arg1: First argument description
        arg2: Second argument description, defaults to 0
        
    Returns:
        bool: Result of the operation
    """
    return True

class ExampleClass:
    """
    [Class intent]
    Example class for testing documentation extraction.
    
    [Design principles]
    Encapsulates related functionality.
    
    [Implementation details]
    Implements basic operations with error handling.
    """
    
    def __init__(self, value: str):
        """
        [Class method intent]
        Initialize the class with a value.
        
        [Design principles]
        Simple initialization with validation.
        
        [Implementation details]
        Stores the value as an instance variable.
        
        Args:
            value: Initial value for the instance
        """
        self.value = value
    
    def process(self) -> Dict[str, Any]:
        """Process the value and return a result."""
        return {"result": self.value}
```

2. Run the agent on the test file:

```bash
python -m src.dbp_cli.commands.hstc_agno.agents test_file.py
```

3. Verify that the agent correctly:
   - Identifies the file as Python source code
   - Extracts the header comment
   - Identifies functions and classes with their comments
   - Detects dependencies (imports)

## Expected Output

After completing this phase, you should have a fully functional File Analyzer Agent that:

1. Identifies file types with high accuracy
2. Detects programming languages and their comment formats
3. Extracts header comments from source files
4. Identifies functions, classes, and methods with their associated comments
5. Detects dependencies on other files and packages

This agent provides the foundation for the Documentation Generator Agent, which will be implemented in Phase 4.

## Next Steps

Proceed to Phase 4 (Documentation Generator Agent) to implement the Claude 3.7-based agent for generating HSTC-compliant documentation.
