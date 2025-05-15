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
# This file implements the FileAnalyzerAgent for HSTC processing using the Agno framework.
# The agent efficiently processes files using Nova Micro to extract language information,
# comments, dependencies, and other metadata needed for HSTC documentation generation.
###############################################################################
# [Source file design principles]
# - Efficient file analysis using lightweight models
# - Adaptive parsing strategies based on file type
# - Comprehensive metadata extraction
# - Resilient error handling for diverse file formats
###############################################################################
# [Source file constraints]
# - Must work with the Agno agent framework
# - Should optimize token usage for efficient processing
# - Should use Nova Micro for efficiency in file analysis
###############################################################################
# [Dependencies]
# system:typing
# system:pathlib
# system:json
# system:os
# system:re
# system:agno.models.aws.bedrock
# system:agno.tools.file
# system:json_repair
# codebase:src/dbp_cli/commands/hstc_agno/abstract_agent.py
# codebase:src/dbp_cli/commands/hstc_agno/models.py
# codebase:src/dbp_cli/commands/hstc_agno/utils.py
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
###############################################################################
# [GenAI tool change history]
# 2025-05-15T14:05:00Z : Split from agents.py by CodeAssistant
# * Extracted FileAnalyzerAgent into dedicated file
# * Updated imports and dependencies
# * Maintained all functionality from original file
###############################################################################

import json
import os
import re
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from json_repair import repair_json

from agno.models.aws.bedrock import AwsBedrock
from agno.tools.file import FileTools
from dbp.api_providers.aws.client_factory import AWSClientFactory
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery

from .abstract_agent import AbstractAgnoAgent
from .models import (
    CommentFormat,
    Dependency,
    Definition,
    FileMetadata,
)
from .utils import (
    get_current_timestamp,
    extract_comment_blocks,
    read_file_content,
    is_binary_file
)


class FileAnalyzerAgent(AbstractAgnoAgent):
    """
    [Class intent]
    Agent for analyzing source files using Nova Micro. Efficiently processes
    files to extract language information, comments, and dependencies.
    
    [Design principles]
    Uses a lightweight model for efficiency in file processing tasks.
    Focuses on pattern recognition and metadata extraction.
    
    [Implementation details]
    Uses Nova Micro through the Bedrock API for optimal performance.
    Applies different parsing strategies based on file language detection.
    """
    
    def __init__(
        self, 
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        base_dir: Optional[Path] = None,
        show_prompts: bool = True,
        **kwargs
    ):
        """
        [Class method intent]
        Initializes the File Analyzer Agent with a Nova Micro model.
        
        [Design principles]
        Uses sensible defaults while allowing customization.
        Separates model configuration from agent functionality.
        
        [Implementation details]
        Creates an instance of AwsBedrock with the specified model ID.
        Passes through any additional keyword arguments to the Agent constructor.
        
        Args:
            model_id: ID of the Nova Micro model to use
            base_dir: Base directory for file operations
            **kwargs: Additional arguments to pass to the Agent constructor
        """
        # Add file tools for reading source files
        base_dir = base_dir or Path.cwd()
        file_tools = FileTools(base_dir=base_dir)
        
        # Get model discovery instance
        discovery = BedrockModelDiscovery.get_instance()
        
        # Get best available regions for this model
        preferred_regions = None  # Can be customized with user preferences if needed
        best_regions = discovery.get_best_regions_for_model(model_id, preferred_regions)
        
        # Select best region if available
        region_name = best_regions[0] if best_regions else None
        
        # Get AWS client factory to obtain boto3 session
        client_factory = AWSClientFactory.get_instance()
        
        # Get session for AWS credentials with the best region
        session = client_factory.get_session(region_name=region_name)
        
        # Initialize Nova model for file analysis with boto3 session
        model = AwsBedrock(id=model_id, session=session)
        
        # Add tools to kwargs to pass to parent constructor
        if 'tools' in kwargs:
            if isinstance(kwargs['tools'], list):
                kwargs['tools'].append(file_tools)
            else:
                kwargs['tools'] = [kwargs['tools'], file_tools]
        else:
            kwargs['tools'] = [file_tools]
        
        # Initialize state for storing analysis results
        self.file_metadata = {}
        self.file_tools = file_tools
            
        # Call parent constructor with model and agent name
        super().__init__(
            model=model,
            model_id=model_id,
            agent_name="FileAnalyzerAgent",
            show_prompts=show_prompts,
            **kwargs
        )
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        [Function intent]
        Perform comprehensive analysis of a source file.
        
        [Design principles]
        Orchestrates all analysis steps in a logical sequence.
        Adapts analysis depth based on file type and content.
        
        [Implementation details]
        Gathers file metadata, detects type and language.
        Analyzes code structure for source files.
        Stores results in internal state for further processing.
        
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
        file_type_info = self.analyze_file_type(file_content, file_path)
        metadata.update(file_type_info)
        
        # For source code files, use language info from file_type_info
        if file_type_info["file_type"] == "source_code":
            # Language info is already in file_type_info
            metadata["language"] = file_type_info.get("language", "unknown")
            metadata["confidence"] = file_type_info.get("confidence", 0)
            metadata["file_extension"] = file_type_info.get("file_extension", "")
            
            # Identify comment formats for this language
            comment_formats = self.identify_comment_formats(file_type_info.get("language", "unknown"))
            metadata["comment_formats"] = comment_formats
            
            # Extract header comment
            header_comment = self.extract_header_comment(file_content, comment_formats)
            if header_comment:
                metadata["header_comment"] = header_comment
            
            # Extract dependencies
            dependency_info = self.extract_dependencies(file_path, file_type_info.get("language", "unknown"))
            metadata["dependencies"] = dependency_info.get("dependencies", [])
            
            # Extract function comments
            function_info = self.extract_function_comments(file_path, file_type_info.get("language", "unknown"), comment_formats)
            metadata["definitions"] = function_info.get("definitions", [])
        
        # Store results in agent state
        self.file_metadata[file_path] = metadata
        
        return metadata
    
    
    def analyze_file_type(self, file_content: str, file_path: str = "") -> Dict[str, Any]:
        """
        [Function intent]
        Analyze content to determine file type using LLM classifier with MIME type hints.

        [Design principles]
        Uses MIME type hints from 'magic' package as guidance for LLM classification.
        Preserves both initial and confirmed MIME types for transparency.

        [Implementation details]
        Gets initial MIME type using 'magic' package if possible.
        Uses file extension as secondary hint if available.
        Always passes these hints to the LLM classifier for final determination.
        Returns both the initial magic-detected MIME type and LLM-confirmed MIME type.

        Args:
            file_content: Content of the file to analyze
            file_path: Optional path to the file for extension and MIME detection

        Returns:
            Dict containing:
            - file_type: The general type of file (e.g., "source_code", "markdown")
            - is_binary: Whether the file appears to be binary
            - initial_mime_type: MIME type determined by magic package
            - confirmed_mime_type: MIME type confirmed by LLM analysis
        """
        # Default response if everything fails
        default_type = {
            "file_type": "unknown", 
            "is_binary": False,
            "initial_mime_type": "application/octet-stream",
            "confirmed_mime_type": "application/octet-stream"
        }

        if not file_content:
            return default_type

        # Get MIME type hint using 'magic' if available
        initial_mime_type = "application/octet-stream"
        file_extension = ""
        
        try:
            import magic
            if file_path:
                initial_mime_type = magic.from_file(file_path, mime=True)
                file_extension = os.path.splitext(file_path)[1]
                self.log(f"Magic detected MIME type: {initial_mime_type} for file with extension {file_extension}", "DEBUG")
        except (ImportError, Exception) as e:
            # Fallback if magic isn't available or errors
            self.log(f"MIME type detection failed: {str(e)}", "WARNING")
            
            # Try to get extension from file path as fallback
            if file_path:
                file_extension = os.path.splitext(file_path)[1]
            
        # Build prompt for LLM file type detection with MIME type hints
        prompt = f"""
        Examine the following file content and determine its type and programming language.
        
        Initial MIME type (detected by a file type guesser): {initial_mime_type}
        File extension hint: {file_extension}
        
        Important: These hints are ONLY suggestions. You must make your own determination based primarily on the file content.
        
        Examples for source code files:
        - Python files often start with imports, comments, or docstrings - even if they start with '#' characters
        - JavaScript/TypeScript may begin with imports, comments, or function declarations
        - Source code with comments at the top is still source code, not markdown
        - Files with shebang lines (#!/usr/bin/env python) are always executable source code
        
Return a JSON structure with:
- file_type: The general type of file (e.g., "source_code", "markdown", "data", "configuration")
- language: The programming language if it's source code (e.g., "Python", "JavaScript", "TypeScript")
- confidence: Your confidence level in the language detection (0-100 integer)
- file_extension: The typical file extension for this language (e.g., ".py", ".js")
- is_binary: Whether the file appears to be binary (should be false for all text files)
- confirmed_mime_type: Your assessment of the correct MIME type for this file

Example JSON response:
```json
{{
  "file_type": "source_code",
  "language": "Python",
  "confidence": 95,
  "file_extension": ".py",
  "is_binary": false,
  "confirmed_mime_type": "text/x-python"
}}
```
        
File content (first 4000 chars):
```
{file_content[:4000]}
```
        
        **CRITICAL**: No explanation, no commentary, just the JSON object.
        """

        try:
            # Always run the LLM classifier for all non-empty files
            response_obj = self.run(prompt)
            
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            if not response_text:
                return default_type
                
            # Default result in case JSON parsing fails
            result = {
                "file_type": "unknown",
                "is_binary": False,
                "language": "unknown",
                "confidence": 0,
                "file_extension": "",
                "initial_mime_type": initial_mime_type
            }
                
            # Extract JSON from response
            try:
                # Try to find JSON content in the response
                repaired_text = repair_json(response_text)
                parsed_result = json.loads(repaired_text)
                
                # Update fields from parsed result
                result.update(parsed_result)
            except (json.JSONDecodeError, ValueError, AttributeError) as e:
                # Log the error but continue with default values
                print(f"Failed to parse LLM response as JSON: {e}")
                print(f"Response was: {response_text[:100]}...")
                
            # Ensure required fields exist and MIME type is always included
            if "confirmed_mime_type" not in result or not result["confirmed_mime_type"]:
                result["confirmed_mime_type"] = initial_mime_type
            result["initial_mime_type"] = initial_mime_type
                
            return result
                
        except Exception as e:
            # Handle all exceptions gracefully
            print(f"Error in analyze_file_type: {e}")
            raise
        
    def identify_comment_formats(self, language: str) -> Dict[str, Any]:
        """
        [Function intent]
        Identify comment formats for the detected language.
        
        [Design principles]
        Uses LLM to analyze and determine appropriate comment formats.
        Handles any programming language without relying on predefined formats.
        
        [Implementation details]
        Generates comment format information dynamically using LLM.
        Returns a list of comment styles with start and stop sequences.
        Ensures conversation history is cleared to prevent context contamination.
        
        Args:
            language: The detected programming language
            
        Returns:
            Dict containing comment style information with start/stop sequences
        """
        # Use LLM to determine comment format for the language
        prompt = f"""
        For the {language} programming language, provide a JSON object describing ALL comment styles.
        
        Examples:
        - For Python, include both # single-line comments and triple-quote docstrings
        - For JavaScript, include // single-line comments, /* */ block comments, and /** */ JSDoc comments
        - For any language with shebang style (#!), include that as a style
        
        Return a JSON object with the following structure:
        {{
          "language": "{language}",
          "comment_and_metadata_styles": [
            {{
              "name": "Descriptive name of comment style", 
              "start_sequence": "Comment start sequence",
              "stop_sequence": "Comment stop sequence"
            }},
            <!-- Include all comment styles for this language, like inline comments, block comments, docstrings, etc. -->
          ]
        }}
        
        **CRITICAL**: Add no explanation, no commentary, dump just the requested JSON object.
        """
        
        # Run with clear_history=True to ensure previous conversation doesn't affect the result
        response_obj = self.run(prompt, clear_history=True)
        try:
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            
            # Parse the response text as JSON
            result = json.loads(response_text)
            
            # Ensure comment_and_metadata_styles exists and is a list
            if "comment_and_metadata_styles" not in result or not isinstance(result["comment_and_metadata_styles"], list):
                result["comment_and_metadata_styles"] = []
                
            # Ensure language field is set
            if "language" not in result:
                result["language"] = language
                
            return result
            
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            error_msg = f"Failed to parse comment format response for {language}: {e}"
            self.log(error_msg, "ERROR")
            raise ValueError(error_msg)
                
    def extract_header_comment(self, file_content: str, comment_formats: Dict[str, Any]) -> Optional[str]:
        """
        [Function intent]
        Extract all header comments, empty lines and whitespace from the beginning of the file.
        
        [Design principles]
        Captures everything until the first non-comment, non-empty line (actual code).
        Preserves all comment blocks, whitespace and formatting to maintain the header structure.
        
        [Implementation details]
        Analyzes the file line by line to detect the end of header section.
        Falls back to LLM for complex or ambiguous comment formats.
        
        Args:
            file_content: Content of the file
            comment_formats: Comment format information with start/stop sequences
            
        Returns:
            Complete header comment block or None if not found
        """
        # Get all comment style information
        comment_styles = []
        if "comment_and_metadata_styles" in comment_formats and isinstance(comment_formats["comment_and_metadata_styles"], list):
            comment_styles = comment_formats["comment_and_metadata_styles"]
        
        # Extract all single-line and multi-line comment markers
        single_line_markers = []
        block_start_markers = []
        block_end_markers = []
        
        for style in comment_styles:
            start_seq = style.get("start_sequence", "")
            stop_seq = style.get("stop_sequence", "")
            
            # Single line comment markers (like # or //)
            if start_seq and (not stop_seq or start_seq == stop_seq or stop_seq == "\n"):
                single_line_markers.append(start_seq)
            
            # Block comment markers (like /* */ or """ """)
            if start_seq and stop_seq and start_seq != stop_seq and stop_seq != "\n":
                block_start_markers.append(start_seq)
                block_end_markers.append(stop_seq)
        
        # Define some default markers if none were found
        if not single_line_markers:
            single_line_markers = ["#", "//", "--"]
        if not block_start_markers:
            block_start_markers = ["/*", "/**", "'''", '"""']
            block_end_markers = ["*/", "*/", "'''", '"""']
        
        # Split file content into lines
        lines = file_content.splitlines()
        header_lines = []
        
        in_block_comment = False
        current_block_marker = None
        
        for line in lines:
            stripped_line = line.strip()
            
            # Skip empty or whitespace-only lines at beginning of file
            if not header_lines and not stripped_line:
                header_lines.append(line)
                continue
            
            # Check if we're inside a block comment
            if in_block_comment:
                header_lines.append(line)
                # Check for end of block comment
                for end_marker in block_end_markers:
                    if end_marker in line:
                        in_block_comment = False
                        current_block_marker = None
                        break
                continue
            
            # Check for start of block comment
            block_comment_started = False
            for i, start_marker in enumerate(block_start_markers):
                if stripped_line.startswith(start_marker):
                    # Found block comment start
                    in_block_comment = True
                    current_block_marker = block_end_markers[i]
                    header_lines.append(line)
                    # Check if block comment ends on same line
                    if current_block_marker in line[line.find(start_marker) + len(start_marker):]:
                        in_block_comment = False
                        current_block_marker = None
                    block_comment_started = True
                    break
            
            if block_comment_started:
                continue
            
            # Check for single-line comment
            is_comment_line = False
            for marker in single_line_markers:
                if stripped_line.startswith(marker):
                    header_lines.append(line)
                    is_comment_line = True
                    break
            
            # Check for empty line (only after we've seen some comments)
            if not is_comment_line:
                if not stripped_line and header_lines:
                    header_lines.append(line)
                else:
                    # Found non-comment, non-empty line - end of header
                    break
        
        # If we found header comments, return them
        if header_lines:
            return "\n".join(header_lines)
        
        # If simple extraction fails, use LLM to extract header
        prompt = f"""
        Extract the COMPLETE header comment block from this file. A header comment appears at the very beginning of the file before any code.
        
        IMPORTANT:
        - Include ALL comments at the top of the file, not just the first block
        - Include empty lines and lines with only whitespace that are part of the header
        - Stop when you reach the first actual code line (non-comment, non-empty line)
        - Preserve the exact format of all comments including indentation and empty lines
        
        File content (first 5000 chars):
        ```
        {file_content[:5000]}
        ```
        
        Comment formats for this file:
        {json.dumps(comment_formats, indent=2)}
        
        Return the COMPLETE raw header text including ALL comments and empty lines before the first actual code line.
        If no header comment is found, return an empty string.
        
        **CRITICAL**: Add no explanation, no commentary, dump just the JSON object.
        """
        
        response = self.run(prompt)
        return response if response else None
    
    def extract_dependencies(self, file_path: str, language: str) -> Dict[str, Any]:
        """
        [Function intent]
        Extract dependencies from the source file.
        
        [Design principles]
        Focuses on import statements and include directives.
        Categorizes dependencies by type for context-aware processing.
        
        [Implementation details]
        Analyzes imports at the beginning of files.
        Distinguishes between project, system, and external dependencies.
        
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
        
        Source code to analyze: {file_path}
        
        For each dependency, identify:
        - name: The name of the dependency
        - kind: One of "codebase" (internal project file), "system" (system package), "external" (third-party library)
        - path_or_package: The import path or package name
        - imported_names: Array of specific functions/classes/methods imported from this dependency
        - called_names: Array of specific functions/class methods called from this dependency
        
        Return a JSON object with a "dependencies" field containing an array of these dependencies.
        
        Project root: "."
        
        Example JSON response:
        ```json
        {{
          "dependencies": [
            {{
              "name": "os",
              "kind": "system",
              "path_or_package": "os",
              "imported_names": ["path", "environ"],
              "called_names": ["path.join", "environ.get"]
            }},
            {{
              "name": "utils",
              "kind": "codebase",
              "path_or_package": "<project_root>/core/utils.py", <!-- MUST be a filepath relative to the project root -->
              "imported_names": ["load_config", "format_data"],
              "called_names": ["load_config"]
            }},
            {{
              "name": "requests",
              "kind": "external",
              "path_or_package": "requests",
              "imported_names": [],
              "called_names": ["get", "post"]
            }}
          ]
        }}
        ```
        
        **CRITICAL**: Add no explanation, no commentary, dump just the JSON object.
        """
        
        response_obj = self.run(prompt, clear_history=True)
        try:
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            
            return json.loads(repair_json(response_text))
            
        except (TypeError, AttributeError, ValueError) as e:
            # Handle the error gracefully
            print(f"Error parsing dependency extraction response: {e}")
            return {"dependencies": []}
    
    def extract_function_comments(self, file_path: str, language: str, comment_formats: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Extract comments associated with functions and classes.
        
        [Design principles]
        Handles large files by processing in manageable chunks.
        Preserves context between function definitions and their comments.
        
        [Implementation details]
        Splits large files into overlapping chunks to maintain context.
        Reconstructs line numbers for accurate source mapping.
        
        Args:
            file_path: Content of the file
            language: The detected programming language
            comment_formats: Comment format information
            
        Returns:
            Dict containing function comment information
        """
        
        # For large files, analyze in smaller chunks to stay within token limits
        all_definitions = []
        
        prompt = f"""
        Analyze this {language} code and extract all function/method/class definitions along with their associated comments.
        
        Source code file path: {file_path}
        
        For each function/method/class, provide:
        - name: The name of the function/method/class
        - type: "function", "method", or "class"
        - line_number: Starting line number of the function/method/class signature definition
        - comments: All comments associated with this definition, including any special documentation comments
        
        Return a JSON object with a "definitions" field containing an array of these items.
        
        Example JSON response:
        ```json
        {{
            "definitions": [
            {{
                "name": "calculate_total",
                "type": "function",
                "line_number": 42,
                "comments": "/**\n * Calculates the sum of all items in the cart\n * @param {{Array}} items - List of cart items\n * @returns {{number}} - Total sum\n */"
            }},
            {{
                "name": "UserAccount",
                "type": "class",
                "line_number": 87,
                "comments": "# UserAccount class for managing user profiles\n# Handles authentication and preferences"
            }},
            {{
                "name": "processPayment",
                "type": "method",
                "line_number": 134,
                "comments": "\"\"\"\n[Function intent]\nProcess payment using the payment gateway.\n\n[Design principles]\nValidates input before sending to gateway.\nHandles errors gracefully.\n\n[Implementation details]\nUses async/await pattern to handle API responses.\n\nArgs:\n    amount: Payment amount\n    method: Payment method\n\nReturns:\n    Transaction ID or error code\n\"\"\""
            }}
            ]
        }}
        ```
        
        **CRITICAL**: Add no explanation, no commentary, dump just the JSON object.
        """
        
        response = self.run(prompt, clear_history=True)
        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"definitions": []}
    
    def clear_state(self, file_path: Optional[str] = None) -> None:
        """
        [Function intent]
        Clear stored metadata.
        
        [Design principles]
        Supports selective or complete state reset.
        Prevents memory leaks with long-running processes.
        
        [Implementation details]
        Can clear a specific file's metadata or all metadata.
        
        Args:
            file_path: Path to clear metadata for, or None to clear all
        """
        if file_path:
            if file_path in self.file_metadata:
                del self.file_metadata[file_path]
        else:
            self.file_metadata = {}
    
    def get_state_item(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        [Function intent]
        Get the stored metadata for a file.
        
        [Design principles]
        Provides clean access to analysis results.
        Maintains state between analysis and processing.
        
        [Implementation details]
        Retrieves stored metadata from agent's internal state.
        Returns None when metadata for the file is not available.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing metadata or None if not available
        """
        return self.file_metadata.get(file_path)

    def get_all_state(self) -> Dict[str, Dict[str, Any]]:
        """
        [Function intent]
        Get all stored file metadata.
        
        [Design principles]
        Provides batch access to all analysis results.
        Supports aggregated processing of multiple files.
        
        [Implementation details]
        Returns complete mapping of file paths to their metadata.
        
        Returns:
            Dict mapping file paths to their metadata
        """
        return self.file_metadata
    
    def test_on_file(self, file_path: str, verbose: bool = False) -> bool:
        """
        [Function intent]
        Run a test analysis on a file to verify functionality.
        
        [Design principles]
        Provides simple validation of agent functionality.
        Supports debugging with optional verbose output.
        
        [Implementation details]
        Runs complete analysis pipeline on a single file.
        Reports key metrics from the analysis process.
        
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
