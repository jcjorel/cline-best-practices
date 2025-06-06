# Interactive Chat Implementation

This document details the implementation of the interactive chat interface for the Bedrock test command.

## Design Goals

The interactive chat implementation aims to provide:
1. A user-friendly command-line interface for chatting with LLMs
2. Proper handling of streaming responses
3. Support for multi-turn conversations with history
4. Special commands for configuration and control

## Interactive Chat Session

The core of the interactive chat interface is the `_run_interactive_chat` method:

```python
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
    from prompt_toolkit import PromptSession
    from prompt_toolkit.history import InMemoryHistory
    from prompt_toolkit.styles import Style
    
    # Create prompt session
    history = InMemoryHistory()
    session = PromptSession(history=history)
    
    # Define styling
    style = Style.from_dict({
        'user': '#88ff88',
        'assistant': '#8888ff',
    })
    
    # Display welcome message
    self.output_formatter.print(f"\nInteractive chat mode with {self.model_client.model_id}")
    self.output_formatter.print("Type 'exit' to quit, 'help' for available commands\n")
    
    while True:
        try:
            # Get user input
            user_input = session.prompt("User > ", style=style)
            
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
            self.output_formatter.error(f"Error during chat: {str(e)}")
            import traceback
            traceback.print_exc()
    
    return 0
```

## Streaming Response Processing

To handle streaming responses from the model:

```python
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
    
    self.output_formatter.print("\nAssistant > ", end="", flush=True)
    
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
```

## Conversation History Management

The chat history is maintained as a list of message objects:

```python
# Initialize empty chat history
self.chat_history = []

# Add user message
self.chat_history.append({"role": "user", "content": user_input})

# Add assistant message
self.chat_history.append({"role": "assistant", "content": response_text})
```

This format is compatible with the Bedrock model client's `stream_chat` method and allows for multi-turn conversations.

## Help Display

The `_print_help` method displays available commands and their usage:

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

## Input Enhancements

The implementation uses `prompt_toolkit` for an enhanced input experience:

1. **Command History**: Users can navigate through previous commands using up/down arrows
2. **Line Editing**: Standard readline-like editing capabilities
3. **Syntax Highlighting**: Different colors for user and assistant messages

These enhancements make the chat interface more user-friendly and efficient.

## Multiline Input Support

For entering longer prompts, the implementation will support multiline input:

```python
from prompt_toolkit import PromptSession
from prompt_toolkit.validation import Validator, ValidationError

class EmptyInputValidator(Validator):
    def validate(self, document):
        text = document.text
        if not text.strip() and text.endswith('\n'):
            raise ValidationError(message="Input cannot be empty")

def _get_multiline_input(self, session):
    """Get multiline input from user (Ctrl+Enter to submit)"""
    validator = EmptyInputValidator()
    multiline_input = session.prompt(
        "User > ", 
        multiline=True, 
        validator=validator
    )
    return multiline_input.rstrip()
```

## Streaming Output Display

The streaming output display is designed to:

1. Display response chunks as they arrive
2. Support rendering of special formatting (e.g., code blocks)
3. Handle cancellation via Ctrl+C
4. Provide visual feedback during processing

This approach gives users immediate feedback and allows them to interrupt long responses if needed.

## Performance Considerations

To ensure good performance during chat sessions:

1. **Efficient Stream Processing**: The implementation uses efficient stream processing to minimize latency
2. **Memory Management**: The chat history is managed to prevent excessive memory usage
3. **Error Recovery**: The implementation can recover from errors without crashing the session

These optimizations help ensure a smooth chat experience even with large response volumes.

## Dependencies

The implementation requires:

1. **prompt_toolkit**: For enhanced CLI input experience
2. **asyncio**: For handling asynchronous streaming responses
3. Access to the Bedrock model client's streaming capabilities via `stream_chat`

These dependencies should be available in the existing environment or specified as requirements.
