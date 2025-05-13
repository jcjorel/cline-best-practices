# Virtual Environment Activation Requirement

## Core Rule
When the `venv/` directory exists in the project root, the coding assistant **MUST** activate the virtual environment before executing any shell commands.

## Implementation Details
- **CRITICAL**: Before executing ANY shell command, check for the existence of a `venv/` directory in the project root.
- If `venv/` exists, ALWAYS prepend the command with `source venv/bin/activate && `.
- This rule takes precedence over all other command execution guidelines.
- The activation must be included in the same command execution (using `&&`) to ensure the virtual environment remains active for the intended command.

## Example Command Transformation
```
# Original command intention
pip install requests

# Transformed command with virtual environment activation
source venv/bin/activate && pip install requests
```

## Reasoning
- Ensures all Python packages are installed within the isolated virtual environment
- Prevents system-wide Python environment contamination
- Maintains consistent package versions across project execution contexts
- Respects project-specific dependency management

## Verification Procedure
1. Before executing `execute_command`, verify existence of `venv/` directory
2. If detected, modify the command appropriately
3. NEVER skip this verification step under any circumstances

## Special Cases
- For batch commands, ensure the virtual environment activation is included in the first command of the chain
- Even for non-Python related commands, the virtual environment should still be activated if it exists, as it may set environment variables needed by other project tooling
