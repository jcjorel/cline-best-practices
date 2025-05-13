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
# codebase:src/dbp/api_providers/aws/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
###############################################################################
# [GenAI tool change history]
# 2025-05-13T10:59:00Z : Added model discovery for optimal region selection by CodeAssistant
# * Integrated BedrockModelDiscovery for finding best regions for each model
# * Used get_best_regions_for_model to automatically select optimal region
# 2025-05-13T10:54:00Z : Fixed AWS credentials issue by CodeAssistant
# * Added integration with AWS client factory for proper AWS credentials
# * Used session from AWS client factory for AwsBedrock model
# 2025-05-12T07:07:30Z : Initial implementation by CodeAssistant
# * Created agent class skeletons
# * Added basic model initialization
###############################################################################

import json
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from agno.agent import Agent
from agno.models.aws.bedrock import AwsBedrock
from agno.models.anthropic import Claude
from agno.tools.file import FileTools
from dbp.api_providers.aws.client_factory import AWSClientFactory
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities as BedrockModelDiscovery

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
    get_language_by_extension,
    get_default_comment_format,
    read_file_content,
    is_binary_file
)


class FileAnalyzerAgent(Agent):
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
            
        super().__init__(model=model, **kwargs)
        self.file_tools = file_tools
        
        # Initialize state for storing analysis results
        self.file_metadata = {}
    
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
    
    def _process_run_response(self, response_obj: Any) -> str:
        """
        [Function intent]
        Process a response from the Agno run method to extract text content.
        
        [Design principles]
        Provides consistent handling of response objects across methods.
        Handles different types of response objects gracefully.
        
        [Implementation details]
        Attempts various methods to extract text from the response object.
        Falls back to string conversion if specific attributes aren't available.
        
        Args:
            response_obj: Response object from self.run()
            
        Returns:
            str: Extracted text content from the response
        """
        # Try using to_json() method if available
        if hasattr(response_obj, 'to_json'):
            try:
                return json.dumps(response_obj.to_json())
            except (TypeError, AttributeError):
                pass
                
        # Try getting string representation for JSON parsing
        if hasattr(response_obj, 'content'):
            return response_obj.content
        elif hasattr(response_obj, 'text'):
            return response_obj.text
        elif isinstance(response_obj, str):
            return response_obj
        else:
            # Fallback to string conversion
            return str(response_obj)
    
    def analyze_file_type(self, file_content: str) -> Dict[str, Any]:
        """
        [Function intent]
        Analyze content to determine file type.
        
        [Design principles]
        Uses lightweight text analysis to categorize file content.
        Maps content patterns to standard file type categories.
        
        [Implementation details]
        Samples the beginning of the file for classification.
        Uses LLM to identify patterns in file content.
        
        Args:
            file_content: Content of the file to analyze
            
        Returns:
            Dict containing file type information
        """
        # Simple content-based detection for common file types
        # This provides a fallback in case the LLM response parsing fails
        default_type = {"file_type": "unknown", "is_binary": False}
        
        if not file_content:
            return default_type
            
        # Check for common file signatures
        if file_content.startswith("<?xml"):
            return {"file_type": "xml", "is_binary": False}
        elif file_content.startswith("<!DOCTYPE html") or "<html" in file_content[:100]:
            return {"file_type": "html", "is_binary": False}
        elif file_content.startswith("{") and "}" in file_content:
            return {"file_type": "json", "is_binary": False}
        elif file_content.startswith("---") or file_content.startswith("#"):
            return {"file_type": "markdown", "is_binary": False}
        elif any(keyword in file_content[:1000] for keyword in ["def ", "class ", "import ", "from ", "public ", "void ", "function"]):
            return {"file_type": "source_code", "is_binary": False}
            
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
        
        try:
            response_obj = self.run(prompt)
            
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            if not response_text:
                return default_type
                
            # Look for JSON content - sometimes the LLM includes extra text
            if '{' in response_text and '}' in response_text:
                json_start = response_text.find('{')
                json_end = response_text.rfind('}') + 1
                json_content = response_text[json_start:json_end]
                try:
                    result = json.loads(json_content)
                    # Verify the required keys exist
                    if "file_type" not in result:
                        result["file_type"] = "unknown"
                    if "is_binary" not in result:
                        result["is_binary"] = False
                    return result
                except json.JSONDecodeError:
                    pass
                    
            # Try parsing the whole response as JSON
            try:
                result = json.loads(response_text)
                # Verify the required keys exist
                if "file_type" in result and isinstance(result, dict):
                    if "is_binary" not in result:
                        result["is_binary"] = False
                    return result
            except json.JSONDecodeError:
                pass
                
            # If we reach here, JSON parsing failed
            return default_type
                
        except Exception as e:
            # Handle all exceptions gracefully
            print(f"Error in analyze_file_type: {e}")
            return default_type
    
    def detect_language(self, file_content: str, file_path: str) -> Dict[str, Any]:
        """
        [Function intent]
        Determine the programming language with confidence score.
        
        [Design principles]
        Prioritizes extension-based detection for accuracy.
        Falls back to content analysis when extension is unknown.
        
        [Implementation details]
        Combines file extension analysis with content inspection.
        Produces confidence scores to indicate detection reliability.
        
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
        
        response_obj = self.run(prompt)
        try:
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            
            # Parse the response text as JSON
            return json.loads(response_text)
            
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            # Handle the error gracefully
            print(f"Error parsing language detection response: {e}")
            return {"language": "unknown", "confidence": 0, "file_extension": ""}
    
    def identify_comment_formats(self, language: str) -> Dict[str, Any]:
        """
        [Function intent]
        Identify comment formats for the detected language.
        
        [Design principles]
        Uses pre-defined formats for common languages.
        Falls back to LLM analysis for uncommon languages.
        
        [Implementation details]
        Retrieves comment syntax from a predefined database.
        Dynamically generates syntax information for unknown languages.
        
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
        
        response_obj = self.run(prompt)
        try:
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            
            # Parse the response text as JSON
            return json.loads(response_text)
            
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            # Handle the error gracefully
            print(f"Error parsing comment format response: {e}")
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
        [Function intent]
        Extract header comment from file content.
        
        [Design principles]
        Prioritizes simple pattern matching for efficiency.
        Falls back to intelligent extraction for complex formats.
        
        [Implementation details]
        Detects block comments at file start for simple extraction.
        Uses LLM for complex or ambiguous comment formats.
        
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
        
        response = self.run(prompt)
        return response.strip() if response.strip() else None
    
    def extract_dependencies(self, file_content: str, language: str) -> Dict[str, Any]:
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
        
        response_obj = self.run(prompt)
        try:
            # Process the response object to extract text
            response_text = self._process_run_response(response_obj)
            
            # Parse the response text as JSON
            return json.loads(response_text)
            
        except (json.JSONDecodeError, TypeError, AttributeError) as e:
            # Handle the error gracefully
            print(f"Error parsing dependency extraction response: {e}")
            return {"dependencies": []}
    
    def extract_function_comments(self, file_content: str, language: str, comment_formats: Dict[str, Any]) -> Dict[str, Any]:
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
        
        # For large files, analyze in smaller chunks to stay within token limits
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
                
                response_obj = self.run(chunk_prompt)
                try:
                    # Process the response object to extract text
                    response_text = self._process_run_response(response_obj)
                    
                    # Parse the response text as JSON
                    chunk_result = json.loads(response_text)
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
            
            response = self.run(prompt)
            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {"definitions": []}
    
    def get_file_metadata(self, file_path: str) -> Optional[Dict[str, Any]]:
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

    def get_all_metadata(self) -> Dict[str, Dict[str, Any]]:
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

    def clear_metadata(self, file_path: Optional[str] = None) -> None:
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


class DocumentationGeneratorAgent(Agent):
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
    
    def __init__(self, model_id: str = "claude-3-5-sonnet-20241022", **kwargs):
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
        from agno.tools.reasoning import ReasoningTools
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
            
        super().__init__(model=model, **kwargs)
        
        # Initialize state for storage
        self.generated_documentation = {}
        
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
    
    def get_generated_documentation(self, file_path: str) -> Optional[Dict[str, Any]]:
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

    def get_all_documentation(self) -> Dict[str, Dict[str, Any]]:
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

    def clear_documentation(self, file_path: Optional[str] = None) -> None:
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
