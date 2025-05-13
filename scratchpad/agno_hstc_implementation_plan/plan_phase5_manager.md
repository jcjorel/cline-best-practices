# HSTC Implementation with Agno - Phase 5: HSTC Manager

This document outlines the detailed steps to implement the HSTC Manager component for the HSTC implementation using the Agno framework.

## Overview

The HSTC Manager is responsible for:

1. Orchestrating the workflow between the File Analyzer and Documentation Generator agents
2. Processing files and their dependencies
3. Managing the hierarchical structure of HSTC documentation
4. Generating implementation plans for documentation updates
5. Providing error handling and progress reporting

This component serves as the central coordination point for the HSTC functionality.

## Prerequisites

Ensure that Phases 1, 2, 3, and 4 are completed:
- The basic project structure is in place
- Data models and utility functions are implemented
- The File Analyzer Agent is functional
- The Documentation Generator Agent is functional

## Step 1: Implement the HSTC Manager Class

Expand the skeleton manager class created in Phase 1:

```python
# src/dbp_cli/commands/hstc_agno/manager.py

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .agents import FileAnalyzerAgent, DocumentationGeneratorAgent
from .utils import get_current_timestamp, append_to_implementation_plan

class HSTCManager:
    """Manager for HSTC file processing and documentation generation."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the HSTC Manager
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir or Path.cwd()
        self.file_analyzer = None
        self.doc_generator = None
        self.processed_files: Dict[str, Any] = {}
        self.dependency_cache: Dict[str, Any] = {}
        
        # Initialize agents
        self.initialize_agents()
    
    def initialize_agents(self):
        """Initialize the File Analyzer and Documentation Generator agents"""
        # Create File Analyzer Agent
        self.file_analyzer = FileAnalyzerAgent(base_dir=self.base_dir)
        
        # Create Documentation Generator Agent
        self.doc_generator = DocumentationGeneratorAgent()
```

## Step 2: Implement Core Process Method

Add the main method that processes files:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def process_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a file through the entire HSTC workflow
    
    Args:
        file_path: Path to the file
        options: Processing options including:
            - output: Output directory for implementation plan
            - recursive: Whether to process dependencies recursively
        
    Returns:
        Dict containing processing results
    """
    try:
        # Validate file path
        if not self._validate_file_path(file_path):
            return {"error": f"Invalid file path: {file_path}"}
        
        # Step 1: Analyze the file
        file_metadata = self.analyze_file(file_path, options.get("recursive", False))
        
        # Step 2: Generate documentation
        documentation = self.generate_documentation(file_path)
        
        # Step 3: Validate documentation
        validation = self.validate_documentation(file_path)
        
        # Step 4: Generate implementation plan
        plan_path = self._output_dir(file_path, options.get("output"))
        plan_files = self.generate_implementation_plan(file_path, documentation, plan_path)
        
        # Return results
        return {
            "file_path": file_path,
            "file_metadata": file_metadata,
            "documentation": documentation,
            "validation": validation,
            "plan_path": plan_path,
            "plan_files": plan_files
        }
    except Exception as e:
        import traceback
        return {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }
```

## Step 3: Implement File Path Validation

Add a method to validate file paths:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _validate_file_path(self, file_path: str) -> bool:
    """
    Validate that the file path exists
    
    Args:
        file_path: Path to validate
        
    Returns:
        bool: True if valid, False otherwise
    """
    path = Path(file_path)
    if not path.exists():
        return False
    if not path.is_file():
        return False
    return True
```

## Step 4: Implement File Analysis Method

Add a method to coordinate file analysis:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def analyze_file(self, file_path: str, recursive: bool = False) -> Dict[str, Any]:
    """
    Analyze a source file using the File Analyzer Agent
    
    Args:
        file_path: Path to the file to analyze
        recursive: Whether to process dependencies recursively
        
    Returns:
        Dict containing file metadata
    """
    # Check if already processed
    if file_path in self.processed_files:
        return self.processed_files[file_path]
    
    # Analyze the file
    file_metadata = self.file_analyzer.analyze_file(file_path)
    self.processed_files[file_path] = file_metadata
    
    # Process dependencies if recursive is enabled and file is source code
    if recursive and file_metadata.get("file_type") == "source_code":
        self._process_dependencies(file_path, file_metadata)
    
    return file_metadata
```

## Step 5: Implement Dependency Processing

Add a method to process file dependencies:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _process_dependencies(self, file_path: str, file_metadata: Dict[str, Any]) -> None:
    """
    Process dependencies of a file
    
    Args:
        file_path: Path to the file
        file_metadata: Metadata about the file
    """
    # Extract dependencies
    dependencies = file_metadata.get("dependencies", [])
    
    # Process each dependency
    for dep in dependencies:
        dep_type = dep.get("kind")
        dep_path = dep.get("path_or_package")
        
        # Only process codebase dependencies
        if dep_type == "codebase" and dep_path:
            # Resolve path relative to current file
            resolved_path = Path(file_path).parent / dep_path
            resolved_path = resolved_path.resolve()
            
            # Skip if already processed or doesn't exist
            if str(resolved_path) in self.dependency_cache or not resolved_path.exists():
                continue
            
            # Analyze dependency
            dep_metadata = self.analyze_file(str(resolved_path), True)
            
            # Cache the result
            self.dependency_cache[str(resolved_path)] = dep_metadata
```

## Step 6: Implement Documentation Generation Method

Add a method to coordinate documentation generation:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def generate_documentation(self, file_path: str) -> Dict[str, Any]:
    """
    Generate documentation for a file
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict containing generated documentation
    """
    # Get file metadata
    file_metadata = self.processed_files.get(file_path)
    if not file_metadata:
        file_metadata = self.analyze_file(file_path)
    
    # Get dependency metadata for related files
    dependency_metadata = {}
    for dep_path, dep_meta in self.dependency_cache.items():
        dependency_metadata[dep_path] = dep_meta
    
    # Generate documentation
    documentation = self.doc_generator.process_file_documentation(
        file_path, file_metadata, dependency_metadata
    )
    
    return documentation
```

## Step 7: Implement Documentation Validation Method

Add a method to validate documentation:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def validate_documentation(self, file_path: str) -> Dict[str, Any]:
    """
    Validate generated documentation
    
    Args:
        file_path: Path to the file
        
    Returns:
        Dict containing validation results
    """
    return self.doc_generator.validate_documentation(file_path)
```

## Step 8: Implement Output Directory Method

Add a method to determine the output directory for implementation plans:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _output_dir(self, file_path: str, output_path: Optional[str] = None) -> str:
    """
    Determine output directory for implementation plan
    
    Args:
        file_path: Path to the source file
        output_path: User-specified output directory
        
    Returns:
        str: Path to the output directory
    """
    if output_path:
        output_dir = Path(output_path)
    else:
        output_dir = self.base_dir / "scratchpad" / f"hstc_update_{Path(file_path).stem}"
    
    output_dir.mkdir(parents=True, exist_ok=True)
    return str(output_dir)
```

## Step 9: Implement Implementation Plan Generation Method

Add a method to generate implementation plans:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def generate_implementation_plan(
    self, 
    file_path: str, 
    documentation: Dict[str, Any], 
    output_path: str
) -> List[str]:
    """
    Generate markdown implementation plan
    
    Args:
        file_path: Path to the file
        documentation: Generated documentation
        output_path: Output directory
        
    Returns:
        List of generated file paths
    """
    output_dir = Path(output_path)
    
    # Create overview plan
    overview_path = output_dir / "plan_overview.md"
    with overview_path.open("w") as f:
        f.write(self._generate_overview_markdown(file_path, documentation))
    
    # Create implementation plan
    impl_path = output_dir / "plan_implementation.md"
    with impl_path.open("w") as f:
        f.write(self._generate_implementation_markdown(file_path, documentation))
    
    # Create progress tracker
    progress_path = output_dir / "plan_progress.md"
    with progress_path.open("w") as f:
        f.write(self._generate_progress_markdown(file_path, documentation))
    
    return [
        str(overview_path),
        str(impl_path),
        str(progress_path)
    ]
```

## Step 10: Implement Overview Generation Method

Add a method to generate the overview markdown:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _generate_overview_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
    """
    Generate overview markdown content
    
    Args:
        file_path: Path to the file
        documentation: Generated documentation
        
    Returns:
        str: Markdown content
    """
    language = documentation.get("language", "unknown")
    file_type = documentation.get("file_type", "unknown")
    
    # Extract definitions and dependencies
    definitions = documentation.get("definitions", [])
    dependencies = []
    if "file_header" in documentation and "dependencies" in documentation["file_header"]:
        dependencies = documentation["file_header"]["dependencies"]
    
    # Generate validation summary
    validation = self.validate_documentation(file_path)
    if validation.get("valid", False):
        validation_summary = "✅ Documentation meets HSTC standards."
    else:
        issues = validation.get("issues", [])
        validation_summary = "⚠️ Documentation has issues:\n\n"
        for issue in issues:
            validation_summary += f"- {issue}\n"
    
    # Build markdown
    return f"""# HSTC Update Implementation Plan

## Overview

This plan outlines the steps to update documentation for `{file_path}` to comply with HSTC standards.

## File Analysis

- **File Type**: {file_type}
- **Language**: {language}
- **Definitions**: {len(definitions)} functions/classes/methods found
- **Dependencies**: {len(dependencies)} dependencies identified

## Documentation Status

{validation_summary}

## Implementation Steps

1. Update file header with standardized documentation
2. Update {len(definitions)} function/class/method definitions with proper documentation
3. Verify documentation meets HSTC requirements

## Required Files

- `plan_implementation.md`: Detailed implementation steps
- `plan_progress.md`: Implementation progress tracker
"""
```

## Step 11: Implement Implementation Markdown Generation Method

Add a method to generate the implementation markdown:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _generate_implementation_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
    """
    Generate implementation markdown content
    
    Args:
        file_path: Path to the file
        documentation: Generated documentation
        
    Returns:
        str: Markdown content
    """
    language = documentation.get("language", "unknown")
    
    # Extract header and definitions
    file_header = documentation.get("file_header", {})
    definitions = documentation.get("definitions", [])
    
    # Build markdown
    md = f"""# HSTC Implementation Details

## File Header Update

```{language}
{file_header.get("raw_header", "")}
```

## Function/Class Documentation Updates
"""
    
    # Add each definition
    for definition in definitions:
        name = definition.get("name", "unknown")
        def_type = definition.get("type", "function")
        original_comment = definition.get("original_comment", "")
        updated_comment = definition.get("updated_comment", "")
        
        md += f"""
### {name} ({def_type})

Original documentation:
```{language}
{original_comment}
```

Updated documentation:
```{language}
{updated_comment}
```
"""
    
    return md
```

## Step 12: Implement Progress Markdown Generation Method

Add a method to generate the progress markdown:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _generate_progress_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
    """
    Generate progress markdown content
    
    Args:
        file_path: Path to the file
        documentation: Generated documentation
        
    Returns:
        str: Markdown content
    """
    # Extract definitions
    definitions = documentation.get("definitions", [])
    
    # Build markdown
    md = """# HSTC Implementation Progress

## Status Legend

- ❌ Not started
- 🔄 In progress
- ✅ Completed

## Tasks

- ❌ Update file header
- ❌ Update function/class documentation
"""
    
    # Add each definition
    for definition in definitions:
        name = definition.get("name", "unknown")
        def_type = definition.get("type", "function")
        md += f"  - ❌ {name} ({def_type})\n"
    
    md += "- ❌ Final validation\n"
    return md
```

## Step 13: Implement Error Handling Methods

Add methods to handle and report errors:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def _generate_error_report(self, file_path: str, error_info: Dict[str, Any]) -> str:
    """
    Generate an error report when processing fails
    
    Args:
        file_path: Path to the file
        error_info: Information about the error
        
    Returns:
        Path to the error report
    """
    # Create output directory
    error_dir = self.base_dir / "scratchpad" / f"hstc_error_{Path(file_path).stem}"
    error_dir.mkdir(parents=True, exist_ok=True)
    
    # Create error report
    error_path = error_dir / "error_report.md"
    with error_path.open("w") as f:
        f.write(f"# HSTC Error Report\n\n")
        f.write(f"File: {file_path}\n\n")
        f.write(f"Error: {error_info['error']}\n\n")
        f.write("## Traceback\n\n```\n")
        f.write(error_info["traceback"])
        f.write("\n```\n\n")
        
        # Include partial results if available
        if file_path in self.processed_files:
            f.write("## Partial Analysis Results\n\n")
            f.write("```json\n")
            f.write(json.dumps(self.processed_files[file_path], indent=2))
            f.write("\n```\n\n")
    
    return str(error_path)

def safe_process_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a file with error handling
    
    Args:
        file_path: Path to the file
        options: Processing options
        
    Returns:
        Dict containing processing results or error information
    """
    try:
        return self.process_file(file_path, options)
    except Exception as e:
        import traceback
        error_info = {
            "error": str(e),
            "traceback": traceback.format_exc(),
            "file_path": file_path
        }
        
        # Log error
        print(f"Error processing {file_path}: {e}")
        
        # Generate error report
        self._generate_error_report(file_path, error_info)
        
        return error_info
```

## Step 14: Implement Multi-File Processing Method

Add a method to process multiple files in parallel:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def process_multiple_files(self, file_paths: List[str], options: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Process multiple files in parallel
    
    Args:
        file_paths: List of file paths to process
        options: Processing options
        
    Returns:
        List of processing results
    """
    import concurrent.futures
    
    results = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # Submit all file processing tasks
        future_to_path = {
            executor.submit(self.safe_process_file, path, options): path
            for path in file_paths
        }
        
        # Process results as they complete
        for future in concurrent.futures.as_completed(future_to_path):
            path = future_to_path[future]
            try:
                result = future.result()
                results.append(result)
                print(f"Completed processing {path}")
            except Exception as e:
                print(f"Error processing {path}: {e}")
                results.append({"file_path": path, "error": str(e)})
    
    return results
```

## Step 15: Implement Directory Processing Method

Add a method to process entire directories:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def process_directory(self, directory_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process all relevant files in a directory
    
    Args:
        directory_path: Path to the directory
        options: Processing options including:
            - recursive_dir: Whether to search subdirectories
            - file_patterns: List of file patterns to include
        
    Returns:
        Dict containing processing results
    """
    import glob
    
    # Default patterns if none provided
    file_patterns = options.get("file_patterns", ["*.py", "*.js", "*.ts", "*.java", "*.c", "*.cpp", "*.h", "*.hpp"])
    
    # Build glob patterns
    if options.get("recursive_dir", False):
        patterns = [f"{directory_path}/**/{pattern}" for pattern in file_patterns]
    else:
        patterns = [f"{directory_path}/{pattern}" for pattern in file_patterns]
    
    # Find all matching files
    file_paths = []
    for pattern in patterns:
        file_paths.extend(glob.glob(pattern, recursive=options.get("recursive_dir", False)))
    
    # Process all files
    results = self.process_multiple_files(file_paths, options)
    
    return {
        "directory": directory_path,
        "files_processed": len(results),
        "results": results
    }
```

## Step 16: Implement Cache Management Methods

Add methods to manage the internal cache:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (Add to HSTCManager class)

def clear_cache(self) -> None:
    """Clear the internal cache"""
    self.processed_files = {}
    self.dependency_cache = {}
    
    # Clear agent caches
    if self.file_analyzer:
        self.file_analyzer.clear_metadata()
    if self.doc_generator:
        self.doc_generator.clear_documentation()

def save_cache(self, cache_path: str) -> None:
    """
    Save the internal cache to a file
    
    Args:
        cache_path: Path to save the cache
    """
    cache_data = {
        "processed_files": self.processed_files,
        "dependency_cache": self.dependency_cache,
        "timestamp": get_current_timestamp()
    }
    
    with open(cache_path, 'w') as f:
        json.dump(cache_data, f, indent=2)

def load_cache(self, cache_path: str) -> bool:
    """
    Load the internal cache from a file
    
    Args:
        cache_path: Path to load the cache from
        
    Returns:
        bool: True if cache was loaded successfully
    """
    try:
        with open(cache_path, 'r') as f:
            cache_data = json.load(f)
        
        self.processed_files = cache_data.get("processed_files", {})
        self.dependency_cache = cache_data.get("dependency_cache", {})
        
        return True
    except Exception:
        return False
```

## Step 17: Add Example Usage to `__main__`

Create an example usage that can be run as a standalone script:

```python
# Add to the bottom of src/dbp_cli/commands/hstc_agno/manager.py

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="HSTC Manager")
    parser.add_argument("file_path", help="Path to a file or directory to process")
    parser.add_argument("--output", "-o", help="Output directory for implementation plan")
    parser.add_argument("--recursive", action="store_true", help="Process dependencies recursively")
    parser.add_argument("--recursive-dir", action="store_true", help="Process subdirectories recursively")
    
    args = parser.parse_args()
    
    manager = HSTCManager()
    
    options = {
        "output": args.output,
        "recursive": args.recursive,
        "recursive_dir": args.recursive_dir
    }
    
    # Process file or directory
    import os
    if os.path.isfile(args.file_path):
        print(f"Processing file: {args.file_path}")
        result = manager.process_file(args.file_path, options)
        
        if "error" in result:
            print(f"Error: {result['error']}")
        else:
            print(f"Implementation plan generated at: {result['plan_path']}")
    
    elif os.path.isdir(args.file_path):
        print(f"Processing directory: {args.file_path}")
        result = manager.process_directory(args.file_path, options)
        
        print(f"Processed {result['files_processed']} files")
        
        successful = sum(1 for r in result['results'] if "error" not in r)
        failed = sum(1 for r in result['results'] if "error" in r)
        
        print(f"Successful: {successful}, Failed: {failed}")
    else:
        print(f"Invalid path: {args.file_path}")
```

## Step 18: Testing the HSTC Manager

To test the manager implementation:

1. Create a test source file:

```python
# test_file.py

"""
Test file for demonstrating the HSTC Manager.
This file contains various functions and classes to test the full workflow.
"""

import os
import sys
from typing import List, Dict, Any

# Global variable
VERSION = "1.0.0"

def main_function(arg1: str, arg2: int = 0) -> bool:
    """
    [Function intent]
    This is the main function that does important things.
    
    [Design principles]
    Follows single responsibility principle.
    
    [Implementation details]
    Uses optimized algorithm for processing input.
    
    Args:
        arg1: First argument description
        arg2: Second argument description, defaults to 0
        
    Returns:
        bool: Result of the operation
    """
    return True

class ExampleClass:
    """
    [Class intent]
    Example class for testing documentation extraction.
    
    [Design principles]
    Encapsulates related functionality.
    
    [Implementation details]
    Implements basic operations with error handling.
    """
    
    def __init__(self, value: str):
        """
        [Class method intent]
        Initialize the class with a value.
        
        [Design principles]
        Simple initialization with validation.
        
        [Implementation details]
        Stores the value as an instance variable.
        
        Args:
            value: Initial value for the instance
        """
        self.value = value
    
    def process(self) -> Dict[str, Any]:
        """Process the value and return a result."""
        return {"result": self.value}
```

2. Run the manager on the test file:

```bash
python -m src.dbp_cli.commands.hstc_agno.manager test_file.py
```

3. Verify that the manager correctly:
   - Analyzes the file using the File Analyzer Agent
   - Generates documentation using the Documentation Generator Agent
   - Creates an implementation plan with overview, implementation details, and progress tracker

## Expected Output

After completing this phase, you should have a fully functional HSTC Manager that:

1. Orchestrates the workflow between the File Analyzer and Documentation Generator agents
2. Processes files and their dependencies
3. Generates implementation plans for documentation updates
4. Provides robust error handling and reporting
5. Supports parallel processing of multiple files

This manager provides the foundation for the CLI integration in Phase 6.

## Next Steps

Proceed to Phase 6 (CLI Integration) to implement the command-line interface for the HSTC functionality.
