# Phase 3: Source Processor

This phase covers the implementation of the SourceCodeProcessor, which is responsible for updating source code files to comply with documentation standards using LLM.

## Files to Implement

1. `src/dbp/hstc/source_processor.py` - Source code processor implementation
2. `src/dbp/hstc/prompts/source_update_prompt.md` - Prompt template for source code documentation updates

## Implementation Details

### Source Update Prompt (`prompts/source_update_prompt.md`)

```markdown
# MANDATORY CODE DOCUMENTATION PATTERNS

⚠️ CRITICAL: ALL functions, methods, and classes MUST include the three-section documentation pattern regardless of size or complexity. NO EXCEPTIONS PERMITTED (except for Markdown files). This is a non-negotiable project standard that takes precedence over all other considerations except correct code functionality.

## Documentation Pattern Reminder:
```
[Function/Class method/Class intent] <!-- It is **critical** to fully capture and contextualize the intent -->
[Design principles]
[Implementation details]
```

You will find below a source code file to analyze. Update ONLY the documentation (file-level and function/method/class-level) to make it compliant with the standards described above. DO NOT modify any functional code.

File: {file_path}

```{file_ext}
{file_content}
```

You must return a valid JSON object with the following structure:

```json
{
  "updated_source_code": "the complete updated source code with improved documentation",
  "changes_summary": {
    "file_header_updated": true|false,
    "functions_updated": 5,
    "classes_updated": 2,
    "methods_updated": 10
  },
  "status": "success|warning|error",
  "messages": ["Optional explanatory message or warning"]
}
```
```

### Source Code Processor (`source_processor.py`)

The SourceCodeProcessor class is responsible for updating source files to comply with documentation standards. The core implementation includes:

```python
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
    
    def __init__(self, logger=None, llm_model_id: str = "anthropic.claude-3-7-sonnet-20250219-v1"):
        self.logger = logger or logging.getLogger("dbp.hstc.source_processor")
        self.llm_model_id = llm_model_id
        self._llm_client = None
        self._prompt_template = None
```

The processor provides these key methods:

1. `_get_llm_client()` - Creates or retrieves a cached LLM client
2. `_load_prompt_template()` - Loads the prompt template for source file updates
3. `_is_processable_file(file_path)` - Checks if a file can be processed (source code file)
4. `_parse_llm_response(response)` - Parses LLM JSON responses with fallbacks
5. `update_source_file(file_path, dry_run=False)` - The main method for updating source files

## Key Functionality

The SourceCodeProcessor implements several core features:

1. **Source File Compatibility Detection**:
   - Determines whether files can be processed based on extension
   - Handles various programming languages through extensions
   - Avoids processing binary files or non-source files

2. **LLM Integration for Documentation Updates**:
   - Uses Claude 3.7 Sonnet by default for optimal code understanding
   - Creates prompts with appropriate documentation standards
   - Processes structured JSON responses for reliable updates

3. **File Handling**:
   - Uses DBPFile for robust file access with encoding detection
   - Preserves file encoding when updating content
   - Creates HSTC_REQUIRES_UPDATE.md markers for updated files

4. **Error Handling and Reporting**:
   - Clear exception hierarchy with specific error types
   - Robust LLM response parsing with fallbacks
   - Detailed logging for operations and errors

## Integration Points

The Source Processor is designed to integrate with:

1. **HSTCManager**: The manager will use this processor to update source files before generating HSTC.md files.

2. **BedrockClientFactory**: Used to create LLM clients for source code processing.

3. **File System**: Direct integration with the file system for reading and writing files.

## Error Cases and Handling

The processor handles several error cases:

1. **File Access Errors**: Cannot read or write files due to permissions or other issues
   - Handled with specific FileAccessError exceptions
   - Provides detailed error messages with file paths

2. **LLM Processing Errors**: API errors, rate limiting, or other LLM issues
   - Handled with specific LLMError exceptions
   - Includes model ID for context

3. **Response Parsing Errors**: Malformed responses from the LLM
   - Uses fallback mechanisms to extract code from responses
   - Provides warnings and status information in results

## Implementation Steps

1. Create `src/dbp/hstc/prompts/` directory
2. Implement `source_update_prompt.md` with the prompt template
3. Implement `source_processor.py` with the SourceCodeProcessor class
4. Test with various file types and scenarios
