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
# Implements the SourceCodeProcessor class that processes source code files to update
# their documentation according to project standards. Uses LLM capabilities to analyze
# existing code and enhance documentation while preserving functionality.
###############################################################################
# [Source file design principles]
# - Specialized handling based on file type (.py, .js, etc.)
# - LLM integration for documentation generation using Claude models
# - Non-destructive updates that preserve code functionality
# - Structured response parsing with robust error handling
###############################################################################
# [Source file constraints]
# - Must handle various source file formats and encodings
# - Must properly detect what files can be processed
# - Must provide detailed feedback on changes made
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
# 2025-05-07T17:35:33Z : Fixed documentation directives substitution in prompt template by CodeAssistant
# * Updated _create_source_update_prompt to correctly handle code documentation directives
# * Modified template parameter passing to use direct format() method
# * Fixed error "'mandatory_code_documentation_directives' is not defined"
# * Enhanced function documentation for template generation
# 2025-05-07T16:28:29Z : Enhanced MIME message encoding and added debugging output by CodeAssistant
# * Changed to use EmailMessage instead of MIMEMultipart for better encoding control
# * Prevented base64 encoding for text files to improve LLM understanding
# * Added proper file extension to attachment filename for better content recognition
# * Added detailed MIME message debugging output to stderr
# 2025-05-07T16:15:21Z : Added json-repair library for robust JSON handling by CodeAssistant
# * Integrated json-repair package for handling malformed JSON responses
# * Updated model parameters for more reliable JSON output (temperature 0.1)
# * Added enhanced error handling with multiple fallback strategies
# 2025-05-07T15:17:42Z : Reimplemented source processor with enhanced JSON parsing by CodeAssistant
# * Implemented robust JSON error handling for malformed LLM responses
# * Added special handling for responses starting with "changes" field
# * Implemented context-based replacement for precise code updates
# * Added detailed logging throughout the process for better diagnostics
###############################################################################

import os
import re
import json
import logging
import mimetypes
import sys
from pathlib import Path
from typing import Dict, Any, Optional, Union, List, Tuple
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from email.message import EmailMessage

from json_repair import repair_json

from dbp.core.file_access import DBPFile, get_dbp_file
from dbp.llm.bedrock.client_factory import BedrockClientFactory
from dbp.hstc.exceptions import SourceProcessingError, LLMError, FileAccessError

# Register the markdown MIME type if not already registered
mimetypes.add_type('text/markdown', '.md')


class SourceCodeProcessor:
    """
    [Class intent]
    Processes source code files to ensure they comply with documentation standards
    using LLM for analysis and enhancement of code comments.
    
    [Design principles]
    Uses specialized LLM (Claude) to understand and enhance source code documentation.
    Provides atomic file-level operations with preview capabilities.
    Handles various programming languages with appropriate processing.
    
    [Implementation details]
    Uses DBPFile for efficient file access with encoding detection.
    Creates LLM prompts with documentation standards and file content.
    Processes JSON responses from LLM to extract updated file content.
    """
    
    def __init__(self, llm_model_id: str = "anthropic.claude-3-7-sonnet-20250219-v1:0", logger=None):
        """
        [Function intent]
        Initializes the source code processor with configuration and LLM client.
        
        [Design principles]
        Clear configuration of LLM model preferences.
        Extensible processing strategies with sensible defaults.
        
        [Implementation details]
        Sets up logger, LLM model ID, and placeholder for client.
        Initializes extension mappings for processable files.
        
        Args:
            logger: Optional logger instance to use (creates child logger if provided)
            llm_model_id: Model ID to use for LLM operations
        """
        self.logger = logger or logging.getLogger("dbp.hstc.source_processor")
        self.llm_model_id = llm_model_id
        self._llm_client = None
        self._prompt_template = None
        
        # Define processable file extensions
        self._processable_extensions = {
            # Python
            '.py': 'python',
            # JavaScript
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            # Java/Kotlin
            '.java': 'java',
            '.kt': 'kotlin',
            # C-family
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c',
            '.hpp': 'cpp',
            # Others
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.cs': 'csharp',
            '.swift': 'swift',
            '.rs': 'rust',
        }

    def update_source_file(self, file_path: Path, dry_run: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Updates a source file's documentation according to project standards.
        
        [Design principles]
        Non-destructive update approach with clear reporting.
        Specialized processing based on file type.
        Option for dry-run to preview changes.
        
        [Implementation details]
        Checks if file is processable based on extension.
        Loads and processes the file content with appropriate encoding.
        Uses LLM to generate improved documentation.
        Optionally writes updated content back to the file.
        Creates HSTC_REQUIRES_UPDATE.md marker in the parent directory.
        
        Args:
            file_path: Path to the source file to update
            dry_run: If True, return changes without applying them
            
        Returns:
            dict: Results of the update operation including changes made
            
        Raises:
            SourceProcessingError: On source file processing failures
            LLMError: On LLM-related failures
            FileAccessError: On file access issues
        """
        try:
            # Convert to Path object if string
            if isinstance(file_path, str):
                file_path = Path(file_path)
                
            self.logger.info(f"Source file update requested for: {file_path} (dry_run: {dry_run})")
            
            # Check if file is processable
            if not self._is_processable_file(file_path):
                self.logger.warning(f"File {file_path} is not a processable source file")
                return {
                    "status": "warning",
                    "file_path": str(file_path),
                    "message": f"File is not a processable source file",
                    "changes_made": False,
                    "dry_run": dry_run
                }
            
            # Read the file with encoding detection
            try:
                file = get_dbp_file(file_path)
                file_content = file.get_content()
                # DBPFile doesn't expose encoding directly, but get_content() handles encoding detection
            except Exception as e:
                raise FileAccessError(f"Failed to read file {file_path}: {str(e)}")
                
            # Get file extension and create prompt
            file_ext = file_path.suffix.lower()
            language = self._processable_extensions.get(file_ext, "text")
            
            # Load prompt template if not already loaded
            if not self._prompt_template:
                self._prompt_template = self._load_prompt_template()
            
            # Create prompt with file content
            self.logger.info(f"Creating prompt for {file_path}")
            prompt = self._create_source_update_prompt(
                file_content=file_content,
                file_path=str(file_path),
                file_ext=language
            )
            
            # Get LLM client and generate completion
            self.logger.info(f"Getting LLM client for model {self.llm_model_id}")
            llm_client = self._get_llm_client()
            
            try:
                # _create_source_update_prompt now returns the correctly formatted message
                # so we can use it directly as the message for the LLM
                messages = [prompt]
                
                # Force streaming to get better error handling
                self.logger.info(f"Invoking LLM with streaming enabled")
                
                # Initialize response variables
                full_response_content = ""
                chunks_received = 0
                
                # Direct console output for debugging
                import sys
                print(f"[SOURCE_PROCESSOR:STREAMING] Starting LLM streaming, will print chunks as they arrive", file=sys.stderr)
                sys.stderr.flush()
                
                # Start streaming
                for chunk in llm_client.stream_text(messages):
                    # Accumulate the response content
                    full_response_content += chunk
                    chunks_received += 1
                    
                    # Print each chunk as it arrives
                    print(chunk, file=sys.stderr, end="")
                    sys.stderr.flush()
                
                print(f"[SOURCE_PROCESSOR:STREAMING] Streaming complete, received {chunks_received} chunks", file=sys.stderr)
                sys.stderr.flush()
                
                # Dump raw response for debugging (only in debug mode)
                if self.logger.isEnabledFor(logging.DEBUG):
                    self.logger.debug(f"Raw LLM response: {full_response_content[:500]}...")
                
                # Parse the response
                self.logger.info(f"Parsing LLM response after receiving {chunks_received} chunks")
                result = self._parse_llm_response(full_response_content)
                self.logger.info(f"Response parsed successfully")
                
            except Exception as e:
                self.logger.error(f"Failed to process file with LLM: {str(e)}")
                raise LLMError(f"Failed to process file with LLM: {str(e)}", model_id=self.llm_model_id)
                
            # Extract changes and metadata
            changes = result.get("changes", [])
            changes_summary = result.get("changes_summary", {})
            status = result.get("status", "error")
            messages = result.get("messages", [])
            
            # Apply changes to generate updated content
            updated_source_code = self._apply_changes(file_content, changes)
            
            # Check if any changes were made
            changes_made = updated_source_code != file_content and len(changes) > 0
            
            # Apply changes if not dry run and changes were made
            if not dry_run and changes_made:
                try:
                    # Write updated content to source file
                    file.write(updated_source_code)
                    
                    # Create HSTC_REQUIRES_UPDATE.md in parent directory
                    parent_dir = file_path.parent
                    update_marker = parent_dir / "HSTC_REQUIRES_UPDATE.md"
                    
                    if not update_marker.exists():
                        with open(update_marker, "w") as f:
                            f.write(f"{file_path.name}\n")
                    else:
                        # Append to existing file if it doesn't contain this filename
                        with open(update_marker, "r+") as f:
                            content = f.read()
                            if file_path.name not in content.split("\n"):
                                f.seek(0, 2)  # Go to end of file
                                f.write(f"{file_path.name}\n")
                    
                    self.logger.info(f"Updated source file and created/updated marker file")
                except Exception as e:
                    raise FileAccessError(f"Failed to write updated content to {file_path}: {str(e)}")
                    
            # Create result object
            result = {
                "status": status,
                "file_path": str(file_path),
                "changes_made": changes_made,
                "changes_summary": changes_summary,
                "messages": messages,
                "dry_run": dry_run,
            }
            
            # Always include updated content in dry run mode
            if dry_run:
                result["updated_content"] = updated_source_code
                
            return result
            
        except (SourceProcessingError, LLMError, FileAccessError) as e:
            # Re-raise known exceptions
            raise
        except Exception as e:
            # Wrap unknown exceptions
            self.logger.error(f"Unexpected error processing {file_path}: {str(e)}")
            raise SourceProcessingError(f"Failed to process source file {file_path}: {str(e)}")
            
    def _get_llm_client(self):
        """
        [Function intent]
        Creates or retrieves a cached LLM client for source code processing.
        
        [Design principles]
        Lazy initialization of expensive resources.
        Consistent client configuration.
        Enhanced parameters for reliable JSON output.
        
        [Implementation details]
        Uses BedrockClientFactory to create a client with the specified model ID.
        Caches the client for reuse across multiple file processing operations.
        Configures model parameters for reliable JSON formatting.
        
        Returns:
            object: LLM client for generating completions
            
        Raises:
            LLMError: If client creation fails
        """
        if not self._llm_client:
            try:
                client_factory = BedrockClientFactory()
                
                # Enhanced model parameters for reliable JSON output
                model_kwargs = {
                    "response_format": {"type": "json_object"},
                    "temperature": 0.1,    # Lower temperature for more deterministic outputs
                    "top_p": 0.95,         # Slightly reduce top_p for more focused responses
                    "max_tokens": 64000    # Ensure enough tokens for complete responses
                }
                
                self._llm_client = client_factory.create_langchain_chatbedrock(
                    model_id=self.llm_model_id,
                    streaming=True,  # Always use streaming for better error handling
                    model_kwargs=model_kwargs,
                    logger=self.logger,
                    use_model_discovery=True,
                    max_retries=3
                )
                
            except Exception as e:
                raise LLMError(f"Failed to initialize LLM client: {str(e)}", model_id=self.llm_model_id)
                
        return self._llm_client
            
    def _load_prompt_template(self) -> str:
        """
        [Function intent]
        Loads the prompt template for source file documentation updates.
        
        [Design principles]
        Centralized prompt management.
        Clear error handling for missing templates.
        
        [Implementation details]
        Loads the template from the prompts directory.
        
        Returns:
            str: Prompt template content
            
        Raises:
            FileAccessError: If template file cannot be loaded
        """
        try:
            prompt_path = Path(__file__).parent / "prompts" / "source_update_prompt.md"
            with open(prompt_path, "r") as f:
                return f.read()
        except Exception as e:
            raise FileAccessError(f"Failed to load source update prompt template: {str(e)}")
            
    def _create_source_update_prompt(self, file_content: str, file_path: str, file_ext: str) -> Union[str, Dict[str, Any]]:
        """
        [Function intent]
        Creates a prompt for the LLM to update source file documentation using MIME encoding for file content.
        
        [Design principles]
        Clear instructions for LLM.
        Consistent output format for reliable parsing.
        Direct text encoding (not base64) for source code to improve LLM understanding.
        
        [Implementation details]
        Loads mandatory code documentation directives and substitutes them in the prompt template.
        Creates a message with EmailMessage with the prompt text and file content as an attachment,
        using appropriate MIME types and avoiding base64 encoding for text files to improve
        LLM's ability to process the code content.
        
        Args:
            file_content: Content of the source file to update
            file_path: Path to the source file for context
            file_ext: File extension/language for syntax highlighting
            
        Returns:
            Dict[str, Any]: Message content for the LLM API with properly encoded file
            
        Raises:
            FileAccessError: If mandatory documentation directives cannot be loaded
        """
        # Load the mandatory code documentation directives
        directives_path = Path(__file__).parent / "prompts" / "mandatory_code_documentation_directives.md"
        try:
            with open(directives_path, "r") as f:
                directives_content = f.read()
        except Exception as e:
            raise FileAccessError(f"Failed to load mandatory documentation directives from {directives_path}: {str(e)}")
        
        # Format the prompt template with file path and directives in a single call
        prompt_text = self._prompt_template.format(
            file_path=file_path,
            mandatory_code_documentation_directives=directives_content
        )
        
        # Create a message with EmailMessage (which has better control over encoding)
        from email.message import EmailMessage
        
        # Create the message
        msg = EmailMessage()
        msg['Subject'] = f"Request for Source Code Documentation Update: {os.path.basename(file_path)}"
        msg['From'] = 'source-processor@dbp.local'
        msg['To'] = 'llm-assistant@dbp.local'
        
        # Add the prompt text as the main content
        msg.set_content("""Hi Mr coding assistant, 
            I need your expertise to process the below request.
            Please follow very precisely the directives.
            Best.
            
            """ + prompt_text)
        
        # Determine content type based on file extension
        mime_type = None
        if file_ext in self._processable_extensions:
            lang = self._processable_extensions[file_ext]
            mime_type = f"text/{lang}"
        
        # Default to text/plain if no specific type
        if not mime_type:
            mime_type = "text/plain"
            
        # Split mime type into main/sub types
        maintype, subtype = mime_type.split('/', 1)
        
        # Add attachment using add_attachment method to avoid base64 encoding for text
        if maintype == 'text':
            msg.add_attachment(
                file_content,
                subtype=subtype,
                filename=f"source_file{file_ext}",
                disposition='attachment',
                charset='utf-8'
            )
        else:
            # Only encode as bytes for non-text types
            msg.add_attachment(
                file_content.encode('utf-8'),
                maintype=maintype,
                subtype=subtype,
                filename=f"source_file{file_ext}",
                disposition='attachment'
            )
        
        # Print full message for debugging purposes
        print(f"=== LLM PROMPT MESSAGE START ===\n{msg.as_string()}\n=== LLM PROMPT MESSAGE END ===", file=sys.stderr)
        sys.stderr.flush()
        
        # For LangChain API, return a properly formatted message
        return {
            "role": "user",
            "content": [
                {
                    "type": "text", 
                    "text": msg.as_string()
                }
            ]
        }
            
    def _apply_changes(self, original_content: str, changes: List[Dict[str, Any]]) -> str:
        """
        [Function intent]
        Applies a series of text changes to the original content.
        
        [Design principles]
        Non-destructive transformation with precise positioning.
        Robust error handling for missing context.
        
        [Implementation details]
        Uses context_before to find positions for changes.
        Applies changes one by one in reverse order to avoid position shifts.
        
        Args:
            original_content: The original source file content
            changes: List of change objects with context_before, original_text, and replacement_text
            
        Returns:
            str: The modified content with all changes applied
            
        Raises:
            SourceProcessingError: On invalid change specification
        """
        if not changes:
            return original_content
            
        # Work with a copy of the original content
        modified_content = original_content
        
        # Track positions for all changes first
        change_positions = []
        for i, change in enumerate(changes):
            context = change.get('context_before', '')
            original = change.get('original_text', '')
            replacement = change.get('replacement_text', '')
            
            # Skip invalid changes
            if not context and not original:
                self.logger.warning(f"Change #{i} has neither context_before nor original_text, skipping")
                continue
                
            # Special handling for start of file marker
            if context == "<<SOF>>":
                self.logger.info(f"Found start of file marker for change #{i}")
                start_pos = 0
                change_positions.append({
                    'index': i,
                    'start_pos': start_pos,
                    'context': '',  # Empty context since we're at the start of the file
                    'original': original,
                    'replacement': replacement
                })
                continue
                
            # Find position based on context
            search_pattern = context + original
            pos = modified_content.find(search_pattern)
            if pos >= 0:
                # Found an exact match
                start_pos = pos + len(context)  # Position after context_before
                self.logger.info(f"Found match for change #{i} at position {start_pos}")
                change_positions.append({
                    'index': i,
                    'start_pos': start_pos,
                    'context': context,
                    'original': original,
                    'replacement': replacement
                })
            else:
                # Try some fallback approaches
                
                # Try finding just the context
                context_pos = modified_content.find(context)
                if context_pos >= 0:
                    start_pos = context_pos + len(context)
                    self.logger.warning(f"Found context only at position {context_pos}, using position {start_pos}")
                    change_positions.append({
                        'index': i,
                        'start_pos': start_pos,
                        'context': context,
                        'original': original,
                        'replacement': replacement
                    })
                elif original:
                    # Try finding just the original text
                    original_pos = modified_content.find(original)
                    if original_pos >= 0:
                        self.logger.warning(f"Found original text only at position {original_pos}, using that position")
                        change_positions.append({
                            'index': i,
                            'start_pos': original_pos,
                            'context': context,
                            'original': original,
                            'replacement': replacement
                        })
                    else:
                        self.logger.error(f"Could not find position for change #{i}, skipping")
                else:
                    self.logger.error(f"Could not find context for change #{i}, skipping")
                
        # Sort positions in reverse order to avoid position shifts
        change_positions.sort(key=lambda x: x['start_pos'], reverse=True)
        
        # Apply changes in reverse order
        for change_info in change_positions:
            start_pos = change_info['start_pos']
            original = change_info['original']
            replacement = change_info['replacement']
            
            # Verify the text at the position matches what we expect
            if original and modified_content[start_pos:start_pos + len(original)] != original:
                actual_text = modified_content[start_pos:start_pos + len(original)]
                self.logger.warning(f"Text mismatch at position {start_pos}")
                self.logger.warning(f"Expected: '{original[:50]}{'...' if len(original) > 50 else ''}'")
                self.logger.warning(f"Actual:   '{actual_text[:50]}{'...' if len(actual_text) > 50 else ''}'")
                self.logger.warning("Skipping this change to avoid corruption")
                continue
                
            # Apply the change
            if original:  # Replacement
                modified_content = modified_content[:start_pos] + replacement + modified_content[start_pos + len(original):]
            else:  # Insertion at the end of context
                modified_content = modified_content[:start_pos] + replacement + modified_content[start_pos:]
                
        return modified_content
    
    def _parse_llm_response(self, content: str) -> Dict[str, Any]:
        """
        [Function intent]
        Processes the LLM response to extract changes and metadata.
        
        [Design principles]
        Robust parsing of LLM response.
        Clear error handling for malformed responses.
        Fallback mechanisms for partial successes.
        
        [Implementation details]
        Parses JSON response from LLM.
        Extracts changes list and metadata.
        Provides fallbacks for common response issues.
        
        Args:
            content: Raw response content from LLM
            
        Returns:
            dict: Processed response with changes and metadata
            
        Raises:
            LLMError: On response parsing failures
        """
        try:
            # Initialize result with default values
            result = {
                "changes": [],
                "changes_summary": {
                    "file_header_updated": False,
                    "functions_updated": 0,
                    "classes_updated": 0,
                    "methods_updated": 0
                },
                "status": "error",
                "messages": ["Failed to parse LLM response"]
            }
            
            # Try to parse the raw content as JSON
            try:
                # Clean up the content for parsing
                cleaned_content = content.strip()
                
                # Remove markdown code block delimiters if present
                if cleaned_content.startswith("```json"):
                    cleaned_content = re.sub(r"^```json\n", "", cleaned_content)
                    cleaned_content = re.sub(r"\n```$", "", cleaned_content)
                elif cleaned_content.startswith("```"):
                    cleaned_content = re.sub(r"^```\n", "", cleaned_content)
                    cleaned_content = re.sub(r"\n```$", "", cleaned_content)
                
                # Basic invalid JSON repair using json-repair library
                try:
                    self.logger.info("Attempting to repair JSON with json-repair")
                    repaired_content = repair_json(cleaned_content)
                    result = json.loads(repaired_content)
                    self.logger.info("Successfully repaired and parsed JSON response")
                except Exception as repair_error:
                    self.logger.warning(f"JSON repair failed: {str(repair_error)}")
                    # Attempt standard JSON loading as a fallback
                    result = json.loads(cleaned_content)
                
            except json.JSONDecodeError as e:
                self.logger.warning(f"Initial JSON parsing failed: {str(e)}")
                
                # Try to extract JSON from markdown code blocks
                json_match = re.search(r'```(?:json)?\n(.*?)\n```', content, re.DOTALL)
                if json_match:
                    try:
                        json_content = json_match.group(1).strip()
                        self.logger.info(f"Found JSON code block, attempting to parse")
                        result = json.loads(json_content)
                    except json.JSONDecodeError as e2:
                        self.logger.warning(f"JSON code block parsing failed: {str(e2)}")
                        
                        # Try more aggressive cleanup - look for JSON-like structure
                        try:
                            json_pattern = r'({[\s\S]*})'
                            match = re.search(json_pattern, content)
                            if match:
                                potential_json = match.group(1).strip()
                                self.logger.info(f"Found potential JSON structure, attempting to parse")
                                result = json.loads(potential_json)
                            else:
                                raise Exception("No JSON-like structure found")
                        except Exception:
                            # If all attempts fail, use default result
                            self.logger.warning("All JSON parsing attempts failed")
                
            # Validate required fields
            if "changes" not in result:
                self.logger.warning("LLM response missing changes field")
                result["changes"] = []
                result["status"] = "error"
                result["messages"] = ["LLM response missing changes field"]
                
            if "changes_summary" not in result:
                self.logger.warning("LLM response missing changes_summary field")
                result["changes_summary"] = {
                    "file_header_updated": False,
                    "functions_updated": 0,
                    "classes_updated": 0,
                    "methods_updated": 0
                }
                
            if "status" not in result:
                result["status"] = "warning" if result.get("changes") else "error"
                
            # Always ensure we have a messages array
            if "messages" not in result:
                result["messages"] = []
            
            # Return the parsed or default result
            return result
                
        except Exception as e:
            # Wrap parsing exceptions
            self.logger.error(f"Failed to parse LLM response: {str(e)}")
            raise LLMError(f"Failed to parse LLM response: {str(e)}", model_id=self.llm_model_id)
            
    def _is_processable_file(self, file_path: Path) -> bool:
        """
        [Function intent]
        Determines if a file can be processed by the source code processor.
        
        [Design principles]
        Clear exclusion criteria for non-processable files.
        Extension-based language detection.
        
        [Implementation details]
        Checks file extension against known processable extensions.
        Verifies file exists and is a regular file.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if file can be processed, False otherwise
        """
        # Check if file exists and is a regular file
        if not file_path.exists() or not file_path.is_file():
            return False
            
        # Check if extension is processable
        extension = file_path.suffix.lower()
        return extension in self._processable_extensions
