# Special Commands Implementation

This document details the implementation of special commands for the interactive chat interface of the Bedrock test command.

## Special Commands Overview

The interactive chat interface will support the following special commands:

1. **exit/quit** - Exit the chat session
2. **help** - Display available commands and help information
3. **clear** - Clear the chat history
4. **config** - View or modify model parameters

## Command Processing

Special commands are processed in the `_run_interactive_chat` method:

```python
# Process special commands
if user_input.lower() in ["exit", "quit"]:
    self.output_formatter.print("\nExiting interactive chat mode.")
    break
elif user_input.lower() == "help":
    self._print_help()
    continue
elif user_input.lower() == "clear":
    self.chat_history = []
    self.output_formatter.print("Chat history cleared.")
    continue
elif user_input.lower().startswith("config"):
    self._handle_config_command(user_input)
    continue
elif not user_input.strip():
    # Skip empty inputs
    continue
```

## Help Command Implementation

The `help` command displays detailed information about available commands:

```python
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
    self.output_formatter.print("\nAvailable commands:")
    self.output_formatter.print("  exit, quit     - Exit the chat session")
    self.output_formatter.print("  help           - Show this help message")
    self.output_formatter.print("  clear          - Clear chat history")
    self.output_formatter.print("  config         - Show current model parameters")
    self.output_formatter.print("  config [param] [value] - Change a model parameter")
    self.output_formatter.print("    Available parameters:")
    
    for param, config in self.MODEL_PARAMETERS.items():
        self.output_formatter.print(
            f"      {param}: {config['help']} "
            f"(current: {self.model_parameters.get(param, config['default'])})"
        )
    
    self.output_formatter.print()
```

## Config Command Implementation

The `config` command allows viewing and modifying model parameters:

```python
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
        self.output_formatter.print("\nCurrent model parameters:")
        for param, value in self.model_parameters.items():
            self.output_formatter.print(f"  {param}: {value}")
        return
    
    # 'config param value' - change a parameter
    if len(parts) == 3:
        param = parts[1]
        value_str = parts[2]
        
        if param not in self.MODEL_PARAMETERS:
            self.output_formatter.print(f"Unknown parameter: {param}")
            return
        
        param_config = self.MODEL_PARAMETERS[param]
        
        try:
            # Convert value to the correct type
            value = param_config["type"](value_str)
            
            # Validate range
            if "min" in param_config and value < param_config["min"]:
                self.output_formatter.print(f"Value too small. Minimum is {param_config['min']}")
                return
                
            if "max" in param_config and value > param_config["max"]:
                self.output_formatter.print(f"Value too large. Maximum is {param_config['max']}")
                return
            
            # Update parameter
            self.model_parameters[param] = value
            self.output_formatter.print(f"Updated {param} to {value}")
            
        except ValueError:
            self.output_formatter.print(f"Invalid value for {param}: {value_str}")
            return
    else:
        self.output_formatter.print("Usage: config [parameter] [value]")
```

## Clear Command Implementation

The `clear` command resets the conversation history:

```python
# Clear command implementation
elif user_input.lower() == "clear":
    self.chat_history = []
    self.output_formatter.print("Chat history cleared.")
    continue
```

This is a simple operation that resets the chat history to an empty list, effectively starting a fresh conversation while maintaining the same model client.

## Exit Command Implementation

The `exit` command terminates the chat session:

```python
# Exit command implementation
if user_input.lower() in ["exit", "quit"]:
    self.output_formatter.print("\nExiting interactive chat mode.")
    break
```

This breaks out of the main chat loop, causing the `_run_interactive_chat` method to return, which ends the command execution.

## Command Arguments Parsing

For commands with arguments (like `config`), the implementation uses a simple space-based tokenization:

```python
parts = command.split()
```

This approach is straightforward for the simple commands supported, though for more complex command syntax a more sophisticated parsing approach could be used.

## Parameter Validation

Parameter validation is handled in the `_handle_config_command` method:

```python
# Convert value to the correct type
value = param_config["type"](value_str)

# Validate range
if "min" in param_config and value < param_config["min"]:
    self.output_formatter.print(f"Value too small. Minimum is {param_config['min']}")
    return
    
if "max" in param_config and value > param_config["max"]:
    self.output_formatter.print(f"Value too large. Maximum is {param_config['max']}")
    return
```

This ensures that parameter values are valid before they are applied to the model.

## Error Handling

Error handling for commands is implemented at multiple levels:

1. **Command Syntax Errors**: Handled by checking the number of parts in the command
2. **Unknown Parameters**: Checked against the known parameter list
3. **Type Conversion Errors**: Caught as `ValueError` exceptions
4. **Range Validation Errors**: Checked explicitly against min/max values

These error handling mechanisms ensure that users get clear feedback when commands are invalid.

## User Experience Considerations

To ensure a good user experience:

1. **Clear Feedback**: Commands provide clear feedback about their execution
2. **Help on Error**: Invalid commands show usage information
3. **Current Values**: The `config` command shows current parameter values
4. **Consistency**: Command syntax follows a consistent pattern

These considerations make the command interface intuitive and easy to use.

## Testing Approach

Testing for special commands should include:

1. **Basic Command Execution**: Test that each command performs its basic function
2. **Error Handling**: Test error cases for invalid commands
3. **Parameter Validation**: Test parameter validation for the `config` command
4. **Edge Cases**: Test edge cases like empty input

This testing approach ensures that the command interface works reliably in all scenarios.
