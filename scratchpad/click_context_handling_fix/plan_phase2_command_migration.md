# Phase 2: Command Migration Strategy

After implementing the core context handling changes in Phase 1, we need a systematic approach for migrating existing commands to the new context pattern. This document outlines the strategy and provides templates for consistent implementation.

## Command Usage Analysis

### Current Command Pattern

Commands currently follow this pattern:

```python
@cli.command()
@pass_context  # Our custom decorator that passes our Context object
def some_command(ctx: Context, arg1, arg2):
    # ctx is our custom Context object with direct access to services
    ctx.api_client.do_something()
    ctx.output_formatter.print("Result")
```

### Target Command Pattern

After migration, commands should follow this pattern:

```python
@cli.command()
@click.pass_context  # Click's native decorator
def some_command(ctx: click.Context, arg1, arg2):
    # ctx is Click's native Context object
    # Our application services are accessed via ctx.obj
    ctx.obj.api_client.do_something()
    ctx.obj.output_formatter.print("Result")
    
    # Can now use Click's context features
    parent_cmd = ctx.parent
    ctx.invoke(other_command, some_arg=value)
```

## Migration Approach

### 1. Identify Command Categories

Categorize commands based on their complexity and usage patterns:

a. **Simple Commands**: Basic commands that only use the context for service access
b. **Complex Commands**: Commands that manage subcommands or have complex workflows
c. **Reusable Functions**: Utility functions that are used by multiple commands

### 2. Prioritize Migration Order

1. First migrate core utility functions used by many commands
2. Then migrate simple commands with minimal dependencies
3. Finally migrate complex command groups and their subcommands

### 3. Migration Steps for Each Command

For each command file:

1. Import changes:
   ```python
   # Before
   from ..common import Context, pass_context
   
   # After
   import click
   from ..common import AppContext  # Our renamed context class
   ```

2. Update command signatures:
   ```python
   # Before
   @pass_context
   def command_func(ctx: Context, ...):
   
   # After
   @click.pass_context
   def command_func(ctx: click.Context, ...):
   ```

3. Update context usage within command functions:
   ```python
   # Before
   ctx.api_client.do_something()
   
   # After
   ctx.obj.api_client.do_something()
   ```

4. Add type annotations for clarity:
   ```python
   @click.pass_context
   def command_func(ctx: click.Context, ...):
       app_ctx: AppContext = ctx.obj  # Optional type annotation for clarity
       app_ctx.api_client.do_something()
   ```

5. Update docstrings to reflect the new context pattern:
   ```python
   """
   [Function intent]
   ...
   
   [Implementation details]
   Receives Click's context object with our AppContext stored in ctx.obj.
   ...
   """
   ```

## Command Template Examples

### Simple Command Template

```python
@cli.command()
@click.argument("name")
@click.option("--option", help="Some option")
@click.pass_context
def simple_command(ctx: click.Context, name: str, option: Optional[str] = None) -> None:
    """
    [Function intent]
    Brief description of command purpose.
    
    [Implementation details]
    Accesses application services via ctx.obj.
    
    [Design principles]
    Command design principles.
    """
    # Access app services via ctx.obj
    app_ctx = ctx.obj
    
    # Use app services
    result = app_ctx.api_client.get_something(name)
    
    # Output results
    app_ctx.output_formatter.print(result)
```

### Command Group Template

```python
@click.group()
@click.pass_context
def group_command(ctx: click.Context) -> None:
    """
    [Function intent]
    Brief description of command group purpose.
    
    [Implementation details]
    Manages group-level state and context for subcommands.
    
    [Design principles]
    Command group design principles.
    """
    # Group-level initialization if needed
    # Note: ctx.obj is already initialized in main cli group
    pass

@group_command.command()
@click.argument("arg")
@click.pass_context
def subcommand(ctx: click.Context, arg: str) -> None:
    """Subcommand implementation."""
    # Access app services via ctx.obj
    app_ctx = ctx.obj
    
    # Access parent context if needed
    parent_ctx = ctx.parent
    
    # Invoke other commands if needed
    ctx.invoke(other_command, arg=value)
    
    # Use app services
    app_ctx.api_client.do_something(arg)
```

## Special Cases

### 1. Commands with Custom State

Some commands may need to store custom state between subcommands.
Use Click's context objects for this purpose:

```python
@click.group()
@click.pass_context
def group_with_state(ctx: click.Context) -> None:
    # Access app services via ctx.obj (AppContext)
    # Store command-specific state in ctx.meta
    ctx.meta['custom_state'] = {'key': 'value'}

@group_with_state.command()
@click.pass_context
def subcommand(ctx: click.Context) -> None:
    # Access the state from the parent command
    custom_state = ctx.parent.meta.get('custom_state')
    # Access app services
    ctx.obj.api_client.do_something(custom_state['key'])
```

### 2. Commands with Callbacks

For commands with callback functions:

```python
def callback_function(ctx: click.Context, param, value):
    if value:
        # Access app services via ctx.obj
        app_ctx = ctx.obj
        app_ctx.api_client.do_something()
    return value

@cli.command()
@click.option('--option', callback=callback_function)
@click.pass_context
def command_with_callback(ctx: click.Context, option):
    # Implementation
    pass
```

### 3. Commands with Dynamic Invocation

```python
@cli.command()
@click.argument("command_name")
@click.pass_context
def dynamic_command(ctx: click.Context, command_name: str) -> None:
    # Dynamically invoke another command by name
    if command_name in ctx.parent.command.commands:
        cmd = ctx.parent.command.commands[command_name]
        ctx.invoke(cmd)
    else:
        ctx.obj.output_formatter.error(f"Unknown command: {command_name}")
```

## Migration Testing

After each command migration:

1. Run unit tests specifically for that command
2. Test command functionality manually to verify behavior
3. Check that service access via ctx.obj works correctly
4. Verify that any Click context features used work as expected

## Command Migration Checklist

For each command:

- [ ] Update imports to use `click.pass_context` instead of custom `pass_context`
- [ ] Change command function signature to accept `click.Context`
- [ ] Update context access from `ctx.service` to `ctx.obj.service`
- [ ] Update any nested function calls that expected the old Context
- [ ] Update type annotations and docstrings
- [ ] Add type hints for `app_ctx` when extracted from `ctx.obj` for clarity
- [ ] Test the command to verify it works with the new context pattern
- [ ] Document any Click context features newly used in the command
