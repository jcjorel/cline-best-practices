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
# Implements the AWS Bedrock test command handler which provides interactive
# testing capabilities for Bedrock LLM models. This handler supports dynamic
# model discovery, interactive chat with streaming responses, and parameter
# configuration.
###############################################################################
# [Source file design principles]
# - Dynamic model discovery using reflection
# - Stream-based response handling for real-time feedback
# - Clear user interface for testing and interaction
# - Consistent error handling and user feedback
# - Support for model parameter configuration
###############################################################################
# [Source file constraints]
# - Requires AWS credentials to be configured
# - Relies on prompt_toolkit for enhanced input experience
# - Requires asyncio support for streaming responses
###############################################################################
# [Dependencies]
# codebase:src/dbp/llm/bedrock/enhanced_base.py
# codebase:src/dbp/llm/bedrock/models
# codebase:src/dbp/llm/common/streaming.py
# codebase:src/dbp/config/config_manager.py
###############################################################################
# [GenAI tool change history]
# 2025-05-02T14:09:47Z : Initial implementation of BedrockTestCommandHandler by CodeAssistant
# * Created handler implementation with model discovery, chat interface, and parameter configuration
###############################################################################

import os
import sys
import logging
import importlib
import inspect
import asyncio
from typing import Dict, Any, List, Optional, Type, AsyncIterator

logger = logging.getLogger(__name__)

class BedrockTestCommandHandler:
    """
    [Class intent]
    Test AWS Bedrock models using server codebase components directly.
    Provides an interactive CLI interface for testing and exploring
    different Bedrock models with streaming responses.
    
    [Design principles]
    - Dynamic model discovery to avoid hardcoding model IDs
    - Interactive CLI interface with streaming responses
    - Parameter configuration for model testing
    - Clean organization of model families
    
    [Implementation details]
    Uses Python reflection to discover available Bedrock model implementations,
    initializes the appropriate model client, and provides an interactive
    chat interface with streaming response display. Supports parameter
    configuration and special commands.
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
        },
        "use_reasoning": {
            "type": bool,
            "default": False,
            "help": "Enable reasoning mode for models that support it",
            "values": [True, False]
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
        
        Args:
            parser: Command-line argument parser
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
        self.output = output_formatter
        self.progress = progress_indicator
        self.model_client = None
        self.chat_history = []
        self.model_parameters = {}
        self.model_class = None
    
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
            self.output.error(f"Error in Bedrock test: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1
        
    def _get_available_models(self):
        """
        [Function intent]
        Dynamically discover supported Bedrock models by inspecting the model modules.
        
        [Design principles]
        - Dynamic discovery instead of hardcoding
        - Robust error handling for missing modules
        - Organization by model family
        
        [Implementation details]
        - Uses reflection to examine model modules
        - Finds subclasses of EnhancedBedrockBase
        - Extracts model IDs from class attributes
        - Returns dictionary mapping model_id to model class and metadata
        
        Returns:
            dict: Dictionary mapping model_id to model information
        """
        import os
        import importlib
        import inspect
        
        # Import EnhancedBedrockBase here to avoid cyclic imports
        from dbp.llm.bedrock.enhanced_base import EnhancedBedrockBase
        
        models_dict = {}
        
        # Get the directory where model implementations are located
        models_dir = os.path.join(os.path.dirname(__file__), "../../../dbp/llm/bedrock/models")
        
        if not os.path.exists(models_dir):
            self.output.warning(f"Models directory not found: {models_dir}")
            return models_dict
        
        # Iterate through modules in the models directory
        for filename in os.listdir(models_dir):
            if filename.endswith('.py') and not filename.startswith('__'):
                module_name = filename[:-3]  # Remove .py extension
                
                try:
                    # Import the module dynamically
                    module_path = f"dbp.llm.bedrock.models.{module_name}"
                    module = importlib.import_module(module_path)
                    
                    # Find model client classes (subclasses of EnhancedBedrockBase)
                    for name, obj in inspect.getmembers(module):
                        if (inspect.isclass(obj) and 
                            issubclass(obj, EnhancedBedrockBase) and 
                            obj != EnhancedBedrockBase):
                            
                            # Get supported model IDs if available
                            if hasattr(obj, 'SUPPORTED_MODELS'):
                                for model_id in obj.SUPPORTED_MODELS:
                                    models_dict[model_id] = {
                                        'class': obj,
                                        'module': module_name,
                                        'family': self._determine_model_family(model_id)
                                    }
                            
                            # If no SUPPORTED_MODELS attribute, check for DEFAULT_MODEL_ID
                            elif hasattr(obj, 'DEFAULT_MODEL_ID'):
                                model_id = obj.DEFAULT_MODEL_ID
                                models_dict[model_id] = {
                                    'class': obj,
                                    'module': module_name,
                                    'family': self._determine_model_family(model_id)
                                }
                
                except (ImportError, AttributeError) as e:
                    # Log error but continue with other modules
                    self.output.warning(f"Could not load models from {module_name}: {e}")
        
        return models_dict
    
    def _determine_model_family(self, model_id):
        """
        [Function intent]
        Determine the model family based on model ID.
        
        [Design principles]
        - Reliable pattern matching
        - Maintainable grouping rules
        - Human-readable family names
        
        [Implementation details]
        - Uses pattern matching on model ID
        - Returns human-readable family name
        
        Args:
            model_id: The model ID to determine family for
            
        Returns:
            str: Human-readable model family name
        """
        model_id_lower = model_id.lower()
        
        if "claude" in model_id_lower:
            return "Claude (Anthropic)"
        elif "titan" in model_id_lower:
            return "Titan (Amazon)"
        elif "llama" in model_id_lower:
            return "Llama (Meta)"
        elif "falcon" in model_id_lower:
            return "Falcon (TII)"
        elif "mistral" in model_id_lower:
            return "Mistral"
        elif "cohere" in model_id_lower:
            return "Cohere"
        elif "nova" in model_id_lower:
            return "Nova (Amazon)"
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
                    
                    # Store the model class for initialization
                    self.model_class = model_info['class']
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
        Initialize the Bedrock model client using the appropriate model class.
        
        [Design principles]
        - Use correct model-specific implementation
        - Validate model availability before initializing
        - Proper configuration from system settings
        
        [Implementation details]
        - First checks if model exists in Bedrock
        - Uses the model class from discovery when available
        - Falls back to generic class if needed
        - Gets AWS credentials from config manager
        
        Args:
            model_id: ID of the model to initialize
            
        Raises:
            ValueError: If the model is not available or initialization fails
        """
        # Get AWS configuration from config manager
        from dbp.config.config_manager import ConfigurationManager
        
        config_manager = ConfigurationManager()
        config = config_manager.get_typed_config()
        
        # First check if model exists in Bedrock
        from dbp.llm.bedrock.model_discovery import BedrockModelDiscovery
        discovery = BedrockModelDiscovery(
            profile_name=config.aws.credentials_profile,
            logger=logger
        )
        
        # Verify model availability
        available_regions = discovery.get_model_regions(model_id)
        if not available_regions:
            raise ValueError(f"Model '{model_id}' is not available in any region. Please verify the model ID.")
            
        # Get the appropriate model class
        # If we already have the model class from selection, use it
        if hasattr(self, 'model_class') and self.model_class is not None:
            model_class = self.model_class
        else:
            # Otherwise, re-discover the appropriate model class
            available_models = self._get_available_models()
            if model_id not in available_models:
                # Fallback to EnhancedBedrockBase if specific model class not found
                from dbp.llm.bedrock.enhanced_base import EnhancedBedrockBase
                model_class = EnhancedBedrockBase
            else:
                model_class = available_models[model_id]['class']
        
        # Initialize the model client using the discovered class
        # Enable model discovery to automatically find the best region where the model is available
        self.model_client = model_class(
            model_id=model_id,
            region_name=config.aws.region,
            profile_name=config.aws.credentials_profile,
            use_model_discovery=True  # Enable model discovery to handle region availability
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
        try:
            from prompt_toolkit import PromptSession
            from prompt_toolkit.history import InMemoryHistory
            from prompt_toolkit.styles import Style
        except ImportError:
            self.output.error("prompt_toolkit package not found. Please install it with: pip install prompt_toolkit")
            return 1
            
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
        self.output.print("Type 'exit' to quit, 'help' for available commands\n")
        
        while True:
            try:
                # Get user input
                user_input = session.prompt("User > ", style=style)
                
                # Process special commands
                if user_input.lower() in ["exit", "quit"]:
                    self.output.print("\nExiting interactive chat mode.")
                    break
                elif user_input.lower() == "help":
                    self._print_help()
                    continue
                elif user_input.lower() == "clear":
                    self.chat_history = []
                    self.output.print("Chat history cleared.")
                    continue
                elif user_input.lower().startswith("config"):
                    self._handle_config_command(user_input)
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
                import traceback
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
        - Displays response chunks as they arrive
        - Updates chat history with complete response
        - Handles streaming errors gracefully
        """
        import asyncio
        
        self.output.print("\nAssistant > ", end="", flush=True)
        
        # Use the model's stream_chat method with our parameters
        response_text = ""
        
        async def process_stream():
            nonlocal response_text
            try:
                # Prepare messages format from history
                messages = [msg.copy() for msg in self.chat_history]
                
                # Stream the response
                async for chunk in self.model_client.stream_chat(
                    messages=messages,
                    **self.model_parameters
                ):
                    if "delta" in chunk and "text" in chunk["delta"]:
                        delta_text = chunk["delta"]["text"]
                        response_text += delta_text
                        print(delta_text, end="", flush=True)
            except Exception as e:
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
        - Shows current model parameters
        """
        self.output.print("\nAvailable commands:")
        self.output.print("  exit, quit     - Exit the chat session")
        self.output.print("  help           - Show this help message")
        self.output.print("  clear          - Clear chat history")
        self.output.print("  config         - Show current model parameters")
        self.output.print("  config [param] [value] - Change a model parameter")
        self.output.print("    Available parameters:")
        
        for param, config in self.MODEL_PARAMETERS.items():
            self.output.print(
                f"      {param}: {config['help']} "
                f"(current: {self.model_parameters.get(param, config['default'])})"
            )
        
        self.output.print()

    def _handle_config_command(self, command):
        """
        [Function intent]
        Handle the config command to view or change model parameters.
        
        [Design principles]
        - Clear parameter display
        - Validation of parameter values
        - Helpful error messages
        
        [Implementation details]
        - Parses command parts
        - Validates parameter names and values
        - Updates parameters when valid
        - Shows current configuration when no parameters specified
        
        Args:
            command: The config command string
        """
        parts = command.split()
        
        # Just 'config' - show current configuration
        if len(parts) == 1:
            self.output.print("\nCurrent model parameters:")
            for param, value in self.model_parameters.items():
                self.output.print(f"  {param}: {value}")
            return
        
        # 'config param value' - change a parameter
        if len(parts) == 3:
            param = parts[1]
            value_str = parts[2]
            
            if param not in self.MODEL_PARAMETERS:
                self.output.print(f"Unknown parameter: {param}")
                return
            
            param_config = self.MODEL_PARAMETERS[param]
            
            try:
                # Handle boolean parameters specially
                if param_config["type"] == bool:
                    # Convert string to boolean
                    if value_str.lower() in ['true', 'yes', 'y', '1', 'on']:
                        value = True
                    elif value_str.lower() in ['false', 'no', 'n', '0', 'off']:
                        value = False
                    else:
                        self.output.print(f"Invalid boolean value. Use true/false, yes/no, y/n, 1/0, or on/off")
                        return
                        
                    # Check if value is in allowed values if specified
                    if "values" in param_config and value not in param_config["values"]:
                        self.output.print(f"Invalid value. Allowed values are: {param_config['values']}")
                        return
                else:
                    # Convert value to the correct type
                    value = param_config["type"](value_str)
                    
                    # Validate range
                    if "min" in param_config and value < param_config["min"]:
                        self.output.print(f"Value too small. Minimum is {param_config['min']}")
                        return
                        
                    if "max" in param_config and value > param_config["max"]:
                        self.output.print(f"Value too large. Maximum is {param_config['max']}")
                        return
                
                # Update parameter
                self.model_parameters[param] = value
                self.output.print(f"Updated {param} to {value}")
                
            except ValueError:
                self.output.print(f"Invalid value for {param}: {value_str}")
                return
        else:
            self.output.print("Usage: config [parameter] [value]")
