# HSTC Implementation with Agno - Phase 1: Project Setup and Structure

This document outlines the detailed steps to set up the project structure for the HSTC implementation using the Agno framework.

## Prerequisites

Before starting the implementation, ensure the following prerequisites are met:

1. Python 3.9 or higher is installed
2. Access to AWS credentials for using Amazon Bedrock services
3. The Agno framework is available for installation
4. The existing DBP CLI project structure is accessible

## Step 1: Create Directory Structure

Create the necessary directory structure for the HSTC Agno implementation:

```bash
# Create the main module directory
mkdir -p src/dbp_cli/commands/hstc_agno

# Create necessary __init__.py files to make the package importable
touch src/dbp_cli/commands/hstc_agno/__init__.py
```

## Step 2: Create Package Files

Create the following empty files that will be implemented in later phases:

```bash
touch src/dbp_cli/commands/hstc_agno/agents.py     # Agent implementations
touch src/dbp_cli/commands/hstc_agno/cli.py        # CLI command definitions
touch src/dbp_cli/commands/hstc_agno/manager.py    # HSTC Manager implementation
touch src/dbp_cli/commands/hstc_agno/models.py     # Data models
touch src/dbp_cli/commands/hstc_agno/utils.py      # Utility functions
```

## Step 3: Configure `__init__.py`

Set up the module initialization file with basic imports and version information:

```python
# src/dbp_cli/commands/hstc_agno/__init__.py

"""HSTC implementation using the Agno framework."""

__version__ = '0.1.0'

from .cli import hstc_agno  # Import the CLI command group for registration
```

## Step 4: Update Dependencies

Ensure the project has the necessary dependencies by adding the following to the project's `requirements.txt` file:

```
agno>=1.0.0
boto3>=1.28.0
click>=8.1.0
```

If using a `setup.py` file, update the dependencies there as well:

```python
# In setup.py

install_requires=[
    # Existing dependencies...
    'agno>=1.0.0',
    'boto3>=1.28.0',
]
```

## Step 5: Set Up AWS Credentials Configuration

Create a configuration utility to handle AWS credentials for Bedrock access:

```python
# src/dbp_cli/commands/hstc_agno/utils.py (initial setup)

import os
import boto3
from typing import Optional

def get_bedrock_client(region: Optional[str] = None) -> boto3.Session:
    """
    Get a Bedrock client session with proper configuration.
    
    Args:
        region: AWS region (optional, defaults to environment variable or 'us-west-2')
        
    Returns:
        boto3.Session: Configured Bedrock session
    """
    region = region or os.environ.get('AWS_REGION', 'us-west-2')
    
    # Create a Boto3 session with the specified region
    session = boto3.Session(region_name=region)
    
    return session
```

## Step 6: Configure Basic CLI Structure

Create a skeleton for the CLI command group:

```python
# src/dbp_cli/commands/hstc_agno/cli.py (initial setup)

import click
from pathlib import Path

@click.group()
def hstc_agno():
    """HSTC implementation with Agno framework."""
    pass

@hstc_agno.command("update")
@click.argument("file_path", type=str)
@click.option("--output", "-o", help="Output directory for implementation plan")
@click.option("--recursive/--no-recursive", default=False, 
              help="Process dependencies recursively")
def update(file_path: str, output: str, recursive: bool):
    """Update documentation for a source file using Agno-powered analysis."""
    click.echo(f"Will process {file_path} (placeholder for implementation)")
```

## Step 7: Register Command with Main CLI

Update the command registration to include the new command group:

```python
# Placeholder for modification to src/dbp_cli/commands/__init__.py

from .hstc_agno.cli import hstc_agno  # Import the new command group

def register_commands(cli_group):
    """Register all commands with the main CLI group."""
    # Existing registrations...
    
    # Register the HSTC Agno command
    cli_group.add_command(hstc_agno)
```

## Step 8: Create Agent Class Skeletons

Create basic skeletons for the agent classes:

```python
# src/dbp_cli/commands/hstc_agno/agents.py (initial setup)

from agno.agent import Agent
from agno.models import BedrockNovaModel
from agno.models.anthropic import Claude
from typing import Dict, Any, Optional

class FileAnalyzerAgent(Agent):
    """Agent for analyzing source files using Nova Micro."""
    
    def __init__(self, model_id: str = "anthropic.claude-3-haiku-20240307-v1:0", **kwargs):
        # Initialize Nova model for file analysis
        model = BedrockNovaModel(id=model_id)
        super().__init__(model=model, **kwargs)
        
        # To be implemented in Phase 3
        pass

class DocumentationGeneratorAgent(Agent):
    """Agent for generating HSTC-compliant documentation using Claude."""
    
    def __init__(self, model_id: str = "claude-3-5-sonnet-20241022", **kwargs):
        # Initialize Claude model for documentation generation
        model = Claude(id=model_id)
        super().__init__(model=model, **kwargs)
        
        # To be implemented in Phase 4
        pass
```

## Step 9: Create Manager Class Skeleton

Create a basic skeleton for the HSTC Manager:

```python
# src/dbp_cli/commands/hstc_agno/manager.py (initial setup)

from pathlib import Path
from typing import Dict, Any, Optional

class HSTCManager:
    """Manager for HSTC file processing and documentation generation."""
    
    def __init__(self, base_dir: Optional[Path] = None):
        """
        Initialize the HSTC Manager
        
        Args:
            base_dir: Base directory for file operations
        """
        self.base_dir = base_dir or Path.cwd()
        
        # To be implemented in Phase 5
        pass
```

## Step 10: Test Basic Project Structure

Verify that the basic structure is set up correctly:

```bash
# Check that the package is importable
python -c "from src.dbp_cli.commands.hstc_agno import hstc_agno; print(hstc_agno.__doc__)"

# Test the CLI command help
python -m src.dbp_cli hstc_agno --help
```

## Expected Output

After completing this phase, you should have:

1. A properly structured package for the HSTC Agno implementation
2. Basic skeletons for all the required modules
3. Command-line interface registration
4. Dependency configuration

## Next Steps

After completing this phase, proceed to Phase 2 (Data Models and Utilities) to implement the core data models that will be used throughout the implementation.
