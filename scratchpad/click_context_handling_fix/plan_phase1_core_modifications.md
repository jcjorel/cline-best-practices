# Phase 1: Core Modifications to Context Handling

## Current Implementation Analysis

The current implementation in `src/dbp_cli/cli_click/common.py` defines:

1. A custom `Context` class that holds our application services (config manager, auth manager, API client, etc.)
2. A custom `pass_context` decorator created with `click.make_pass_decorator(Context, ensure=True)`
3. Command functions that receive this custom Context directly via the decorator

```python
# Current pattern
@cli.command()
@pass_context
def some_command(ctx: Context):  # ctx is our custom Context, not Click's
    ctx.api_client.do_something()  # Direct access to our Context's attributes
```

This approach prevents commands from accessing Click's native context features.

## Required Changes

### 1. Rename Custom Context Class

Rename our custom `Context` class to `AppContext` to clearly distinguish it from Click's native context.

```python
# Before
class Context:
    # ...

# After
class AppContext:
    # ...
```

Update all type annotations and references throughout the file.

### 2. Modify Main CLI Entry Point

Update the main CLI entry point in `main.py` to initialize our `AppContext` and store it in Click's context:

```python
@click.group(...)
@click.pass_context  # Use Click's context
def cli(ctx: click.Context) -> None:
    """Main command group."""
    # Initialize our AppContext and store it in Click's context
    ctx.obj = AppContext()
    # Note: Detailed initialization will happen in common_options decorator
```

### 3. Replace Custom pass_context Decorator

Remove our custom `pass_context` decorator and use Click's native `@click.pass_context` instead:

```python
# Before
pass_context = click.make_pass_decorator(Context, ensure=True)

# After
# No custom decorator, use click.pass_context directly
```

### 4. Update the common_options Decorator

Modify the `common_options` decorator to work with Click's context:

```python
def common_options(function: F) -> F:
    # Option decorators remain the same
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        # Extract options as before
        
        # Initialize app context if needed
        if not hasattr(ctx, 'obj') or ctx.obj is None:
            ctx.obj = AppContext()
            
        # Initialize services if not already initialized
        if not ctx.obj.config_manager:
            ctx.obj.init_services(
                # Parameters as before
            )
            
            # Configure logging based on verbosity
            ctx.obj.configure_logging()
        
        # Call the original function
        return function(ctx, *args, **kwargs)
    
    return cast(F, wrapper)
```

### 5. Update the api_command Decorator

```python
def api_command(function: CommandFunction) -> CommandFunction:
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        # Initialize the API client if not already initialized
        if ctx.obj.api_client and not ctx.obj.api_client._initialized:
            try:
                ctx.obj.api_client.init_api_client()
            except ConfigurationError as e:
                ctx.obj.output_formatter.error(f"Configuration error: {e}")
                return 2
                
        # Call the original function
        return function(ctx, *args, **kwargs)
    
    return cast(CommandFunction, wrapper)
```

### 6. Update the catch_errors Decorator

```python
def catch_errors(function: CommandFunction) -> CommandFunction:
    @functools.wraps(function)
    def wrapper(ctx: click.Context, *args: Any, **kwargs: Any) -> Any:
        try:
            return function(ctx, *args, **kwargs)
        except Exception as e:
            return ctx.obj.handle_error(e)
    
    return cast(CommandFunction, wrapper)
```

## Implementation Steps

1. **Create a backup** of `common.py` and `main.py` before making changes

2. **Update `common.py`**:
   - Rename `Context` class to `AppContext`
   - Update all references to the class within the file
   - Remove the custom `pass_context` decorator
   - Update the `common_options`, `api_command`, and `catch_errors` decorators
   - Update type hints and docstrings

3. **Update `main.py`**:
   - Change import from `from .common import Context, pass_context` to `from .common import AppContext`
   - Import `click.pass_context` directly
   - Update the CLI entry point to initialize `AppContext` as `ctx.obj`
   - Update the version command to use `click.pass_context`

4. **Add helpful code comments** explaining the context pattern:
   ```python
   # IMPORTANT: ctx is Click's native context object
   # Our application services are accessible via ctx.obj (AppContext)
   ```

## Validation

After implementing these changes, use the validation methods defined in Phase 3 to:

1. Verify that commands receive Click's native context object
2. Confirm that application services are correctly accessible via `ctx.obj`
3. Test that Click's context features (like parent, command invocation) work correctly

## Potential Challenges

1. **Inconsistent typing**: Ensure all type annotations are updated consistently
2. **Nested command inheritance**: Ensure context is correctly passed through multiple command levels
3. **Backward compatibility**: If any direct usage of our previous Context exists in application code

## Example Command Migration

Before:
```python
@cli.command()
@pass_context
def some_command(ctx: Context):
    ctx.api_client.do_something()
```

After:
```python
@cli.command()
@click.pass_context
def some_command(ctx: click.Context):
    ctx.obj.api_client.do_something()  # Access via ctx.obj
    
    # Can also use Click's context features
    parent_context = ctx.parent  # Get parent command's context
    ctx.invoke(other_command)  # Invoke another command
