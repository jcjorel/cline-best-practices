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
# Provides command handling functionality for the Bedrock test CLI, separating the
# command processing logic from the main command handler to improve maintainability
# and follow the Single Responsibility Principle.
###############################################################################
# [Source file design principles]
# - Single responsibility for command processing
# - Clear command routing and execution
# - Consistent error handling
# - Easily extensible for new commands
# - Dependency injection for required services
###############################################################################
# [Source file constraints]
# - Must coordinate with BedrockTestCommandHandler for state management
# - Depends on model_parameters module for parameter handling
# - Requires output_formatter for user feedback
###############################################################################
# [Dependencies]
# codebase:src/dbp_cli/commands/test/bedrock.py
# codebase:src/dbp/llm/bedrock/model_parameters.py
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-06T22:10:00Z : Enhanced command registry for auto-completion support by CodeAssistant
# * Updated command registry with rich metadata for completion
# * Added methods to support command completion
# * Added parameter value provider methods
# * Added version-agnostic field type utilities
# 2025-05-06T19:47:00Z : Simplified parameter validation by leveraging pydantic capabilities by CodeAssistant
# * Removed _extract_field_constraints() and _validate_constraints() methods
# * Directly used model_param_model.validate_config() for parameter validation
# * Simplified the command handling code with direct validation
# * Eliminated complex constraint extraction logic in favor of built-in validation
# 2025-05-06T12:13:00Z : Created file for command handling separation by CodeAssistant
# * Extracted command handling logic from bedrock.py
# * Implemented command registry for extensible command management
# * Added state management through callbacks
# * Improved modularity by separating command processing concerns
###############################################################################

"""
Command handling for the Bedrock test CLI.

This module contains the command handling functionality for the Bedrock test command-line
interface, separated from the main command handler for improved maintainability.
"""

import logging
from typing import Dict, Any, Optional, Callable, List, Union


class BedrockCommandHandler:
    """
    [Class intent]
    Handles processing and execution of special commands in the Bedrock test CLI.
    
    [Design principles]
    - Single responsibility for command processing
    - Clear command routing and execution 
    - Consistent error handling
    - Easily extensible for new commands
    
    [Implementation details]
    - Uses command registry pattern for command routing
    - Provides callback mechanism for state coordination
    - Separates command parsing from execution
    - Leverages Pydantic for parameter validation
    """
    
    # Result code definitions
    RESULT_EXIT = "exit"
    RESULT_CONTINUE = "continue"
    RESULT_NORMAL = "normal"
    
    def __init__(self, output_formatter, model_param_model, current_model_id=None, 
                 get_model_constraints_fn=None, chat_history=None, state_callbacks=None):
        """
        [Function intent]
        Initialize the command handler with required dependencies.
        
        [Design principles]
        - Clean dependency injection
        - Flexible state management
        - Clear initialization
        
        [Implementation details]
        - Stores references to required services
        - Sets up command registry
        - Initializes callback dictionary
        
        Args:
            output_formatter: Output formatter for displaying results
            model_param_model: Model parameters model for configuration
            current_model_id: Current model ID reference
            get_model_constraints_fn: Function to get model constraints
            chat_history: Reference to chat history list
            state_callbacks: Dictionary of callback functions for state changes
        """
        self.output = output_formatter
        self.model_param_model = model_param_model
        self.current_model_id = current_model_id
        self.get_model_constraints = get_model_constraints_fn
        self.chat_history = chat_history or []
        self.state_callbacks = state_callbacks or {}
        
        # Enhanced command registry - maps command prefixes to handler metadata
        self.command_registry = {
            "/help": {
                "handler": self.cmd_help,
                "help": "Show available commands and usage",
                "parameters": {}
            },
            "/exit": {
                "handler": self.cmd_exit,
                "help": "Exit the chat session",
                "parameters": {}
            },
            "/quit": {
                "handler": self.cmd_exit,
                "help": "Exit the chat session (alias for /exit)",
                "parameters": {}
            },
            "/clear": {
                "handler": self.cmd_clear,
                "help": "Clear chat history",
                "parameters": {}
            },
            "/config": {
                "handler": self.cmd_config,
                "help": "Show or change model parameters",
                "parameters": {
                    "profile": {
                        "help": "Apply a parameter profile",
                        "values": lambda: list(self.model_param_model._profiles.keys()),
                        "completion_hint": "<profile_name>"
                    }
                    # Parameter name completion handled dynamically
                }
            }
        }
    
    def get_command_registry(self):
        """
        [Function intent]
        Get the command registry for auto-completion.
        
        [Design principles]
        - Simple accessor for command registry
        - Supports external command completer
        
        [Implementation details]
        - Returns the command registry dictionary
        - Used by the CommandCompleter
        
        Returns:
            dict: The command registry
        """
        return self.command_registry
        
    def process_command(self, command_text):
        """
        [Function intent]
        Process a command and return an action code.
        
        [Design principles]
        - Clean command routing
        - Consistent return values
        - Clear error handling
        
        [Implementation details]
        - Enhanced to work with the new registry structure
        - Finds matching command prefix
        - Delegates to appropriate handler
        - Handles missing commands gracefully
        
        Args:
            command_text: The raw command text from the user
            
        Returns:
            str: Action code - "exit", "continue", or "normal"
        """
        # Find matching command prefix
        matching_prefix = None
        for prefix in self.command_registry:
            if command_text.lower().startswith(prefix):
                matching_prefix = prefix
                break
        
        # Execute the appropriate command handler if found
        if matching_prefix:
            cmd_info = self.command_registry[matching_prefix]
            handler = cmd_info["handler"]
            # Pass the remainder of the command (after the prefix) to the handler
            return handler(command_text[len(matching_prefix):].strip())
            
        # No matching command found - treat as normal message
        return self.RESULT_NORMAL
    
    def cmd_help(self, args):
        """
        [Function intent]
        Handle /help command to display available commands and parameters.
        
        [Design principles]
        - Clear organization of help content
        - Comprehensive command descriptions
        
        [Implementation details]
        - Lists all available commands
        - Shows current parameter profiles and values
        
        Args:
            args: Command arguments (unused for help)
            
        Returns:
            str: Action code (always RESULT_CONTINUE)
        """
        self.print_help()
        return self.RESULT_CONTINUE
    
    def cmd_exit(self, args):
        """
        [Function intent]
        Handle /exit or /quit command to terminate the chat session.
        
        [Design principles]
        - Clean exit process
        - Clear user feedback
        
        [Implementation details]
        - Displays exit message
        - Returns exit code for flow control
        
        Args:
            args: Command arguments (unused for exit)
            
        Returns:
            str: Action code (always RESULT_EXIT)
        """
        self.output.print("\nExiting interactive chat mode.")
        return self.RESULT_EXIT
    
    def cmd_clear(self, args):
        """
        [Function intent]
        Handle /clear command to reset chat history.
        
        [Design principles]
        - Clean state reset
        - Proper coordination with main handler
        
        [Implementation details]
        - Clears local history reference if available
        - Calls callback for state coordination if provided
        
        Args:
            args: Command arguments (unused for clear)
            
        Returns:
            str: Action code (always RESULT_CONTINUE)
        """
        if self.chat_history is not None:
            self.chat_history.clear()
            
        # Notify if callback exists
        if "on_history_clear" in self.state_callbacks:
            self.state_callbacks["on_history_clear"]()
            
        self.output.print("Chat history cleared.")
        return self.RESULT_CONTINUE
    
    def cmd_config(self, args):
        """
        [Function intent]
        Handle /config command for parameter configuration.
        
        [Design principles]
        - Parameter validation
        - Clear user feedback
        - State coordination
        
        [Implementation details]
        - Delegates to configuration handler
        - Handles parameter validation and updates
        
        Args:
            args: Command arguments for configuration
            
        Returns:
            str: Action code (always RESULT_CONTINUE)
        """
        # Delegate to the configuration handler
        self._handle_config_command(args)
        return self.RESULT_CONTINUE
    
    def print_help(self):
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
        
        # Show available profiles using the dedicated helper
        self._display_profile_info()
        
        # Show available parameters using the dedicated helper
        self.output.print("\nAvailable parameters:")
        self._display_parameter_info()
        
        self.output.print()
        
    def _parse_config_command(self, command_input):
        """
        [Function intent]
        Parse config command input into structured command data.
        
        [Design principles]
        - Clear separation of parsing and execution logic
        - Structured command representation
        - Standardized format
        
        [Implementation details]
        - Parses command string into meaningful parts
        - Identifies command type
        - Extracts relevant parameters
        - Returns command data dictionary
        
        Args:
            command_input: Raw config command string from user
            
        Returns:
            dict: Command data with type and parameters
        """
        parts = command_input.split(None, 3)
        command = {"type": "unknown"}
        
        # Just "config" - show all parameters
        if len(parts) == 0:
            command["type"] = "show_all"
            return command
            
        # Handle "config profile <name>" - Apply a profile
        if len(parts) >= 2 and parts[0].lower() == "profile":
            command["type"] = "apply_profile"
            command["profile_name"] = parts[1]
            return command
            
        # "config param value" - set parameter
        if len(parts) >= 2:
            command["type"] = "set_parameter"
            command["param"] = parts[0]
            command["value"] = parts[1]
            return command
            
        # "config param" - show specific parameter
        if len(parts) == 1:
            param = parts[0]
            
            # Special handling for "profile"
            if param.lower() == "profile":
                command["type"] = "show_profile"
                return command
                
            command["type"] = "show_parameter"
            command["param"] = param
            return command
            
        return command
    
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
        - Uses command parser to get structured command data
        - Validates parameter names and values
        - Updates parameters and provides feedback
        - Handles profile selection
        
        Args:
            command_input: Config command input from user
        """
        # Parse the command input
        command = self._parse_config_command(command_input)
        
        # Handle different command types
        if command["type"] == "show_all":
            # Show all configuration
            self.print_help()
            return
            
        elif command["type"] == "apply_profile":
            profile_name = command["profile_name"]
            
            # Validate profile name
            if profile_name not in self.model_param_model._profiles:
                self.output.error(f"Unknown profile: {profile_name}")
                self.output.print("Available profiles: " + ", ".join(self.model_param_model._profiles.keys()))
                return
            
            # Apply the profile if we have a model ID
            if self.current_model_id:
                # Notify parent handler to create a fresh model
                if "on_apply_profile" in self.state_callbacks:
                    self.state_callbacks["on_apply_profile"](profile_name)
                    self.output.print(f"Applied profile: {profile_name}")
                    
                    # Show updated parameters
                    self.output.print("\nCurrent parameters:")
                    self._display_parameter_info(show_description=False)
                    return
                else:
                    self.output.error("Cannot apply profile: Callback not available")
                    return
            else:
                self.output.error("Cannot apply profile: Model ID not available")
                return
                
        elif command["type"] == "show_profile":
            # Show current profile
            self.output.print(f"Current profile: {self.model_param_model._current_profile}")
            return
            
        elif command["type"] == "show_parameter":
            param = command["param"]
            
            # Check if parameter exists
            if param not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {param}")
                return
                
            # Display parameter info
            self._display_parameter_info(param, show_description=True)
            return
            
        elif command["type"] == "set_parameter":
            param = command["param"]
            value_str = command["value"]
            
            # Debugging to help understand parameter validation
            self.output.print(f"Validating parameter '{param}' with value '{value_str}'...")
            
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
                    # Validate the value using Pydantic's built-in validation
                    valid, errors = self.model_param_model.validate_config({param: value})
                    if not valid:
                        self.output.error(errors[param])
                        return
                    
                    # If we have a model ID and this is a max_tokens parameter, double-check against
                    # model-specific constraints
                    if param == "max_tokens" and self.current_model_id and self.get_model_constraints:
                        # Use centralized model constraints method
                        constraints = self.get_model_constraints(self.current_model_id)
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
                
                # Notify parent handler if needed
                if "on_parameter_change" in self.state_callbacks:
                    self.state_callbacks["on_parameter_change"](param, value)
                
            except ValueError:
                self.output.error(f"Invalid value for {param}: {value_str}")
            
            return
        
        # Unknown command type
        self.output.print("Usage: config [param] [value] or config profile <name>")

    def _display_parameter_info(self, field_name=None, show_description=True):
        """
        [Function intent]
        Display information about model parameters in a consistent format.
        
        [Design principles]
        - Reusable parameter display logic
        - Consistent formatting across commands
        - Flexible display options
        
        [Implementation details]
        - Can display all parameters or just a specific one
        - Handles field description extraction
        - Shows applicability information
        - Can be used by both help and config commands
        
        Args:
            field_name: Optional specific parameter to display, or None for all
            show_description: Whether to include field descriptions
        """
        if field_name is not None:
            # Display a specific parameter
            if field_name not in self.model_param_model.__fields__:
                self.output.error(f"Unknown parameter: {field_name}")
                return
                
            field = self.model_param_model.__fields__[field_name]
            value = getattr(self.model_param_model, field_name)
            
            # Get description if requested
            desc = ""
            if show_description:
                desc = self._get_field_description(field)
                
            # Show applicability info
            applicable = self.model_param_model.is_applicable(field_name)
            applicable_str = " (applicable)" if applicable else " (not applicable in current profile)"
            
            desc_str = f" ({desc})" if desc and show_description else ""
            self.output.print(f"{field_name} = {value}{desc_str}{applicable_str}")
        else:
            # Display all applicable parameters
            for field_name, field in self.model_param_model.__fields__.items():
                # Only show applicable parameters in current profile
                if self.model_param_model.is_applicable(field_name):
                    value = getattr(self.model_param_model, field_name)
                    
                    # Get field description if requested
                    desc = ""
                    if show_description:
                        desc = self._get_field_description(field)
                        
                    desc_str = f" ({desc})" if desc and show_description else ""
                    self.output.print(f"  {field_name} = {value}{desc_str}")
                    
    def _display_profile_info(self):
        """
        [Function intent]
        Display information about available parameter profiles.
        
        [Design principles]
        - Reusable profile display logic
        - Consistent formatting
        - Clear indication of active profile
        
        [Implementation details]
        - Shows all available profiles
        - Marks the active profile with an asterisk
        - Can be used by both help and config commands
        """
        self.output.print("\nAvailable parameter profiles:")
        for profile_name in self.model_param_model._profiles.keys():
            if profile_name == self.model_param_model._current_profile:
                self.output.print(f"  * {profile_name} (active)")
            else:
                self.output.print(f"  - {profile_name}")
    
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
    
    def get_parameter_values(self, param_name):
        """
        [Function intent]
        Get possible values for a parameter based on context.
        
        [Design principles]
        - Type-aware value generation
        - Support for different parameter types
        - Extensible for new parameter types
        
        [Implementation details]
        - Handles different parameter types
        - Returns appropriate values for each parameter type
        - Supports dynamic values based on current state
        
        Args:
            param_name: The parameter name to get values for
            
        Returns:
            list: Possible values for the parameter
        """
        if param_name == 'profile':
            return list(self.model_param_model._profiles.keys())
        elif param_name in self.model_param_model.__fields__:
            field = self.model_param_model.__fields__[param_name]
            
            # Handle enum types
            if self._is_enum_field(field):
                return self._get_enum_values(field)
                
            # Handle boolean parameters
            elif self._get_field_type(field) is bool:
                return ['True', 'False']
                
        return []
    
    def _is_enum_field(self, field):
        """
        [Function intent]
        Check if a field is an enum type.
        
        [Design principles]
        - Compatible with different Pydantic versions
        - Robust detection of enum types
        
        [Implementation details]
        - Inspects field type metadata
        - Works with both Pydantic v1 and v2
        
        Args:
            field: The field to check
            
        Returns:
            bool: True if the field is an enum type
        """
        # Logic to detect enum types in Pydantic fields
        field_type = self._get_field_type(field)
        
        # Check for enum types in different ways
        if hasattr(field_type, '__members__'):
            return True
            
        # Additional enum detection logic
        return False
    
    def _get_enum_values(self, field):
        """
        [Function intent]
        Get possible values for an enum field.
        
        [Design principles]
        - Compatible with different Pydantic versions
        - Extract values in a consistent format
        
        [Implementation details]
        - Extracts enum values from field metadata
        - Works with both Pydantic v1 and v2
        
        Args:
            field: The enum field to get values for
            
        Returns:
            list: Enum values as strings
        """
        field_type = self._get_field_type(field)
        
        # Extract enum values
        if hasattr(field_type, '__members__'):
            return list(field_type.__members__.keys())
            
        return []
    
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
    
    
    def update_model_param_model(self, model_param_model):
        """
        [Function intent] 
        Update the model parameter model reference.
        
        [Design principles]
        - Clean state synchronization
        - Dependency injection
        
        [Implementation details]
        - Updates internal reference to model parameter model
        
        Args:
            model_param_model: New model parameter model instance
        """
        self.model_param_model = model_param_model
        
    def update_current_model_id(self, current_model_id):
        """
        [Function intent]
        Update the current model ID reference.
        
        [Design principles]
        - Clean state synchronization
        - Dependency injection
        
        [Implementation details]
        - Updates internal reference to current model ID
        
        Args:
            current_model_id: New current model ID
        """
        self.current_model_id = current_model_id
