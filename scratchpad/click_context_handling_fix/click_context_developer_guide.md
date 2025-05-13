# Click Context Handling Developer Guide

## Overview

This guide explains the improved context handling mechanism in our Click-based CLI implementation. The changes ensure our commands can access both Click's native context features and our application services.

## Key Concepts

### Before the Change

Previously, we defined our own `Context` class and used a custom `pass_context` decorator:

```python
# Old approach (don't use this anymore)
@pass_context
def some_command(ctx: Context):
    ctx.api_client.do_something()  # Direct access to our Context attributes
```

This prevented commands from accessing Click's native context features.

### After the Change

Now we use Click's native context with our application services stored in the `obj` attribute:

```python
# New approach (use this going forward)
@click.pass_context
def some_command(ctx: click.Context):
    ctx.obj.api_client.do_something()  # Access via ctx.obj
    
    # Can also use Click's context features
    parent_context = ctx.parent  # Get parent command's context
    ctx.invoke(other_command)  # Invoke another command
```

## How It Works

1. Our application context (`AppContext`) is created and stored in Click's context `obj` attribute
2. Commands receive Click's native context via `@click.pass_context`
3. Application services are accessed via `ctx.obj`
4. Click's context features are available directly on `ctx`

## Application Context (AppContext)

The `AppContext` class contains all our application services:

- `config_manager` - Configuration management
- `auth_manager` - Authentication services
- `api_client` - API client for server communication
- `output_formatter` - Output formatting utilities
- `progress_indicator` - Progress indication for long operations

## Accessing Services

Access application services through the `obj` attribute:

```python
# Access configuration manager
ctx.obj.config_manager.get_config()

# Use API client
ctx.obj.api_client.call_tool("tool_name", parameters)

# Format output
ctx.obj.output_formatter.format_output(result)

# Show progress
ctx.obj.with_progress("Working...", some_function, arg1, arg2)
```

## Click's Context Features

You can now use native Click context features:

```python
# Get metadata about the command
command_name = ctx.command.name
command_help = ctx.command.help

# Access parent context (for nested commands)
parent_ctx = ctx.parent

# Invoke another command
ctx.invoke(other_command, param1="value")

# Forward parameters
ctx.forward(other_command)

# Get parameters from the context
param_value = ctx.params["param_name"]
```

## Decorator Order

When applying multiple decorators, follow this order:

```python
@click.command()
@click.option("--option", help="Some option")
@click.pass_context  # Click's context decorator comes before our decorators
@api_command  # Our custom decorators come after Click's
@catch_errors
def some_command(ctx, option):
    # ...
```

## Command Migration Checklist

When migrating existing commands:

1. Replace `@pass_context` with `@click.pass_context`
2. Change parameter type from `ctx: Context` to `ctx: click.Context`
3. Update service access from `ctx.service` to `ctx.obj.service`
4. Update documentation to mention Click's context

## Benefits of the New Approach

- Access to Click's powerful context features
- Better separation of Click context and application services
- Follows Click's recommended best practices
- More maintainable and easier to understand
- Ability to use commands like `ctx.invoke()` and `ctx.forward()`

## Example: Complete Command

```python
@click.command()
@click.argument("name")
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
@click.pass_context
@api_command
@catch_errors
def fetch_command(ctx: click.Context, name: str, format: str) -> int:
    """Fetch an item by name."""
    try:
        # Access application services via ctx.obj
        result = ctx.obj.api_client.fetch_item(name)
        
        # Format output using output formatter service
        ctx.obj.output_formatter.format_output(result, format=format)
        
        # Use Click's context features if needed
        if ctx.parent and hasattr(ctx.parent.obj, "last_result"):
            ctx.parent.obj.last_result = result
            
        return 0
    except Exception as e:
        ctx.obj.output_formatter.error(str(e))
        return 1
```

## Testing Context Handling

Our test suite includes specific tests for context handling:

- `test_app_context_initialization` - Verifies `AppContext` initialization
- `test_cli_context_setup` - Validates CLI context setup
- `test_context_service_access` - Tests access to application services
- `test_click_context_features` - Checks access to Click's context features
- `test_context_command_invocation` - Validates command invocation capabilities

Run the tests with:

```bash
pytest src/dbp_cli/cli_click/tests/test_context_handling.py
