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
# chat interface, enhancing user experience with auto-completion for commands.
# Supports both empty input (double tab) completion and completion for commands
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
# 2025-05-07T00:36:00Z : Added empty input command completion on double tab by CodeAssistant
# * Added functionality to show all commands when pressing Tab with empty input
# * Updated function intent documentation to reflect empty input handling
# * Enhanced design principles to support double tab completion without slash prefix
# * Modified implementation details to recognize and handle empty input state
# 2025-05-06T22:35:00Z : Improved completion priority logic by CodeAssistant
# * Completely redesigned the completion logic with explicit priority handling
# * Fixed edge case with "/config profile " space completion showing "profile" again
# * Added early return statements to ensure only one completion type is shown
# * Separated parameter name and value completion into distinct code paths
# 2025-05-06T22:10:00Z : Initial creation of command completion module by CodeAssistant
# * Implemented CommandCompleter class for prompt_toolkit integration
# * Added support for command, parameter name, and parameter value completion
# * Created utils for extracting parameter values from different field types
###############################################################################

"""
Command completion module for Bedrock test CLI.

This module provides command completion functionality for the Bedrock test CLI
interactive chat interface, enhancing user experience with auto-completion for
commands. Supports both empty input completion (double tab to show all commands)
and completion for commands starting with '/'.
"""

from prompt_toolkit.completion import Completer, Completion
from typing import Iterable, List, Dict, Any, Callable, Optional

class CommandCompleter(Completer):
    """
    [Class intent]
    Provides command completion for CLI commands with enhanced user experience.
    Supports both empty input (double tab to show all commands) and commands
    starting with '/'.
    
    [Design principles]
    - Context-aware completion based on command structure
    - Support for command name, parameter name, and parameter value completion
    - Dynamic value generation based on command context
    - Empty input completion for discoverable commands
    
    [Implementation details]
    - Uses enhanced command registry for completion metadata
    - Parses command input to determine completion context
    - Supports dynamic parameter value providers
    - Shows all available commands on double tab with empty input
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
        - Support for empty input completion (double tab)
        
        [Implementation details]
        - Parses the document text to identify completion context
        - Generates appropriate completions based on context
        - Returns completions with metadata for display
        - Shows command completions on double tab with empty input
        
        Args:
            document: The document containing the input text
            complete_event: The completion event
            
        Returns:
            Iterable of Completion objects
        """
        text = document.text_before_cursor
        
        # Handle empty or whitespace-only input for double tab (showing all commands)
        if not text.strip():
            # Return completions for all commands
            for cmd, data in self.command_handler.get_command_registry().items():
                yield Completion(
                    cmd,
                    display=cmd,
                    display_meta=data.get('help', '')
                )
            return
            
        # Only provide completions for command text starting with '/'
        if not text.startswith('/'):
            return
            
        # Split text into command parts
        parts = text.strip().split()
        
        # Case 1: Completing a command name
        if len(parts) == 1:
            cmd_fragment = parts[0]
            yield from self._complete_command(cmd_fragment)
            return
            
        # For all other cases, we need at least 2 parts and a valid command
        if len(parts) < 2:
            return
            
        command = parts[0]
            
        # Check if the command exists in the registry
        if command not in self.command_handler.get_command_registry():
            return
            
        # Get command info from registry
        cmd_info = self.command_handler.get_command_registry()[command]
        
        # If command has no parameters, no completions to offer
        if not cmd_info.get('parameters', {}):
            return
            
        # Case 2: Parameter value completion - highest priority
        # This handles "/config profile " with a space after parameter
        if len(parts) == 2 and text.endswith(' '):
            param = parts[1]
            
            # If this is a valid parameter, complete values
            if param in cmd_info.get('parameters', {}):
                yield from self._complete_parameter_value(command, param, '')
                return
            
        # Case 3: Parameter value with partial input
        # This handles "/config profile d" with partial value
        elif len(parts) == 3:
            param = parts[1]
            
            # If this is a valid parameter, complete values
            if param in cmd_info.get('parameters', {}):
                value_fragment = parts[2]
                yield from self._complete_parameter_value(command, param, value_fragment)
                return
                
        # Case 4: Parameter name completion (lowest priority)
        # Only reached if we're not completing values
        if len(parts) == 2 and not text.endswith(' '):
            yield from self._complete_parameters(command, parts[1])
        else:
            yield from self._complete_parameters(command)
    
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
                if hasattr(values_provider, '__code__') and 'self' in values_provider.__code__.co_varnames:
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
