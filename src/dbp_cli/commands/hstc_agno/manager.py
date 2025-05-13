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
# This file implements the HSTC Manager for coordinating the HSTC workflow using
# the Agno framework. It orchestrates the process of file analysis, documentation
# generation, and implementation plan creation using specialized agents.
###############################################################################
# [Source file design principles]
# - Clear workflow organization
# - Separation of orchestration from agent implementation
# - Effective error handling and recovery
# - Progress tracking and reporting
###############################################################################
# [Source file constraints]
# - Must coordinate multiple agent types
# - Should handle file dependencies properly
# - Must provide clear progress updates
# - Should generate well-structured implementation plans
###############################################################################
# [Dependencies]
# system:typing
# system:pathlib
# system:os
# system:agno
# codebase:src/dbp_cli/commands/hstc_agno/agents.py
# codebase:src/dbp_cli/commands/hstc_agno/models.py
# codebase:src/dbp_cli/commands/hstc_agno/utils.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:08:00Z : Initial implementation by CodeAssistant
# * Created manager class skeleton
# * Added basic initialization structure
###############################################################################

import json
import os
import time
import traceback
import glob
import concurrent.futures
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Set, Union

from .agents import FileAnalyzerAgent, DocumentationGeneratorAgent
from .utils import get_current_timestamp


class HSTCManager:
    """
    [Class intent]
    Manager for HSTC file processing and documentation generation. Orchestrates
    the workflow between agents and handles the overall HSTC update process.
    
    [Design principles]
    Maintains clear separation between orchestration logic and agent functionality.
    Provides centralized state management and progress tracking.
    
    [Implementation details]
    Coordinates the File Analyzer and Documentation Generator agents.
    Manages file dependencies and processing order.
    Generates implementation plans based on processing results.
    """
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        [Class method intent]
        Initializes the HSTC Manager with the specified base directory.
        
        [Design principles]
        Uses sensible defaults with optional customization.
        Establishes a solid foundation for the manager operations.
        
        [Implementation details]
        Sets up the base directory for file operations.
        Initializes agents and state storage for processing.
        
        Args:
            base_dir: Base directory for file operations (defaults to current working directory)
        """
        self.base_dir = base_dir or Path.cwd()
        self.file_analyzer = None
        self.doc_generator = None
        self.processed_files: Dict[str, Any] = {}
        self.dependency_cache: Dict[str, Any] = {}
        
        # Initialize agents
        self.initialize_agents()
    
    def initialize_agents(self):
        """
        [Function intent]
        Initialize the File Analyzer and Documentation Generator agents.
        
        [Design principles]
        Ensures agents are properly configured for the current environment.
        Centralizes agent creation for consistent configuration.
        
        [Implementation details]
        Creates agent instances with appropriate parameters.
        Configures base directory for file operations.
        """
        # Create File Analyzer Agent
        self.file_analyzer = FileAnalyzerAgent(base_dir=self.base_dir)
        
        # Create Documentation Generator Agent
        self.doc_generator = DocumentationGeneratorAgent()
    
    def process_file(self, file_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Process a file through the entire HSTC workflow.
        
        [Design principles]
        Orchestrates the complete processing pipeline for a single file.
        Handles errors gracefully with comprehensive reporting.
        
        [Implementation details]
        Validates file path, analyzes the file, generates documentation,
        validates results, and produces implementation plans.
        Captures and reports errors during processing.
        
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
            return {
                "error": str(e),
                "traceback": traceback.format_exc(),
                "file_path": file_path
            }
    
    def _validate_file_path(self, file_path: str) -> bool:
        """
        [Function intent]
        Validate that the file path exists and is a file.
        
        [Design principles]
        Provides basic input validation before processing.
        Prevents errors from invalid file paths early in the process.
        
        [Implementation details]
        Checks if the path exists and is a file.
        Returns a boolean indicating validity.
        
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
    
    def analyze_file(self, file_path: str, recursive: bool = False) -> Dict[str, Any]:
        """
        [Function intent]
        Analyze a source file using the File Analyzer Agent.
        
        [Design principles]
        Manages file analysis with caching for efficient processing.
        Supports recursive dependency analysis when needed.
        
        [Implementation details]
        Checks cache before processing to avoid redundant work.
        Triggers dependency processing for recursive analysis.
        Stores results in the processed_files cache.
        
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
    
    def _process_dependencies(self, file_path: str, file_metadata: Dict[str, Any]) -> None:
        """
        [Function intent]
        Process dependencies of a file recursively.
        
        [Design principles]
        Ensures comprehensive analysis of related files.
        Prevents infinite recursion with dependency caching.
        
        [Implementation details]
        Extracts dependencies from file metadata.
        Resolves relative paths for codebase dependencies.
        Recursively analyzes each dependency.
        
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
    
    def generate_documentation(self, file_path: str) -> Dict[str, Any]:
        """
        [Function intent]
        Generate documentation for a file using the Documentation Generator Agent.
        
        [Design principles]
        Leverages file analysis results to produce high-quality documentation.
        Provides contextual information about dependencies for better documentation.
        
        [Implementation details]
        Retrieves file metadata from cache or triggers analysis.
        Collects dependency information for context-aware generation.
        Uses the DocumentationGeneratorAgent for actual generation.
        
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
    
    def validate_documentation(self, file_path: str) -> Dict[str, Any]:
        """
        [Function intent]
        Validate generated documentation against HSTC standards.
        
        [Design principles]
        Ensures documentation meets quality standards before plan generation.
        Provides actionable feedback for documentation issues.
        
        [Implementation details]
        Delegates validation to the DocumentationGeneratorAgent.
        Returns structured validation results with issues if found.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dict containing validation results
        """
        return self.doc_generator.validate_documentation(file_path)
    
    def _output_dir(self, file_path: str, output_path: Optional[str] = None) -> str:
        """
        [Function intent]
        Determine output directory for implementation plan.
        
        [Design principles]
        Supports user-specified output locations while providing sensible defaults.
        Ensures output directories exist before writing files.
        
        [Implementation details]
        Uses specified output path if provided.
        Creates a default path in the scratchpad directory if not specified.
        Creates directories recursively if they don't exist.
        
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
    
    def generate_implementation_plan(
        self, 
        file_path: str, 
        documentation: Dict[str, Any], 
        output_path: str
    ) -> List[str]:
        """
        [Function intent]
        Generate markdown implementation plan files.
        
        [Design principles]
        Creates clear, actionable implementation plans for documentation updates.
        Structures content for different stakeholder needs.
        
        [Implementation details]
        Creates overview, implementation details, and progress tracking files.
        Formats content based on documentation analysis and validation.
        Returns paths to all generated files.
        
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
    
    def _generate_overview_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """
        [Function intent]
        Generate overview markdown content for implementation plan.
        
        [Design principles]
        Provides high-level summary of the implementation plan.
        Includes key metrics and status information.
        
        [Implementation details]
        Extracts file information and validation status.
        Formats content in structured markdown sections.
        
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
    
    def _generate_implementation_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """
        [Function intent]
        Generate implementation markdown content with detailed changes.
        
        [Design principles]
        Provides detailed view of all documentation changes.
        Organizes content by file header and individual definitions.
        
        [Implementation details]
        Extracts header and definition documentation.
        Formats both original and updated content for comparison.
        Structures content in clear markdown sections.
        
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
    
    def _generate_progress_markdown(self, file_path: str, documentation: Dict[str, Any]) -> str:
        """
        [Function intent]
        Generate progress tracking markdown for implementation.
        
        [Design principles]
        Provides clear tracking of implementation progress.
        Uses simple visual indicators for status reporting.
        
        [Implementation details]
        Creates a task list with status indicators.
        Includes items for file header and each definition.
        Uses emoji status markers for visual clarity.
        
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
    
    def _generate_error_report(self, file_path: str, error_info: Dict[str, Any]) -> str:
        """
        [Function intent]
        Generate an error report when processing fails.
        
        [Design principles]
        Provides detailed diagnostic information for troubleshooting.
        Preserves partial results when available.
        
        [Implementation details]
        Creates an error report with exception details and traceback.
        Includes partial analysis results if available.
        Saves report to a dedicated directory.
        
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
        [Function intent]
        Process a file with comprehensive error handling.
        
        [Design principles]
        Ensures processing failures don't halt overall workflow.
        Provides detailed error information for diagnosis.
        
        [Implementation details]
        Wraps process_file with exception handling.
        Generates error reports for failed processing.
        Returns structured error information.
        
        Args:
            file_path: Path to the file
            options: Processing options
            
        Returns:
            Dict containing processing results or error information
        """
        try:
            return self.process_file(file_path, options)
        except Exception as e:
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
    
    def process_multiple_files(self, file_paths: List[str], options: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        [Function intent]
        Process multiple files with parallel execution.
        
        [Design principles]
        Maximizes throughput with concurrent processing.
        Maintains individual error handling for each file.
        
        [Implementation details]
        Uses a thread pool for concurrent file processing.
        Collects results as files complete processing.
        Provides progress reporting during execution.
        
        Args:
            file_paths: List of file paths to process
            options: Processing options
            
        Returns:
            List of processing results
        """
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
    
    def process_directory(self, directory_path: str, options: Dict[str, Any]) -> Dict[str, Any]:
        """
        [Function intent]
        Process all relevant files in a directory.
        
        [Design principles]
        Supports batch processing of entire directories.
        Provides flexible file filtering with patterns.
        
        [Implementation details]
        Finds files matching specified patterns.
        Supports recursive directory traversal.
        Processes all matching files in parallel.
        
        Args:
            directory_path: Path to the directory
            options: Processing options including:
                - recursive_dir: Whether to search subdirectories
                - file_patterns: List of file patterns to include
            
        Returns:
            Dict containing processing results
        """
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
    
    def clear_cache(self) -> None:
        """
        [Function intent]
        Clear the internal cache of processed files.
        
        [Design principles]
        Supports fresh processing when needed.
        Clears all levels of caching for consistency.
        
        [Implementation details]
        Resets internal cache dictionaries.
        Clears agent caches for completeness.
        """
        self.processed_files = {}
        self.dependency_cache = {}
        
        # Clear agent caches
        if self.file_analyzer:
            self.file_analyzer.clear_metadata()
        if self.doc_generator:
            self.doc_generator.clear_documentation()
    
    def save_cache(self, cache_path: str) -> None:
        """
        [Function intent]
        Save the internal cache to a file for persistence.
        
        [Design principles]
        Enables processing resumption across sessions.
        Preserves work for large-scale processing.
        
        [Implementation details]
        Serializes cache data to JSON format.
        Includes timestamp for cache freshness tracking.
        
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
        [Function intent]
        Load the internal cache from a file.
        
        [Design principles]
        Provides processing continuity between sessions.
        Handles cache loading failures gracefully.
        
        [Implementation details]
        Deserializes cache data from JSON format.
        Restores internal state from cached data.
        Returns success/failure status.
        
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


# Example usage
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
