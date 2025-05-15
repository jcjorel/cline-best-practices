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
# This file implements the core agent classes for HSTC processing using the Agno framework.
# It includes the File Analyzer Agent for efficient file processing using Nova Micro and
# the Documentation Generator Agent for producing high-quality documentation using Claude 3.7.
###############################################################################
# [Source file design principles]
# - Clear separation of agent responsibilities
# - Effective prompting strategies for each model type
# - Consistent agent interfaces for interoperability
# - Error handling with appropriate fallback strategies
###############################################################################
# [Source file constraints]
# - Must work with the Agno agent framework
# - Should optimize token usage for each model type
# - File Analyzer should use Nova for efficiency
# - Documentation Generator should use Claude for quality
###############################################################################
# [Dependencies]
# system:typing
# system:pathlib
# system:agno.agent
# system:agno.models
# system:agno.models.anthropic
# codebase:src/dbp_cli/commands/hstc_agno/models.py
# codebase:src/dbp_cli/commands/hstc_agno/utils.py
# codebase:src/dbp_cli/commands/hstc_agno/abstract_agent.py
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
###############################################################################
# [GenAI tool change history]
# 2025-05-13T17:38:00Z : Refactored to use AbstractAgnoAgent by CodeAssistant
# * Modified agents to inherit from AbstractAgnoAgent
# * Removed duplicated code for prompt display and response processing
# * Implemented abstract methods for state management
# 2025-05-13T10:59:00Z : Added model discovery for optimal region selection by CodeAssistant
# * Integrated BedrockModelDiscovery for finding best regions for each model
# * Used get_best_regions_for_model to automatically select optimal region
# 2025-05-13T10:54:00Z : Fixed AWS credentials issue by CodeAssistant
# * Added integration with AWS client factory for proper AWS credentials
# * Used session from AWS client factory for AwsBedrock model
###############################################################################

import json
import os
import re
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from json_repair import repair_json

from agno.models.aws.bedrock import AwsBedrock
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from agno.tools.reasoning import ReasoningTools
from dbp.api_providers.aws.client_factory import AWSClientFactory
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery

from .abstract_agent import AbstractAgnoAgent
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
from .utils import (
    get_current_timestamp,
    parse_dependency_string,
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
            
            import pdb
            pdb.set_trace()
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


class DocumentationGeneratorAgent(AbstractAgnoAgent):
    """
    [Class intent]
    Agent for generating HSTC-compliant documentation using Claude 3.7.
    Produces high-quality documentation based on file content and metadata.
    
    [Design principles]
    Uses a powerful model for comprehensive reasoning and quality documentation.
    Structures prompts to ensure HSTC standard compliance.
    
    [Implementation details]
    Uses Claude 3.7 through the Agno framework for optimal documentation quality.
    Applies contextual awareness of HSTC requirements and project standards.
    """
    
    def __init__(self, model_id: str = "claude-3-5-sonnet-20241022", show_prompts: bool = True, **kwargs):
        """
        [Class method intent]
        Initialize the Documentation Generator Agent with a Claude 3.7 model.
        
        [Design principles]
        Uses sensible defaults while allowing customization.
        Separates model configuration from agent functionality.
        
        [Implementation details]
        Creates an instance of Claude with the specified model ID.
        Passes through any additional keyword arguments to the Agent constructor.
        
        Args:
            model_id: ID of the Claude model to use
            **kwargs: Additional arguments to pass to the Agent constructor
        """
        # Add reasoning tools for step-by-step analysis
        reasoning_tools = ReasoningTools()
        
        # Initialize Claude model for documentation generation
        model = Claude(id=model_id)
        
        # Add tools to kwargs to pass to parent constructor
        if 'tools' in kwargs:
            if isinstance(kwargs['tools'], list):
                kwargs['tools'].append(reasoning_tools)
            else:
                kwargs['tools'] = [kwargs['tools'], reasoning_tools]
        else:
            kwargs['tools'] = [reasoning_tools]
        
        # Initialize state for storage
        self.generated_documentation = {}
            
        # Call parent constructor with model and agent name
        super().__init__(
            model=model,
            model_id=model_id,
            agent_name="DocumentationGeneratorAgent",
            show_prompts=show_prompts,
            **kwargs
        )
        
    
    def process_file_documentation(
        self, 
        file_path: str, 
        file_metadata: Dict[str, Any], 
        dependency_metadata: Dict[str, Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        [Function intent]
        Process file metadata and generate updated documentation that meets HSTC standards.
        
        [Design principles]
        Routes processing based on file type for appropriate documentation generation.
        Handles different file types with specialized processing logic.
        
        [Implementation details]
        Orchestrates the complete documentation workflow including analysis and generation.
        Dispatches to specialized handlers based on file type.
        
        Args:
            file_path: Path to the file being processed
            file_metadata: Metadata about the file from the File Analyzer
            dependency_metadata: Metadata about dependencies from the File Analyzer
            
        Returns:
            Dict containing updated documentation
        """
        # Use empty dependency metadata if none provided
        if dependency_metadata is None:
            dependency_metadata = {}
            
        # Extract key information from metadata
        file_type = file_metadata.get("file_type", "unknown")
        
        # Process differently based on file type
        if file_type == "source_code":
            return self._process_source_file(file_path, file_metadata, dependency_metadata)
        elif file_type == "markdown":
            return self._process_markdown_file(file_path, file_metadata)
        else:
            # For other file types, just return basic documentation
            return {
                "path": file_path,
                "file_type": file_type,
                "documentation_updated": False,
                "reason": f"File type {file_type} does not require HSTC documentation"
            }
    
    def _process_source_file(
        self, 
        file_path: str, 
        file_metadata: Dict[str, Any], 
        dependency_metadata: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [Function intent]
        Process a source code file and generate HSTC-compliant documentation.
        
        [Design principles]
        Follows a structured approach to documentation generation.
        Separates analysis from generation for better reasoning.
        
        [Implementation details]
        Executes a multi-step process to analyze and generate documentation.
        Handles both file header and individual definitions.
        
        Args:
            file_path: Path to the file
            file_metadata: Metadata about the file
            dependency_metadata: Metadata about dependencies
            
        Returns:
            Dict containing updated documentation
        """
        language = file_metadata.get("language", "unknown")
        definitions = file_metadata.get("definitions", [])
        
        # Step 1: Analyze existing documentation
        analysis_response = self._analyze_existing_documentation(file_path, file_metadata, dependency_metadata)
        
        # Step 2: Generate updated documentation for the file header
        file_header = self._generate_header_documentation(file_path, file_metadata, dependency_metadata, analysis_response)
        
        # Step 3: Generate documentation for each function/method/class
        definitions_documentation = []
        for definition in definitions:
            definition_doc = self._generate_definition_documentation(
                definition, file_metadata, dependency_metadata
            )
            definitions_documentation.append(definition_doc)
        
        # Step 4: Build the final documentation result
        result = {
            "path": file_path,
            "file_type": "source_code",
            "language": language,
            "file_header": file_header,
            "definitions": definitions_documentation,
            "documentation_updated": True,
            "analysis": analysis_response
        }
        
        # Store generated documentation
        self.generated_documentation[file_path] = result
        
        return result
    
    def _process_markdown_file(self, file_path: str, file_metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Process a markdown file to determine documentation needs.
        
        [Design principles]
        Recognizes that markdown files have different documentation requirements.
        Provides clear separation between source code and markdown processing.
        
        [Implementation details]
        Returns appropriate metadata for markdown files.
        Recognizes that markdown files don't need standard HSTC documentation.
        
        Args:
            file_path: Path to the file
            file_metadata: Metadata about the file
            
        Returns:
            Dict containing markdown file information
        """
        # Markdown files don't need special HSTC documentation processing
        return {
            "path": file_path,
            "file_type": "markdown",
            "documentation_updated": False,
            "reason": "Markdown files do not require HSTC documentation"
        }
    
    def _analyze_existing_documentation(
        self, 
        file_path: str, 
        file_metadata: Dict[str, Any], 
        dependency_metadata: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        [Function intent]
        Analyze existing documentation and determine what needs to be updated.
        
        [Design principles]
        Uses structured reasoning to assess documentation quality.
        Considers both file header and definition documentation.
        
        [Implementation details]
        Extracts dependency information from metadata.
        Uses step-by-step analysis to identify gaps and improvements.
        
        Args:
            file_path: Path to the file
            file_metadata: Metadata about the file
            dependency_metadata: Metadata about dependencies
            
        Returns:
            String containing detailed analysis
        """
        language = file_metadata.get("language", "unknown")
        definitions = file_metadata.get("definitions", [])
        dependencies = file_metadata.get("dependencies", [])
        
        # Extract dependency information
        dependency_info = []
        for dep in dependencies:
            dep_name = dep.get("name", "unknown")
            dep_path = dep.get("path_or_package", "")
            dep_metadata = dependency_metadata.get(dep_path, {})
            
            dep_info = {
                "name": dep_name,
                "path": dep_path,
                "has_metadata": bool(dep_metadata)
            }
            dependency_info.append(dep_info)
        
        # Use reasoning tools for step-by-step analysis
        analysis_prompt = f"""
        Analyze the documentation status and needs for this {language} source file:
        
        File path: {file_path}
        
        # Existing Documentation Analysis
        
        ## File Header Documentation
        {file_metadata.get("header_comment", "No existing header comment found")}
        
        ## Function/Method/Class Documentation
        {len(definitions)} definitions found.
        
        # HSTC Documentation Requirements
        
        According to HSTC standards, documentation must include:
        
        1. Source file header with:
           - Source file intent
           - Source file design principles
           - Source file constraints
           - Dependencies (with kind: codebase, system, or other)
           - Change history
        
        2. Function/Method/Class documentation with:
           - Function/Class method/Class intent
           - Design principles
           - Implementation details
        
        Analyze the current documentation against these standards.
        Identify specific areas that need improvement.
        Think about what information should be included in each section based on the file content.
        """
        
        try:
            analysis_response = self.tools.think(
                agent=self,
                title="Documentation Analysis",
                thought=analysis_prompt,
                action="Analyze existing documentation and determine necessary updates",
                confidence=0.9
            )
            return analysis_response
        except AttributeError:
            # If ReasoningTools not available, use direct run
            return self.run(analysis_prompt)
    
    def _generate_header_documentation(
        self, 
        file_path: str, 
        file_metadata: Dict[str, Any], 
        dependency_metadata: Dict[str, Dict[str, Any]], 
        analysis: str
    ) -> Dict[str, Any]:
        """
        [Function intent]
        Generate documentation for file header that meets HSTC standards.
        
        [Design principles]
        Ensures compliance with standard HSTC header format.
        Adapts output based on file language and analysis results.
        
        [Implementation details]
        Selects appropriate comment syntax based on language.
        Creates a comprehensive header with all required sections.
        
        Args:
            file_path: Path to the file
            file_metadata: Metadata about the file
            dependency_metadata: Metadata about dependencies
            analysis: Analysis of existing documentation
            
        Returns:
            Dict containing header documentation
        """
        language = file_metadata.get("language", "unknown")
        comment_formats = file_metadata.get("comment_formats", {})
        existing_header = file_metadata.get("header_comment", "")
        
        # Determine appropriate comment syntax
        block_start = comment_formats.get("block_comment_start", "/*")
        block_end = comment_formats.get("block_comment_end", "*/")
        if not block_start or not block_end:
            # Fallback to language-specific defaults
            if language == "python":
                block_start = '"""'
                block_end = '"""'
            elif language in ["javascript", "typescript", "java", "c", "cpp", "csharp"]:
                block_start = "/*"
                block_end = "*/"
            elif language in ["ruby", "perl", "shell", "bash"]:
                block_start = "#"
                block_end = "#"
        
        # Get current timestamp
        current_timestamp = get_current_timestamp()
        
        # Build prompt for header generation
        header_prompt = f"""
        Generate a file header comment for this {language} source file that meets HSTC documentation standards.
        
        File path: {file_path}
        
        Based on the analysis:
        {analysis}
        
        The file header must follow this EXACT format:
        
        {block_start}
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
        # <Describe the detailed purpose of this file. Intent must be fully captured and contextualized.>
        ###############################################################################
        # [Source file design principles]
        # <List key design principles guiding this implementation>
        ###############################################################################
        # [Source file constraints]
        # <Document any limitations or requirements for this file>
        ###############################################################################
        # [Dependencies]
        # <File paths of others codebase and documentation files. List also language specific libraries if any>
        # <List of markdown files in doc/ that provide broader context for this file>
        # <Prefix the dependency with its kind like "<codebase|system|other>:<dependency>">
        ###############################################################################
        # [GenAI tool change history]
        # {current_timestamp} : Initial documentation generated by HSTC tool
        # * Added standardized header documentation
        ###############################################################################
        {block_end}
        
        Use the file metadata and analysis to create a comprehensive header that fully captures the file's intent,
        design principles, constraints, and dependencies. Fill in ALL sections with meaningful content.
        
        Return the complete header in valid {language} comment syntax.
        Return ONLY the comment content as a raw string, without any JSON or code formatting.
        """
        
        # Generate header
        header_response = self.run(header_prompt)
        
        # Parse the header to extract sections
        header_sections = self._extract_header_sections(header_response)
        
        return header_sections
    
    def _generate_definition_documentation(
        self, 
        definition: Dict[str, Any], 
        file_metadata: Dict[str, Any], 
        dependency_metadata: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        [Function intent]
        Generate documentation for a function/method/class that meets HSTC standards.
        
        [Design principles]
        Creates standardized documentation with required sections.
        Respects language-specific documentation conventions.
        
        [Implementation details]
        Determines appropriate docstring format based on language.
        Ensures all three required HSTC sections are included.
        
        Args:
            definition: Definition information
            file_metadata: Metadata about the file
            dependency_metadata: Metadata about dependencies
            
        Returns:
            Dict containing definition documentation
        """
        language = file_metadata.get("language", "unknown")
        comment_formats = file_metadata.get("comment_formats", {})
        name = definition.get("name", "unknown")
        def_type = definition.get("type", "function")
        existing_comment = definition.get("comments", "")
        
        # Determine appropriate docstring format
        docstring_format = comment_formats.get("docstring_format")
        docstring_start = comment_formats.get("docstring_start")
        docstring_end = comment_formats.get("docstring_end")
        
        # Fallback to language-specific defaults
        if not docstring_format:
            if language == "python":
                docstring_format = "triple quotes"
                docstring_start = '"""'
                docstring_end = '"""'
            elif language in ["javascript", "typescript"]:
                docstring_format = "JSDoc"
                docstring_start = "/**"
                docstring_end = "*/"
            elif language in ["java", "c", "cpp", "csharp"]:
                docstring_format = "block comment"
                docstring_start = "/*"
                docstring_end = "*/"
        
        # Build prompt for definition documentation
        definition_prompt = f"""
        Generate documentation for this {language} {def_type} named "{name}" that meets HSTC standards.
        
        Existing documentation:
        ```
        {existing_comment}
        ```
        
        The documentation must include these three sections in this exact order:
        1. [Function/Class method/Class intent] - Purpose and role description
        2. [Design principles] - Patterns and approaches used
        3. [Implementation details] - Key technical implementation notes
        
        Use the appropriate {language} documentation format ({docstring_format}).
        
        Return a JSON object with these fields:
        - name: The name of the function/method/class
        - type: The type ("function", "method", or "class")
        - original_comment: The existing comment
        - updated_comment: The new documentation that follows HSTC standards
        
        Ensure the updated_comment uses proper {language} documentation syntax.
        """
        
        # Generate definition documentation
        definition_response = self.run(definition_prompt)
        
        try:
            definition_doc = json.loads(definition_response)
            return definition_doc
        except json.JSONDecodeError:
            # If parsing fails, create a structured response manually
            return {
                "name": name,
                "type": def_type,
                "original_comment": existing_comment,
                "updated_comment": definition_response,
                "error": "Failed to parse response as JSON"
            }
    
    def _extract_header_sections(self, header_text: str) -> Dict[str, Any]:
        """
        [Function intent]
        Extract structured header documentation from the raw text.
        
        [Design principles]
        Parses raw header text into structured components.
        Provides clean data structure for further processing.
        
        [Implementation details]
        Uses carefully defined section markers to extract each required part.
        Handles both standard sections and specialized formats like dependencies.
        
        Args:
            header_text: Raw header text
            
        Returns:
            Dict containing extracted sections
        """
        # Parse the raw response to extract key sections
        sections = {
            "intent": self._extract_section(header_text, "[Source file intent]"),
            "design_principles": self._extract_section(header_text, "[Source file design principles]"),
            "constraints": self._extract_section(header_text, "[Source file constraints]"),
            "dependencies": self._extract_dependencies(header_text),
            "change_history": self._extract_change_history(header_text),
        }
        
        # Include the full raw header response
        sections["raw_header"] = header_text
        
        return sections

    def _extract_section(self, text: str, section_marker: str) -> str:
        """
        [Function intent]
        Extract a specific section from the header text.
        
        [Design principles]
        Provides robust text extraction for header sections.
        Handles edge cases with graceful degradation.
        
        [Implementation details]
        Uses string operations to identify section boundaries.
        Removes comment markers and cleans up extracted text.
        
        Args:
            text: Header text
            section_marker: Marker for the section to extract
            
        Returns:
            Extracted section text
        """
        try:
            start_idx = text.find(section_marker)
            if start_idx == -1:
                return ""
            
            # Find the start of the actual content
            start_idx = text.find("\n", start_idx)
            if start_idx == -1:
                return ""
            
            # Find the end of the section (next section marker or end of header)
            end_idx = text.find("###############################################################################", start_idx)
            if end_idx == -1:
                end_idx = len(text)
            
            # Extract and clean up
            section_text = text[start_idx:end_idx].strip()
            # Remove comment markers
            section_text = section_text.replace("# ", "").replace("#", "")
            
            return section_text.strip()
        except Exception:
            return ""

    def _extract_dependencies(self, text: str) -> List[Dict[str, str]]:
        """
        [Function intent]
        Extract dependency information from the header text.
        
        [Design principles]
        Parses dependencies with their structured attributes.
        Handles both structured and unstructured dependency listings.
        
        [Implementation details]
        Extracts dependencies with their kinds from the dependencies section.
        Handles the special format syntax for codebase, system, and other dependencies.
        
        Args:
            text: Header text
            
        Returns:
            List of dependency dictionaries
        """
        dependencies_section = self._extract_section(text, "[Dependencies]")
        dependencies = []
        
        for line in dependencies_section.split('\n'):
            line = line.strip()
            if not line:
                continue
                
            if ":" in line:
                # Parse structured dependency with kind
                parts = line.split(":", 1)
                if len(parts) == 2:
                    kind = parts[0].strip().strip("<>")
                    path = parts[1].strip()
                    dependencies.append({
                        "kind": kind,
                        "dependency": path
                    })
            else:
                # Default to unknown kind
                dependencies.append({
                    "kind": "unknown",
                    "dependency": line
                })
        
        return dependencies

    def _extract_change_history(self, text: str) -> List[str]:
        """
        [Function intent]
        Extract change history from the header text.
        
        [Design principles]
        Parses the chronological record of file modifications.
        Maintains the timestamp and description format.
        
        [Implementation details]
        Extracts history entries with their timestamps.
        Preserves the formatted entries for the documentation.
        
        Args:
            text: Header text
            
        Returns:
            List of change history entries
        """
        history_section = self._extract_section(text, "[GenAI tool change history]")
        history = []
        
        for line in history_section.split('\n'):
            line = line.strip()
            if line and ":" in line:
                history.append(line)
        
        return history
    
    def validate_documentation(self, file_path: str) -> Dict[str, Any]:
        """
        [Function intent]
        Validate documentation against HSTC standards.
        
        [Design principles]
        Provides quality checks against established standards.
        Generates actionable feedback for improvements.
        
        [Implementation details]
        Checks for all required HSTC documentation sections.
        Validates both the file header and individual definitions.
        
        Args:
            file_path: Path to the file with documentation to validate
            
        Returns:
            Dict containing validation results
        """
        doc = self.generated_documentation.get(file_path)
        if not doc:
            return {"valid": False, "reason": "No documentation found for this file"}
        
        # Initialize validation results
        validation = {
            "valid": True,
            "issues": [],
            "file_path": file_path
        }
        
        # Check file header required sections
        header = doc.get("file_header", {})
        for section in ["intent", "design_principles", "constraints"]:
            if not header.get(section):
                validation["valid"] = False
                validation["issues"].append(f"Missing or empty {section} section in file header")
        
        # Check individual definitions
        for definition in doc.get("definitions", []):
            updated_comment = definition.get("updated_comment", "")
            name = definition.get("name", "unknown")
            
            # Check required sections
            if "[Function/Class method/Class intent]" not in updated_comment and \
               "[Function intent]" not in updated_comment and \
               "[Class intent]" not in updated_comment and \
               "[Class method intent]" not in updated_comment:
                validation["valid"] = False
                validation["issues"].append(f"Missing intent section in {name} documentation")
                
            if "[Design principles]" not in updated_comment:
                validation["valid"] = False
                validation["issues"].append(f"Missing design principles in {name} documentation")
                
            if "[Implementation details]" not in updated_comment:
                validation["valid"] = False
                validation["issues"].append(f"Missing implementation details in {name} documentation")
        
        return validation
    
    def clear_state(self, file_path: Optional[str] = None) -> None:
        """
        [Function intent]
        Clear stored documentation.
        
        [Design principles]
        Supports selective or complete state reset.
        Prevents memory issues with long-running processes.
        
        [Implementation details]
        Can clear a specific file's documentation or all documentation.
        
        Args:
            file_path: Path to clear documentation for, or None to clear all
        """
        if file_path:
            if file_path in self.generated_documentation:
                del self.generated_documentation[file_path]
        else:
            self.generated_documentation = {}
    
    def get_state_item(self, file_path: str) -> Optional[Dict[str, Any]]:
        """
        [Function intent]
        Get generated documentation for a specific file.
        
        [Design principles]
        Provides clean access to generated documentation.
        Maintains state between processing steps.
        
        [Implementation details]
        Retrieves documentation from agent's internal state.
        Returns None when documentation for the file is not available.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing documentation or None if not available
        """
        return self.generated_documentation.get(file_path)

    def get_all_state(self) -> Dict[str, Dict[str, Any]]:
        """
        [Function intent]
        Get all generated documentation.
        
        [Design principles]
        Provides batch access to all processing results.
        Supports aggregated operations on multiple files.
        
        [Implementation details]
        Returns complete mapping of file paths to documentation data.
        
        Returns:
            Dict mapping file paths to documentation
        """
        return self.generated_documentation
    
    def test_on_file(
        self, 
        file_path: str, 
        file_metadata: Dict[str, Any],
        dependency_metadata: Dict[str, Dict[str, Any]] = None,
        verbose: bool = False
    ) -> bool:
        """
        [Function intent]
        Run a test documentation generation on a file.
        
        [Design principles]
        Provides simplified testing interface.
        Supports debugging with optional verbose output.
        
        [Implementation details]
        Runs complete generation pipeline on a single file.
        Reports key metrics from the documentation process.
        
        Args:
            file_path: Path to the file
            file_metadata: Metadata about the file
            dependency_metadata: Metadata about dependencies
            verbose: Whether to print verbose output
            
        Returns:
            bool: True if generation succeeded, False otherwise
        """
        try:
            if verbose:
                print(f"Testing documentation generator on {file_path}...")
            
            # Use empty dependency metadata if none provided
            if dependency_metadata is None:
                dependency_metadata = {}
            
            # Generate documentation
            doc = self.process_file_documentation(file_path, file_metadata, dependency_metadata)
            
            # Validate documentation
            validation = self.validate_documentation(file_path)
            
            if verbose:
                print(f"Documentation generated: {doc.get('documentation_updated', False)}")
                print(f"Documentation valid: {validation.get('valid', False)}")
                if not validation.get('valid', False):
                    print("Issues:")
                    for issue in validation.get('issues', []):
                        print(f"- {issue}")
            
            return True
        except Exception as e:
            if verbose:
                print(f"Error generating documentation for {file_path}: {e}")
            return False
