# Documentation-Based Programming Coding Guidelines

This document outlines the programming approaches and constraints specific to the Documentation-Based Programming project, including variable naming conventions, problem-solving patterns, and coding standards.

## Core Principles

### 1. Documentation as Source of Truth

- Documentation always takes precedence over code for understanding project intent
- Code must align with documentation, not the other way around
- Documentation-code consistency is enforced through automated verification

### 2. "Throw on Error" Error Handling Strategy

- Implement "throw on error" behavior for ALL error conditions without exception
- Never silently catch errors - always include both error logging and error re-throwing
- Do not return null, undefined, or empty objects as a response to error conditions
- Construct descriptive error messages that specify: 1) the exact component that failed and 2) the precise reason for the failure
- Never implement fallback mechanisms or graceful degradation behavior without explicit user approval

### 3. Centralized Exception Definition

- All exceptions are defined in a single centralized exceptions.py module to prevent circular imports
- Exception hierarchy must follow clear inheritance patterns
- Component-specific exceptions should inherit from appropriate base exception classes

## Coding Standards

### File Organization

- Maximum file size: 600 lines
- Break down larger files into multiple smaller files with clear cross-references
- Group related functionality into logical modules
- Each file should have a single, clear responsibility

### Naming Conventions

#### Python

- **Classes**: PascalCase (e.g., `ComponentSystem`, `DatabaseManager`)
- **Functions/Methods**: snake_case (e.g., `initialize_component`, `get_metadata`)
- **Variables**: snake_case (e.g., `file_path`, `user_count`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_RETRY_COUNT`, `DEFAULT_TIMEOUT`)
- **Private Members**: Prefix with underscore (e.g., `_private_method`, `_internal_state`)

#### JavaScript/TypeScript

- **Classes**: PascalCase (e.g., `EventEmitter`, `RequestHandler`)
- **Functions/Methods**: camelCase (e.g., `calculateTotal`, `fetchUserData`)
- **Variables**: camelCase (e.g., `userId`, `fileCount`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `API_ENDPOINT`, `MAX_CONNECTIONS`)
- **Private Members**: Prefix with underscore (e.g., `_privateMethod`, `_internalState`)

### Documentation Standards

#### File Headers

- All files must include the standard header template from `coding_assistant/GENAI_HEADER_TEMPLATE.txt`
- Headers must include sections for intent, design principles, constraints, and reference documentation
- Headers must be kept up-to-date with all changes

#### Function and Method Documentation

- All functions and methods must include documentation following the template in `coding_assistant/GENAI_FUNCTION_TEMPLATE.txt`
- Documentation must include the three required sections:
  1. Function/Class method/Class intent
  2. Design principles
  3. Implementation details
- Parameter and return type documentation must be accurate and complete

### Code Style

#### Python

- Follow PEP 8 style guide
- Use type hints for all function parameters and return values
- Line length: 100 characters maximum
- Indentation: 4 spaces (no tabs)
- Use fstrings for string formatting
- Import order: standard library, third-party, local application imports

#### JavaScript/TypeScript

- Follow StandardJS style for JavaScript and TSLint recommendations for TypeScript
- Use strict equality comparisons (`===` and `!==`)
- Line length: 100 characters maximum
- Indentation: 2 spaces (no tabs)
- Use template literals for string formatting
- Use semicolons at the end of statements

### Testing Guidelines

- Unit tests must be written for all non-trivial functions and methods
- Tests should be organized to match the structure of the code they're testing
- Test files should be named `test_[module_name].py` for Python and `[module_name].test.js` for JavaScript
- Mock all external dependencies in unit tests
- All code paths, including error handling, must be tested

## Component Development

### Component Structure

- All components must implement the `Component` interface
- Component lifecycle (initialization and shutdown) must be handled properly
- Components must explicitly declare their dependencies
- No hidden dependencies are allowed

### Component Dependency Management

- Components must not access other components directly without declaring them as dependencies
- Dependencies must be injected during component initialization
- Dependency access must use the `get_dependency` method
- Circular dependencies are not allowed

## Specific Programming Patterns

### Configuration Management

- Configuration must be accessed using direct attribute access on Pydantic models (no dictionary-style access)
- Default values must be defined in `src/dbp/config/default_config.py`
- Configuration validation must happen at startup
- Configuration schema must be defined using Pydantic models

### Database Operations

- All database operations must be made thread-safe through proper connection management
- Schema changes must be managed through Alembic migrations
- SQLite must use Write-Ahead Logging (WAL) mode
- All SQL queries must be aligned to SQLite capabilities for cross-database compatibility

### Logging

- All components must use the logger provided during initialization
- Log messages must follow the standardized format:
  ```
  YYYY-MM-DD HH:MM:SS,mmm - logger.name - LOGLEVEL - message
  ```
- Log levels must be used appropriately:
  - DEBUG: Detailed information for debugging
  - INFO: Confirmation that things are working as expected
  - WARNING: An indication of something unexpected
  - ERROR: A failure in an operation
  - CRITICAL: A failure that requires immediate attention

### Path Resolution

- All relative paths must be resolved relative to the Git project root
- Home directory expansion must be handled properly
- Absolute paths must be used unchanged
- Path resolution must fail explicitly when the Git root cannot be found

### Code Complexity Guidelines

- Maximum cyclomatic complexity per function: 10
- Maximum function length: 50 lines
- Maximum class length: 300 lines
- Maximum nesting depth: 3 levels
- Maximum arguments per function: 5

## Code Reviews

Code reviews should focus on:
- Documentation completeness and accuracy
- Error handling correctness
- Component dependency declarations
- Adherence to the file organization and naming conventions
- Test coverage
- Performance considerations
- Security implications

## Version Control Practices

- Commit messages should follow the Conventional Commits format
- PRs should be focused on a single change or related set of changes
- PRs should include appropriate documentation updates
- Code should be well-tested before submitting a PR

## Tools and Automation

The project uses these tools to enforce coding standards:
- **Python**: flake8, mypy, black
- **JavaScript/TypeScript**: ESLint, Prettier
- **Documentation**: Documentation-Based Programming system's own consistency checker
