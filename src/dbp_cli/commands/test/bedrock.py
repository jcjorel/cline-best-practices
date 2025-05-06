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
# Provides a command-line interface for testing AWS Bedrock models using LangChain wrapper classes
# for interactive chat with streaming responses. This allows direct testing of the Bedrock model
# implementations without requiring the full MCP server infrastructure.
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
# codebase:src/dbp/llm/bedrock/langchain_wrapper.py
# codebase:src/dbp/llm/bedrock/models/claude3.py
# codebase:src/dbp/llm/bedrock/models/nova.py
# codebase:src/dbp/llm/bedrock/client_factory.py
# codebase:src/dbp_cli/commands/base.py
# codebase:src/dbp_cli/commands/test/bedrock_commands.py
# codebase:src/dbp_cli/commands/test/command_completion.py
# system:prompt_toolkit
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-07T00:15:00Z : Added model availability display in interactive chat by CodeAssistant
# * Integrated BedrockModelCapabilities to show availability details
# * Added format_availability_table call for the selected model
# * Enhanced user experience by displaying availability before chat prompt
# * Added dependency on models_capabilities.py
# 2025-05-06T18:38:00Z : Added parameter validation to model initialization by CodeAssistant
# * Enhanced _initialize_model with explicit parameter validation
# * Added detailed error reporting for validation failures
# * Improved user feedback with parameter display
# * Added more robust error handling for profile application
# 2025-05-06T16:32:00Z : Applied DRY principle with BedrockClientFactory.get_model_info() by CodeAssistant
# * Updated _get_available_models to use centralized model info from factory
# * Updated _get_model_family to use official model metadata
# * Updated _get_model_constraints to leverage model metadata for token limits
# * Added dependency on client_factory.py for centralized model information
# 2025-05-06T12:25:00Z : Removed redundant command handling methods by CodeAssistant
# * Created BedrockCommandHandler class for command management
# * Moved special command processing logic to dedicated handler
# * Implemented state synchronization via callback system
# * Enhanced modularity through clear separation of concerns
# 2025-05-06T12:04:30Z : Applied message handling DRY principle by CodeAssistant  
# * Added _format_chat_messages method for consistent message formatting
# * Created _handle_streaming_error for centralized error handling
# * Simplified code flow with specialized helper methods
# * Improved readability and maintainability of message processing
###############################################################################

"""
Bedrock test command implementation for testing AWS Bedrock models.
"""

import asyncio
import os
import importlib
import inspect
import logging
import sys
import traceback
from typing import Dict, List, Any, Optional, Tuple, Type, Callable

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.shortcuts import CompleteStyle

# Import LangChain wrapper classes
from dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
from dbp.llm.bedrock.model_parameters import ModelParameters
from dbp.config.config_manager import ConfigurationManager
from dbp.llm.bedrock.discovery.models_capabilities import BedrockModelCapabilities

# Import command handler and completer
from .bedrock_commands import BedrockCommandHandler
from .command_completion import CommandCompleter


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
        - Adds model parameter arguments using ModelParameters
        
        Args:
            parser: ArgumentParser object to add arguments to
        """
        parser.add_argument(
            "--model", "-m",
            help="Bedrock model to use (if not specified, will prompt to choose)"
        )
        
        # Add model parameters using ModelParameters
        ModelParameters.add_arguments_to_parser(parser)
    
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
        self.output = output_formatter
        self.progress = progress_indicator
        self.model_client = None
        self.chat_history = []
        self.model_parameters = {}
        self.current_model_id = None  # Store current model ID for recreating parameter models
        self.command_handler = None  # Will be initialized after model_param_model is ready
    
    def execute(self, args):
        """
        [Function intent]
        Execute the Bedrock test command.
        
        [Design principles]
        - Robust error handling
        - Clear user feedback
        - Logical execution flow
        
        [Implementation details]
        - Stores args for later use in model initialization
        - Handles model selection (interactive if not specified)
        - Initializes model client
        - Runs interactive chat session
        
        Args:
            args: Command-line arguments
            
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        try:
            # Store args for use in _initialize_model
            self.args = args
            
            # If model is not specified, prompt user to choose
            model_id = args.model
            if not model_id:
                model_id = self._prompt_for_model_selection()
                if not model_id:  # User cancelled
                    return 1
                    
            # Store the current model ID for later parameter model recreation
            self.current_model_id = model_id
            
            # Initialize the model client
            try:
                self._initialize_model(model_id)
                        # Display model availability information
                model_capabilities = BedrockModelCapabilities.get_instance()
                
                availability_data = model_capabilities.get_model_availability_table(model_id)
                availability_display = model_capabilities.format_availability_table(availability_data, model_id)
                self.output.print(availability_display)        

                # Start interactive chat session
                return self._run_interactive_chat()
            except Exception as e:
                if "UnsupportedModelError" in str(type(e)):
                    # Handle unsupported model gracefully
                    self.output.error(f"Unsupported model: {model_id}")
                    
                    # Get list of available models to suggest to the user
                    available_models = self._get_available_models()
                    if available_models:
                        # Group by family for easier reading
                        model_families = {}
                        for model_id in available_models:
                            family = available_models[model_id]['family']
                            if family not in model_families:
                                model_families[family] = []
                            model_families[family].append(model_id)
                        
                        self.output.print("\nAvailable models:")
                        for family, models in model_families.items():
                            self.output.print(f"\n{family}:")
                            for model in sorted(models):
                                self.output.print(f"  {model}")
                    else:
                        self.output.print("\nNo available models found. Please check your installation.")
                    return 1
                else:
                    # Re-raise for other errors
                    raise
                
        except KeyboardInterrupt:
            print("\nOperation cancelled")
            return 130
        except Exception as e:
            self.output.error(f"Error in Bedrock test: {str(e)}")
            # Print traceback for debugging
            import traceback
            traceback.print_exc()
            return 1
    
    def _get_available_models(self):
        """
        [Function intent]
        Dynamically discover supported Bedrock models using the BedrockClientFactory.get_model_info() method.
        
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
    
    def _get_model_family(self, model_id, family_name=""):
        """
        [Function intent]
        Determine the model family based on model ID using the BedrockClientFactory.get_model_info() method.
        
        [Design principles]
        - Single source of truth for model family names
        - Strict error propagation for debugging
        - Consistent naming across the application
        
        [Implementation details]
        - Uses get_model_info() to retrieve official model family information
        - Returns consistent family naming from model metadata
        - Does not implement fallback mechanisms to ensure problems are immediately visible
        
        Args:
            model_id: The model ID to determine family for
            family_name: Optional family name hint (for backward compatibility, not used)
            
        Returns:
            str: Human-readable model family name
            
        Raises:
            Exception: If model info cannot be retrieved or model is not supported
        """
        
        # Import the model info method from BedrockClientFactory
        from dbp.llm.bedrock.client_factory import get_model_info
        
        # Get model information from the factory - will raise an exception if not supported
        model_info = get_model_info(model_id)
        
        # Return the formatted family name with provider
        return f"{model_info['model_family_friendly_name']} ({model_info['model_provider']})"
    
    def _prompt_for_model_selection(self):
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
        
        Returns:
            str: Selected model ID or None if cancelled
        """
        # Get available models
        available_models = self._get_available_models()
        
        if not available_models:
            self.output.error("No Bedrock model implementations found.")
            return None
        
        # Group models by family
        model_groups = {}
        for model_id, model_info in available_models.items():
            family = model_info['family']
            
            if family not in model_groups:
                model_groups[family] = []
            model_groups[family].append(model_id)
        
        # Display available models grouped by family
        self.output.print("\nAvailable Bedrock models:")
        model_options = []
        idx = 1
        
        for family in sorted(model_groups.keys()):
            self.output.print(f"\n{family}:")
            for model_id in sorted(model_groups[family]):
                self.output.print(f"  [{idx}] {model_id}")
                model_options.append(model_id)
                idx += 1
        
        # Prompt for selection
        while True:
            try:
                choice = input("\nEnter model number (or 'q' to quit): ")
                
                if choice.lower() in ('q', 'quit', 'exit'):
                    self.output.print("Exiting...")
                    return None
                
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(model_options):
                    selected_model = model_options[choice_idx]
                    model_info = available_models[selected_model]
                    self.output.print(f"Selected model: {selected_model} ({model_info['family']})")
                    return selected_model
                else:
                    self.output.print(f"Please enter a number between 1 and {len(model_options)}")
            except ValueError:
                self.output.print("Please enter a valid number")
            except KeyboardInterrupt:
                self.output.print("\nOperation cancelled")
                return None
    
    def _initialize_model(self, model_id):
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
        
        Args:
            model_id: ID of the model to initialize
            
        Raises:
            ValueError: If the model initialization fails
        """
        # Get AWS configuration from config manager
        config_manager = ConfigurationManager()
        config = config_manager.get_typed_config()
        
        # Import the BedrockClientFactory
        from dbp.llm.bedrock.client_factory import BedrockClientFactory
        
        # Get region and profile name if available
        region_name = None
        profile_name = None
        
        # Extract AWS configuration
        try:
            aws_config = getattr(config, 'aws', None)
            if aws_config is not None:
                region_name = getattr(aws_config, 'region', None)
                profile_name = getattr(aws_config, 'profile_name', None)
                
                # Display AWS configuration in a user-friendly format
                self.output.print("\n[AWS Configuration]")
                self.output.print(f"  Region: {region_name or 'Not configured (will use default)'}")
                self.output.print(f"  Profile: {profile_name or 'Not configured (will use default)'}")
            else:
                self.output.print("\n[AWS Configuration]")
                self.output.print("  No AWS configuration found. Using default settings.")
                
        except Exception as e:
            self.output.warning(f"Error accessing AWS configuration: {str(e)}")
            self.output.print("  Falling back to default AWS settings.")
            # Fall back to None values
            region_name = None
            profile_name = None
        
        # Create parameter model for selected model and populate from args
        self.model_param_model = ModelParameters.for_model(model_id)
        
        # Apply selected profile if specified, with validation
        if hasattr(self.args, "profile") and self.args.profile:
            self.output.print(f"Applying parameter profile: {self.args.profile}")
            try:
                self.model_param_model._apply_profile(self.args.profile, validate_overrides=True)
            except ValueError as e:
                self.output.error(f"Profile validation error: {str(e)}")
                return None
            
        # Update with CLI args with validation (these override profile defaults)
        try:
            args_dict = vars(self.args)
            # Explicitly validate parameters before updating
            valid, errors = self.model_param_model.validate_config({
                k: v for k, v in args_dict.items() 
                if k in self.model_param_model.__fields__ and v is not None
            })
            
            if not valid:
                error_messages = [f"- {param}: {msg}" for param, msg in errors.items()]
                error_str = "\n".join(error_messages)
                self.output.error(f"Parameter validation failed:\n{error_str}")
                return None
                
            # If validation passes, update with the args
            self.model_param_model.update_from_args(args_dict, validate_first=False)  # Already validated
            self.output.print("Parameter validation successful")
        except Exception as e:
            self.output.error(f"Parameter validation error: {str(e)}")
            return None
            
        # Convert to model_kwargs format
        model_kwargs = self.model_param_model.to_model_kwargs()
        
        # Display the model parameters being used
        self.output.print("\n[Model Parameters]")
        for param_name, param_value in model_kwargs.items():
            self.output.print(f"  {param_name}: {param_value}")
        
        # Use the BedrockClientFactory to create the model instance
        self.model_client = BedrockClientFactory.create_langchain_chatbedrock(
            model_id=model_id,
            region_name=region_name,
            profile_name=profile_name,
            model_kwargs=model_kwargs,  # Pass model parameters properly formatted
            use_model_discovery=True,
            logger=logging.getLogger("BedrockTestCommandHandler")
        )
        
        # Test the client initialization
        if self.model_client is None:
            raise ValueError(f"Failed to initialize client for model: {model_id}")
            
        # Initialize the command handler
        self.command_handler = BedrockCommandHandler(
            output_formatter=self.output,
            model_param_model=self.model_param_model,
            current_model_id=self.current_model_id,
            get_model_constraints_fn=self._get_model_constraints,
            chat_history=self.chat_history,
            state_callbacks={
                "on_history_clear": lambda: setattr(self, "chat_history", []),
                "on_apply_profile": self._on_apply_profile,
                "on_parameter_change": lambda param, value: None  # No-op for now
            }
        )

    def _run_interactive_chat(self):
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
        self.output.print(f"\nInteractive chat mode with {self.model_client.model_id}")
        
        self.output.print("Type '/exit' to quit, '/help' for available commands")
        self.output.print("Use Tab for command and parameter auto-completion")
        self.output.print("Press Tab twice to see all available options\n")
        
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
                self.output.error(f"Error during chat: {str(e)}")
                traceback.print_exc()
        
        return 0

    def _format_chat_messages(self):
        """
        [Function intent]
        Format internal chat history into the structure expected by LangChain.
        
        [Design principles]
        - Consistent message formatting
        - Clean separation of internal and external formats
        - Reusable conversion logic
        
        [Implementation details]
        - Converts internal chat history format to LangChain format
        - Maintains role and content structure
        - Can be used by any method that needs formatted messages
        
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
        - Can be used by any method that handles streaming
        
        Args:
            error: The exception that occurred
        """
        logging.error(f"Error during streaming: {str(error)}")
        print(f"\nError during streaming: {str(error)}")
    
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
        self.output.print("\nAssistant > ", end="", flush=True)
        
        response_text = ""
        
        async def process_stream():
            nonlocal response_text
            try:
                # Get formatted messages using our helper method
                messages = self._format_chat_messages()
                
                # Stream the response using LangChain wrapper's astream_text method
                # IMPORTANT: Do not pass model_kwargs here as they were already
                # set during model initialization, which avoids the validation error
                async for chunk in self.model_client.astream_text(messages=messages):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                    
            except Exception as e:
                # Handle streaming errors consistently
                self._handle_streaming_error(e)
        
        # Run the async function
        try:
            asyncio.run(process_stream())
            print()  # New line after response
        except KeyboardInterrupt:
            print("\n[Response interrupted]")
        
        # Add to history if we got a response
        if response_text:
            self.chat_history.append({"role": "assistant", "content": response_text})
            
    def _get_model_constraints(self, model_id):
        """
        [Function intent]
        Get model-specific constraints and capabilities for a given model ID using
        BedrockClientFactory.get_model_info() as the single source of truth.
        
        [Design principles]
        - Centralized constraint management through factory metadata
        - Consistent naming and identification across the application
        - Direct error propagation without fallbacks
        
        [Implementation details]
        - Uses get_model_info() for model family and provider information
        - Determines token limits based on model family and version
        - Returns a comprehensive constraint dictionary
        - Raises exceptions rather than using fallbacks
        
        Args:
            model_id: The model ID to get constraints for
            
        Returns:
            dict: Dictionary containing model constraints and capabilities
            
        Raises:
            Exception: If model info cannot be retrieved or model is not supported
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
        - Consistent parameter handling
        
        [Implementation details]
        - Creates a fresh parameter model with the specified profile
        - Synchronizes state across main handler and command handler
        - Called as callback from the command handler
        
        Args:
            profile_name: Name of the profile to apply
        """
        # Create a fresh model with just the profile settings
        if self.current_model_id:
            self.model_param_model = ModelParameters.for_model(self.current_model_id)
            self.model_param_model._apply_profile(profile_name)
            
            # Update the command handler's reference to the new model parameters
            if self.command_handler:
                self.command_handler.update_model_param_model(self.model_param_model)
    
    def _get_multiline_input(self, session):
        """
        [Function intent]
        Get multiline input from user with support for cancellation.
        
        [Design principles]
        - Support for longer prompts
        - Clear visual feedback
        - Consistent user experience
        
        [Implementation details]
        - Uses prompt_toolkit's multiline mode
        - Supports Ctrl+Enter to submit
        - Validates non-empty input
        
        Args:
            session: PromptSession instance
            
        Returns:
            str: The multiline input text
        """
        class EmptyInputValidator(Validator):
            def validate(self, document):
                text = document.text
                if not text.strip() and text.endswith('\n'):
                    raise ValidationError(message="Input cannot be empty")

        self.output.print("Enter multiline input (Ctrl+Enter to submit):")
        
        return session.prompt(
            "> ", 
            multiline=True, 
            validator=EmptyInputValidator()
        ).rstrip()
