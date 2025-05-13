# HSTC Implementation Details with Agno - Part 1

## Overview

This document provides detailed implementation guidance for the HSTC feature using the Agno framework. It includes code organization, best practices, and specific examples of key components.

## Project Structure

The HSTC feature will be implemented within the following directory structure:

```
src/
├── dbp_cli/
│   ├── commands/
│   │   ├── __init__.py
│   │   ├── hstc_agno/
│   │   │   ├── __init__.py
│   │   │   ├── agents.py            # Agent implementations
│   │   │   ├── cli.py               # CLI command definitions
│   │   │   ├── manager.py           # HSTC Manager implementation
│   │   │   ├── models.py            # Data models
│   │   │   └── utils.py             # Utility functions
```

## Key Classes and Interfaces

### 1. CLI Command Implementation

```python
# src/dbp_cli/commands/hstc_agno/cli.py

import click
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .manager import HSTCManager
from dbp_cli.progress import progress_bar

@click.group()
def hstc_agno():
    """HSTC implementation with Agno framework."""
    pass

@hstc_agno.command("update")
@click.argument("file_path", type=str)
@click.option("--output", "-o", help="Output directory for implementation plan")
@click.option("--recursive/--no-recursive", default=False, 
              help="Process dependencies recursively")
def update(file_path: str, output: Optional[str], recursive: bool):
    """Update documentation for a source file using Agno-powered analysis."""
    
    # Initialize options dictionary
    options = {
        "output": output,
        "recursive": recursive
    }
    
    # Create HSTC Manager and process file
    with progress_bar("Initializing HSTC Manager..."):
        manager = HSTCManager(base_dir=Path.cwd())
    
    with progress_bar(f"Processing {file_path}..."):
        result = manager.process_file(file_path, options)
    
    # Display results
    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        return
    
    click.echo(click.style("✅ HSTC processing completed successfully!", fg="green"))
    click.echo(f"Implementation plan generated at: {result['plan_path']}")
    
    if "validation" in result and result["validation"].get("issues"):
        click.echo(click.style("⚠️ Validation issues:", fg="yellow"))
        for issue in result["validation"].get("issues", []):
            click.echo(f"  - {issue}")
```

### 2. HSTC Manager Implementation

```python
# src/dbp_cli/commands/hstc_agno/manager.py

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

from .agents import FileAnalyzerAgent, DocumentationGeneratorAgent

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
    
    def process_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a file through the entire HSTC workflow
        
        Args:
            file_path: Path to the file
            options: Processing options
            
        Returns:
            Dict containing processing results
        """
        try:
            # Validate file path
            if not self._validate_file_path(file_path):
                return {"error": f"Invalid file path: {file_path}"}
            
            # Step 1: Analyze the file
            file_metadata = self.analyze_file(file_path)
            
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
    
    def _validate_file_path(self, file_path: str) -> bool:
        """Validate that the file path exists"""
        path = Path(file_path)
        if not path.exists():
            return False
        if not path.is_file():
            return False
        return True
    
    def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a source file using the File Analyzer Agent
        """
        # Check if already processed
        if file_path in self.processed_files:
            return self.processed_files[file_path]
        
        # Analyze the file
        file_metadata = self.file_analyzer.analyze_file(file_path)
        self.processed_files[file_path] = file_metadata
        
        # Process dependencies if source code and recursive option enabled
        if file_metadata.get("file_type") == "source_code":
            self._process_dependencies(file_path, file_metadata)
        
        return file_metadata
    
    def _process_dependencies(self, file_path: str, file_metadata: Dict[str, Any]) -> None:
        """Process dependencies of a file"""
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
                dep_metadata = self.analyze_file(str(resolved_path))
                
                # Cache the result
                self.dependency_cache[str(resolved_path)] = dep_metadata
    
    def generate_documentation(self, file_path: str) -> Dict[str, Any]:
        """Generate documentation for a file"""
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
    
    def validate_documentation(self, file_path: str) -> Dict[str, Any]:
        """Validate generated documentation"""
        return self.doc_generator.validate_documentation(file_path)
    
    def _output_dir(self, file_path: str, output_path: Optional[str] = None) -> str:
        """Determine output directory for implementation plan"""
        if output_path:
            output_dir = Path(output_path)
        else:
            output_dir = self.base_dir / "scratchpad" / f"hstc_update_{Path(file_path).stem}"
        
        output_dir.mkdir(parents=True, exist_ok=True)
        return str(output_dir)
    
    def generate_implementation_plan(
        self, 
        file_path: str, 
        documentation: Dict[str, Any], 
        output_path: str
    ) -> List[str]:
        """Generate markdown implementation plan"""
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
    
    def _generate_overview_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """Generate overview markdown content"""
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

    def _generate_implementation_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """Generate implementation markdown content"""
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

    def _generate_progress_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """Generate progress markdown content"""
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
