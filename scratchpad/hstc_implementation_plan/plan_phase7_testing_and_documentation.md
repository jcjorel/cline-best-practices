# Phase 7: Testing and Documentation

This phase covers the testing strategy and documentation for the HSTC module.

## Testing Strategy

### Unit Tests

1. `tests/dbp/hstc/test_scanner.py` - Tests for the HSTCScanner class
2. `tests/dbp/hstc/test_source_processor.py` - Tests for the SourceCodeProcessor class
3. `tests/dbp/hstc/test_hstc_processor.py` - Tests for the HSTCFileProcessor class
4. `tests/dbp/hstc/test_manager.py` - Tests for the HSTCManager class
5. `tests/dbp/hstc/test_component.py` - Tests for the HSTCComponent class
6. `tests/dbp_cli/commands/test_hstc.py` - Tests for the HSTCCommand class

### Test Coverage Goals

- Scanner: Test directory traversal, update detection, and ordering logic
- Source Processor: Test file processing, LLM interaction, error handling
- HSTC Processor: Test file generation, child directory processing
- Manager: Test orchestration and error handling
- Component: Test initialization, shutdown, and delegation
- CLI: Test command parsing and execution

### Mocking Strategy

Mock the following to ensure tests are reliable and don't make external calls:

1. **LLM Clients**: Mock responses with predefined content
2. **File System**: Use `unittest.mock` or temporary directories
3. **Component Registry**: Mock initialization context and dependencies

Example for mocking LLM client:

```python
@patch('dbp.hstc.source_processor.BedrockClientFactory')
def test_update_source_file(self, mock_factory):
    # Set up mock client
    mock_client = Mock()
    mock_client.invoke.return_value = Mock(content='{"updated_source_code": "updated content", "status": "success"}')
    mock_factory.create_langchain_chatbedrock.return_value = mock_client
    
    # Test processor
    processor = SourceCodeProcessor()
    result = processor.update_source_file('test_file.py', dry_run=True)
    
    # Assert expectations
    self.assertEqual(result['status'], 'success')
```

### Integration Testing

1. **Directory Tree Processing**: Verify end-to-end workflow with a sample directory structure
2. **CLI Command Testing**: Verify command execution with various parameters
3. **Error Recovery**: Verify handling of various error scenarios

## Module Documentation

### HSTC.md

Create an HSTC.md file for the module itself to showcase its capabilities:

```markdown
# Hierarchical Semantic Tree Context: hstc

## Directory Purpose
The HSTC (Hierarchical Semantic Tree Context) module provides functionality for managing HSTC.md files 
throughout the project. It updates source code documentation to comply with standards and generates 
HSTC.md files that capture metadata about source files and directory structure. The module follows 
a bottom-up approach when updating the HSTC hierarchy to maintain consistency.

## Local Files

### `__init__.py`
```yaml
source_file_intent: |
  Package initialization for the HSTC module that manages Hierarchical Semantic Tree 
  Context (HSTC) files. Provides public imports for key components and functions.
  
source_file_design_principles: |
  - Minimal imports to avoid circular dependencies
  - Clear public interface through explicit exports
  - Version information for module tracking
  
source_file_constraints: |
  - Must not contain implementation details, only imports and version
```

### `component.py`
```yaml
source_file_intent: |
  Implements the HSTCComponent class that integrates with the DBP component system
  to provide HSTC.md file management capabilities. This component acts as the entry
  point for HSTC operations and manages the underlying services.
  
source_file_design_principles: |
  - Clean component lifecycle management (initialization, shutdown)
  - Delegation to specialized services for core functionality
  - Simple public API for HSTC operations
  - Explicit dependency declaration and management
  
source_file_constraints: |
  - Must comply with DBP component system requirements
  - Must handle initialization and shutdown correctly
  - Must manage dependencies on other components
```

[...additional files would be documented in the actual HSTC.md...]

<!-- End of HSTC.md file -->
```

### README.md

Create a README.md file with usage instructions:

```markdown
# HSTC Module

The HSTC (Hierarchical Semantic Tree Context) module provides functionality for managing HSTC.md files throughout the project. These files capture metadata about source files and directory structure, providing valuable context for code navigation and understanding.

## Features

- Update source code documentation to comply with project standards
- Generate and update HSTC.md files based on source file metadata
- Process directories in bottom-up order to maintain hierarchical consistency
- Command-line interface for easy updates

## Usage

### Using the CLI

1. Update HSTC files in a directory tree:
   ```bash
   python -m dbp_cli hstc update [--directory DIR] [--dry-run]
   ```

2. Update a single source file:
   ```bash
   python -m dbp_cli hstc update-file FILE [--dry-run]
   ```

### Using the Component Programmatically

```python
from dbp.hstc.component import HSTCComponent

# Create and initialize the component
component = HSTCComponent()
# Initialize component according to your system's requirements

# Update HSTC.md files in a directory tree
result = component.update_hstc(
    directory_path='path/to/directory',
    dry_run=False  # Set to True to preview changes without applying them
)
print(f"Updated {result['directories_updated']} directories")

# Update a single source file
result = component.update_source_file(
    file_path='path/to/file.py',
    dry_run=False  # Set to True to preview changes without applying them
)
print(f"File update status: {result['status']}")
```

## LLM Model Selection

The HSTC module uses two different LLM models for different tasks:

1. **Source Code Processing**: Uses Claude 3.7 Sonnet by default (`anthropic.claude-3-7-sonnet-20250219-v1`) for best code understanding and documentation generation.

2. **HSTC.md Generation**: Uses Nova Lite by default (`amazon.nova-lite-v1`) for efficient processing of directory structure and metadata.

These can be configured when initializing the HSTCComponent or its underlying services.
```

## Implementation Steps

1. Create test files for each module component
2. Implement comprehensive test coverage
3. Create HSTC.md for the module itself
4. Create README.md with usage instructions
