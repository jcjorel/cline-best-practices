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
# Implements the HSTCFileProcessor class that generates and updates HSTC.md files
# based on directory contents. Processes source file metadata and child directory
# information to create hierarchical semantic tree context documentation.
###############################################################################
# [Source file design principles]
# - Hierarchical tree analysis with bottom-up processing
# - LLM integration for HSTC generation using Nova models
# - Structured JSON processing for reliable parsing
# - Child directory integration in parent HSTC files
###############################################################################
# [Source file constraints]
# - Must maintain hierarchical consistency in HSTC files
# - Must handle large directory structures efficiently
# - Must extract metadata from various file types
###############################################################################
# [Dependencies]
# codebase:src/dbp/hstc/exceptions.py
# codebase:src/dbp/core/file_access.py
# codebase:src/dbp/llm/bedrock/client_factory.py
# system:pathlib
# system:typing
# system:logging
# system:os
# system:json
# system:re
###############################################################################
# [GenAI tool change history]
# 2025-05-07T12:12:50Z : Implemented full HSTCFileProcessor functionality by CodeAssistant
# * Added file header extraction and child directory processing
# * Implemented LLM integration for HSTC generation
# * Added HSTC file creation and updating logic
# 2025-05-07T11:50:30Z : Initial placeholder implementation of HSTCFileProcessor by CodeAssistant
# * Created placeholder class with interface methods
# * Added basic logging and NotImplementedError responses
###############################################################################

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple, Set

from dbp.core.file_access import DBPFile, get_dbp_file
from dbp.llm.bedrock.client_factory import BedrockClientFactory
from dbp.hstc.exceptions import HSTCProcessingError, LLMError, FileAccessError


class HSTCFileProcessor:
    """
    [Class intent]
    Processes directories to create or update HSTC.md files based on source file
    metadata, providing hierarchical semantic context for the project structure.
    
    [Design principles]
    Uses specialized LLM (Nova) for efficient HSTC.md file generation.
    Maintains hierarchical relationships between HSTC.md files at different levels.
    Provides directory-level operations with preview capabilities.
    
    [Implementation details]
    Extracts metadata from source files in a directory.
    Collects information about child directories with HSTC.md files.
    Creates a prompt with the metadata and hierarchical context.
    Processes responses from LLM to generate HSTC.md content.
    """
    
    def __init__(self, logger=None, llm_model_id: str = "amazon.nova-lite-v1"):
        """
        [Function intent]
        Initializes the HSTCFileProcessor with a logger and LLM model.
        
        [Design principles]
        Configurable LLM model selection with sensible defaults.
        Clear logging configuration for operational visibility.
        
        [Implementation details]
        Sets up logger instance with proper child hierarchy if parent provided.
        Initializes with the specified LLM model ID, defaulting to Nova Lite.
        """
        self.logger = logger or logging.getLogger("dbp.hstc.hstc_processor")
        self.llm_model_id = llm_model_id
        self._llm_client = None
        self._prompt_template = None
    
    def _get_llm_client(self):
        """
        [Function intent]
        Gets or creates an LLM client instance for HSTC.md file processing.
        
        [Design principles]
        Lazy initialization of LLM client for efficient resource usage.
        Clear error handling for LLM client creation failures.
        Dynamic model selection using discovery.
        
        [Implementation details]
        Creates a LangChain client using BedrockClientFactory.
        Uses model discovery to find available models if needed.
        Caches the client for reuse across multiple file processing operations.
        """
        if self._llm_client is None:
            self.logger.debug(f"Creating new LLM client with model {self.llm_model_id}")
            try:
                client_factory = BedrockClientFactory()
                self._llm_client = client_factory.create_langchain_chatbedrock(
                    model_id=self.llm_model_id,
                    streaming=False,
                    logger=self.logger,
                    use_model_discovery=True,
                    preferred_regions=["us-west-2", "us-east-1"],
                    max_retries=3
                )
            except Exception as e:
                error_msg = f"Failed to create LLM client: {str(e)}"
                self.logger.error(error_msg)
                raise LLMError(error_msg, model_id=self.llm_model_id)
                
        return self._llm_client
    
    def _load_prompt_template(self) -> str:
        """
        [Function intent]
        Loads the HSTC update prompt template from the prompt file.
        
        [Design principles]
        External prompt storage for easier maintenance and updates.
        Efficient caching of prompt template for reuse.
        
        [Implementation details]
        Reads the prompt template from the prompts directory.
        Caches the template for reuse across multiple file processing operations.
        """
        if self._prompt_template is None:
            try:
                # Get the module directory
                module_dir = Path(__file__).parent
                prompt_path = module_dir / "prompts" / "hstc_update_prompt.md"
                
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._prompt_template = f.read()
            except Exception as e:
                self.logger.error(f"Failed to load prompt template: {str(e)}")
                # Fallback to a basic prompt template
                self._prompt_template = """
# Hierarchical Semantic Tree Context (HSTC)

You will find below information about a directory and its contents.
Your task is to create or update the HSTC.md file for this directory.

Directory: {directory_name}

## Source Files:
{files_json_data}

## Child Directories:
{child_directories_json_data}

## Existing HSTC.md (if available):
{existing_hstc_content}

You must return a valid JSON object with the structured HSTC content.
"""
                
        return self._prompt_template
    
    def _extract_file_headers(self, directory_path: Path) -> Dict[str, Dict[str, Any]]:
        """
        [Function intent]
        Extracts headers and metadata from source files in a directory.
        
        [Design principles]
        Comprehensive metadata extraction focusing on documentation sections.
        Skip non-source files and files without proper headers.
        
        [Implementation details]
        Reads each source file in the directory and extracts header sections.
        Organizes extracted data by file name for easy access.
        """
        file_headers = {}
        
        # Process each file in the directory
        for item in directory_path.iterdir():
            # Skip directories and HSTC files
            if item.is_dir() or item.name == "HSTC.md" or item.name == "HSTC_REQUIRES_UPDATE.md":
                continue
                
            try:
                # Get the file content
                dbp_file = get_dbp_file(item)
                
                # Skip binary files
                if not dbp_file.mime_type.startswith('text/'):
                    continue
                
                file_content = dbp_file.get_content()
                
                # Extract header sections using regex
                header = {}
                
                # Extract source file intent
                intent_match = re.search(r'\[Source file intent\]\s*\n(.*?)(\n\[|\n###|\Z)', 
                                        file_content, re.DOTALL)
                if intent_match:
                    header['source_file_intent'] = intent_match.group(1).strip()
                
                # Extract source file design principles
                design_match = re.search(r'\[Source file design principles\]\s*\n(.*?)(\n\[|\n###|\Z)', 
                                        file_content, re.DOTALL)
                if design_match:
                    header['source_file_design_principles'] = design_match.group(1).strip()
                
                # Extract source file constraints
                constraints_match = re.search(r'\[Source file constraints\]\s*\n(.*?)(\n\[|\n###|\Z)', 
                                            file_content, re.DOTALL)
                if constraints_match:
                    header['source_file_constraints'] = constraints_match.group(1).strip()
                
                # Extract dependencies
                dependencies = []
                dependencies_section = re.search(r'\[Dependencies\]\s*\n(.*?)(\n\[|\n###|\Z)', 
                                              file_content, re.DOTALL)
                if dependencies_section:
                    dep_lines = dependencies_section.group(1).strip().split('\n')
                    for line in dep_lines:
                        line = line.strip()
                        if line.startswith('#') or not line:
                            continue
                            
                        # Parse dependency kind and path
                        kind = "unknown"
                        dep = line
                        
                        if ":" in line:
                            parts = line.split(":", 1)
                            if parts[0].strip() in ["codebase", "system", "other"]:
                                kind = parts[0].strip()
                                dep = parts[1].strip()
                                
                        dependencies.append({
                            "kind": kind,
                            "dependency": dep
                        })
                
                if dependencies:
                    header['dependencies'] = dependencies
                
                # Extract change history
                history = []
                history_section = re.search(r'\[GenAI tool change history\]\s*\n(.*?)(\n\[|\n###|\Z)', 
                                          file_content, re.DOTALL)
                if history_section:
                    history_content = history_section.group(1).strip()
                    timestamp_pattern = r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)\s*:(.*?)(?=\d{4}-\d{2}-\d{2}T|\Z)'
                    
                    for match in re.finditer(timestamp_pattern, history_content, re.DOTALL):
                        timestamp = match.group(1).strip()
                        content = match.group(2).strip()
                        
                        # Extract summary and details
                        summary = content
                        details = []
                        
                        # Look for bullet points for details
                        lines = content.split('\n')
                        if len(lines) > 0:
                            summary = lines[0].strip()
                            for i in range(1, len(lines)):
                                detail_line = lines[i].strip()
                                if detail_line.startswith('*'):
                                    details.append(detail_line[1:].strip())
                        
                        history.append({
                            "timestamp": timestamp,
                            "summary": summary,
                            "details": details
                        })
                
                if history:
                    header['change_history'] = history
                
                # Only add files with at least one header section
                if header:
                    file_headers[item.name] = header
                    
            except Exception as e:
                self.logger.warning(f"Error extracting headers from {item.name}: {str(e)}")
                
        return file_headers
    
    def _get_child_directories(self, directory_path: Path) -> List[Path]:
        """
        [Function intent]
        Gets child directories that contain HSTC.md files.
        
        [Design principles]
        Hierarchical awareness for accurate parent-child relationships.
        
        [Implementation details]
        Finds immediate child directories with HSTC.md files.
        Returns list of directory paths for further processing.
        """
        child_dirs = []
        
        for item in directory_path.iterdir():
            if item.is_dir():
                hstc_path = item / "HSTC.md"
                if hstc_path.exists():
                    child_dirs.append(item)
                    
        return child_dirs

    def _extract_child_directory_purposes(self, child_dirs: List[Path]) -> Dict[str, str]:
        """
        [Function intent]
        Extracts the Directory Purpose section from child HSTC.md files.
        
        [Design principles]
        Maintains hierarchical relationships between HSTC.md files.
        
        [Implementation details]
        Reads each child HSTC.md file and extracts the Directory Purpose section.
        Returns mapping of directory names to their purpose descriptions.
        """
        child_purposes = {}
        
        for child_dir in child_dirs:
            hstc_path = child_dir / "HSTC.md"
            if hstc_path.exists():
                try:
                    dbp_file = get_dbp_file(hstc_path)
                    content = dbp_file.get_content()
                    
                    # Extract directory purpose section
                    purpose_match = re.search(r'## Directory Purpose\s*\n(.*?)(?=\n##|\Z)', 
                                            content, re.DOTALL)
                    if purpose_match:
                        purpose = purpose_match.group(1).strip()
                        child_purposes[child_dir.name] = purpose
                        
                except Exception as e:
                    self.logger.warning(f"Failed to extract purpose from {hstc_path}: {str(e)}")
                    
        return child_purposes
    
    def _create_hstc_update_prompt(self, directory_path: Path, 
                                 file_headers: Dict[str, Dict[str, Any]], 
                                 child_purposes: Dict[str, str], 
                                 existing_hstc: Optional[str] = None) -> str:
        """
        [Function intent]
        Creates a prompt for the LLM to generate or update an HSTC.md file.
        
        [Design principles]
        Clear instruction for the LLM with comprehensive context.
        JSON output format specification for structured responses.
        
        [Implementation details]
        Loads prompt template and fills in directory-specific values.
        Formats file headers and child directory information as JSON.
        Includes existing HSTC.md content if available.
        """
        # Load the prompt template
        template = self._load_prompt_template()
        
        # Format file headers as JSON
        files_json = json.dumps(file_headers, indent=2)
        
        # Format child directories as JSON
        child_dirs_json = json.dumps(child_purposes, indent=2)
        
        # Fill in the template
        prompt = template.format(
            directory_name=directory_path.name,
            files_json_data=files_json,
            child_directories_json_data=child_dirs_json,
            existing_hstc_content=existing_hstc or "None"
        )
        
        return prompt

    def _parse_llm_response(self, response: str) -> Dict[str, Any]:
        """
        [Function intent]
        Parses the LLM response to extract HSTC content and metadata.
        
        [Design principles]
        Robust JSON parsing with fallback mechanisms.
        Clear validation of expected response structure.
        
        [Implementation details]
        Attempts to parse the response as JSON.
        Falls back to extracting content from code blocks if JSON parsing fails.
        Validates the presence of required fields.
        """
        # Try to parse as JSON directly
        try:
            response_data = json.loads(response)
            
            # Validate required fields
            if "hstc_content" not in response_data:
                raise ValueError("Missing 'hstc_content' field in LLM response")
                
            return response_data
            
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON from the response
            json_match = re.search(r'```json\s*(.*?)\s*```', response, re.DOTALL)
            if json_match:
                try:
                    response_data = json.loads(json_match.group(1))
                    
                    # Validate required fields
                    if "hstc_content" not in response_data:
                        raise ValueError("Missing 'hstc_content' field in extracted JSON")
                        
                    return response_data
                except json.JSONDecodeError:
                    pass
            
            # Return a basic error response if parsing fails
            return {
                "hstc_content": None,
                "status": "error",
                "messages": ["LLM response format was not valid JSON"]
            }
    
    def _generate_hstc_markdown(self, hstc_data: Dict[str, Any]) -> str:
        """
        [Function intent]
        Generates HSTC.md content from parsed LLM response data.
        
        [Design principles]
        Consistent HSTC.md formatting following the template.
        Robust handling of missing or malformed data.
        
        [Implementation details]
        Formats the directory name, purpose, child directories, and files
        into a properly structured markdown document.
        """
        if not hstc_data:
            raise ValueError("Missing HSTC content data")
            
        # Extract required fields
        directory_name = hstc_data.get("directory_name", "Unknown")
        directory_purpose = hstc_data.get("directory_purpose", "No purpose provided")
        child_directories = hstc_data.get("child_directories", [])
        files = hstc_data.get("files", [])
        
        # Build the markdown content
        content = []
        
        # Header section
        content.append(f"# Hierarchical Semantic Tree Context: {directory_name}")
        content.append("")
        
        # Directory purpose section
        content.append("## Directory Purpose")
        content.append(directory_purpose)
        content.append("")
        
        # Child directories section
        if child_directories:
            content.append("## Child Directories")
            content.append("")
            
            for child in child_directories:
                child_name = child.get("name", "Unknown")
                child_purpose = child.get("purpose", "No purpose provided")
                
                content.append(f"### {child_name}")
                content.append(child_purpose)
                content.append("")
        
        # Local files section
        if files:
            content.append("## Local Files")
            content.append("")
            
            for file in files:
                file_name = file.get("name", "Unknown")
                content.append(f"### `{file_name}`")
                content.append("```yaml")
                
                # Add file sections if they exist
                if "source_file_intent" in file:
                    content.append(f"source_file_intent: |")
                    for line in file["source_file_intent"].split('\n'):
                        content.append(f"  {line}")
                    content.append("")
                
                if "source_file_design_principles" in file:
                    content.append(f"source_file_design_principles: |")
                    for line in file["source_file_design_principles"].split('\n'):
                        content.append(f"  {line}")
                    content.append("")
                
                if "source_file_constraints" in file:
                    content.append(f"source_file_constraints: |")
                    for line in file["source_file_constraints"].split('\n'):
                        content.append(f"  {line}")
                    content.append("")
                
                # Add dependencies if they exist
                if "dependencies" in file and file["dependencies"]:
                    content.append(f"dependencies:")
                    for dep in file["dependencies"]:
                        kind = dep.get("kind", "unknown")
                        dependency = dep.get("dependency", "")
                        content.append(f"  - kind: {kind}")
                        content.append(f"    dependency: {dependency}")
                    content.append("")
                
                # Add change history if it exists
                if "change_history" in file and file["change_history"]:
                    content.append(f"change_history:")
                    for history in file["change_history"]:
                        timestamp = history.get("timestamp", "")
                        summary = history.get("summary", "")
                        details = history.get("details", [])
                        content.append(f"  - timestamp: \"{timestamp}\"")
                        content.append(f"    summary: \"{summary}\"")
                        if details:
                            content.append(f"    details: {json.dumps(details)}")
                    content.append("")
                
                content.append("```")
                content.append("")
        
        # Footer note for truncation detection
        content.append("<!-- End of HSTC.md file -->")
        
        return os.linesep.join(content)

    def update_hstc_file(self, directory_path: Union[str, Path], dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates an existing HSTC.md file or creates a new one if it doesn't exist.
        
        [Design principles]
        Atomic file-level operation with preview capability through dry-run mode.
        Thorough validation and error handling to prevent data loss.
        
        [Implementation details]
        Extracts metadata from source files in the directory.
        Collects information about child directories with HSTC.md files.
        Sends the data to an LLM with appropriate prompt.
        Processes the structured JSON response to generate HSTC.md content.
        Updates the file if not in dry-run mode.
        """
        # Convert to Path object
        path_obj = Path(directory_path) if isinstance(directory_path, str) else directory_path
        
        # Log the operation
        self.logger.info(f"Processing HSTC.md for directory: {path_obj} (dry_run={dry_run})")
        
        try:
            # Check if directory exists and is a directory
            if not path_obj.exists() or not path_obj.is_dir():
                message = f"Directory {path_obj} does not exist or is not a directory"
                self.logger.error(message)
                raise HSTCProcessingError(message, directory_path=str(path_obj))
            
            # Extract metadata from source files
            file_headers = self._extract_file_headers(path_obj)
            
            # Get child directories with HSTC.md files
            child_dirs = self._get_child_directories(path_obj)
            child_purposes = self._extract_child_directory_purposes(child_dirs)
            
            # Check for existing HSTC.md
            hstc_path = path_obj / "HSTC.md"
            existing_hstc = None
            
            if hstc_path.exists():
                try:
                    dbp_file = get_dbp_file(hstc_path)
                    existing_hstc = dbp_file.get_content()
                except Exception as e:
                    self.logger.warning(f"Failed to read existing HSTC.md: {str(e)}")
            
            # Create prompt for LLM
            prompt = self._create_hstc_update_prompt(
                path_obj, file_headers, child_purposes, existing_hstc
            )
            
            # Get LLM client
            llm_client = self._get_llm_client()
            
            # Call LLM to generate HSTC content
            self.logger.info(f"Sending directory data to LLM for HSTC generation")
            
            # Format as LangChain message (single user message with the prompt)
            messages = [{"role": "user", "content": prompt}]
            
            # Send to LLM
            try:
                response = llm_client.invoke(messages)
                response_text = response.content
            except Exception as e:
                error_msg = f"LLM processing failed: {str(e)}"
                self.logger.error(error_msg)
                raise LLMError(error_msg, model_id=self.llm_model_id)
            
            # Parse LLM response
            parsed_response = self._parse_llm_response(response_text)
            
            # Generate markdown content
            hstc_content = self._generate_hstc_markdown(parsed_response["hstc_content"])
            
            # Check if content actually changed (if updating existing file)
            if existing_hstc and hstc_content == existing_hstc:
                return {
                    "status": "unchanged",
                    "message": f"No changes needed for HSTC.md in {path_obj}",
                    "directory_path": str(path_obj),
                    "dry_run": dry_run
                }
            
            # In dry-run mode, just return the content
            if dry_run:
                return {
                    "status": "preview",
                    "message": f"Preview of HSTC.md for {path_obj}",
                    "directory_path": str(path_obj),
                    "content": hstc_content,
                    "dry_run": True
                }
            
            # Write to file
            try:
                with open(hstc_path, 'w', encoding='utf-8') as f:
                    f.write(hstc_content)
                    
                # Remove HSTC_REQUIRES_UPDATE.md if it exists
                update_marker = path_obj / "HSTC_REQUIRES_UPDATE.md"
                if update_marker.exists():
                    update_marker.unlink()
                    
                return {
                    "status": "updated",
                    "message": f"Successfully updated HSTC.md for {path_obj}",
                    "directory_path": str(path_obj),
                    "dry_run": False
                }
            except Exception as e:
                error_msg = f"Failed to write HSTC.md file: {str(e)}"
                self.logger.error(error_msg)
                raise HSTCProcessingError(error_msg, directory_path=str(path_obj))
                
        except Exception as e:
            if isinstance(e, (HSTCProcessingError, LLMError)):
                # Re-raise known exceptions
                raise e
            else:
                # Wrap other exceptions
                error_msg = f"Error processing HSTC for directory {path_obj}: {str(e)}"
                self.logger.error(error_msg)
                raise HSTCProcessingError(error_msg, directory_path=str(path_obj))

    def create_hstc_file(self, directory_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Creates a new HSTC.md file for a directory that doesn't have one.
        
        [Design principles]
        Comprehensive analysis of directory contents.
        Standard HSTC file structure creation.
        
        [Implementation details]
        Delegates to update_hstc_file since the logic is the same.
        Ensures HSTC.md doesn't exist before creating.
        
        Args:
            directory_path: Path to the directory for which to create an HSTC.md file
            dry_run: If True, return the file content without creating the file
            
        Returns:
            dict: Results of the creation operation including the generated content
            
        Raises:
            HSTCProcessingError: On HSTC file generation failures
            LLMError: On LLM-related failures
        """
        # Check if HSTC.md already exists
        hstc_path = Path(directory_path) / "HSTC.md"
        if hstc_path.exists():
            return {
                "status": "error",
                "message": f"HSTC.md already exists in {directory_path}",
                "directory_path": str(directory_path),
                "dry_run": dry_run
            }
            
        # Delegate to update_hstc_file since the logic is the same
        return self.update_hstc_file(directory_path, dry_run)
