# Hierarchical Semantic Tree Context - Configuration Module

This directory contains the configuration management components for the Document-Based Programming (DBP) system. It provides a layered configuration system with multiple sources (defaults, files, environment variables, CLI arguments) and validation using Pydantic schemas.

## Child Directory Summaries
*No child directories with HSTC.md files.*

## Local File Headers

### Filename 'component.py':
**Intent:** Implements the ConfigManagerComponent class, which wraps the ConfigurationManager singleton in a Component-compatible interface to integrate with the component lifecycle framework. This enables the configuration manager to be available to other components via the component registry.

**Design principles:**
- Acts as an adapter between ConfigurationManager singleton and Component protocol
- Provides access to configuration via the component system
- Has no dependencies itself (should be one of the first components initialized)
- Design Decision: Component Wrapper for ConfigurationManager (2025-04-16)
  * Rationale: Allows configuration access through the standard component mechanism
  * Alternatives considered: Direct singleton access (less consistent with component model)

**Constraints:**
- Depends on ConfigurationManager being implemented as a singleton
- Must be registered early in the component initialization sequence
- Must be named "config_manager" to meet dependency declarations

**Change History:**
- 2025-04-20T10:21:00Z : Fixed initialization flag naming
- 2025-04-20T01:44:31Z : Completed dependency injection refactoring
- 2025-04-19T23:49:00Z : Added dependency injection support
- 2025-04-17T23:29:30Z : Enhanced with strongly-typed configuration access

### Filename 'config_manager.py':
**Intent:** Implements the ConfigurationManager singleton class responsible for loading, validating, merging, and providing access to the DBP system's configuration. It handles multiple configuration sources with a defined priority order.

**Design principles:**
- Singleton pattern ensures a single instance manages configuration globally.
- Thread-safe access using RLock.
- Layered configuration loading (defaults, files, env vars, CLI args).
- Uses Pydantic schema (`AppConfig`) for validation and type coercion.
- Supports JSON and YAML configuration file formats.
- Handles environment variables with a specific prefix (`DBP_`).
- Parses command-line arguments for overrides.
- Provides methods for getting/setting values and loading project-specific configs.
- Design Decision: Singleton Pattern (2025-04-14)
  * Rationale: Ensures consistent configuration access across the application without passing instances around.
  * Alternatives considered: Global variable (less controlled), Dependency injection (more complex for simple config access).
- Design Decision: Layered Configuration Loading (2025-04-14)
  * Rationale: Provides flexibility for users to override defaults at different levels (system, user, project, runtime).
  * Alternatives considered: Single config file (less flexible), Only env vars (harder for complex configs).
- Design Decision: No Default Values in get() Method (2025-04-17)
  * Rationale: Forces callers to explicitly handle missing configuration values rather than relying on implicit defaults.
  * Alternatives considered: Supporting default values in get() method (rejected to encourage explicit error handling).

**Constraints:**
- Requires `config_schema.py` for the `AppConfig` model.
- Requires `PyYAML` library for YAML file support.
- Initialization (`initialize()`) must be called before accessing configuration.
- Project-specific configuration loading requires the project root path.

**Change History:**
- 2025-04-18T09:14:00Z : Fixed template variable recursion issue in resolve_template_string
- 2025-04-18T08:33:00Z : Enhanced template variable resolution to handle nested templates
- 2025-04-18T07:39:00Z : Added automatic template variable resolution
- 2025-04-17T23:04:30Z : Simplified ConfigurationManager with Pydantic-first approach

### Filename 'config_schema.py':
**Intent:** Defines the Pydantic models that represent the configuration schema for the DBP application. These models provide type validation, documentation, and structured access to configuration values across the application.

**Design principles:**
- Uses Pydantic for strong typing and automatic validation
- Hierarchical structure with nested models that mirror configuration sections
- Self-documenting with field descriptions and examples
- Default values for all fields to ensure valid initial state
- Design Decision: Strongly-Typed Configuration (2025-04-14)
  * Rationale: Provides type safety and IDE autocompletion for configuration access
  * Alternatives considered: Dictionary-based config (less type safety but more flexible)

**Constraints:**
- Requires Pydantic library
- Must include defaults for all fields
- Must handle optional vs. required fields appropriately
- Schema changes must be backward compatible unless major version change

**Change History:**
- 2025-04-17T14:21:30Z : Added template configurations for new GenAI models
- 2025-04-17T14:20:00Z : Enhanced database configuration with connection pooling options
- 2025-04-17T12:32:00Z : Added project.root_path configuration field
- 2025-04-16T17:14:30Z : Updated MCP server configuration schema

### Filename 'default_config.py':
**Intent:** Provides default configuration values used when no explicit configuration is provided. This serves as the baseline configuration that can be overridden by configuration files, environment variables, or command-line arguments.

**Design principles:**
- Single source of truth for default configuration values
- Organized by component or functional area
- Uses the same structure as the Pydantic configuration models
- Values are chosen to work in most development environments
- Design Decision: Separate Default Configuration File (2025-04-14)
  * Rationale: Keeps defaults separate from schema, making them easier to modify
  * Alternatives considered: Hardcoded defaults in schema (less flexible)

**Constraints:**
- Must align with the structure defined in config_schema.py
- Must provide sensible defaults that work in most environments
- Values should be secure by default when security is a consideration
- Should not contain sensitive information or credentials

**Change History:**
- 2025-04-17T15:42:00Z : Added default watchdog configuration values
- 2025-04-17T14:27:00Z : Updated default LLM model settings for Claude 3.5
- 2025-04-17T12:45:00Z : Added default paths for Git-based project structure
- 2025-04-16T09:23:45Z : Added default MCP server port and authentication settings

### Filename 'project_config.py':
**Intent:** Provides utilities for loading and managing project-specific configuration, including discovery of project configuration files in the project directory structure, validation of project settings, and application of project-level overrides.

**Design principles:**
- Separation between project configuration and global/user configuration
- Project configuration takes precedence for project-specific settings
- Uses standard locations for project configuration files (.dbp directory)
- Integrates with version control (e.g., Git) for project root detection
- Design Decision: Project-Specific Configuration (2025-04-14)
  * Rationale: Allows projects to customize behavior while maintaining global defaults
  * Alternatives considered: Single configuration model (less flexible for multi-project scenarios)

**Constraints:**
- Project configuration must be validated against the same schema as global configuration
- Must handle missing or partial project configuration gracefully
- Directory structure must be consistent with project conventions
- Project configuration should not override critical system settings

**Change History:**
- 2025-04-17T16:23:00Z : Added auto-discovery of project root directory using Git
- 2025-04-17T16:14:00Z : Implemented project configuration validation
- 2025-04-17T12:38:00Z : Enhanced project configuration loading with error handling
- 2025-04-16T11:45:30Z : Initial implementation of project configuration loading

### Filename 'config_cli.py':
**Intent:** Provides command-line interface utilities for the configuration system, including argument parsing, configuration file specification, and runtime configuration overrides through command-line arguments.

**Design principles:**
- Consistent command-line syntax for configuration operations
- Integration with the main ConfigurationManager for loading/applying settings
- Clear help text and documentation for command-line options
- Support for both configuration file specification and direct setting overrides
- Design Decision: CLI Configuration Access (2025-04-15)
  * Rationale: Provides flexible configuration modification without editing files
  * Alternatives considered: Configuration only through files (less flexible)

**Constraints:**
- Must preserve type safety when parsing command-line arguments
- Should provide helpful error messages for invalid inputs
- Must integrate with the application's overall CLI structure
- Should handle conflicting settings gracefully (e.g., CLI vs. file)

**Change History:**
- 2025-04-17T14:52:00Z : Added support for configuration validation via CLI
- 2025-04-17T13:26:00Z : Enhanced error handling for invalid configuration values
- 2025-04-16T16:37:00Z : Implemented dynamic configuration display with filtering
- 2025-04-15T14:18:30Z : Initial implementation of config_cli module
