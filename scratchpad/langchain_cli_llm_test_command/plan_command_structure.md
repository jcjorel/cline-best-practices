# Command Structure Implementation

This document details the implementation of the command structure for the `test llm bedrock` CLI command, using the current LangChain implementation.

## Command Handler Hierarchy

The command structure will follow a hierarchical pattern to support nested subcommands:

```
test (TestCommandHandler)
└── llm (LLMTestCommandHandler)
    └── bedrock (BedrockTestCommandHandler)
```

## TestCommandHandler Implementation

The `TestCommandHandler` class will serve as the entry point for all test-related commands:

```python
"""
Test command implementation for running tests against system components.
"""
from ..commands.base import BaseCommandHandler
from .test.llm import LLMTestCommandHandler

class TestCommandHandler(BaseCommandHandler):
    """
    [Class intent]
    Provides command-line interface for testing system components directly
    using server codebase functionality.
    
    [Design principles]
    - Clear subcommand structure for different test types
    - Extensible for additional test types in the future
    - Consistent interface with other CLI commands
    
    [Implementation details]
    - Extends BaseCommandHandler for CLI integration
    - Uses subparsers for organized command structure
    - Delegates to specialized handlers for each test type
    """
    
    def add_arguments(self, parser):
        """
        [Function intent]
        Add command-line arguments for the test command.
        
        [Design principles]
        - Clear subcommand structure
        - Organized help text
        - Extensible for future test types
        
        [Implementation details]
        - Creates subparsers for different test types
        - Currently supports 'llm' subcommand
        """
        subparsers = parser.add_subparsers(dest="test_type", help="Type of test to run")
        
        # Create LLM test subcommand
        llm_parser = subparsers.add_parser("llm", help="Test LLM functionality")
        LLMTestCommandHandler.add_arguments(llm_parser)
        
        # Add more test types here as needed
    
    def execute(self, args):
        """
        [Function intent]
        Execute the appropriate test subcommand based on arguments.
        
        [Design principles]
        - Delegate to appropriate subcommand handler
        - Clear error messaging
        - Consistent return codes
        
        [Implementation details]
        - Checks test_type from args
        - Creates and delegates to appropriate handler
        - Returns handler's exit code
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        if args.test_type == "llm":
            return LLMTestCommandHandler(
                self.mcp_client, 
                self.output_formatter, 
                self.progress_indicator
            ).execute(args)
        else:
            self.output_formatter.error("Please specify a test type")
            return 1
```

## LLMTestCommandHandler Implementation

The `LLMTestCommandHandler` class will handle the `llm` subcommand:

```python
"""
LLM test command implementation for testing LLM functionalities.
"""
from .bedrock import BedrockTestCommandHandler

class LLMTestCommandHandler:
    """
    [Class intent]
    Provides command-line interface for testing LLM functionality
    using actual LLM implementations from the server codebase.
    
    [Design principles]
    - Provider-specific subcommand structure
    - Consistent interface across providers
    - Extensible for additional LLM providers
    
    [Implementation details]
    - Uses subparsers for different LLM providers
    - Currently supports Bedrock provider
    - Delegates to specialized handlers for each provider
    """
    
    @staticmethod
    def add_arguments(parser):
        """
        [Function intent]
        Add command-line arguments for the LLM test command.
        
        [Design principles]
        - Clear subcommand structure
        - Organized help text
        - Extensible for future LLM providers
        
        [Implementation details]
        - Creates subparsers for different LLM providers
        - Currently supports 'bedrock' subcommand
        """
        subparsers = parser.add_subparsers(dest="llm_provider", help="LLM provider to test")
        
        # Create Bedrock test subcommand
        bedrock_parser = subparsers.add_parser("bedrock", help="Test AWS Bedrock models")
        BedrockTestCommandHandler.add_arguments(bedrock_parser)
        
        # Add more LLM providers here as needed
    
    def __init__(self, mcp_client, output_formatter, progress_indicator):
        """
        [Function intent]
        Initialize the LLM test command handler.
        
        [Design principles]
        - Consistent dependency injection
        - Clean initialization
        
        [Implementation details]
        - Stores references to required services
        
        Args:
            mcp_client: MCP client for API access
            output_formatter: Output formatter for displaying results
            progress_indicator: Progress indicator for showing progress
        """
        self.mcp_client = mcp_client
        self.output_formatter = output_formatter
        self.progress_indicator = progress_indicator
    
    def execute(self, args):
        """
        [Function intent]
        Execute the appropriate LLM provider test based on arguments.
        
        [Design principles]
        - Delegate to appropriate provider handler
        - Clear error messaging
        - Consistent return codes
        
        [Implementation details]
        - Checks llm_provider from args
        - Creates and delegates to appropriate handler
        - Returns handler's exit code
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        if args.llm_provider == "bedrock":
            return BedrockTestCommandHandler(
                self.mcp_client, 
                self.output_formatter, 
                self.progress_indicator
            ).execute(args)
        else:
            self.output_formatter.error("Please specify an LLM provider")
            return 1
```

## BedrockTestCommandHandler Implementation

The `BedrockTestCommandHandler` class will handle the `bedrock` subcommand:

```python
"""
Bedrock test command implementation for testing AWS Bedrock models.
"""
import asyncio
import os
import importlib
import inspect

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style

from src.dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
from src.dbp.config.config_manager import ConfigurationManager

class BedrockTestCommandHandler:
    """
    [Class intent]
    Provides command-line interface for testing AWS Bedrock models using
    LangChain wrapper classes for interactive chat with streaming responses.
    
    [Design principles]
    - Dynamic model discovery using reflection
    - Interactive model selection when not specified
    - Streaming response display with asyncio
    - Special commands for configuration and control
    
    [Implementation details]
    - Uses LangChain wrapper classes from src/dbp/llm/bedrock/models/
    - Discovers models based on SUPPORTED_MODELS class attributes
    - Streams responses using astream_text method
    - Manages conversation history for multi-turn chat
    """
    
    # Common model parameters
    MODEL_PARAMETERS = {
        "temperature": {
            "type": float,
            "default": 0.7,
            "help": "Model temperature (0.0 to 1.0)",
            "min": 0.0,
            "max": 1.0
        },
        "max_tokens": {
            "type": int,
            "default": 1024,
            "help": "Maximum tokens in response",
            "min": 1,
            "max": 4096
        },
        "top_p": {
            "type": float,
            "default": 0.9,
            "help": "Top-p sampling parameter",
            "min": 0.0,
            "max": 1.0
        },
        "top_k": {
            "type": int,
            "default": 50,
            "help": "Top-k sampling parameter",
            "min": 0,
            "max": 500
        }
    }
    
    @staticmethod
    def add_arguments(parser):
        """
        [Function intent]
        Add command-line arguments for the Bedrock test command.
        
        [Design principles]
        - Clear parameter definitions
        - Support for model selection
        - Support for model parameters
        
        [Implementation details]
        - Adds model selection argument
        - Adds model parameter arguments
        """
        parser.add_argument(
            "--model", "-m",
            help="Bedrock model to use (if not specified, will prompt to choose)"
        )
        
        # Add model parameters
        for param_name, param_config in BedrockTestCommandHandler.MODEL_PARAMETERS.items():
            parser.add_argument(
                f"--{param_name}",
                type=param_config["type"],
                default=param_config["default"],
                help=param_config["help"]
            )
    
    def __init__(self, mcp_client, output_formatter, progress_indicator):
        """
        [Function intent]
        Initialize the Bedrock test command handler.
        
        [Design principles]
        - Consistent dependency injection
        - Clean initialization
        
        [Implementation details]
        - Stores references to required services
        - Initializes state for chat session
        
        Args:
            mcp_client: MCP client for API access
            output_formatter: Output formatter for displaying results
            progress_indicator: Progress indicator for showing progress
        """
        self.mcp_client = mcp_client
        self.output_formatter = output_formatter
        self.progress_indicator = progress_indicator
        self.model_client = None
        self.chat_history = []
        self.model_parameters = {}
    
    def execute(self, args):
        """
        [Function intent]
        Execute the Bedrock test command.
        
        [Design principles]
        - Robust error handling
        - Clear user feedback
        - Logical execution flow
        
        [Implementation details]
        - Extracts model parameters from args
        - Handles model selection (interactive if not specified)
        - Initializes model client
        - Runs interactive chat session
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        try:
            # Extract model parameters from args
            self.model_parameters = {
                param: getattr(args, param)
                for param in self.MODEL_PARAMETERS.keys()
                if hasattr(args, param)
            }
            
            # If model is not specified, prompt user to choose
            model_id = args.model
            if not model_id:
                model_id = self._prompt_for_model_selection()
                if not model_id:  # User cancelled
                    return 1
            
            # Initialize the model client
            self._initialize_model(model_id)
            
            # Start interactive chat session
            return self._run_interactive_chat()
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 130
        except Exception as e:
            self.output_formatter.error(f"Error in Bedrock test: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
```

## CLI Integration

To integrate the new test command with the CLI, we need to update the `DocumentationProgrammingCLI` class in `src/dbp_cli/cli.py`:

```python
def _init_command_handlers(self) -> None:
    """
    [Function intent]
    Create and register all command handler instances for the CLI.
    
    [Implementation details]
    Creates instances of all command handlers and registers them in a
    dictionary with command names as keys. Each handler is initialized
    with the core components (MCP client, output formatter, progress indicator).
    
    [Design principles]
    Command registry pattern - stores handlers in a central registry.
    Component injection - passes required dependencies to all handlers.
    Extensibility - easy to add new command handlers to the registry.
    """
    self.logger.debug("Initializing command handlers")
    
    # Import the TestCommandHandler
    from src.dbp_cli.commands.test import TestCommandHandler
    
    # Register command handlers
    self.command_handlers = {
        # Main MCP tool commands
        "query": QueryCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        "commit": CommitCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        # System commands
        "config": ConfigCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        "status": StatusCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        "server": ServerCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
        # Test command
        "test": TestCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
    }
```

## Directory Structure

The implementation will create the following files:

```
src/dbp_cli/commands/
├── test.py                # TestCommandHandler
└── test/
    ├── __init__.py        # Package initialization
    ├── llm.py             # LLMTestCommandHandler
    └── bedrock.py         # BedrockTestCommandHandler
```

## Implementation Steps

1. Create `src/dbp_cli/commands/test/__init__.py` to initialize the package
2. Create `src/dbp_cli/commands/test/bedrock.py` with the `BedrockTestCommandHandler` class
3. Create `src/dbp_cli/commands/test/llm.py` with the `LLMTestCommandHandler` class
4. Create `src/dbp_cli/commands/test.py` with the `TestCommandHandler` class
5. Update `src/dbp_cli/cli.py` to register the test command

This implementation order ensures that dependencies are available when they're needed.
