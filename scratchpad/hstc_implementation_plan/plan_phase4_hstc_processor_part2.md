# Phase 4: HSTC Processor (Part 2 - Additional Methods & Integration)

This phase covers the remaining implementation details of the HSTCFileProcessor class.

## Child Directory Processing

```python
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
```

## Prompt Creation & LLM Response Processing

```python
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
```

## HSTC Generation & Update

```python
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
            
            # Add file sections
            # (Implementation details for yaml formatting omitted for brevity)
            
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
```

## HSTC Update Prompt (`prompts/hstc_update_prompt.md`)

```markdown
# Hierarchical Semantic Tree Context (HSTC)

- **Purpose**: Documents how the project IS actually implemented (descriptive)
- **Focus**: Current codebase structure, file purposes, implementation details
- **Authority**: Serves as the authoritative source for implementation context
- **Key Files**: HSTC.md files distributed throughout the directory hierarchy

You will find below information about a directory and its contents. Your task is to create or update the HSTC.md file for this directory.

Directory: {directory_name}

## Source Files:
{files_json_data}

## Child Directories:
{child_directories_json_data}

## Existing HSTC.md (if available):
{existing_hstc_content}

You must return a valid JSON object with the following structure:

```json
{
  "hstc_content": {
    "directory_name": "name of this directory",
    "directory_purpose": "detailed description of this directory's purpose",
    "child_directories": [
      {
        "name": "child_directory_name",
        "purpose": "description of child directory purpose"
      }
    ],
    "files": [
      {
        "name": "filename.ext",
        "source_file_intent": "content of source file intent section",
        "source_file_design_principles": "content of design principles section",
        "source_file_constraints": "content of constraints section",
        "dependencies": [
          {"kind": "codebase|system|other", "dependency": "dependency path"}
        ],
        "change_history": [
          {
            "timestamp": "YYYY-MM-DDThh:mm:ssZ",
            "summary": "change summary",
            "details": ["change detail 1", "change detail 2"]
          }
        ]
      }
    ]
  },
  "status": "success|warning|error",
  "messages": ["Optional explanatory message or warning"]
}
```
```

## Integration Points

The HSTC Processor is designed to integrate with:

1. **HSTCManager**: The manager will use this processor to update HSTC.md files after source files are processed.

2. **BedrockClientFactory**: Used to create LLM clients for HSTC file generation.

3. **File System**: Direct integration with the file system for reading and writing files.

## Implementation Steps

1. Create `src/dbp/hstc/prompts/hstc_update_prompt.md` with the prompt template
2. Implement `hstc_processor.py` with the HSTCFileProcessor class
3. Test with various directory structures to verify hierarchical consistency
