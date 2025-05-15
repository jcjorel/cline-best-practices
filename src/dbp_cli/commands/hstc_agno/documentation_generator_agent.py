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
# This file implements the DocumentationGeneratorAgent for HSTC processing using the Agno framework.
# The agent processes file metadata to generate high-quality documentation using Claude 3 models
# that meets the project's HSTC documentation standards.
###############################################################################
# [Source file design principles]
# - High-quality documentation generation with Claude models
# - Structured prompting for consistent documentation output
# - Comprehensive validation of generated documentation
# - Multi-stage processing for complex documentation needs
###############################################################################
# [Source file constraints]
# - Must work with the Agno agent framework
# - Should use Claude models for optimal documentation quality
# - Must adhere strictly to documentation format standards
###############################################################################
# [Dependencies]
# system:typing
# system:pathlib
# system:json
# system:os
# system:agno.models.anthropic
# system:agno.tools.reasoning
# codebase:src/dbp_cli/commands/hstc_agno/abstract_agent.py
# codebase:src/dbp_cli/commands/hstc_agno/models.py
# codebase:src/dbp_cli/commands/hstc_agno/utils.py
###############################################################################
# [GenAI tool change history]
# 2025-05-15T14:05:00Z : Split from agents.py by CodeAssistant
# * Extracted DocumentationGeneratorAgent into dedicated file
# * Updated imports and dependencies
# * Maintained all functionality from original file
###############################################################################

import json
import os
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

from agno.models.anthropic import Claude
from agno.tools.reasoning import ReasoningTools

from .abstract_agent import AbstractAgnoAgent
from .models import (
    HeaderDocumentation,
    DefinitionDocumentation,
    Documentation,
    ValidationResult
)
from .utils import get_current_timestamp


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
