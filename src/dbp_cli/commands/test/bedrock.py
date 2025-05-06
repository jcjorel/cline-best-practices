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
# codebase:src/dbp_cli/commands/base.py
# system:prompt_toolkit
# system:asyncio
###############################################################################
# [GenAI tool change history]
# 2025-05-06T11:51:45Z : Applied extensive DRY principle to field type handling by CodeAssistant
# * Added _get_field_type helper to centralize field type extraction logic
# * Implemented version-agnostic type access across Pydantic versions
# * Added robust handling of Optional/Union types with proper unwrapping
# * Improved fallback handling with current value type detection
# 2025-05-06T11:50:30Z : Applied comprehensive DRY principle to constraint handling by CodeAssistant
# * Extracted duplicated constraint extraction logic into _extract_field_constraints helper method
# * Created schema-based constraints detection with fallbacks for different Pydantic versions
# * Added support for OpenAPI-compatible constraint extraction from schema objects
# * Improved constraint validation readability and maintainability
# 2025-05-06T11:47:30Z : Applied advanced DRY principle to field handling by CodeAssistant
# * Extracted duplicated field description logic into _get_field_description helper method
# * Created version-agnostic field metadata accessor with Pydantic v1/v2 compatibility
# * Standardized field description retrieval across multiple methods
# * Improved error handling with graceful fallbacks for field information access
# 2025-05-06T11:42:00Z : Applied deeper DRY principle to model handling by CodeAssistant
# * Created unified _get_model_family method by merging _determine_model_family and _get_model_family_name
# * Added comprehensive _get_model_constraints method as single source of truth for model capabilities
# * Enhanced model family detection with more specific version identification
# * Standardized family name format for better consistency
# 2025-05-06T11:33:50Z : Applied DRY principle to model constraints by CodeAssistant
# * Refactored hard-coded model constraints into helper methods
# * Added _get_model_max_tokens_limit method for centralized limit management
# * Added _get_model_family_name method for consistent model family naming
# * Improved readability and maintainability of parameter validation
# 2025-05-06T11:17:00Z : Improved error handling for invalid models by CodeAssistant
# * Added user-friendly error handling for unsupported models
# * Removed stack trace display for better user experience
# * Added display of available models when an invalid model is specified
# * Organized available models by family for easier selection
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
from typing import Dict, List, Any, Optional, Tuple, Type

from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.validation import Validator, ValidationError

# Import LangChain wrapper classes
from src.dbp.llm.bedrock.langchain_wrapper import EnhancedChatBedrockConverse
from src.dbp.llm.bedrock.model_parameters import ModelParameters
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
            # Don't show stack trace for better user experience
            return 1
    
    def _get_available_models(self):
        """
        [Function intent]
        Dynamically discover supported Bedrock models using LangChain wrapper classes.
        
        [Design principles]
        - Dynamic discovery instead of hardcoding
        - Robust error handling for missing modules
        - Organization by model family
        
        [Implementation details]
        - Uses reflection to find model classes
        - Checks for SUPPORTED_MODELS attribute
        - Returns dictionary mapping model_id to model information
        
        Returns:
            dict: Dictionary mapping model_id to model information
        """
        models_dict = {}
        
        # Import model modules
        try:
            from src.dbp.llm.bedrock.models import claude3, nova
            # Add more model modules as they become available
        except ImportError as e:
            self.output.warning(f"Could not import model modules: {e}")
            return models_dict
            
        # Get all modules to scan
        modules_to_scan = [claude3, nova]  # Add more as needed
        
        # Find model client classes in each module
        for module in modules_to_scan:
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, EnhancedChatBedrockConverse) and 
                    obj != EnhancedChatBedrockConverse and
                    hasattr(obj, 'SUPPORTED_MODELS')):
                    
                    # Get model family name from class name
                    family_name = name.replace('EnhancedChatBedrockConverse', '')
                    
                    # Register each supported model
                    for model_id in obj.SUPPORTED_MODELS:
                        models_dict[model_id] = {
                            'class': obj,
                            'module': module.__name__,
                            'family': self._get_model_family(model_id, family_name)
                        }
        
        return models_dict
    
    def _get_model_family(self, model_id, family_name=""):
        """
        [Function intent]
        Determine the model family based on model ID and class name.
        Unified method combining previous _determine_model_family and _get_model_family_name functions.
        
        [Design principles]
        - Reliable pattern matching
        - Human-readable family names
        - Single source of truth for model family identification
        
        [Implementation details]
        - Uses model ID patterns for identification
        - Uses class name as fallback hint
        - Returns consistent family naming across the application
        - Supports both display names and internal family identifiers
        
        Args:
            model_id: The model ID to determine family for
            family_name: Optional family name hint from class name
            
        Returns:
            str: Human-readable model family name
        """
        if not model_id:
            return "Unknown"
            
        model_id_lower = model_id.lower()
        
        # Claude model detection with version specificity
        if "claude-3-5" in model_id_lower:
            return "Claude 3.5 (Anthropic)"
        elif "claude-3-7" in model_id_lower: 
            return "Claude 3.7 (Anthropic)"
        elif "claude-3" in model_id_lower:
            return "Claude 3 (Anthropic)"
        elif "claude" in model_id_lower or "anthropic" in model_id_lower or family_name == "Claude":
            return "Claude (Anthropic)"
            
        # Amazon models
        elif "titan" in model_id_lower:
            return "Titan (Amazon)"
        elif "nova" in model_id_lower or family_name == "Nova":
            return "Nova (Amazon)"
            
        # Other common models
        elif "llama" in model_id_lower or "meta" in model_id_lower:
            return "Llama (Meta)"
        elif "falcon" in model_id_lower:
            return "Falcon (TII)"
        elif "mistral" in model_id_lower:
            return "Mistral"
        elif "cohere" in model_id_lower:
            return "Cohere"
        else:
            return "Other"
    
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
        
        Args:
            model_id: ID of the model to initialize
            
        Raises:
            ValueError: If the model initialization fails
        """
        # Get AWS configuration from config manager
        config_manager = ConfigurationManager()
        config = config_manager.get_typed_config()
        
        # Import the BedrockClientFactory
        from src.dbp.llm.bedrock.client_factory import BedrockClientFactory
        
        # Get region and profile name if available
        region_name = None
        profile_name = None
        if hasattr(config, 'aws'):
            if hasattr(config.aws, 'region'):
                region_name = config.aws.region
            if hasattr(config.aws, 'profile_name'):
                profile_name = config.aws.profile_name
        
        # Create parameter model for selected model and populate from args
        self.model_param_model = ModelParameters.for_model(model_id)
        
        # Apply selected profile if specified
        if hasattr(self.args, "profile") and self.args.profile:
            self.model_param_model._apply_profile(self.args.profile)
            
        # Update with CLI args (these override profile defaults)
        self.model_param_model.update_from_args(vars(self.args))
        
        # Convert to model_kwargs format
        model_kwargs = self.model_param_model.to_model_kwargs()
        
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
        - Uses prompt_toolkit for enhanced input experience
        - Displays streaming responses in real time
        - Maintains chat history for context
        - Handles special commands
        
        Returns:
            int: Exit code (0 for success, non-zero for error)
        """
        # Create prompt session
        history = InMemoryHistory()
        session = PromptSession(history=history)
        
        # Define styling
        style = Style.from_dict({
            'user': '#88ff88',
            'assistant': '#8888ff',
        })
        
        # Display welcome message
        self.output.print(f"\nInteractive chat mode with {self.model_client.model_id}")
        self.output.print("Type '/exit' to quit, '/help' for available commands\n")
        
        while True:
            try:
                # Get user input
                user_input = session.prompt("User > ", style=style)
                
                # Process special commands that start with "/"
                if user_input.lower() in ["/exit", "/quit"]:
                    self.output.print("\nExiting interactive chat mode.")
                    break
                elif user_input.lower() == "/help":
                    self._print_help()
                    continue
                elif user_input.lower() == "/clear":
                    self.chat_history = []
                    self.output.print("Chat history cleared.")
                    continue
                elif user_input.lower().startswith("/config"):
                    # Remove the leading slash when handling the config command
                    self._handle_config_command(user_input[1:])
                    continue
                elif not user_input.strip():
                    # Skip empty inputs
                    continue
                
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
                # Format messages for the LangChain model
                messages = [{"role": msg["role"], "content": msg["content"]} 
                            for msg in self.chat_history]
                
                # Stream the response using LangChain wrapper's astream_text method
                # IMPORTANT: Do not pass model_kwargs here as they were already
                # set during model initialization, which avoids the validation error
                async for chunk in self.model_client.astream_text(messages=messages):
                    print(chunk, end="", flush=True)
                    response_text += chunk
                    
            except Exception as e:
                logging.error(f"Error during streaming: {str(e)}")
                print(f"\nError during streaming: {str(e)}")
        
        # Run the async function
        try:
            asyncio.run(process_stream())
            print()  # New line after response
        except KeyboardInterrupt:
            print("\n[Response interrupted]")
        
        # Add to history if we got a response
        if response_text:
            self.chat_history.append({"role": "assistant", "content": response_text})

    def _get_field_description(self, field):
        """
        [Function intent]
        Extract field description from Pydantic field with version compatibility.
        
        [Design principles]
        - Version-agnostic access to field metadata
        - Graceful fallbacks for different Pydantic versions
        - Clean error handling
        
        [Implementation details]
        - Supports both Pydantic v1 and v2 field structures
        - Tries multiple accessor patterns for description
        - Returns empty string if no description is found
        
        Args:
            field: Pydantic field to extract description from
            
        Returns:
            str: Field description or empty string if not found
        """
        desc = ""
        try:
            # Try direct attribute access first (Pydantic v1)
            if hasattr(field, 'description'):
                desc = field.description
            # Then try field_info if available (Pydantic v2)
            elif hasattr(field, 'field_info') and hasattr(field.field_info, 'description'):
                desc = field.field_info.description
            # Finally try schema (works with both v1 and v2)
            elif hasattr(field, 'schema') and callable(field.schema):
                try:
                    schema = field.schema()
                    if isinstance(schema, dict) and 'description' in schema:
                        desc = schema['description']
                except:
                    pass
        except Exception:
            # Fallback for any access errors
            pass
            
        return desc
    
    def _print_help(self):
        """
        [Function intent]
        Print help information for available commands.
        
        [Design principles]
        - Clear organization
        - Comprehensive command descriptions
        - Current parameter values display
        
        [Implementation details]
        - Lists all available commands
        - Shows current model parameters and profiles
        """
        self.output.print("\nAvailable commands:")
        self.output.print("  /exit, /quit   - Exit the chat session")
        self.output.print("  /help          - Show this help message")
        self.output.print("  /clear         - Clear chat history")
        self.output.print("  /config        - Show current model parameters")
        self.output.print("  /config profile <name> - Apply a parameter profile")
        self.output.print("  /config [param] [value] - Change a model parameter")
        
        # Show available profiles
        self.output.print("\nAvailable parameter profiles:")
        for profile_name in self.model_param_model._profiles.keys():
            if profile_name == self.model_param_model._current_profile:
                self.output.print(f"  * {profile_name} (active)")
            else:
                self.output.print(f"  - {profile_name}")
        
        # Show available parameters
        self.output.print("\nAvailable parameters:")
        for field_name, field in self.model_param_model.__fields__.items():
            # Only show applicable parameters in current profile
            if self.model_param_model.is_applicable(field_name):
                value = getattr(self.model_param_model, field_name)
                
                # Get field description using the centralized helper method
                desc = self._get_field_description(field)
                    
                self.output.print(f"  {field_name} = {value} ({desc})")
        
        self.output.print()

    def _handle_config_command(self, command_input):
        """
        [Function intent]
        Handle the config command to show or modify model parameters.
        
        [Design principles]
        - Clear parameter display
        - Input validation
        - User feedback
        - Profile support
        
        [Implementation details]
        - Parses config command format
        - Validates parameter names and values
        - Updates parameters and provides feedback
        - Handles profile selection
        
        Args:
            command_input: Config command input from user
        """
        parts = command_input.split(None, 3)
        
        # Just "config" - show current config
        if len(parts) == 1:
            # Use _print_help to show parameters
            self._print_help()
            return
            
        # Handle "config profile <name>" - Apply a profile
        if len(parts) >= 3 and parts[1].lower() == "profile":
            profile_name = parts[2]
            
            if profile_name not in self.model_param_model._profiles:
                self.output.error(f"Unknown profile: {profile_name}")
                self.output.print("Available profiles: " + ", ".join(self.model_param_model._profiles.keys()))
                return
            
            # Create a fresh parameter model with this profile
            # This ensures command line arguments are discarded
            if self.current_model_id:
                # Create a fresh model with just the profile settings
                self.model_param_model = ModelParameters.for_model(self.current_model_id)
                self.model_param_model._apply_profile(profile_name)
                self.output.print(f"Applied profile: {profile_name}")
                
                # Show updated parameters
                self.output.print("\nCurrent parameters:")
                for field_name, field in self.model_param_model.__fields__.items():
                    if self.model_param_model.is_applicable(field_name):
                        value = getattr(self.model_param_model, field_name)
                        self.output.print(f"  {field_name} = {value}")
                return
            else:
                self.output.error("Cannot apply profile: Model ID not available")
                return
            
        # "config param value" - set parameter
        if len(parts) >= 3:
            param = parts[1]
            value_str = parts[2]
            
            # Debugging to help understand parameter limits
            self.output.print(f"Checking parameter '{param}' with value '{value_str}'...")
            
            # Check if parameter exists and is applicable
            if param not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {param}")
                return
                
            if not self.model_param_model.is_applicable(param):
                self.output.error(f"Parameter '{param}' is not applicable in current profile: {self.model_param_model._current_profile}")
                return
                
            field = self.model_param_model.__fields__[param]
            
            # Get field type using our helper method
            field_type = self._get_field_type(field, getattr(self.model_param_model, param))
            
            try:
                # Convert and validate value
                value = field_type(value_str)
                
                # Validate constraints using proper validation (handles both Pydantic v1 and v2)
                try:
                    # Try to validate using the model's built-in validator
                    # Create a temporary dict with just the parameter we're setting
                    validate_data = {param: value}
                    
                    # Extract field constraints using our helper method
                    constraints = self._extract_field_constraints(field)
                    
                    # Debug constraint output
                    self.output.print(f"Found constraints: {constraints}")
                    
                    # Manual validation using extracted constraints
                    if 'min' in constraints:
                        min_val = constraints['min']
                        if constraints['min_inclusive']:
                            if value < min_val:
                                self.output.error(f"Value {value} for {param} must be at least {min_val}")
                                return
                        else:
                            if value <= min_val:
                                self.output.error(f"Value {value} for {param} must be greater than {min_val}")
                                return
                                
                    if 'max' in constraints:
                        max_val = constraints['max']
                        if constraints['max_inclusive']:
                            if value > max_val:
                                self.output.error(f"Value {value} for {param} must be at most {max_val}")
                                return
                        else:
                            if value >= max_val:
                                self.output.error(f"Value {value} for {param} must be less than {max_val}")
                                return
                    
                    # If we have a model ID and this is a max_tokens parameter, double-check against
                    # model-specific constraints
                    if param == "max_tokens" and self.current_model_id:
                        # Use centralized model constraints method
                        constraints = self._get_model_constraints(self.current_model_id)
                        max_limit = constraints["max_tokens"]
                        if max_limit and value > max_limit:
                            model_family = constraints["family_short"]
                            self.output.error(f"Value {value} for max_tokens exceeds {model_family} maximum of {max_limit}")
                            return
                except Exception as e:
                    self.output.error(f"Value validation error for {param}: {str(e)}")
                    return
                    
                # Set parameter
                setattr(self.model_param_model, param, value)
                self.output.print(f"Set {param} = {value}")
                
            except ValueError:
                self.output.error(f"Invalid value for {param}: {value_str}")
            
            return
            
        # "config param" - show specific parameter
        if len(parts) == 2:
            param = parts[1]
            
            # Handle special case for "profile" to show current profile
            if param.lower() == "profile":
                self.output.print(f"Current profile: {self.model_param_model._current_profile}")
                return
                
            if param not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {param}")
                return
                
            # Get value and description - with safe access to description
            value = getattr(self.model_param_model, param)
            field = self.model_param_model.__fields__[param]
            
            # Get description using our centralized helper method
            desc = self._get_field_description(field)
            
            # Show applicability info
            applicable = self.model_param_model.is_applicable(param)
            applicable_str = " (applicable)" if applicable else " (not applicable in current profile)"
            
            self.output.print(f"{param} = {value} ({desc}){applicable_str}")
            return
            
        self.output.print("Usage: config [param] [value] or config profile <name>")

    def _get_field_type(self, field, current_value=None):
        """
        [Function intent]
        Extract field type from a Pydantic field with version compatibility.
        
        [Design principles]
        - Version-agnostic type extraction
        - Support for both Pydantic v1 and v2
        - Handles Optional/Union types
        - Clean error handling with reasonable defaults
        
        [Implementation details]
        - Supports both Pydantic v1 and v2 field structures
        - Handles Optional types by extracting the inner type
        - Falls back to current value type if metadata extraction fails
        
        Args:
            field: Pydantic field to extract type from
            current_value: Current field value for fallback type detection
            
        Returns:
            type: The extracted field type
        """
        field_type = None
        
        # Try different ways to access the type information
        if hasattr(field, 'type_'):
            # Pydantic v1 style
            field_type = field.type_
        elif hasattr(field, 'annotation'):
            # Pydantic v2 style
            field_type = field.annotation
        else:
            # Fallback to the type of the current value
            field_type = type(current_value) if current_value is not None else str
        
        # Handle Optional types
        if hasattr(field_type, "__origin__") and field_type.__origin__ is Union:
            # Get the actual type from Optional (assuming first non-None type)
            for arg_type in field_type.__args__:
                if arg_type is not type(None):  # noqa: E721
                    field_type = arg_type
                    break
                
        return field_type
    
    def _extract_field_constraints(self, field):
        """
        [Function intent]
        Extract field constraints from a Pydantic field with version compatibility.
        
        [Design principles]
        - Version-agnostic constraint extraction
        - Support for both inclusive and exclusive ranges
        - Clean error handling with reasonable defaults
        - Centralized constraint management
        
        [Implementation details]
        - Handles both Pydantic v1 and v2 field structures
        - Extracts min/max constraints with inclusivity information
        - Returns a structured dictionary of constraints
        - Works with both direct field attributes and field_info
        
        Args:
            field: Pydantic field to extract constraints from
            
        Returns:
            dict: Dictionary containing extracted constraints
        """
        constraints = {}
        
        # Extract min constraint (ge or gt)
        if hasattr(field, 'ge'):
            constraints['min'] = field.ge
            constraints['min_inclusive'] = True
        elif hasattr(field, 'gt'):
            constraints['min'] = field.gt
            constraints['min_inclusive'] = False
        elif hasattr(field, 'field_info'):
            if hasattr(field.field_info, 'ge'):
                constraints['min'] = field.field_info.ge
                constraints['min_inclusive'] = True
            elif hasattr(field.field_info, 'gt'):
                constraints['min'] = field.field_info.gt
                constraints['min_inclusive'] = False
                
        # Extract max constraint (le or lt)
        if hasattr(field, 'le'):
            constraints['max'] = field.le
            constraints['max_inclusive'] = True
        elif hasattr(field, 'lt'):
            constraints['max'] = field.lt
            constraints['max_inclusive'] = False
        elif hasattr(field, 'field_info'):
            if hasattr(field.field_info, 'le'):
                constraints['max'] = field.field_info.le
                constraints['max_inclusive'] = True
            elif hasattr(field.field_info, 'lt'):
                constraints['max'] = field.field_info.lt
                constraints['max_inclusive'] = False
                
        # Try to extract from schema (works in some cases)
        if not constraints and hasattr(field, 'schema') and callable(field.schema):
            try:
                schema = field.schema()
                if isinstance(schema, dict):
                    if 'minimum' in schema:
                        constraints['min'] = schema['minimum']
                        constraints['min_inclusive'] = True
                    elif 'exclusiveMinimum' in schema:
                        constraints['min'] = schema['exclusiveMinimum']
                        constraints['min_inclusive'] = False
                        
                    if 'maximum' in schema:
                        constraints['max'] = schema['maximum']
                        constraints['max_inclusive'] = True
                    elif 'exclusiveMaximum' in schema:
                        constraints['max'] = schema['exclusiveMaximum']
                        constraints['max_inclusive'] = False
            except:
                pass
                
        return constraints
    
    def _get_model_constraints(self, model_id):
        """
        [Function intent]
        Get model-specific constraints and capabilities for a given model ID.
        Acts as a centralized source of truth for all model-specific information.
        
        [Design principles]
        - Centralized constraint management
        - Single source of truth for model capabilities
        - DRY implementation for model-specific logic
        
        [Implementation details]
        - Covers token limits and other model constraints
        - Organizes constraints by model family
        - Returns a comprehensive constraint dictionary
        - Uses pattern matching for model identification
        
        Args:
            model_id: The model ID to get constraints for
            
        Returns:
            dict: Dictionary containing model constraints and capabilities
        """
        if not model_id:
            return {"max_tokens": None, "family": "Unknown", "family_short": "Unknown"}
        
        model_id_lower = model_id.lower()
        constraints = {}
        
        # Get family information with full vendor name
        constraints["family"] = self._get_model_family(model_id)
        
        # Get short family name (without vendor)
        if " (" in constraints["family"]:
            constraints["family_short"] = constraints["family"].split(" (")[0]
        else:
            constraints["family_short"] = constraints["family"]
        
        # Token limits by model family
        if "claude-3-5" in model_id_lower:
            constraints["max_tokens"] = 8192
        elif "claude-3-7" in model_id_lower:
            constraints["max_tokens"] = 64000
        elif "claude-3" in model_id_lower:
            constraints["max_tokens"] = 4096
        elif "claude" in model_id_lower:
            constraints["max_tokens"] = 4096  # Default for other Claude models
        elif "nova" in model_id_lower:
            constraints["max_tokens"] = 4096  # Approximate for Nova models
        elif "titan" in model_id_lower:
            constraints["max_tokens"] = 4096  # Approximate for Titan models
        else:
            constraints["max_tokens"] = None  # Unknown model
        
        return constraints
        
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
