# File Analyzer Agent for HSTC

## Overview

The File Analyzer Agent is a core component of the HSTC implementation responsible for analyzing source code files using the Nova Micro model from Amazon Bedrock. This document details how the agent is structured, how it analyzes files, and how it extracts dependencies and comment information.

## Agent Implementation

The File Analyzer Agent is implemented as an Agno agent with the Nova Micro model, focusing on efficient, targeted analysis tasks:

```python
from agno.agent import Agent
from agno.models import BedrockNovaModel
from agno.tools import FileTools
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

class FileAnalyzerAgent(Agent):
    """Agent for analyzing source files using Nova Micro."""
    
    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        base_dir: Optional[Path] = None,
        **kwargs
    ):
        # Initialize Nova Micro model for file analysis
        model = BedrockNovaModel(id=model_id)
        super().__init__(model=model, **kwargs)
        
        # Add file tools for reading source files
        base_dir = base_dir or Path.cwd()
        file_tools = FileTools(base_dir=base_dir)
        self.add_toolkit(file_tools)
        
        # Initialize state for storing analysis results
        self.file_metadata = {}
```

## File Analysis Workflow

The file analyzer performs its tasks in stages:

1. **Initial File Inspection** - Basic metadata collection and file type identification
2. **Language Detection** - Determine the programming language with confidence score
3. **Comment Syntax Analysis** - Identify comment formats for the detected language
4. **Dependency Analysis** - Extract dependencies on other files or packages

### 1. File Type Detection

```python
def analyze_file_type(self, file_path: str) -> Dict[str, Any]:
    """
    Analyze the file to determine its type (source code, markdown, etc.)
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dict containing file type information
    """
    file_content = self.tools.read_file(file_path)
    
    # Build prompt for file type detection
    prompt = f"""
    Examine the following file content and determine its type.
    Return a JSON structure with:
    - file_type: The general type of file (e.g., "source_code", "markdown", "data", "configuration")
    - is_binary: Whether the file appears to be binary (true/false)
    
    File content:
    ```
    {file_content[:1000]}  # First 1000 chars for detection
    ```
    
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"file_type": "unknown", "is_binary": False}
```

### 2. Language Detection

For source code files, we need to detect the programming language:

```python
def detect_language(self, file_path: str) -> Dict[str, Any]:
    """
    Determine the programming language with confidence score
    
    Args:
        file_path: Path to the file to analyze
        
    Returns:
        Dict containing language information and confidence score
    """
    file_content = self.tools.read_file(file_path)
    
    prompt = f"""
    Analyze this source code and determine:
    1. The primary programming language
    2. Your confidence level (0-100%)
    
    Source code:
    ```
    {file_content[:2000]}  # First 2000 chars for language detection
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

### 3. Comment Syntax Detection

Once the language is identified, we need to determine the comment formats:

```python
def identify_comment_formats(self, language: str) -> Dict[str, Any]:
    """
    Identify comment formats for the detected language
    
    Args:
        language: The detected programming language
        
    Returns:
        Dict containing comment syntax information
    """
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

### 4. Dependency Extraction

Extract dependencies from the source file:

```python
def extract_dependencies(self, file_path: str, language: str, comment_formats: Dict) -> Dict[str, Any]:
    """
    Extract dependencies from the source file
    
    Args:
        file_path: Path to the file to analyze
        language: The detected programming language
        comment_formats: The detected comment formats
        
    Returns:
        Dict containing dependency information
    """
    file_content = self.tools.read_file(file_path)
    
    # Build a prompt based on the language
    prompt = f"""
    Analyze this {language} code and identify all external dependencies:
    1. Other source file imports or includes
    2. External libraries or packages
    3. System dependencies
    
    Source code:
    ```
    {file_content}
    ```
    
    For each dependency, identify:
    - name: The name of the dependency
    - kind: One of "codebase" (internal project file), "system" (system package), "external" (third-party library)
    - path_or_package: The import path or package name
    - function_names: List of specific functions/classes/methods imported from this dependency
    
    Return a JSON object with a "dependencies" field containing an array of these dependencies.
    Return only the JSON object with no other text.
    """
    
    response = self.query(prompt)
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        return {"dependencies": []}
```

## Extracting Function Comments

For source files, we need to extract comments associated with functions and classes:

```python
def extract_function_comments(self, file_path: str, language: str, comment_formats: Dict) -> Dict[str, Any]:
    """
    Extract comments associated with functions and classes
    
    Args:
        file_path: Path to the file to analyze
        language: The detected programming language
        comment_formats: The detected comment formats
        
    Returns:
        Dict containing function comment information
    """
    file_content = self.tools.read_file(file_path)
    
    # Build a prompt based on the language and comment formats
    docstring_info = ""
    if comment_formats["docstring_format"]:
        docstring_info = f"Docstrings in this language are denoted by {comment_formats['docstring_format']}."
    
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

## Comprehensive File Analysis

The main entry point for file analysis combines all the above steps:

```python
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
    
    # Detect file type
    file_type_info = self.analyze_file_type(file_path)
    metadata.update(file_type_info)
    
    # For source code files, perform deeper analysis
    if file_type_info["file_type"] == "source_code":
        # Detect language
        language_info = self.detect_language(file_path)
        metadata.update(language_info)
        
        # Identify comment formats for this language
        comment_formats = self.identify_comment_formats(language_info["language"])
        metadata["comment_formats"] = comment_formats
        
        # Extract dependencies
        dependency_info = self.extract_dependencies(file_path, language_info["language"], comment_formats)
        metadata["dependencies"] = dependency_info.get("dependencies", [])
        
        # Extract function comments
        function_info = self.extract_function_comments(file_path, language_info["language"], comment_formats)
        metadata["definitions"] = function_info.get("definitions", [])
    
    # Store results in agent state
    self.file_metadata[file_path] = metadata
    
    return metadata
```

## Integration with HSTC Manager

The File Analyzer Agent integrates with the HSTC Manager by providing methods to retrieve stored metadata:

```python
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
```

## Prompt Engineering for Optimal Results

The File Analyzer Agent relies heavily on well-crafted prompts for Nova Micro. Some key principles in these prompts:

1. **Structure the output** - Always request JSON output with specific fields
2. **Sample selectively** - Use subsets of the file content where appropriate
3. **Provide context** - Include language and syntactic information when known
4. **Be specific** - Give clear criteria for confidence levels and classifications
5. **Balance detail and efficiency** - Request only the necessary information

## Nova Micro Performance Considerations

Nova Micro is selected for these tasks because:

1. **Speed** - Faster inference for simple classification tasks
2. **Cost** - Lower token usage than larger models
3. **Focus** - Good at structured extraction tasks
4. **Reliability** - Consistent JSON outputs for programmatic use

However, for deeper code understanding and documentation generation, we'll need to pass results to the Claude 3.7 agent detailed in the next context document.
