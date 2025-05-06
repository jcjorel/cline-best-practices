# Integration Implementation

This document outlines how to integrate the new command completion functionality with the existing Bedrock test CLI code.

## Creating the Command Completion Module

First, create a new file `src/dbp_cli/commands/test/command_completion.py` with our command completer implementation:

```python
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
# Provides command completion functionality for the Bedrock test CLI interactive
# chat interface, enhancing user experience with auto-completion for commands
# starting with '/'.
###############################################################################
# [Source file design principles]
# - Clean separation of completion logic from command handling
# - Extensible design for adding new completable commands
# - Context-aware completion based on command structure
# - Support for dynamic parameter value generation
###############################################################################
# [Source file constraints]
# - Must work with prompt_toolkit's Completer interface
# - Depends on BedrockCommandHandler for command registry
# - Must handle nested command structures
###############################################################################
# [Dependencies]
# system:prompt_toolkit
# codebase:src/dbp_cli/commands/test/bedrock_commands.py
###############################################################################
# [GenAI tool change history]
# 2025-05-06T22:04:00Z : Initial creation of command completion module by CodeAssistant
# * Implemented CommandCompleter class for prompt_toolkit integration
# * Added support for command, parameter name, and parameter value completion
# * Created utils for extracting parameter values from different field types
###############################################################################

"""
Command completion module for Bedrock test CLI.

This module provides command completion functionality for the Bedrock test CLI
interactive chat interface, enhancing user experience with auto-completion for
commands starting with '/'.
"""

from prompt_toolkit.completion import Completer, Completion
from typing import Iterable, List, Dict, Any, Callable, Optional

class CommandCompleter(Completer):
    """
    [Class intent]
    Provides command completion for CLI commands starting with '/'.
    
    [Design principles]
    - Context-aware completion based on command structure
    - Support for command name, parameter name, and parameter value completion
    - Dynamic value generation based on command context
    
    [Implementation details]
    - Uses enhanced command registry for completion metadata
    - Parses command input to determine completion context
    - Supports dynamic parameter value providers
    """
    
    def __init__(self, command_handler):
        """
        [Function intent]
        Initialize the completer with the command handler.
        
        [Design principles]
        - Clean dependency injection
        - Simple initialization
        
        [Implementation details]
        - Stores reference to command handler for registry access
        - Sets up completion context state
        
        Args:
            command_handler: The BedrockCommandHandler instance
        """
        self.command_handler = command_handler
        
    def get_completions(self, document, complete_event):
        """
        [Function intent]
        Generate completions based on the current input text.
        
        [Design principles]
        - Context-aware completions
        - Progressive parsing of command input
        - Clear separation of completion types
        
        [Implementation details]
        - Parses the document text to identify completion context
        - Generates appropriate completions based on context
        - Returns completions with metadata for display
        
        Args:
            document: The document containing the input text
            complete_event: The completion event
            
        Returns:
            Iterable of Completion objects
        """
        text = document.text_before_cursor
        
        # Only provide completions for command text starting with '/'
        if not text.startswith('/'):
            return
            
        # Split text into command parts
        parts = text.strip().split()
        
        # Case 1: Completing a command name
        if len(parts) == 1:
            cmd_fragment = parts[0]
            yield from self._complete_command(cmd_fragment)
            
        # Case 2: Completing a parameter name or value
        elif len(parts) >= 2:
            command = parts[0]
            
            # Check if the command exists in the registry
            if command not in self.command_handler.get_command_registry():
                return
                
            # Get command info from registry
            cmd_info = self.command_handler.get_command_registry()[command]
            
            # If command has no parameters, no completions to offer
            if not cmd_info.get('parameters', {}):
                return
                
            # Case 2a: We're at a position to complete a parameter name or value
            if len(parts) == 2:
                # If the input ends with a space, we're starting a new parameter
                if text.endswith(' '):
                    yield from self._complete_parameters(command)
                else:
                    # Otherwise, we're completing a partial parameter
                    yield from self._complete_parameters(command, parts[1])
            
            # Case 2b: We have a parameter and we're completing its value
            elif len(parts) == 3:
                param = parts[1]
                
                # If param exists and we're starting or continuing a value
                if param in cmd_info.get('parameters', {}):
                    # If value is empty or partial
                    if text.endswith(' '):
                        value_fragment = ''
                    else:
                        value_fragment = parts[2]
                        
                    yield from self._complete_parameter_value(command, param, value_fragment)
    
    def _complete_command(self, cmd_fragment):
        """
        [Function intent]
        Complete command names based on the fragment.
        
        [Design principles]
        - Simple filtering of available commands
        - Include help text for context
        
        [Implementation details]
        - Filters commands that match the fragment
        - Provides command metadata for display
        
        Args:
            cmd_fragment: The command fragment to complete
            
        Returns:
            Iterable of Completion objects
        """
        for cmd, data in self.command_handler.get_command_registry().items():
            if cmd.startswith(cmd_fragment):
                yield Completion(
                    cmd[len(cmd_fragment):],
                    display=cmd,
                    display_meta=data.get('help', '')
                )
    
    def _complete_parameters(self, command, param_fragment=''):
        """
        [Function intent]
        Complete parameter names for a command.
        
        [Design principles]
        - Parameter name filtering based on partial input
        - Include help text for context
        
        [Implementation details]
        - Filters parameters that match the fragment
        - Provides parameter metadata for display
        
        Args:
            command: The command to get parameters for
            param_fragment: The parameter fragment to complete (optional)
            
        Returns:
            Iterable of Completion objects
        """
        cmd_info = self.command_handler.get_command_registry().get(command, {})
        parameters = cmd_info.get('parameters', {})
        
        for param, param_info in parameters.items():
            if param.startswith(param_fragment):
                yield Completion(
                    param[len(param_fragment):],
                    display=param,
                    display_meta=param_info.get('help', '')
                )
    
    def _complete_parameter_value(self, command, param, value_fragment=''):
        """
        [Function intent]
        Complete parameter values based on the parameter's value provider.
        
        [Design principles]
        - Dynamic value generation based on parameter type
        - Support for both static and callable value providers
        - Value filtering based on partial input
        
        [Implementation details]
        - Gets possible values from the parameter's value provider
        - Filters values that match the fragment
        - Provides value metadata for display
        
        Args:
            command: The command context
            param: The parameter to get values for
            value_fragment: The value fragment to complete (optional)
            
        Returns:
            Iterable of Completion objects
        """
        cmd_info = self.command_handler.get_command_registry().get(command, {})
        param_info = cmd_info.get('parameters', {}).get(param, {})
        
        # Get possible values from the value provider
        values_provider = param_info.get('values')
        if values_provider:
            if callable(values_provider):
                # Call with self (command_handler) if it requires it
                if 'self' in values_provider.__code__.co_varnames:
                    possible_values = values_provider(self.command_handler)
                else:
                    possible_values = values_provider()
            else:
                # Static list of values
                possible_values = values_provider
                
            # Generate completions for matching values
            for value in possible_values:
                if str(value).startswith(value_fragment):
                    # Special case for boolean values: complete as is
                    if isinstance(value, bool):
                        display_value = str(value)
                    else:
                        display_value = value
                    
                    yield Completion(
                        str(value)[len(value_fragment):],
                        display=str(display_value),
                        display_meta=param_info.get('help', '')
                    )
```

## Updating the BedrockCommandHandler

Modify `src/dbp_cli/commands/test/bedrock_commands.py` to use the enhanced command registry:

```python
def __init__(self, output_formatter, model_param_model, current_model_id=None, 
             get_model_constraints_fn=None, chat_history=None, state_callbacks=None):
    """
    [Function intent]
    Initialize the command handler with required dependencies.
    
    [Implementation details]
    - Enhanced with richer command registry for auto-completion
    - Maintains backwards compatibility with existing code
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
```

Add the new methods to support the command completer:

```python
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
```

Update the `process_command` method to work with the new registry structure:

```python
def process_command(self, command_text):
    """
    [Function intent]
    Process a command and return an action code.
    
    [Implementation details]
    - Enhanced to work with the new registry structure
    - Maintains backwards compatibility with existing code
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
```

## Updating the BedrockTestCommandHandler

Modify `src/dbp_cli/commands/test/bedrock.py` to use the new CommandCompleter class:

```python
# Add import for CommandCompleter at the top of the file
from .command_completion import CommandCompleter
```

Update the `_run_interactive_chat` method to use the command completer:

```python
def _run_interactive_chat(self):
    """
    [Function intent]
    Run an interactive chat session with the selected model.
    
    [Implementation details]
    - Enhanced with command completion support
    - Maintains full existing functionality
    """
    # Create prompt session with command completion
    history = InMemoryHistory()
    command_completer = CommandCompleter(self.command_handler)
    session = PromptSession(
        history=history,
        completer=command_completer
    )
    
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
```

## Testing Strategy

To validate the command completion implementation, we should test the following scenarios:

1. **Command Name Completion**: 
   - Enter "/" and press Tab to see all available commands
   - Enter partial command (e.g., "/h") and press Tab to complete it

2. **Parameter Name Completion**: 
   - Enter "/config " and press Tab to see available parameters
   - Enter "/config p" and press Tab to complete to "profile"

3. **Parameter Value Completion**:
   - Enter "/config profile " and press Tab to see available profiles
   - Enter "/config profile cl" and press Tab to complete profile name starting with "cl"

4. **Backward Compatibility**:
   - Ensure existing commands still work as expected
   - Verify command processing logic handles the enhanced registry correctly

## Edge Cases

Some edge cases to consider during implementation:

1. **Empty Completions**: Handle cases where no completions are available gracefully
2. **Nested Parameters**: Support for complex parameter structures if needed in the future
3. **Dynamic Parameters**: Ensure parameter values are generated based on current state
4. **Error Handling**: Handle exceptions in value providers without breaking the completer
5. **Performance**: Ensure completion operations are efficient, especially for large value lists
