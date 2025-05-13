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
# Provides a Click command interface for testing AWS Bedrock models using LangChain wrapper 
# classes for interactive chat with streaming responses. This adapts the functionality from 
# the original CLI's BedrockTestCommandHandler to the Click-based CLI structure.
###############################################################################
# [Source file design principles]
# - Dynamic model discovery using reflection to avoid hardcoding model IDs
# - Interactive model selection when not explicitly specified
# - Clean streaming response display with asyncio
# - Support for special commands for configuration and control
# - Robust error handling to provide good feedback to users
###############################################################################
# [Source file constraints]
# - Relies on LangChain wrapper classes existing at src/dbp/llm/bedrock/models/
# - Depends on prompt_toolkit and asyncio for enhanced interaction
# - Requires AWS credentials to be properly configured
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/cli_click/common.py
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/bedrock/model_parameters.py
# codebase:src/dbp/llm/bedrock/client_factory.py
# codebase:src/dbp/llm/bedrock/discovery/models_capabilities.py
# system:prompt_toolkit
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-13T16:13:00Z : Internalized BedrockCommandHandler and CommandCompleter by CodeAssistant
# * Implemented BedrockCommandHandler and CommandCompleter directly in the file
# * Removed imports from the legacy CLI implementation that was removed
# * Removed external dependencies on dbp_cli.commands.test package
# * Updated file header to reflect removed dependencies
# 2025-05-13T13:36:00Z : Enhanced BedrockTester to use get_output_adapter by CodeAssistant
# * Updated BedrockTester to use get_output_adapter() for consistent adapter management
# * Improved output formatting reliability by using the centralized adapter function
# * Fixed parameter compatibility issues between Click and OutputFormatter interfaces
# 2025-05-13T12:41:00Z : Fixed output formatter compatibility issue by CodeAssistant
# * Added ClickContextOutputAdapter class to bridge Click context and output formatter interface
# * Updated BedrockTester to use the adapter instead of passing Click context directly
# * Fixed 'Context' object has no attribute 'print' error in special commands
# 2025-05-12T23:44:00Z : Fixed command behavior with early exit in callback by CodeAssistant
# * Modified bedrock_callback to detect subcommand presence in sys.argv
# * Added early exit in callback when subcommand is detected
# * Prevented model selection UI from appearing in subcommand execution
# 2025-05-12T23:30:00Z : Fixed subcommand behavior to prevent model menu propagation by CodeAssistant
# * Made model parameter optional for subcommands and added explicit help display
# * Implemented early return with help display for subcommands with no args
# * Separated parent command model selection behavior from subcommands
# 2025-05-12T23:24:00Z : Fixed subcommand behavior for consistent help display by CodeAssistant
# * Added no_args_is_help=True to chat and interactive subcommands
# * Ensured model selection menu only appears for parent command
# * Maintained consistent behavior across all subcommands
###############################################################################

"""
Bedrock test command implementation for the Click-based CLI.
"""

import asyncio
import logging
import importlib
import inspect
import os
import sys
import traceback
from typing import Dict, List, Any, Optional, Tuple, Type, Callable

import click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.shortcuts import CompleteStyle

from ..common import catch_errors, ClickContextOutputAdapter, get_output_adapter
from .bedrock_group import BedrockGroup

# Import from original implementation to reuse functionality
from dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
from dbp.llm.bedrock.model_parameters import ModelParameters
from dbp.config.config_manager import ConfigurationManager
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities

# Implement command handler and completer directly (previously imported from old CLI)
class BedrockCommandHandler:
    """
    Handler for Bedrock test commands. Ported from the original CLI implementation.
    
    Provides special commands processing for the interactive Bedrock test functionality.
    """
    
    # Command result constants
    RESULT_NORMAL = "normal"
    RESULT_CONTINUE = "continue"
    RESULT_EXIT = "exit"
    
    def __init__(self, output_formatter, model_param_model, current_model_id, 
                get_model_constraints_fn, chat_history, state_callbacks=None):
        """Initialize the command handler."""
        self.output_formatter = output_formatter
        self.model_param_model = model_param_model
        self.current_model_id = current_model_id
        self.get_model_constraints_fn = get_model_constraints_fn
        self.chat_history = chat_history
        self.state_callbacks = state_callbacks or {}
        
    def process_command(self, cmd_text):
        """Process a special command prefixed with '/'."""
        cmd_parts = cmd_text[1:].strip().split()
        if not cmd_parts:
            return self.RESULT_CONTINUE
            
        cmd = cmd_parts[0].lower()
        args = cmd_parts[1:]
        
        # Exit command
        if cmd in ["exit", "quit"]:
            return self.RESULT_EXIT
            
        # Help command
        elif cmd == "help":
            self._show_help()
            return self.RESULT_CONTINUE
            
        # History command
        elif cmd == "history":
            self._show_history()
            return self.RESULT_CONTINUE
            
        # Clear command
        elif cmd == "clear":
            self._clear_history()
            return self.RESULT_CONTINUE
            
        # Profile command
        elif cmd == "profile":
            if not args:
                self._show_profiles()
            else:
                self._apply_profile(args[0])
            return self.RESULT_CONTINUE
            
        # Parameters command
        elif cmd in ["params", "parameters"]:
            self._show_parameters()
            return self.RESULT_CONTINUE
            
        # Set command
        elif cmd == "set":
            if len(args) >= 2:
                self._set_parameter(args[0], " ".join(args[1:]))
            else:
                self.output_formatter.error("Usage: /set <parameter> <value>")
            return self.RESULT_CONTINUE
            
        # Info command
        elif cmd == "info":
            self._show_info()
            return self.RESULT_CONTINUE
            
        # Command not recognized - treat as normal input
        return self.RESULT_NORMAL
    
    def _show_help(self):
        """Show available commands and their descriptions."""
        self.output_formatter.info("Available commands:")
        self.output_formatter.info("  /exit, /quit - Exit the chat")
        self.output_formatter.info("  /help - Show this help message")
        self.output_formatter.info("  /history - Show chat history")
        self.output_formatter.info("  /clear - Clear chat history")
        self.output_formatter.info("  /profile <name> - Apply parameter profile")
        self.output_formatter.info("  /params, /parameters - Show current parameters")
        self.output_formatter.info("  /set <parameter> <value> - Set parameter value")
        self.output_formatter.info("  /info - Show model information")
        
    def _show_history(self):
        """Show chat history."""
        if not self.chat_history:
            self.output_formatter.info("Chat history is empty.")
            return
            
        self.output_formatter.info("Chat history:")
        for i, message in enumerate(self.chat_history):
            role_display = "User" if message["role"] == "user" else "Assistant"
            self.output_formatter.info(f"[{i+1}] {role_display}: {message['content'][:60]}...")
            
    def _clear_history(self):
        """Clear chat history."""
        self.chat_history.clear()
        if "on_history_clear" in self.state_callbacks:
            self.state_callbacks["on_history_clear"]()
        self.output_formatter.info("Chat history cleared.")
        
    def _show_profiles(self):
        """Show available parameter profiles."""
        profiles = self.model_param_model._get_available_profiles()
        
        if not profiles:
            self.output_formatter.info("No parameter profiles available for this model.")
            return
            
        self.output_formatter.info("Available parameter profiles:")
        for profile in profiles:
            self.output_formatter.info(f"  {profile}")
            
    def _apply_profile(self, profile_name):
        """Apply a parameter profile."""
        try:
            if "on_apply_profile" in self.state_callbacks:
                self.state_callbacks["on_apply_profile"](profile_name)
            else:
                self.model_param_model._apply_profile(profile_name)
                
            self.output_formatter.info(f"Applied profile: {profile_name}")
        except Exception as e:
            self.output_formatter.error(f"Failed to apply profile: {str(e)}")
            
    def _show_parameters(self):
        """Show current parameters."""
        self.output_formatter.info("Current parameters:")
        params = self.model_param_model.to_dict()
        for name, value in params.items():
            self.output_formatter.info(f"  {name}: {value}")
            
    def _set_parameter(self, param_name, value_str):
        """Set parameter value."""
        try:
            # Parse value based on type
            value = self._parse_parameter_value(value_str)
            
            # Check if parameter exists
            if not hasattr(self.model_param_model, param_name):
                self.output_formatter.error(f"Unknown parameter: {param_name}")
                return
                
            # Set parameter value
            setattr(self.model_param_model, param_name, value)
            self.output_formatter.info(f"Set {param_name} = {value}")
            
            # Notify callbacks
            if "on_parameter_change" in self.state_callbacks:
                self.state_callbacks["on_parameter_change"](param_name, value)
                
        except Exception as e:
            self.output_formatter.error(f"Failed to set parameter: {str(e)}")
            
    def _parse_parameter_value(self, value_str):
        """Parse parameter value string to appropriate type."""
        # Try parsing as float
        try:
            if '.' in value_str:
                return float(value_str)
            else:
                return int(value_str)
        except ValueError:
            pass
            
        # Handle boolean values
        if value_str.lower() in ['true', 'yes', 'on']:
            return True
        if value_str.lower() in ['false', 'no', 'off']:
            return False
            
        # Default to string
        return value_str
        
    def _show_info(self):
        """Show model information."""
        self.output_formatter.info(f"Current model: {self.current_model_id}")
        
        # Get model constraints
        try:
            constraints = self.get_model_constraints_fn(self.current_model_id)
            
            self.output_formatter.info("Model information:")
            self.output_formatter.info(f"  Model family: {constraints.get('family', 'Unknown')}")
            self.output_formatter.info(f"  Max tokens: {constraints.get('max_tokens', 'Unknown')}")
            
        except Exception as e:
            self.output_formatter.error(f"Error retrieving model info: {str(e)}")
    
    def update_model_param_model(self, model_param_model):
        """Update the model parameter model reference."""
        self.model_param_model = model_param_model


class CommandCompleter:
    """
    Command completer for interactive Bedrock test. Ported from the original CLI implementation.
    
    Provides auto-completion for special commands and their parameters.
    """
    
    def __init__(self, command_handler):
        """Initialize the command completer."""
        self.command_handler = command_handler
        
        # Define command completions
        self.completions = {
            "": [
                "/exit", "/quit", "/help", "/history", "/clear",
                "/profile", "/params", "/parameters", "/set", "/info"
            ],
            "profile": [],  # Will be populated dynamically
            "set": [],      # Will be populated dynamically
        }
        
    def get_completions(self, document, complete_event):
        """Get completions for the current input."""
        from prompt_toolkit.completion import Completion
        
        text = document.text
        
        # Complete commands
        if text.startswith("/"):
            parts = text[1:].split()
            
            # Complete root commands
            if len(parts) <= 1:
                cmd_prefix = parts[0] if parts else ""
                for cmd in self.completions[""]:
                    if cmd[1:].startswith(cmd_prefix):
                        yield Completion(cmd[1:], start_position=-len(cmd_prefix))
                        
            # Complete command parameters
            elif len(parts) == 2:
                cmd = parts[0]
                param_prefix = parts[1]
                
                # Handle profile completion
                if cmd == "profile":
                    profiles = self._get_profiles()
                    for profile in profiles:
                        if profile.startswith(param_prefix):
                            yield Completion(profile, start_position=-len(param_prefix))
                            
                # Handle set parameter completion
                elif cmd == "set":
                    params = self._get_parameters()
                    for param in params:
                        if param.startswith(param_prefix):
                            yield Completion(param, start_position=-len(param_prefix))
                            
            # Complete parameter values
            elif len(parts) == 3 and parts[0] == "set":
                param = parts[1]
                value_prefix = parts[2]
                
                # Complete boolean parameters
                param_type = self._get_parameter_type(param)
                if param_type == bool:
                    for value in ["true", "false"]:
                        if value.startswith(value_prefix.lower()):
                            yield Completion(value, start_position=-len(value_prefix))
    
    def _get_profiles(self):
        """Get available parameter profiles."""
        try:
            return self.command_handler.model_param_model._get_available_profiles()
        except Exception:
            return []
    
    def _get_parameters(self):
        """Get available parameters."""
        try:
            return list(self.command_handler.model_param_model.to_dict().keys())
        except Exception:
            return []
    
    def _get_parameter_type(self, param_name):
        """Get parameter type."""
        try:
            value = getattr(self.command_handler.model_param_model, param_name)
            return type(value)
        except Exception:
            return str

# Set up logger
logger = logging.getLogger(__name__)


# Model parameters from original implementation
def add_model_parameters(func):
    """
    [Function intent]
    Decorator to add model parameters to a Click command.
    
    [Design principles]
    - DRY approach to parameter definition
    - Consistent parameter names
    - Clear organization
    
    [Implementation details]
    - Adds common model parameters as Click options
    - Uses the same parameter names as ModelParameters
    
    Args:
        func: The Click command function to decorate
        
    Returns:
        function: Decorated function with model parameters
    """
    # Add model selection parameter
    func = click.option(
        "--model", "-m",
        help="Bedrock model to use (if not specified, will prompt to choose)"
    )(func)
    
    # Temperature
    func = click.option(
        "--temperature", "-t",
        type=float,
        help="Temperature (higher = more creative, lower = more deterministic)"
    )(func)
    
    # Top P
    func = click.option(
        "--top-p",
        type=float,
        help="Top P (nucleus sampling probability threshold)"
    )(func)
    
    # Max tokens
    func = click.option(
        "--max-tokens",
        type=int,
        help="Maximum number of tokens to generate"
    )(func)
    
    # Additional parameters can be added here based on model needs
    
    # Profile support
    func = click.option(
        "--profile",
        help="Parameter profile name to apply"
    )(func)
    
    return func


# Define a callback for the bedrock_group that will be called when invoked without subcommands
@click.pass_context
@add_model_parameters
@catch_errors
def bedrock_callback(ctx: click.Context, **kwargs):
    """
    [Function intent]
    Provides default behavior when 'test llm bedrock' is invoked directly.
    
    [Design principles]
    - Consistent with original CLI behavior
    - Direct path to model selection
    
    [Implementation details]
    - Automatically shows model selection UI
    - Passes through to chat command with model selection
    - Properly handles execution in different contexts
    - Exits early if any subcommand is specified
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    # Critical: Check if we're in a parsing phase
    if hasattr(ctx, 'resilient_parsing') and ctx.resilient_parsing:
        return None
        
    # Standard Click approach: check for invoked_subcommand
    if ctx.invoked_subcommand is not None:
        # This command has a subcommand specified - exit early
        return 0
    
    
    # Get available models
    available_models = _get_available_models()
    
    if not available_models:
        output.error("No Bedrock model implementations found.")
        return 1
    
    # Group models by family
    model_groups = {}
    for model_id, model_info in available_models.items():
        family = model_info['family']
        
        if family not in model_groups:
            model_groups[family] = []
        model_groups[family].append(model_id)
    
    # Display available models grouped by family
    output.info("\nAvailable Bedrock models:")
    model_options = []
    idx = 1
    
    for family in sorted(model_groups.keys()):
        output.info(f"\n{family}:")
        for model_id in sorted(model_groups[family]):
            output.info(f"  [{idx}] {model_id}")
            model_options.append(model_id)
            idx += 1
    
    # Prompt for selection
    while True:
        try:
            choice = input("\nEnter model number (or 'q' to quit): ")
            
            if choice.lower() in ('q', 'quit', 'exit'):
                click.echo("Exiting...")
                return 0
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(model_options):
                selected_model = model_options[choice_idx]
                model_info = available_models[selected_model]
                click.echo(f"Selected model: {selected_model} ({model_info['family']})")
                
                # Get the chat command directly from the command group
                chat_cmd = ctx.command.get_command(ctx, "chat")
                
                # Create a new context with the model parameter
                new_kwargs = {'model': selected_model}
                
                # Copy over any other parameters that were passed
                for param_name in ['temperature', 'top_p', 'max_tokens', 'profile']:
                    if kwargs.get(param_name) is not None:
                        new_kwargs[param_name] = kwargs[param_name]
                
                # Invoke the chat command directly with the proper parameters
                return ctx.invoke(chat_cmd, **new_kwargs)
            else:
                click.echo(f"Please enter a number between 1 and {len(model_options)}")
        except ValueError:
            click.echo("Please enter a valid number")
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled")
            return 130


# Now define the group that uses the command function
@click.group(
    name="bedrock", 
    help="Test AWS Bedrock models", 
    invoke_without_command=True,
    no_args_is_help=False
)
@click.pass_context
@catch_errors
def bedrock_group(ctx, **kwargs):
    """
    [Function intent]
    Provides a command group for testing AWS Bedrock models.
    
    [Design principles]
    - Consistent interface with other Click CLI commands
    - Easy to discover functionality
    - Compatible with original CLI behavior
    
    [Implementation details]
    - Creates a Click group for Bedrock test commands
    - When invoked without a subcommand, shows model selection UI
    - Uses appropriate Click context handling to prevent behavior propagation
    """
    # Store model parameters in case this is a direct "bedrock" command
    ctx._model_params = kwargs
    
    # Critical check: Only show model selection UI if explicitly running the bedrock command
    # without subcommands. This is the key to preventing behavior propagation to subcommands.
    if ctx.invoked_subcommand is None:
        # No subcommand specified - show model selection UI
        return bedrock_callback(**kwargs)


# Also define a named command for those who use 'bedrock' with an empty command
@bedrock_group.command(name="", hidden=True)
@click.pass_context
@add_model_parameters
@catch_errors
def _bedrock_empty_command(ctx: click.Context, **kwargs):
    """
    [Function intent]
    Provides default behavior when 'test llm bedrock' is invoked directly.
    
    [Design principles]
    - Consistent with original CLI behavior
    - Direct path to model selection
    
    [Implementation details]
    - Delegates to the bedrock_callback handler
    - Maintains backwards compatibility with empty command name
    """
    return bedrock_callback(ctx, **kwargs)
@bedrock_group.command("interactive", help="Start an interactive chat with a Bedrock model")
@click.pass_context
@add_model_parameters
@catch_errors
def bedrock_interactive(ctx: click.Context, **kwargs):
    """
    [Function intent]
    Start interactive model selection and chat with selected model.
    
    [Design principles]
    - Simple, direct path to model selection
    
    [Implementation details]
    - Prompts for model selection
    - Then launches interactive chat with selected model
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    # If model parameter is not provided, show help
    if kwargs.get('model') is None:
        click.echo(ctx.get_help())  # Use Click's built-in help echo
        return 0
        
    try:
        # Get model ID from options, or prompt for selection if not specified
        model_id = kwargs.get("model")
        
        # Create and initialize the tester
        tester = BedrockTester(ctx, model_id, **kwargs)
        
        try:
            # Initialize model
            tester.initialize_model()
            
            # Display model availability information
            model_capabilities = BedrockModelCapabilities.get_instance()
            availability_data = model_capabilities.get_model_availability_table(model_id)
            availability_display = model_capabilities.format_availability_table(availability_data, model_id)
            output.info(availability_display)
            
            # Start interactive chat session
            return tester.run_interactive_chat()
        except Exception as e:
            if "UnsupportedModelError" in str(type(e)):
                # Handle unsupported model gracefully
                click.echo(f"Error: Unsupported model: {model_id}", err=True)
                
                # Get list of available models to suggest to the user
                available_models = _get_available_models()
                if available_models:
                    # Group by family for easier reading
                    model_families = {}
                    for model_id in available_models:
                        family = available_models[model_id]['family']
                        if family not in model_families:
                            model_families[family] = []
                        model_families[family].append(model_id)
                    
                    click.echo("\nAvailable models:")
                    for family, models in model_families.items():
                        click.echo(f"\n{family}:")
                        for model in sorted(models):
                            click.echo(f"  {model}")
                else:
                    click.echo("\nNo available models found. Please check your installation.")
                return 1
            else:
                # Re-raise for other errors
                raise
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled")
        return 130
    except Exception as e:
        click.secho(f"Error in Bedrock test: {str(e)}", fg="red", err=True)
        # Print traceback for debugging
        traceback.print_exc()
        return 1


def _get_available_models():
    """
    [Function intent]
    Dynamically discover supported Bedrock models using the BedrockClientFactory.
    
    [Design principles]
    - Use centralized discovery mechanism with single source of truth
    - Strict error propagation for debugging
    - Organization by model family
    
    [Implementation details]
    - Uses BedrockClientFactory.get_model_info() for complete model metadata
    - Returns dictionary mapping model_id to model information
    - Propagates errors instead of using fallbacks or degraded modes
    
    Returns:
        dict: Dictionary mapping model_id to model information
        
    Raises:
        ImportError: If BedrockClientFactory module cannot be imported
        Exception: For any other errors during model processing
    """
    models_dict = {}
    
    # Import the BedrockClientFactory and model info methods
    from dbp.llm.bedrock.client_factory import (
        get_all_supported_model_ids,
        get_model_info
    )
    
    # Get all supported model IDs
    model_ids = get_all_supported_model_ids()
    
    # For each model ID, get complete model info
    for model_id in model_ids:
        # Get comprehensive model information
        model_info = get_model_info(model_id)
        
        # Create friendly family name with provider
        family_display = f"{model_info['model_family_friendly_name']} ({model_info['model_provider']})"
        
        # Add model to dictionary with standard information
        models_dict[model_id] = {
            'class': model_info['client_class'],
            'module': model_info['client_class'].__module__,
            'family': family_display,
            'parameter_class': model_info['parameter_class']
        }
    
    return models_dict


def _prompt_for_model_selection(ctx: click.Context):
    """
    [Function intent]
    Prompt the user to select a model from available Bedrock models.
    
    [Design principles]
    - Clear organization by model family
    - User-friendly selection interface
    - Graceful handling of cancellation
    
    [Implementation details]
    - Groups models by family
    - Displays numbered list for selection
    - Supports cancellation via 'q' or Ctrl+C
    
    Args:
        ctx: Click context object for output
        
    Returns:
        str: Selected model ID or None if cancelled
    """
    # Get available models
    available_models = _get_available_models()
    
    if not available_models:
        ctx.error("No Bedrock model implementations found.")
        return None
    
    # Group models by family
    model_groups = {}
    for model_id, model_info in available_models.items():
        family = model_info['family']
        
        if family not in model_groups:
            model_groups[family] = []
        model_groups[family].append(model_id)
    
    # Display available models grouped by family
    click.echo("\nAvailable Bedrock models:")
    model_options = []
    idx = 1
    
    for family in sorted(model_groups.keys()):
        click.echo(f"\n{family}:")
        for model_id in sorted(model_groups[family]):
            click.echo(f"  [{idx}] {model_id}")
            model_options.append(model_id)
            idx += 1
    
    # Prompt for selection
    while True:
        try:
            choice = input("\nEnter model number (or 'q' to quit): ")
            
            if choice.lower() in ('q', 'quit', 'exit'):
                click.echo("Exiting...")
                return None
            
            choice_idx = int(choice) - 1
            if 0 <= choice_idx < len(model_options):
                selected_model = model_options[choice_idx]
                model_info = available_models[selected_model]
                click.echo(f"Selected model: {selected_model} ({model_info['family']})")
                return selected_model
            else:
                click.echo(f"Please enter a number between 1 and {len(model_options)}")
        except ValueError:
            click.echo("Please enter a valid number")
        except KeyboardInterrupt:
            click.echo("\nOperation cancelled")
            return None


class BedrockTester:
    """
    [Class intent]
    Implements the functionality for testing Bedrock models interactively.
    This class encapsulates the functionality from BedrockTestCommandHandler.
    
    [Design principles]
    - Clean adaptation of original functionality
    - Proper state management
    - Consistent interface
    
    [Implementation details]
    - Takes model parameters from Click options
    - Manages interactive chat session
    - Wraps functionality from original implementation
    """
    
    def __init__(self, ctx: click.Context, model_id: str, **model_kwargs):
        """
        [Function intent]
        Initialize the Bedrock tester with the provided parameters.
        
        [Design principles]
        - Clean state initialization
        - Proper error handling
        
        [Implementation details]
        - Stores context for output
        - Initializes state for chat session
        
        Args:
            ctx: Click context object
            model_id: Bedrock model ID
            model_kwargs: Additional model parameters
        """
        self.ctx = ctx
        self.model_id = model_id
        self.model_kwargs = model_kwargs
        self.chat_history = []
        self.model_client = None
        self.model_param_model = None
        self.command_handler = None
        # Use the get_output_adapter function to get or create an adapter
        from ..common import get_output_adapter
        self.output_adapter = get_output_adapter(ctx)
    
    def initialize_model(self):
        """
        [Function intent]
        Initialize the selected LangChain model implementation.
        
        [Design principles]
        - Use correct model-specific implementation
        - Proper configuration from system settings
        - Model-specific parameter handling
        
        [Implementation details]
        - Gets AWS credentials from config manager
        - Uses the model class from discovery
        - Uses ModelParameters for model-specific parameter constraints
        - Initializes command handler for special command processing
        
        Raises:
            ValueError: If the model initialization fails
            Exception: For other errors during initialization
        """
        # Get AWS configuration from config manager
        config_manager = ConfigurationManager()
        config = config_manager.get_typed_config()
        
        # Import needed components
        from dbp.llm.bedrock.client_factory import BedrockClientFactory
        from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities
        
        # Get model capabilities instance for recommended region info
        model_capabilities = BedrockModelCapabilities.get_instance()
        
        # Get region and profile name if available from config
        profile_name = None
        
        # Get the recommended region for this model
        recommended_region = None
        best_regions = model_capabilities.get_best_regions_for_model(self.model_id)
        if best_regions:
            recommended_region = best_regions[0]
        
        # Extract AWS configuration and determine final region to use
        region_name = None  # This will be the actual region we use
        config_region = None  # This is just what's in the config
        
        try:
            aws_config = getattr(config, 'aws', None)
            if aws_config is not None:
                config_region = getattr(aws_config, 'region', None)
                profile_name = getattr(aws_config, 'profile_name', None)
                
                # Display AWS configuration in a user-friendly format
                click.echo("\n[AWS Configuration]")
                click.echo(f"  Config Region: {config_region or 'Not configured'}")
                click.echo(f"  Profile: {profile_name or 'Not configured (will use default)'}")
            else:
                click.echo("\n[AWS Configuration]")
                click.echo("  No AWS configuration found.")
                
        except Exception as e:
            click.echo(f"Warning: Error accessing AWS configuration: {str(e)}")
            click.echo("  Falling back to default settings.")
            # Fall back to None values
            config_region = None
            profile_name = None
            
        # Determine which region to use in this priority order:
        # 1. Recommended region from model capabilities (if available)
        # 2. Region from AWS configuration (if available)
        # 3. Let the BedrockClientFactory choose (typically us-west-2)
        
        if recommended_region:
            region_name = recommended_region
            click.echo(f"  Selected Region: {region_name} (recommended for this model)")
        elif config_region:
            region_name = config_region
            click.echo(f"  Selected Region: {region_name} (from configuration)")
        else:
            click.echo("  Selected Region: Will be auto-selected by client factory")
        
        # Create parameter model for selected model and populate from args
        self.model_param_model = ModelParameters.for_model(self.model_id)
        
        # Apply user-provided parameters
        try:
            # Filter parameters to only include those that are valid for this model
            filtered_kwargs = {
                k: v for k, v in self.model_kwargs.items() 
                if k in self.model_param_model.__fields__ and v is not None
            }
            
            # Validate parameters
            valid, errors = self.model_param_model.validate_config(filtered_kwargs)
            
            if not valid:
                error_messages = [f"- {param}: {msg}" for param, msg in errors.items()]
                error_str = "\n".join(error_messages)
                raise ValueError(f"Parameter validation failed:\n{error_str}")
            
            # Update model parameters
            self.model_param_model.update_from_args(filtered_kwargs)
            click.echo("Parameter validation successful")
        except Exception as e:
            raise ValueError(f"Parameter validation error: {str(e)}")
            
        # Convert to model_kwargs format
        model_kwargs = self.model_param_model.to_model_kwargs()
        
        # Display the model parameters being used
        click.echo("\n[Model Parameters]")
        for param_name, param_value in model_kwargs.items():
            click.echo(f"  {param_name}: {param_value}")
        
        # Use the BedrockClientFactory to create the model instance
        self.model_client = BedrockClientFactory.create_langchain_chatbedrock(
            model_id=self.model_id,
            region_name=region_name,
            profile_name=profile_name,
            model_kwargs=model_kwargs,
            use_model_discovery=True,
            logger=logging.getLogger("BedrockTester")
        )
        
        # Test the client initialization
        if self.model_client is None:
            raise ValueError(f"Failed to initialize client for model: {self.model_id}")
            
        # Initialize the command handler
        self.command_handler = BedrockCommandHandler(
            output_formatter=self.output_adapter,
            model_param_model=self.model_param_model,
            current_model_id=self.model_id,
            get_model_constraints_fn=self._get_model_constraints,
            chat_history=self.chat_history,
            state_callbacks={
                "on_history_clear": lambda: setattr(self, "chat_history", []),
                "on_apply_profile": self._on_apply_profile,
                "on_parameter_change": lambda param, value: None  # No-op for now
            }
        )
    
    def run_interactive_chat(self):
        """
        [Function intent]
        Run an interactive chat session with the selected model.
        
        [Design principles]
        - Clean interactive UI
        - Proper streaming display
        - Support for special commands
        - Clear error handling
        
        [Implementation details]
        - Enhanced with command completion support
        - Uses prompt_toolkit for enhanced input experience
        - Displays streaming responses in real time
        - Maintains chat history for context
        - Handles special commands
        
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        # Create prompt session with command completion
        history = InMemoryHistory()
        command_completer = CommandCompleter(self.command_handler)
        session = PromptSession(
            history=history,
            completer=command_completer,
            complete_while_typing=False,  # Show completions only when Tab is pressed
            complete_in_thread=True,      # Run completion in a separate thread for responsiveness
            complete_style=CompleteStyle.MULTI_COLUMN  # Show completions in a multi-column menu
        )
        
        # Define styling
        style = Style.from_dict({
            'user': '#88ff88',
            'assistant': '#8888ff',
        })
        
        # Display welcome message
        click.echo(f"\nInteractive chat mode with {self.model_client.model_id}")
        
        click.echo("Type '/exit' to quit, '/help' for available commands")
        click.echo("Use Tab for command and parameter auto-completion")
        click.echo("Press Tab twice on empty input to see all commands")
        click.echo("Press Tab twice after a command to see available options\n")
        
        while True:
            try:
                # Get user input with enhanced completion
                user_input = session.prompt("User > ", style=style)
                
                # Skip empty inputs
                if not user_input.strip():
                    continue

                # Check if this is a special command
                if user_input.startswith("/"):
                    # Process special commands using the dedicated handler
                    command_result = self.command_handler.process_command(user_input)
                    
                    # Handle command result
                    if command_result == BedrockCommandHandler.RESULT_EXIT:
                        break  # Exit loop and end chat
                    elif command_result == BedrockCommandHandler.RESULT_CONTINUE:
                        continue  # Skip to next iteration
                    # command_result == "normal" means process as normal message
                    elif command_result == BedrockCommandHandler.RESULT_NORMAL:
                        pass
                    else:
                        # Unknown result, treat as normal message
                        pass
                
                # Add to history
                self.chat_history.append({"role": "user", "content": user_input})
                
                # Process through model
                self._process_model_response()
                
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                continue
            except EOFError:
                # Handle Ctrl+D gracefully
                break
            except Exception as e:
                click.echo(f"Error during chat: {str(e)}")
                traceback.print_exc()
        
        return 0
    
    def _format_chat_messages(self):
        """
        [Function intent]
        Format internal chat history into the structure expected by LangChain.
        
        [Design principles]
        - Consistent message formatting
        - Clean separation of internal and external formats
        
        [Implementation details]
        - Converts internal chat history format to LangChain format
        - Maintains role and content structure
        
        Returns:
            list: List of messages in LangChain-compatible format
        """
        return [{"role": msg["role"], "content": msg["content"]} 
                for msg in self.chat_history]
    
    def _handle_streaming_error(self, error):
        """
        [Function intent]
        Handle errors during streaming responses in a consistent way.
        
        [Design principles]
        - Centralized error handling
        - Consistent user feedback
        - Proper logging
        
        [Implementation details]
        - Logs error details
        - Provides user-friendly error message
        
        Args:
            error: The exception that occurred
        """
        logging.error(f"Error during streaming: {str(error)}")
        click.echo(f"\nError during streaming: {str(error)}")
    
    def _process_model_response(self):
        """
        [Function intent]
        Process the user input through the model and display streaming response.
        
        [Design principles]
        - Real-time response display
        - Proper async/await handling
        - Clean error reporting
        
        [Implementation details]
        - Uses asyncio to process stream
        - Uses LangChain's astream_text method for clean text streaming
        - Updates chat history with complete response
        - Handles streaming errors gracefully
        """
        click.echo("\nAssistant > ", nl=False)
        
        response_text = ""
        
        async def process_stream():
            nonlocal response_text
            try:
                # Get formatted messages using our helper method
                messages = self._format_chat_messages()
                
                # Stream the response using LangChain wrapper's astream_text method
                async for chunk in self.model_client.astream_text(messages=messages):
                    click.echo(chunk, nl=False)
                    response_text += chunk
                    
            except Exception as e:
                # Handle streaming errors consistently
                self._handle_streaming_error(e)
        
        # Run the async function
        try:
            asyncio.run(process_stream())
            click.echo()  # New line after response
        except KeyboardInterrupt:
            click.echo("\n[Response interrupted]")
        
        # Add to history if we got a response
        if response_text:
            self.chat_history.append({"role": "assistant", "content": response_text})
    
    def _get_model_constraints(self, model_id):
        """
        [Function intent]
        Get model-specific constraints and capabilities for a given model ID.
        
        [Design principles]
        - Centralized constraint management
        - Consistent naming and identification
        
        [Implementation details]
        - Uses factory methods for model family and provider information
        - Determines token limits based on model family and version
        
        Args:
            model_id: The model ID to get constraints for
            
        Returns:
            dict: Dictionary containing model constraints and capabilities
        """
        # Handle None case with explicit error
        if not model_id:
            raise ValueError("Model ID cannot be None")
        
        # Import the model info method from BedrockClientFactory
        from dbp.llm.bedrock.client_factory import get_model_info
        
        # Get comprehensive model information - will raise exception if model not supported
        model_info = get_model_info(model_id)
        constraints = {}
        
        # Get family information with full vendor name
        constraints["family"] = f"{model_info['model_family_friendly_name']} ({model_info['model_provider']})"
        
        # Get short family name (without vendor)
        constraints["family_short"] = model_info['model_family_friendly_name']
        
        # Extract model family and version for token limits
        model_family = model_info['model_family_friendly_name'].lower()
        model_version = model_info.get('model_version', '')
        
        # Token limits based on model family and version
        if model_family == "claude":
            if model_version == "3.5":
                constraints["max_tokens"] = 8192
            elif model_version == "3.7":
                constraints["max_tokens"] = 64000
            elif model_version.startswith("3"):  # Any Claude 3.x
                constraints["max_tokens"] = 4096
            else:  # Other Claude models
                constraints["max_tokens"] = 4096
        elif model_family == "nova":
            constraints["max_tokens"] = 4096
        elif model_family == "titan":
            constraints["max_tokens"] = 4096
        else:
            # For unrecognized models, use default 4096 as a reasonable guess
            constraints["max_tokens"] = 4096
        
        return constraints
    
    def _on_apply_profile(self, profile_name):
        """
        [Function intent]
        Apply a parameter profile and update related state.
        
        [Design principles]
        - Clean state synchronization
        - Proper model recreation
        
        [Implementation details]
        - Creates a fresh parameter model with the specified profile
        - Synchronizes state across main handler and command handler
        
        Args:
            profile_name: Name of the profile to apply
        """
        # Create a fresh model with just the profile settings
        if self.model_id:
            self.model_param_model = ModelParameters.for_model(self.model_id)
            self.model_param_model._apply_profile(profile_name)
            
            # Update the command handler's reference to the new model parameters
            if self.command_handler:
                self.command_handler.update_model_param_model(self.model_param_model)



@bedrock_group.command(name="chat", help="Start an interactive chat with a Bedrock model")
@click.option('--model', '-m', help="Bedrock model to use")
@click.option('--temperature', '-t', type=float, help="Temperature (higher = more creative, lower = more deterministic)")
@click.option('--top-p', type=float, help="Top P (nucleus sampling probability threshold)")
@click.option('--max-tokens', type=int, help="Maximum number of tokens to generate")
@click.option('--profile', help="Parameter profile name to apply")
@click.pass_context
@catch_errors
def bedrock_chat_command(ctx: click.Context, **kwargs):
    """
    [Function intent]
    Start an interactive chat with a Bedrock model.
    
    [Design principles]
    - Intuitive command interface
    - Robust error handling
    - Comparable experience to original CLI
    
    [Implementation details]
    - Requires explicit model specification
    - No interactive model selection within the subcommand
    - Initializes model client with parameters
    - Runs interactive chat session
    """
    # Get output adapter
    output = get_output_adapter(ctx)
    
    # If model parameter is not provided, show help
    if kwargs.get('model') is None:
        output.info(ctx.get_help())  # Use built-in help display with adapter
        return 0
    try:
        # Get model ID from options
        model_id = kwargs.get("model")
        
        # Create and initialize the tester
        tester = BedrockTester(ctx, model_id, **kwargs)
        
        try:
            # Initialize model
            tester.initialize_model()
            
            # Display model availability information
            model_capabilities = BedrockModelCapabilities.get_instance()
            availability_data = model_capabilities.get_model_availability_table(model_id)
            availability_display = model_capabilities.format_availability_table(availability_data, model_id)
            click.echo(availability_display)
            
            # Start interactive chat session
            return tester.run_interactive_chat()
        except Exception as e:
            if "UnsupportedModelError" in str(type(e)):
                # Handle unsupported model gracefully
                click.secho(f"Error: Unsupported model: {model_id}", fg="red", err=True)
                
                # Get list of available models to suggest to the user
                available_models = _get_available_models()
                if available_models:
                    # Group by family for easier reading
                    model_families = {}
                    for model_id in available_models:
                        family = available_models[model_id]['family']
                        if family not in model_families:
                            model_families[family] = []
                        model_families[family].append(model_id)
                    
                    click.echo("\nAvailable models:")
                    for family, models in model_families.items():
                        click.echo(f"\n{family}:")
                        for model in sorted(models):
                            click.echo(f"  {model}")
                else:
                    click.echo("\nNo available models found. Please check your installation.")
                return 1
            else:
                # Re-raise for other errors
                raise
    except KeyboardInterrupt:
        click.echo("\nOperation cancelled")
        return 130
    except Exception as e:
        click.secho(f"Error in Bedrock test: {str(e)}", fg="red", err=True)
        # Print traceback for debugging
        traceback.print_exc()
        return 1
