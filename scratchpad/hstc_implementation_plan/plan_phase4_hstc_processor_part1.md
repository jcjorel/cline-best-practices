# Phase 4: HSTC Processor (Part 1 - Overview & Core Implementation)

This phase covers the first part of the HSTCFileProcessor implementation, which is responsible for creating and updating HSTC.md files based on source file metadata.

## Files to Implement

1. `src/dbp/hstc/hstc_processor.py` - HSTC file processor implementation
2. `src/dbp/hstc/prompts/hstc_update_prompt.md` - Prompt template for HSTC file generation/updates

## Overview

The HSTCFileProcessor is responsible for:

1. Extracting metadata from source files in a directory
2. Collecting information about child directories with HSTC.md files
3. Using LLM (Nova model) to generate or update HSTC.md files
4. Maintaining the hierarchical structure of HSTC.md files

## Core Implementation

```python
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
```

## Key Methods

### LLM Client Management

```python
def _get_llm_client(self):
    """
    [Function intent]
    Gets or creates an LLM client instance for HSTC.md file processing.
    
    [Design principles]
    Lazy initialization of LLM client for efficient resource usage.
    Clear error handling for LLM client creation failures.
    
    [Implementation details]
    Creates a LangChain client using BedrockClientFactory.
    Caches the client for reuse across multiple file processing operations.
    """
    if self._llm_client is None:
        self.logger.debug(f"Creating new LLM client with model {self.llm_model_id}")
        try:
            self._llm_client = BedrockClientFactory.create_langchain_chatbedrock(
                model_id=self.llm_model_id,
                streaming=False,
                logger=self.logger
            )
        except Exception as e:
            error_msg = f"Failed to create LLM client: {str(e)}"
            self.logger.error(error_msg)
            raise LLMError(error_msg, model_id=self.llm_model_id)
            
    return self._llm_client
```

### Prompt Template Loading

```python
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
```

### File Header Extraction

```python
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
            
            # Extract dependencies and change history
            # (Implementation details omitted for brevity)
            
            # Only add files with at least one header section
            if header:
                file_headers[item.name] = header
                
        except Exception as e:
            self.logger.warning(f"Error extracting headers from {item.name}: {str(e)}")
            
    return file_headers
