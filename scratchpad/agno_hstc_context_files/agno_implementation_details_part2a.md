# HSTC Implementation Details with Agno - Part 2A: File Analyzer Agent

## Key Classes and Interfaces (continued)

### 3. File Analyzer Agent Implementation

```python
# src/dbp_cli/commands/hstc_agno/agents.py (Part 1: File Analyzer)

import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

from agno.agent import Agent
from agno.models import BedrockNovaModel
from agno.tools import FileTools

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
        file_content = self.file_tools.read_file(file_path)
        if not file_content:
            metadata["file_type"] = "unknown"
            metadata["error"] = "Could not read file content"
            return metadata
        
        # Detect file type
        file_type_info = self.analyze_file_type(file_content)
        metadata.update(file_type_info)
        
        # For source code files, perform deeper analysis
        if file_type_info["file_type"] == "source_code":
            # Detect language
            language_info = self.detect_language(file_content)
            metadata.update(language_info)
            
            # Identify comment formats for this language
            comment_formats = self.identify_comment_formats(language_info["language"])
            metadata["comment_formats"] = comment_formats
            
            # Check for header comment
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
    
    def detect_language(self, file_content: str) -> Dict[str, Any]:
        """
        Determine the programming language with confidence score
        
        Args:
            file_content: Content of the file to analyze
            
        Returns:
            Dict containing language information and confidence score
        """
        # Build prompt for language detection
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
    
    def identify_comment_formats(self, language: str) -> Dict[str, Any]:
        """
        Identify comment formats for the detected language
        
        Args:
            language: The detected programming language
            
        Returns:
            Dict containing comment syntax information
        """
        # Build prompt for comment format detection
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
    
    def extract_header_comment(self, file_content: str, comment_formats: Dict[str, Any]) -> Optional[str]:
        """
        Extract header comment from file content
        
        Args:
            file_content: Content of the file
            comment_formats: Comment format information
            
        Returns:
            Header comment or None if not found
        """
        # Build prompt for header extraction
        prompt = f"""
        Extract the header comment from this file.
        A header comment appears at the very beginning of the file before any code.
        
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
    
    def extract_dependencies(self, file_content: str, language: str) -> Dict[str, Any]:
        """
        Extract dependencies from the source file
        
        Args:
            file_content: Content of the file
            language: The detected programming language
            
        Returns:
            Dict containing dependency information
        """
        # Build prompt for dependency extraction
        prompt = f"""
        Analyze this {language} code and identify all external dependencies:
        1. Other source file imports or includes
        2. External libraries or packages
        3. System dependencies
        
        Source code:
        ```
        {file_content[:5000]}  # First 5000 chars for dependency detection
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
    
    def extract_function_comments(
        self, file_content: str, language: str, comment_formats: Dict[str, Any]
    ) -> Dict[str, Any]:
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
