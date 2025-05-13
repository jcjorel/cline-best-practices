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
# This file defines the CLI command group for the HSTC implementation using the Agno
# framework. It provides user-friendly commands for updating HSTC documentation and
# generating implementation plans using Amazon Bedrock models integrated through Agno.
###############################################################################
# [Source file design principles]
# - Clear separation between CLI interface and implementation logic
# - Consistent command structure and naming
# - Informative help messages and documentation for all commands
# - Error handling with user-friendly messages
###############################################################################
# [Source file constraints]
# - Must maintain compatibility with the Click framework
# - Should follow the design patterns of the existing CLI
# - Commands must provide progress feedback for long-running operations
###############################################################################
# [Dependencies]
# system:click
# system:pathlib
# codebase:src/dbp_cli/commands/hstc_agno/manager.py
###############################################################################
# [GenAI tool change history]
# 2025-05-12T07:06:30Z : Initial implementation by CodeAssistant
# * Created basic CLI command group structure
# * Added update command skeleton
###############################################################################

import click
import os
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional

from .manager import HSTCManager


@click.group()
def hstc_agno():
    """
    [Function intent]
    HSTC implementation with Agno framework, using Amazon Bedrock models.
    
    [Design principles]
    Groups related commands under a consistent namespace.
    Follows Click group pattern for extensibility.
    
    [Implementation details]
    Serves as a container for HSTC-related commands using the Agno framework.
    
    This command group provides tools for managing Hierarchical Semantic Tree Context (HSTC)
    documentation using the Agno framework and Amazon Bedrock models.
    
    Examples:
    
    \b
    # Update documentation for a single file
    dbp_cli hstc_agno update path/to/file.py
    
    \b
    # Update documentation for all Python files in a directory
    dbp_cli hstc_agno update-dir src/module --pattern "*.py"
    
    \b
    # Check documentation status for a file
    dbp_cli hstc_agno status path/to/file.py --verbose
    
    \b
    # View generated documentation
    dbp_cli hstc_agno view path/to/file.py --output-format markdown
    """
    pass


def get_file_completions(ctx, param, incomplete):
    """Return completions for file paths."""
    import glob
    for f in glob.glob(f"{incomplete}*"):
        yield f


def get_dir_completions(ctx, param, incomplete):
    """Return completions for directory paths."""
    import glob
    for f in glob.glob(f"{incomplete}*"):
        if os.path.isdir(f):
            yield f


class ProgressBar:
    """Simple progress bar context manager."""
    def __init__(self, message):
        self.message = message
    
    def __enter__(self):
        click.echo(self.message, nl=False)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        click.echo(" Done!")


@hstc_agno.command("update")
@click.argument("file_path", type=str, shell_complete=get_file_completions)
@click.option("--output", "-o", help="Output directory for implementation plan")
@click.option("--recursive/--no-recursive", default=False, 
              help="Process dependencies recursively")
@click.option("--verbose/--quiet", default=False,
              help="Show detailed output")
def update(file_path: str, output: Optional[str], recursive: bool, verbose: bool):
    """
    [Function intent]
    Update documentation for a source file using Agno-powered analysis.
    
    [Design principles]
    Provides a simple interface for the most common HSTC operation.
    Uses clear options with sensible defaults.
    
    [Implementation details]
    Processes a source file to generate or update HSTC documentation.
    Can work recursively to process dependencies as well.
    
    Args:
        file_path: Path to the source file to process
        output: Directory where implementation plan will be saved (optional)
        recursive: Whether to process dependencies recursively
        verbose: Whether to show detailed output
    """
    # Initialize options dictionary
    options = {
        "output": output,
        "recursive": recursive,
        "verbose": verbose
    }
    
    # Create HSTC Manager and process file
    with ProgressBar("Initializing HSTC Manager..."):
        manager = HSTCManager(base_dir=Path.cwd())
    
    with ProgressBar(f"Processing {file_path}..."):
        result = manager.process_file(file_path, options)
    
    # Display results
    if "error" in result:
        click.echo(click.style(f"Error: {result['error']}", fg="red"))
        if verbose and "traceback" in result:
            click.echo(click.style("Traceback:", fg="red"))
            click.echo(result["traceback"])
        return
    
    click.echo(click.style("✅ HSTC processing completed successfully!", fg="green"))
    click.echo(f"Implementation plan generated at: {result['plan_path']}")
    
    if "validation" in result and result["validation"].get("issues"):
        click.echo(click.style("⚠️ Validation issues:", fg="yellow"))
        for issue in result["validation"].get("issues", []):
            click.echo(f"  - {issue}")
    
    # Show summary of generated documentation
    if verbose:
        documentation = result.get("documentation", {})
        click.echo("\nDocumentation Summary:")
        click.echo(f"- File type: {documentation.get('file_type', 'unknown')}")
        click.echo(f"- Language: {documentation.get('language', 'unknown')}")
        click.echo(f"- Definitions documented: {len(documentation.get('definitions', []))}")


@hstc_agno.command("update-dir")
@click.argument("directory_path", type=str, shell_complete=get_dir_completions)
@click.option("--output", "-o", help="Output directory for implementation plans")
@click.option("--recursive/--no-recursive", default=False,
              help="Process dependencies recursively")
@click.option("--recursive-dir/--no-recursive-dir", default=False,
              help="Process subdirectories recursively")
@click.option("--pattern", "-p", multiple=True,
              help="File patterns to include (e.g., '*.py', '*.js')")
@click.option("--verbose/--quiet", default=False,
              help="Show detailed output")
def update_directory(
    directory_path: str, 
    output: Optional[str], 
    recursive: bool,
    recursive_dir: bool,
    pattern: List[str],
    verbose: bool
):
    """
    [Function intent]
    Update documentation for all matching files in a directory.
    
    [Design principles]
    Provides batch processing capabilities for efficient documentation updates.
    Supports flexible file selection with pattern matching.
    
    [Implementation details]
    Recursively processes files in the specified directory based on patterns.
    Uses parallel processing for efficient handling of multiple files.
    
    Args:
        directory_path: Path to the directory to process
        output: Directory where implementation plans will be saved (optional)
        recursive: Whether to process dependencies recursively
        recursive_dir: Whether to process subdirectories recursively
        pattern: File patterns to include (can be specified multiple times)
        verbose: Whether to show detailed output
    """
    # Initialize options dictionary
    options = {
        "output": output,
        "recursive": recursive,
        "recursive_dir": recursive_dir,
        "verbose": verbose,
        "file_patterns": list(pattern) if pattern else ["*.py", "*.js", "*.ts", "*.java", "*.c", "*.cpp", "*.h", "*.hpp"]
    }
    
    # Create HSTC Manager and process directory
    with ProgressBar("Initializing HSTC Manager..."):
        manager = HSTCManager(base_dir=Path.cwd())
    
    with ProgressBar(f"Processing directory {directory_path}..."):
        result = manager.process_directory(directory_path, options)
    
    # Display results
    click.echo(f"\nProcessed {result['files_processed']} files")
    
    successful = sum(1 for r in result['results'] if "error" not in r)
    failed = sum(1 for r in result['results'] if "error" in r)
    
    click.echo(click.style(f"✅ Successful: {successful}", fg="green"))
    if failed > 0:
        click.echo(click.style(f"❌ Failed: {failed}", fg="red"))
    
    # Show detailed results if verbose
    if verbose and failed > 0:
        click.echo("\nFailed files:")
        for r in result['results']:
            if "error" in r:
                click.echo(f"  - {r.get('file_path', 'unknown')}: {r['error']}")


@hstc_agno.command("status")
@click.argument("file_path", type=str, shell_complete=get_file_completions)
@click.option("--verbose/--quiet", default=False,
              help="Show detailed output")
def status(file_path: str, verbose: bool):
    """
    [Function intent]
    Check the status of HSTC documentation for a file or directory.
    
    [Design principles]
    Provides a quick overview of documentation status without full processing.
    Focuses on key metrics for documentation quality assessment.
    
    [Implementation details]
    Uses file analyzer to examine documentation without generating updates.
    Shows presence/absence of key documentation components.
    
    Args:
        file_path: Path to the file or directory to check
        verbose: Whether to show detailed output
    """
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Check if path is a file or directory
    if os.path.isfile(file_path):
        # Process single file
        with ProgressBar(f"Analyzing {file_path}..."):
            file_metadata = manager.file_analyzer.analyze_file(file_path)
        
        # Display results
        click.echo(f"File: {file_path}")
        click.echo(f"Type: {file_metadata.get('file_type', 'unknown')}")
        click.echo(f"Language: {file_metadata.get('language', 'unknown')}")
        
        if file_metadata.get("file_type") == "source_code":
            # Check for header comment
            has_header = bool(file_metadata.get("header_comment"))
            if has_header:
                click.echo(click.style("✅ Has header documentation", fg="green"))
            else:
                click.echo(click.style("❌ Missing header documentation", fg="red"))
            
            # Check definitions
            definitions = file_metadata.get("definitions", [])
            documented_defs = sum(1 for d in definitions if d.get("comments"))
            click.echo(f"Definitions: {len(definitions)} (documented: {documented_defs})")
            
            if verbose and definitions:
                click.echo("\nDefinitions:")
                for definition in definitions:
                    name = definition.get("name", "unknown")
                    has_docs = bool(definition.get("comments"))
                    if has_docs:
                        click.echo(f"  ✅ {name}")
                    else:
                        click.echo(f"  ❌ {name}")
            
            # Display dependencies
            dependencies = file_metadata.get("dependencies", [])
            if dependencies and verbose:
                click.echo("\nDependencies:")
                for dep in dependencies:
                    dep_name = dep.get("name", "unknown")
                    dep_kind = dep.get("kind", "unknown")
                    click.echo(f"  - {dep_name} ({dep_kind})")
    
    elif os.path.isdir(file_path):
        click.echo(f"Directory: {file_path}")
        click.echo("Use 'hstc_agno update-dir' to process all files in the directory.")
    
    else:
        click.echo(click.style(f"Error: '{file_path}' is not a valid file or directory", fg="red"))


@hstc_agno.command("view")
@click.argument("file_path", type=str, shell_complete=get_file_completions)
@click.option("--output-format", "-f", type=click.Choice(["text", "json", "markdown"]), default="text",
              help="Output format")
def view(file_path: str, output_format: str):
    """
    [Function intent]
    View the generated HSTC documentation for a file.
    
    [Design principles]
    Provides multiple output formats for different use cases.
    Focuses on readability and information organization.
    
    [Implementation details]
    Analyzes the file and formats the documentation according to the specified format.
    Structures output to highlight key documentation components.
    
    Args:
        file_path: Path to the file to view
        output_format: Format for displaying the documentation
    """
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Process the file
    with ProgressBar(f"Analyzing {file_path}..."):
        file_metadata = manager.file_analyzer.analyze_file(file_path)
    
    with ProgressBar("Generating documentation..."):
        documentation = manager.generate_documentation(file_path)
    
    # Display in selected format
    if output_format == "json":
        click.echo(json.dumps(documentation, indent=2))
    
    elif output_format == "markdown":
        # Generate markdown representation
        md = f"# HSTC Documentation for {file_path}\n\n"
        
        # Add file header
        md += "## File Header\n\n"
        if "file_header" in documentation:
            md += f"### Intent\n\n{documentation['file_header'].get('intent', '')}\n\n"
            md += f"### Design Principles\n\n{documentation['file_header'].get('design_principles', '')}\n\n"
            md += f"### Constraints\n\n{documentation['file_header'].get('constraints', '')}\n\n"
            
            # Add dependencies
            deps = documentation['file_header'].get('dependencies', [])
            if deps:
                md += "### Dependencies\n\n"
                for dep in deps:
                    md += f"- `{dep.get('kind', 'unknown')}:{dep.get('dependency', '')}`\n"
                md += "\n"
        
        # Add definitions
        if "definitions" in documentation:
            md += "## Definitions\n\n"
            for definition in documentation.get("definitions", []):
                md += f"### {definition.get('name')} ({definition.get('type')})\n\n"
                md += f"```{documentation.get('language', '')}\n{definition.get('updated_comment', '')}\n```\n\n"
        
        click.echo(md)
    
    else:  # text format
        # Display as formatted text
        click.echo(f"HSTC Documentation for {file_path}\n")
        
        # File header
        click.echo("File Header:")
        if "file_header" in documentation:
            header_intent = documentation['file_header'].get('intent', '')
            click.echo(f"  Intent: {header_intent[:80]}..." if len(header_intent) > 80 else f"  Intent: {header_intent}")
            
            header_principles = documentation['file_header'].get('design_principles', '')
            click.echo(f"  Design Principles: {header_principles[:80]}..." if len(header_principles) > 80 else f"  Design Principles: {header_principles}")
            
            header_constraints = documentation['file_header'].get('constraints', '')
            click.echo(f"  Constraints: {header_constraints[:80]}..." if len(header_constraints) > 80 else f"  Constraints: {header_constraints}")
            
            # Dependencies
            deps = documentation['file_header'].get('dependencies', [])
            if deps:
                click.echo("  Dependencies:")
                for dep in deps:
                    click.echo(f"    - {dep.get('kind', 'unknown')}:{dep.get('dependency', '')}")
        
        # Definitions
        if "definitions" in documentation:
            click.echo("\nDefinitions:")
            for definition in documentation.get("definitions", []):
                click.echo(f"  {definition.get('name')} ({definition.get('type')})")
                # Display first few lines of updated comment
                updated_comment = definition.get('updated_comment', '').split('\n')
                for i, line in enumerate(updated_comment[:3]):
                    click.echo(f"    {line}")
                if len(updated_comment) > 3:
                    click.echo("    ...")


@hstc_agno.command("clear-cache")
def clear_cache():
    """
    [Function intent]
    Clear the HSTC cache to ensure fresh processing.
    
    [Design principles]
    Provides simple cache management for troubleshooting.
    Maintains clean state between processing runs.
    
    [Implementation details]
    Removes all stored analysis results from memory.
    Creates a fresh processing environment.
    """
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Clear cache
    manager.clear_cache()
    
    click.echo("Cache cleared successfully.")


@hstc_agno.command("save-cache")
@click.argument("cache_path", type=str)
def save_cache(cache_path: str):
    """
    [Function intent]
    Save the HSTC cache to a file for persistence.
    
    [Design principles]
    Enables processing continuity across sessions.
    Preserves analysis results for large projects.
    
    [Implementation details]
    Serializes cache data to JSON format.
    Includes timestamp for cache freshness tracking.
    
    Args:
        cache_path: Path to save the cache file
    """
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Save cache
    manager.save_cache(cache_path)
    
    click.echo(f"Cache saved to {cache_path}.")


@hstc_agno.command("load-cache")
@click.argument("cache_path", type=str, shell_complete=get_file_completions)
def load_cache(cache_path: str):
    """
    [Function intent]
    Load the HSTC cache from a file for reuse.
    
    [Design principles]
    Supports processing continuation between sessions.
    Enables efficient reuse of previous analysis results.
    
    [Implementation details]
    Deserializes cache data from JSON format.
    Verifies cache integrity before loading.
    
    Args:
        cache_path: Path to the cache file to load
    """
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Load cache
    success = manager.load_cache(cache_path)
    
    if success:
        click.echo(f"Cache loaded from {cache_path}.")
    else:
        click.echo(click.style(f"Error: Failed to load cache from {cache_path}", fg="red"))
