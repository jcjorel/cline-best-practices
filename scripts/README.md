# Diagnostic Scripts

This directory contains scripts for diagnosing issues with the component system and server.

## Available Scripts

### debug_server.sh

Runs the server with DEBUG log level to provide detailed information about component registration, dependency validation, and initialization.

Usage:
```bash
./debug_server.sh
```

### analyze_logs.sh

Analyzes the MCP server logs to identify common component issues:
- Component registration status
- Component dependency validation problems
- Initialization order
- Initialization failures
- Exception details

Usage:
```bash
./analyze_logs.sh
```

### check_component_dependencies.sh

Statically analyzes the component Python code to detect:
- All defined components
- Component name definitions
- Component dependency declarations
- Potential circular dependencies
- Dependency mismatches (dependence on non-existent components)

Usage:
```bash
./check_component_dependencies.sh
```

## Workflow for Diagnosing Component Issues

1. Run the server with debug logging:
   ```bash
   ./debug_server.sh
   ```

2. Analyze the logs for issues:
   ```bash
   ./analyze_logs.sh
   ```

3. Check for component dependency problems in the code:
   ```bash
   ./check_component_dependencies.sh
   ```

4. Fix identified issues in the component classes or their registration.

## Common Issues and Solutions

1. **Missing Component Registration**: Make sure the component is properly registered in the lifecycle.py file.

2. **Incorrect Component Name**: Ensure the component's `name` property returns the correct string that other components use in their dependencies.

3. **Circular Dependencies**: Restructure dependencies to avoid circular references between components.

4. **Missing Import**: Ensure the component class is properly imported in the registration file.

5. **Initialization Failures**: Check the component's `initialize` method for errors handling the config parameter.
