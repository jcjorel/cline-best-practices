# HSTC Implementation with Agno - Phase 6: CLI Integration

This document outlines the detailed steps to implement the CLI integration for the HSTC implementation using the Agno framework.

## Overview

The CLI integration is responsible for:

1. Exposing the HSTC functionality through the command-line interface
2. Providing user-friendly commands and options
3. Formatting and displaying results to the user
4. Integrating with the existing CLI framework

This component provides the user-facing interface to the HSTC functionality.

## Prerequisites

Ensure that Phases 1 through 5 are completed:
- The basic project structure is in place
- Data models and utility functions are implemented
- The File Analyzer Agent is functional
- The Documentation Generator Agent is functional
- The HSTC Manager is functional

## Step 1: Implement the CLI Command Group

Create the main command group for the HSTC functionality:

```python
# src/dbp_cli/commands/hstc_agno/cli.py

import click
import os
from pathlib import Path
from typing import Dict, Any, List, Optional

from .manager import HSTCManager
from dbp_cli.progress import progress_bar  # Assuming a progress bar utility exists

@click.group()
def hstc_agno():
    """HSTC implementation with Agno framework."""
    pass
```

## Step 2: Implement the Update Command

Add the main update command that processes a file and updates its documentation:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add to hstc_agno group)

@hstc_agno.command("update")
@click.argument("file_path", type=str)
@click.option("--output", "-o", help="Output directory for implementation plan")
@click.option("--recursive/--no-recursive", default=False, 
              help="Process dependencies recursively")
@click.option("--verbose/--quiet", default=False,
              help="Show detailed output")
def update(file_path: str, output: Optional[str], recursive: bool, verbose: bool):
    """Update documentation for a source file using Agno-powered analysis."""
    
    # Initialize options dictionary
    options = {
        "output": output,
        "recursive": recursive,
        "verbose": verbose
    }
    
    # Create HSTC Manager and process file
    with progress_bar("Initializing HSTC Manager..."):
        manager = HSTCManager(base_dir=Path.cwd())
    
    with progress_bar(f"Processing {file_path}..."):
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
```

## Step 3: Implement the Update Directory Command

Add a command to update documentation for all files in a directory:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add to hstc_agno group)

@hstc_agno.command("update-dir")
@click.argument("directory_path", type=str)
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
    """Update documentation for all matching files in a directory."""
    
    # Initialize options dictionary
    options = {
        "output": output,
        "recursive": recursive,
        "recursive_dir": recursive_dir,
        "verbose": verbose,
        "file_patterns": list(pattern) if pattern else ["*.py", "*.js", "*.ts", "*.java", "*.c", "*.cpp", "*.h", "*.hpp"]
    }
    
    # Create HSTC Manager and process directory
    with progress_bar("Initializing HSTC Manager..."):
        manager = HSTCManager(base_dir=Path.cwd())
    
    with progress_bar(f"Processing directory {directory_path}..."):
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
```

## Step 4: Implement a Status Command

Add a command to check the status of HSTC documentation:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add to hstc_agno group)

@hstc_agno.command("status")
@click.argument("file_path", type=str)
@click.option("--verbose/--quiet", default=False,
              help="Show detailed output")
def status(file_path: str, verbose: bool):
    """Check the status of HSTC documentation for a file or directory."""
    
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Check if path is a file or directory
    if os.path.isfile(file_path):
        # Process single file
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
```

## Step 5: Implement a View Command

Add a command to view the generated documentation:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add to hstc_agno group)

@hstc_agno.command("view")
@click.argument("file_path", type=str)
@click.option("--output-format", "-f", type=click.Choice(["text", "json", "markdown"]), default="text",
              help="Output format")
def view(file_path: str, output_format: str):
    """View the generated HSTC documentation for a file."""
    
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Process the file
    file_metadata = manager.file_analyzer.analyze_file(file_path)
    documentation = manager.generate_documentation(file_path)
    
    # Display in selected format
    if output_format == "json":
        import json
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
            click.echo(f"  Intent: {documentation['file_header'].get('intent', '')[:80]}...")
            click.echo(f"  Design Principles: {documentation['file_header'].get('design_principles', '')[:80]}...")
            click.echo(f"  Constraints: {documentation['file_header'].get('constraints', '')[:80]}...")
            
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
```

## Step 6: Implement a Cache Management Command

Add commands for managing the cache:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add to hstc_agno group)

@hstc_agno.command("clear-cache")
def clear_cache():
    """Clear the HSTC cache."""
    
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Clear cache
    manager.clear_cache()
    
    click.echo("Cache cleared.")

@hstc_agno.command("save-cache")
@click.argument("cache_path", type=str)
def save_cache(cache_path: str):
    """Save the HSTC cache to a file."""
    
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Save cache
    manager.save_cache(cache_path)
    
    click.echo(f"Cache saved to {cache_path}.")

@hstc_agno.command("load-cache")
@click.argument("cache_path", type=str)
def load_cache(cache_path: str):
    """Load the HSTC cache from a file."""
    
    # Create HSTC Manager
    manager = HSTCManager(base_dir=Path.cwd())
    
    # Load cache
    success = manager.load_cache(cache_path)
    
    if success:
        click.echo(f"Cache loaded from {cache_path}.")
    else:
        click.echo(click.style(f"Error: Failed to load cache from {cache_path}", fg="red"))
```

## Step 7: Implement Command Help and Examples

Add detailed help and examples for the commands:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Update hstc_agno group docstring)

@click.group()
def hstc_agno():
    """HSTC implementation with Agno framework.
    
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
```

## Step 8: Define Command Completion Functions

Add command completion functions for better usability:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add after command definitions)

def get_file_completions(ctx, param, incomplete):
    """Return completions for file paths."""
    import glob
    for f in glob.glob(f"{incomplete}*"):
        yield f

def get_dir_completions(ctx, param, incomplete):
    """Return completions for directory paths."""
    import glob
    import os
    for f in glob.glob(f"{incomplete}*"):
        if os.path.isdir(f):
            yield f

# Update argument declarations to use completions
# For example:
# @click.argument("file_path", type=str, autocompletion=get_file_completions)
```

## Step 9: Register CLI Command Group

Update the command registration to include our command group:

```python
# src/dbp_cli/commands/__init__.py (modified part)

from .hstc_agno.cli import hstc_agno  # Import our command group

def register_commands(cli_group):
    """Register all CLI commands with the main cli_group."""
    # Register existing command groups...
    
    # Register the HSTC Agno command group
    cli_group.add_command(hstc_agno)
```

## Step 10: Add Global Options

Update the CLI commands to handle global options:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add function at the end of the file)

def set_default_options_from_config(ctx, param, value):
    """Load default options from configuration."""
    # Example implementation to load options from a config file
    import os
    config_file = os.path.expanduser("~/.dbp_cli/config.json")
    
    if os.path.exists(config_file):
        import json
        with open(config_file, 'r') as f:
            try:
                config = json.load(f)
                hstc_config = config.get("hstc_agno", {})
                
                # Apply config to context
                ctx = ctx or click.get_current_context()
                
                # Only set values that aren't already set
                for param_name, param_value in hstc_config.items():
                    if param_name not in ctx.params or ctx.params[param_name] is None:
                        ctx.params[param_name] = param_value
            except json.JSONDecodeError:
                pass
    
    return value

# Apply to all commands
# For example:
# @click.option("--config", is_flag=True, callback=set_default_options_from_config,
#               expose_value=False, is_eager=True, help="Load default options from config")
```

## Step 11: Add Progress Reporting

Add progress reporting functionality:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (Add function for use in commands)

def display_progress(current: int, total: int, task: str = None):
    """Display progress bar."""
    from tqdm import tqdm
    
    # Use tqdm to display progress
    with tqdm(total=total, desc=task) as pbar:
        pbar.update(current)
```

## Step 12: Test CLI Command Registration

To test that the command is properly registered:

```bash
# Make the package discoverable (if needed)
export PYTHONPATH=$PYTHONPATH:/path/to/project

# Run the help command to see if it's registered
python -m dbp_cli hstc_agno --help
```

## Step 13: Create User Documentation

Create a README file to document the CLI usage:

```markdown
# HSTC Agno CLI Commands

This document describes the command-line interface for the HSTC implementation with Agno.

## Command Overview

The `hstc_agno` command group provides tools for managing Hierarchical Semantic Tree Context (HSTC)
documentation using the Agno framework and Amazon Bedrock models.

### Available Commands

- `update`: Update documentation for a single file
- `update-dir`: Update documentation for all files in a directory
- `status`: Check documentation status for a file or directory
- `view`: View the generated documentation
- `clear-cache`: Clear the HSTC cache
- `save-cache`: Save the HSTC cache to a file
- `load-cache`: Load the HSTC cache from a file

## Usage Examples

### Update a single file

```bash
dbp_cli hstc_agno update path/to/file.py
```

### Update all Python files in a directory

```bash
dbp_cli hstc_agno update-dir src/module --pattern "*.py"
```

### Check documentation status

```bash
dbp_cli hstc_agno status path/to/file.py --verbose
```

### View generated documentation

```bash
dbp_cli hstc_agno view path/to/file.py --output-format markdown
```

## Options

### Global Options

- `--verbose/--quiet`: Show detailed output

### Update Options

- `--output, -o`: Output directory for implementation plan
- `--recursive/--no-recursive`: Process dependencies recursively

### Update Directory Options

- `--output, -o`: Output directory for implementation plans
- `--recursive/--no-recursive`: Process dependencies recursively
- `--recursive-dir/--no-recursive-dir`: Process subdirectories recursively
- `--pattern, -p`: File patterns to include (can be specified multiple times)

### View Options

- `--output-format, -f`: Output format (text, json, markdown)
```

Save this file as `src/dbp_cli/commands/hstc_agno/README.md`.

## Expected Output

After completing this phase, you should have a fully functional CLI interface that:

1. Exposes the HSTC functionality through user-friendly commands
2. Provides options for controlling the behavior of the HSTC functionality
3. Displays results in a clear and informative manner
4. Integrates with the existing CLI framework

This interface allows users to easily interact with the HSTC functionality.

## Next Steps

Proceed to Phase 7 (Testing and Validation) to implement comprehensive tests for the HSTC functionality.
