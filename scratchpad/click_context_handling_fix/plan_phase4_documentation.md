# Phase 4: Documentation Updates

This document outlines the documentation changes needed to support the Click context handling updates. Good documentation is crucial for ensuring proper use of the new context pattern in current and future code.

## Docstring Updates

### AppContext Class Docstring

Update the renamed `AppContext` class docstring to clearly identify its role:

```python
class AppContext:
    """
    [Class intent]
    Represents the application-level services container passed between Click commands,
    providing access to shared configuration, authentication, API clients, and output formatting.
    
    [Implementation details]
    Used as the 'obj' attribute of Click's context object (ctx.obj). Holds instances of 
    core services like configuration, authentication, API client, output formatting,
    and progress indication. Provides convenience methods for accessing
    configuration values and handling errors.
    
    [Design principles]
    Dependency injection container - centralizes service creation and access.
    Progressive initialization - services are created only when needed.
    Consistent error handling - standardized approach for all error conditions.
    """
    # Implementation...
```

### Decorator Docstrings

Update the docstrings for the decorator functions:

```python
def common_options(function: F) -> F:
    """
    [Function intent]
    Apply common CLI options to a Click command function.
    
    [Implementation details]
    Creates a decorator that adds standard global options like:
    - --config for configuration file path
    - --verbose/-v for verbosity level
    - --quiet/-q for suppressing non-error output
    - --debug for enabling debug mode
    - --output/-o for output format
    - --no-color for disabling colored output
    - --no-progress for disabling progress indicators
    
    Option values are used to initialize the AppContext (stored in ctx.obj)
    for use by commands.
    
    [Design principles]
    Decorator pattern - attaches common options to command functions.
    Composition - decorators are applied in a specific order for correct behavior.
    DRY principle - avoids repeating option definitions across commands.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with common options
    """
    # Implementation...
```

```python
def api_command(function: CommandFunction) -> CommandFunction:
    """
    [Function intent]
    Mark a command as requiring API access and ensure API client is initialized.
    
    [Implementation details]
    Creates a decorator that initializes the API client in AppContext (ctx.obj)
    before executing the command. Catches API initialization errors and handles
    them appropriately.
    
    [Design principles]
    Decorator pattern - separates API initialization from command logic.
    Fail-fast - immediately reports API-related errors.
    Composition - can be combined with other command decorators.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with API initialization
    """
    # Implementation...
```

```python
def catch_errors(function: CommandFunction) -> CommandFunction:
    """
    [Function intent]
    Catch and handle errors during command execution.
    
    [Implementation details]
    Creates a decorator that wraps command execution in a try-except block.
    Catches and handles common error types with appropriate messages and exit codes
    using the error handling methods in AppContext (ctx.obj).
    
    [Design principles]
    Decorator pattern - separates error handling from command logic.
    Centralized error handling - ensures consistent handling across commands.
    Composition - can be combined with other command decorators.
    
    Args:
        function: Click command function to decorate
        
    Returns:
        Decorated function with error handling
    """
    # Implementation...
```

## In-code Comments

Add helpful comments in key sections of the code to guide developers:

### Context Usage Pattern Comment

Add this comment block near the imports or at the beginning of command files:

```python
# Click Context Usage Notes:
# 
# - ctx is Click's native context object with our AppContext in ctx.obj
# - Application services are available as: ctx.obj.service_name
# - Click's context features are available directly on ctx:
#   - ctx.parent: Access the parent command's context
#   - ctx.invoke(): Invoke other commands programmatically 
#   - ctx.meta: Store command-specific data
#   - ctx.command: Access the current command object
```

### Command Function Comment

Add brief inline comments in command functions to reinforce proper usage:

```python
@cli.command()
@click.pass_context
def some_command(ctx: click.Context):
    # Access app services via ctx.obj
    app_ctx = ctx.obj  # Our AppContext with application services
    
    # Now use app services
    app_ctx.api_client.do_something()
    
    # Access Click's native context features directly
    parent_ctx = ctx.parent  # Get parent command's context
```

## Developer Documentation

### Update Migration Guide

Create or update migration guide documentation that explains:

1. Why we switched to using Click's native context
2. How to use the new context pattern in commands
3. Examples of Click context features now available

```markdown
# Click Context Usage Guide

## Context Handling Model

Our CLI now follows Click's recommended context handling pattern:

- `click.Context`: Click's native context object with command execution state
  - Passed to commands via `@click.pass_context` decorator
  - Access with parameter `ctx: click.Context` in command functions
  - Provides Click's built-in context features (parent, invoke, etc.)

- `AppContext`: Our application service container
  - Stored in `ctx.obj` of Click's context
  - Contains shared services (config, API client, etc.)
  - Accessed via `ctx.obj.service_name` in commands

## Using Context in Commands

### Basic Command Template

```python
@cli.command()
@click.pass_context
def command_name(ctx: click.Context):
    # Get our app context with services
    app_ctx = ctx.obj
    
    # Use application services
    app_ctx.api_client.do_something()
    app_ctx.output_formatter.print("Result")
    
    # Use Click context features if needed
    parent_ctx = ctx.parent
    ctx.invoke(other_command, arg=value)
```

### Context Features

- `ctx.parent`: Access parent command's context
- `ctx.command`: Access the command object
- `ctx.invoke()`: Programmatically call other commands
- `ctx.meta`: Dictionary for storing command-specific data
- `ctx.obj`: Our AppContext with application services
- `ctx.params`: Dictionary of parsed parameters
```

### Command Development Guidelines

Update guidelines for developing new commands:

```markdown
# Command Development Best Practices

## Context Access Pattern

Always follow this pattern for accessing services in commands:

1. Use Click's context decorator to receive the context object
   ```python
   @click.pass_context
   def command_name(ctx: click.Context):
       # Command implementation
   ```

2. Access application services through ctx.obj
   ```python
   app_ctx = ctx.obj  # Optional but improves readability
   result = app_ctx.api_client.get_data()
   app_ctx.output_formatter.print(result)
   ```

3. Use Click's context features directly on ctx
   ```python
   # Invoke another command
   ctx.invoke(other_command)
   
   # Access parent command context
   parent_ctx = ctx.parent
   
   # Store command-specific data
   ctx.meta['key'] = value
   ```
```

## Command Docstring Template

```python
"""
[Function intent]
Brief description of command purpose.

[Implementation details]
Receives Click's native context object with our AppContext in ctx.obj.
Accesses application services via ctx.obj.
Uses Click's context features for X, Y, Z.

[Design principles]
Command design principles here.

Args:
    ctx: Click's context object containing our AppContext in ctx.obj
    arg1: Description of argument
    
Returns:
    Command result description
"""
```

## Command Migration Checklist Document

Create a cheat sheet for developers to use when migrating commands:

```markdown
# Click Context Migration Checklist

## Command Function Updates

- [ ] Update import from `from ..common import Context, pass_context` to `import click` and `from ..common import AppContext`
- [ ] Change decorator from `@pass_context` to `@click.pass_context`
- [ ] Update type hint from `ctx: Context` to `ctx: click.Context`
- [ ] Update context usage from `ctx.service` to `ctx.obj.service`
- [ ] Add inline comment identifying AppContext: `app_ctx = ctx.obj  # Our application services`
- [ ] Update docstring to reflect the new context pattern

## Testing Updates

- [ ] Update mock creation to mock Click's context with our AppContext in obj
- [ ] Test that services are accessible via ctx.obj
- [ ] If using Click context features, add tests for those features
```

## Future-proofing Documentation

Add documentation about future expansion of Click context usage:

```markdown
# Future Click Context Feature Usage

Our migration to Click's native context unlocks additional features that may be useful in future development:

## 1. Context-Local Resources

Click's `with_resource()` method provides resource management tied to context lifecycle:

```python
@cli.command()
@click.pass_context
def command(ctx):
    # Create a resource tied to the context lifecycle
    with ctx.with_resource(open("data.txt")) as f:
        data = f.read()
    # File is automatically closed when context exits
```

## 2. Parameter Sources

Click's context provides information about where parameters came from:

```python
@cli.command()
@click.option("--debug")
@click.pass_context
def command(ctx, debug):
    # Check where the parameter came from
    param_source = ctx.get_parameter_source("debug")
    if param_source == click.core.ParameterSource.ENVIRONMENT:
        print("Debug set from environment variable")
```

## 3. Custom Command Invocation

Invoke commands with modified parameters or behavior:

```python
@cli.command()
@click.pass_context
def command(ctx):
    # Invoke another command with custom parameters
    ctx.invoke(other_command, param="custom_value")
    
    # Forward current parameters to another command
    ctx.forward(other_command)
```
```

## Documentation Update Process

1. Update docstrings in `common.py` and `main.py` first
2. Then update command files during migration
3. Create or update developer documentation
4. Add code comments to reinforce proper usage
