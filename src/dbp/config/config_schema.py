###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from newer to older.
# - Preserve Intent, Design, and Constraints sections
# - Use this header as context for code reviews and modifications
# - Ensure all changes align with the design principles
# - Respect system prompt directives at all times
###############################################################################
# [Source file intent]
# Defines the Pydantic models for the DBP system's configuration schema.
# This ensures type safety, validation, and provides default values for all
# configuration parameters used throughout the application.
###############################################################################
# [Source file design principles]
# - Uses Pydantic for robust data validation and settings management.
# - Defines nested models for logical grouping of configuration parameters.
# - Includes clear descriptions and validation rules (e.g., ranges, choices) for each field.
# - References centralized default values from default_config.py.
# - Uses validators for custom validation logic (e.g., path expansion, enum checks).
# - Design Decision: Use Pydantic for Schema Definition (2025-04-14)
#   * Rationale: Simplifies configuration loading, validation, and access; integrates well with type hinting; reduces boilerplate code.
#   * Alternatives considered: Manual validation (error-prone), JSON Schema (less integrated with Python).
# - Design Decision: Centralized Default Values (2025-04-16)
#   * Rationale: Separates default values from schema definition for better maintainability.
#   * Alternatives considered: Keep defaults in schema (less maintainable, harder to synchronize with documentation).
# - Design Decision: No Hardcoded Default Values in Field Default Parameter (2025-04-25)
#   * Rationale: All default values in Field(default=...) must be defined in default_config.py to maintain a single source of truth.
#   * Note: This applies specifically to the 'default' parameter in Field() and not to 'default_factory' parameter.
#   * Alternatives considered: Inline defaults (creates maintenance issues, inconsistencies between code and documentation).
###############################################################################
# [Source file constraints]
# - Requires Pydantic library.
# - Schema must be kept consistent with doc/CONFIGURATION.md.
# - Field names should align with the hierarchical structure used in config files/env vars/CLI args.
# - Default values should always come from default_config.py, not hardcoded here.
###############################################################################
# [Dependencies]
# codebase:doc/CONFIGURATION.md
# codebase:doc/DESIGN.md
# system:pydantic
# system:os
# system:logging
###############################################################################
# [GenAI tool change history]
# 2025-05-02T01:21:15Z : Removed scheduler component from ComponentEnabledConfig by CodeAssistant
# * Removed scheduler field from ComponentEnabledConfig class
# * Kept SchedulerConfig and scheduler field in AppConfig for configuration documentation
# 2025-05-02T01:12:00Z : Removed metadata_extraction references by CodeAssistant
# * Removed MetadataExtractionConfig class
# * Removed metadata_extraction field from main AppConfig class
# * Updated imports to remove METADATA_EXTRACTION_DEFAULTS
# 2025-05-02T00:39:23Z : Removed consistency_analysis references by CodeAssistant
# * Removed consistency_analysis field from ComponentEnabledConfig class
# * Removed ConsistencyAnalysisConfig class
# 2025-04-25T14:36:00Z : Added missing COMPONENT_ENABLED_DEFAULTS import by CodeAssistant
# * Added COMPONENT_ENABLED_DEFAULTS to the imports from default_config.py
# * Fixed NameError in ComponentEnabledConfig class
###############################################################################

from pydantic import BaseModel, Field, validator, DirectoryPath, FilePath
from typing import List, Optional, Dict, Union, Any
import os
import logging

# Import centralized default values
from .default_config import (
    GENERAL_DEFAULTS,
    PROJECT_DEFAULTS,
    CLI_SERVER_CONNECTION_DEFAULTS,
    CLI_OUTPUT_DEFAULTS,
    CLI_HISTORY_DEFAULTS,
    SCRIPT_DEFAULTS,
    MONITOR_DEFAULTS,
    DATABASE_DEFAULTS,
    INITIALIZATION_DEFAULTS,
    COORDINATOR_LLM_DEFAULTS,
    LLM_COORDINATOR_DEFAULTS,
    NOVA_LITE_DEFAULTS,
    CLAUDE_DEFAULTS,
    MCP_SERVER_DEFAULTS,
    CLI_DEFAULTS,
    AWS_DEFAULTS,
    BEDROCK_DEFAULTS,
    COMPONENT_ENABLED_DEFAULTS,
    FILE_ACCESS_DEFAULTS,
)

logger = logging.getLogger(__name__)

# General application settings
class GeneralConfig(BaseModel):
    """General application settings."""
    base_dir: str = Field(default=GENERAL_DEFAULTS["base_dir"], description="Base directory for all DBP files, relative to Git root")

class ServerConfig(BaseModel):
    """Server configuration settings."""
    default: str = Field(default=CLI_SERVER_CONNECTION_DEFAULTS["default"], description="Default MCP server to connect to")
    port: int = Field(default=CLI_SERVER_CONNECTION_DEFAULTS["port"], ge=1024, le=65535, description="Port to use when connecting to MCP servers")
    timeout: int = Field(default=CLI_SERVER_CONNECTION_DEFAULTS["timeout"], ge=1, le=60, description="Connection timeout in seconds")
    retry_attempts: int = Field(default=CLI_SERVER_CONNECTION_DEFAULTS["retry_attempts"], ge=0, le=10, description="Number of connection retry attempts")
    retry_interval: int = Field(default=CLI_SERVER_CONNECTION_DEFAULTS["retry_interval"], ge=1, le=30, description="Seconds between retry attempts")

class ProjectConfig(BaseModel):
    """Project settings."""
    name: str = Field(default=PROJECT_DEFAULTS["name"], description="Project name")
    description: str = Field(default=PROJECT_DEFAULTS["description"], description="Project description")
    root_path: str = Field(default=PROJECT_DEFAULTS["root_path"], description="Git root path for the project")

class OutputConfig(BaseModel):
    """Output formatting settings."""
    format: str = Field(default=CLI_OUTPUT_DEFAULTS["format"], description="Default output format for responses")
    color: bool = Field(default=CLI_OUTPUT_DEFAULTS["color"], description="Use colored output in terminal")
    verbosity: str = Field(default=CLI_OUTPUT_DEFAULTS["verbosity"], description="Level of detail in output")
    max_width: Optional[int] = Field(default=CLI_OUTPUT_DEFAULTS["max_width"], ge=80, le=1000, description="Maximum width for formatted output")

    @validator('format')
    def validate_format(cls, v):
        allowed = ["json", "yaml", "formatted"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Format must be one of: {allowed}")
        return v

    @validator('verbosity')
    def validate_verbosity(cls, v):
        allowed = ["minimal", "normal", "detailed"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Verbosity must be one of: {allowed}")
        return v

class HistoryConfig(BaseModel):
    """Command history settings."""
    enabled: bool = Field(default=CLI_HISTORY_DEFAULTS["enabled"], description="Enable command history")
    size: int = Field(default=CLI_HISTORY_DEFAULTS["size"], ge=10, le=1000, description="Maximum number of commands to store")
    file: str = Field(default=CLI_HISTORY_DEFAULTS["file"], description="File location for persistent history")
    save_failed: bool = Field(default=CLI_HISTORY_DEFAULTS["save_failed"], description="Include failed commands in history")

    @validator('file', pre=True, always=True) # Use pre=True to modify before validation
    def expand_path(cls, v):
        try:
            return os.path.expanduser(v)
        except Exception as e:
            logger.error(f"Could not expand history file path '{v}': {e}")
            # Raise exception instead of providing fallback
            raise ValueError(f"Invalid history file path: {v}")


class ScriptConfig(BaseModel):
    """Script settings."""
    directories: List[str] = Field(default=SCRIPT_DEFAULTS["directories"], description="Directories to search for custom scripts")
    autoload: bool = Field(default=SCRIPT_DEFAULTS["autoload"], description="Automatically load scripts at startup")
    allow_remote: bool = Field(default=SCRIPT_DEFAULTS["allow_remote"], description="Allow loading scripts from remote URLs")

    @validator('directories', pre=True, always=True)
    def expand_paths(cls, v):
        expanded_paths = []
        if isinstance(v, list):
            for dir_path in v:
                try:
                    expanded_paths.append(os.path.expanduser(str(dir_path)))
                except Exception as e:
                    logger.error(f"Could not expand script directory path '{dir_path}': {e}")
                    raise ValueError(f"Invalid script directory path: {dir_path}")
            return expanded_paths
        # Handle case where default is passed directly
        elif isinstance(v, str):
             try:
                 return [os.path.expanduser(v)]
             except Exception as e:
                 logger.error(f"Could not expand script directory path '{v}': {e}")
                 raise ValueError(f"Invalid script directory path: {v}")
        # If neither list nor string, raise error
        raise ValueError("Script directories must be a list of paths or a single path string")



class PollingFallbackConfig(BaseModel):
    """Configuration for the polling fallback monitor."""
    enabled: bool = Field(default=MONITOR_DEFAULTS["polling_fallback"]["enabled"], description="Enable polling fallback when native APIs are unavailable")
    poll_interval: float = Field(default=MONITOR_DEFAULTS["polling_fallback"]["poll_interval"], ge=0.1, le=60.0, description="Polling interval in seconds")
    hash_size: int = Field(default=MONITOR_DEFAULTS["polling_fallback"]["hash_size"], ge=0, le=1048576, description="Number of bytes to hash for file change detection")

class FSMonitorConfig(BaseModel):
    """File system monitoring settings."""
    enabled: bool = Field(default=MONITOR_DEFAULTS["enabled"], description="Enable file system monitoring")
    ignore_patterns: List[str] = Field(default=MONITOR_DEFAULTS["ignore_patterns"], description="Glob patterns to ignore during monitoring")
    recursive: bool = Field(default=MONITOR_DEFAULTS["recursive"], description="Monitor subdirectories recursively")
    thread_count: int = Field(default=MONITOR_DEFAULTS["thread_count"], ge=1, le=16, description="Number of worker threads for event dispatching")
    thread_priority: str = Field(default=MONITOR_DEFAULTS["thread_priority"], description="Priority for worker threads")
    default_debounce_ms: int = Field(default=MONITOR_DEFAULTS["default_debounce_ms"], ge=0, le=10000, description="Default debounce delay in milliseconds")
    polling_fallback: PollingFallbackConfig = Field(default_factory=PollingFallbackConfig, description="Polling fallback configuration")
    
    @validator('thread_priority')
    def validate_thread_priority(cls, v):
        allowed = ["low", "normal", "high"]
        if v not in allowed:
            raise ValueError(f"Thread priority must be one of: {allowed}")
        return v

class DatabaseConfig(BaseModel):
    """Database settings."""
    type: str = Field(default=DATABASE_DEFAULTS["type"], description="Database backend to use ('sqlite' or 'postgresql')")
    path: str = Field(default=DATABASE_DEFAULTS["path"], description="Path to SQLite database file (if type is sqlite)")
    connection_string: Optional[str] = Field(default=DATABASE_DEFAULTS["connection_string"], description="PostgreSQL connection string (if type is postgresql)")
    max_size_mb: int = Field(default=DATABASE_DEFAULTS["max_size_mb"], ge=10, le=10000, description="Approximate maximum database size in MB (informational)")
    vacuum_threshold: int = Field(default=DATABASE_DEFAULTS["vacuum_threshold"], ge=5, le=50, description="Fragmentation % threshold for automatic vacuum (SQLite only)")
    connection_timeout: int = Field(default=DATABASE_DEFAULTS["connection_timeout"], ge=1, le=30, description="Database connection timeout in seconds")
    max_connections: int = Field(default=DATABASE_DEFAULTS["max_connections"], ge=1, le=16, description="Maximum number of concurrent connections in the pool")
    use_wal_mode: bool = Field(default=DATABASE_DEFAULTS["use_wal_mode"], description="Use Write-Ahead Logging mode for SQLite (recommended)")
    echo_sql: bool = Field(default=DATABASE_DEFAULTS["echo_sql"], description="Log SQL statements executed by SQLAlchemy")
    alembic_ini_path: str = Field(default=DATABASE_DEFAULTS["alembic_ini_path"], description="Path to the Alembic configuration file for database migrations")
    verbose_migrations: bool = Field(default=DATABASE_DEFAULTS["verbose_migrations"], description="Enable detailed logging during database migrations")

    @validator('path', pre=True, always=True)
    def expand_path(cls, v):
        try:
            return os.path.expanduser(v)
        except Exception as e:
            logger.error(f"Could not expand database path '{v}': {e}")
            # Raise exception instead of providing fallback
            raise ValueError(f"Invalid database path: {v}")

    @validator('type')
    def validate_type(cls, v):
        allowed = ["sqlite", "postgresql"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Database type must be one of: {allowed}")
        return v


class InitializationConfig(BaseModel):
    """Initialization settings."""
    timeout_seconds: int = Field(default=INITIALIZATION_DEFAULTS["timeout_seconds"], ge=30, le=600, description="Maximum time allowed for full system initialization")
    retry_attempts: int = Field(default=INITIALIZATION_DEFAULTS["retry_attempts"], ge=0, le=10, description="Number of retry attempts for failed components during init")
    retry_delay_seconds: int = Field(default=INITIALIZATION_DEFAULTS["retry_delay_seconds"], ge=1, le=30, description="Delay between initialization retry attempts")
    verification_level: str = Field(default=INITIALIZATION_DEFAULTS["verification_level"], description="Level of verification during initialization ('minimal', 'normal', 'thorough')")
    startup_mode: str = Field(default=INITIALIZATION_DEFAULTS["startup_mode"], description="System startup mode ('normal', 'maintenance', 'recovery', 'minimal')")
    watchdog_timeout: int = Field(default=INITIALIZATION_DEFAULTS["watchdog_timeout"], ge=5, le=300, description="Timeout in seconds for the initialization watchdog")

    @validator('verification_level')
    def validate_verification_level(cls, v):
        allowed = ["minimal", "normal", "thorough"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Verification level must be one of: {allowed}")
        return v

    @validator('startup_mode')
    def validate_startup_mode(cls, v):
        allowed = ["normal", "maintenance", "recovery", "minimal"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Startup mode must be one of: {allowed}")
        return v

# --- LLM Coordinator Configuration ---

class BedrockConfig(BaseModel):
    """AWS Bedrock client configuration."""
    region: Optional[str] = Field(default=BEDROCK_DEFAULTS["region"], description="AWS region for Bedrock API calls")

class CoordinatorLLMConfig(BaseModel):
    """Configuration specific to the Coordinator LLM instance."""
    model_id: str = Field(default=COORDINATOR_LLM_DEFAULTS["model_id"], description="AWS Bedrock model ID for the coordinator LLM (e.g., amazon.titan-text-lite-v1, anthropic.claude-3-sonnet-20240229-v1:0)")
    model_name: str = Field(default=COORDINATOR_LLM_DEFAULTS["model_name"], description="Friendly name for the model (e.g., nova-lite)")
    temperature: float = Field(default=COORDINATOR_LLM_DEFAULTS["temperature"], ge=0.0, le=1.0, description="Temperature parameter for LLM generation (0.0 for deterministic)")
    max_tokens: int = Field(default=COORDINATOR_LLM_DEFAULTS["max_tokens"], ge=1, le=8192, description="Maximum tokens for LLM response") # Adjusted max based on typical limits
    prompt_templates_dir: str = Field(default=COORDINATOR_LLM_DEFAULTS["prompt_templates_dir"], description="Directory containing prompt templates for the coordinator")
    response_format: str = Field(default=COORDINATOR_LLM_DEFAULTS["response_format"], description="Expected response format from coordinator LLM ('json' or 'text')")
    bedrock: BedrockConfig = Field(default_factory=BedrockConfig, description="AWS Bedrock configuration")

    @validator('response_format')
    def validate_response_format(cls, v):
        allowed = ["json", "text"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Response format must be one of: {allowed}")
        return v

    @validator('prompt_templates_dir', pre=True, always=True)
    def expand_prompt_dir(cls, v):
        try:
            # Assume relative to project root or CWD if not absolute
            # This might need adjustment based on where config is loaded
            return os.path.abspath(os.path.expanduser(v))
        except Exception as e:
            logger.error(f"Could not expand prompt template directory path '{v}': {e}")
            # Raise exception instead of providing fallback
            raise ValueError(f"Invalid prompt template directory path: {v}")


class LLMCoordinatorConfig(BaseModel):
    """Configuration for the overall LLM Coordinator component."""
    coordinator_llm: CoordinatorLLMConfig = Field(default_factory=CoordinatorLLMConfig, description="Configuration for the main coordinator LLM")
    default_max_execution_time_ms: int = Field(default=LLM_COORDINATOR_DEFAULTS["default_max_execution_time_ms"], ge=1000, le=300000, description="Default maximum total execution time for a coordinator request in milliseconds")
    default_max_cost_budget: float = Field(default=LLM_COORDINATOR_DEFAULTS["default_max_cost_budget"], ge=0.01, le=10.0, description="Default maximum cost budget (e.g., in USD) for a coordinator request") # Units need definition
    job_wait_timeout_seconds: int = Field(default=LLM_COORDINATOR_DEFAULTS["job_wait_timeout_seconds"], ge=10, le=300, description="Maximum time to wait for individual internal tool jobs to complete in seconds")
    max_parallel_jobs: int = Field(default=LLM_COORDINATOR_DEFAULTS["max_parallel_jobs"], ge=1, le=10, description="Maximum number of internal tool jobs to run in parallel")

# --- Internal LLM Tools Configuration ---

class NovaLiteConfig(BaseModel):
    """Configuration for Amazon Nova Lite LLM instance used by internal tools."""
    model_id: str = Field(default=NOVA_LITE_DEFAULTS["model_id"], description="AWS Bedrock model ID for Nova Lite")
    temperature: float = Field(default=NOVA_LITE_DEFAULTS["temperature"], ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: int = Field(default=NOVA_LITE_DEFAULTS["max_tokens"], ge=1, le=8192, description="Maximum tokens for response")
    retry_limit: int = Field(default=NOVA_LITE_DEFAULTS["retry_limit"], ge=0, le=5, description="Maximum retry attempts for Bedrock API calls")
    retry_delay_seconds: int = Field(default=NOVA_LITE_DEFAULTS["retry_delay_seconds"], ge=0, le=10, description="Base delay between retries in seconds")

class ClaudeConfig(BaseModel):
    """Configuration for Anthropic Claude LLM instance used by internal tools."""
    model_id: str = Field(default=CLAUDE_DEFAULTS["model_id"], description="AWS Bedrock model ID for Claude")
    temperature: float = Field(default=CLAUDE_DEFAULTS["temperature"], ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: int = Field(default=CLAUDE_DEFAULTS["max_tokens"], ge=1, le=8192, description="Maximum tokens for response")
    retry_limit: int = Field(default=CLAUDE_DEFAULTS["retry_limit"], ge=0, le=5, description="Maximum retry attempts for Bedrock API calls")
    retry_delay_seconds: int = Field(default=CLAUDE_DEFAULTS["retry_delay_seconds"], ge=0, le=10, description="Base delay between retries in seconds")

class InternalToolsConfig(BaseModel):
    """Configuration for the Internal LLM Tools component."""
    nova_lite: NovaLiteConfig = Field(default_factory=NovaLiteConfig, description="Configuration for the Nova Lite instance")
    claude: ClaudeConfig = Field(default_factory=ClaudeConfig, description="Configuration for the Claude instance")
    # Note: prompt_templates_dir is already defined in CoordinatorLLMConfig, reuse that? Or define separately?
    # Let's assume it uses the same directory for now. If needed, add:
    # prompt_templates_dir: str = Field(default="doc/llm/prompts", description="Directory containing prompt templates for internal tools")


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")



# --- AWS Configuration ---

class AWSConfig(BaseModel):
    """Configuration for AWS services."""
    region: Optional[str] = Field(default=AWS_DEFAULTS["region"], description="AWS region for API calls")
    endpoint_url: Optional[str] = Field(default=AWS_DEFAULTS["endpoint_url"], description="Optional custom endpoint URL for AWS services")
    credentials_profile: Optional[str] = Field(default=AWS_DEFAULTS["credentials_profile"], description="AWS credentials profile name")

# --- File Access Configuration ---

class FileAccessConfig(BaseModel):
    """Configuration for the File Access component."""
    cache_size: int = Field(default=FILE_ACCESS_DEFAULTS["cache_size"], ge=10, le=10000, description="Maximum number of DBPFile instances to cache")

# --- Memory Cache Configuration ---


# --- MCP Server Integration Configuration ---

class APIKeyEntry(BaseModel):
    """Represents a single API key configuration."""
    key: str = Field(..., description="The API key string.")
    client_id: str = Field(..., description="An identifier for the client using this key.")
    permissions: List[str] = Field(default_factory=list, description="List of permissions granted (e.g., 'tool:analyze', 'resource:documentation:*').")

class MCPServerConfig(BaseModel):
    """Configuration for the MCP Server Integration component."""
    host: str = Field(default=MCP_SERVER_DEFAULTS["host"], description="Host address for the MCP server to bind to.")
    port: int = Field(default=MCP_SERVER_DEFAULTS["port"], ge=1024, le=65535, description="Port number for the MCP server.") # Default MCP port
    server_name: str = Field(default=MCP_SERVER_DEFAULTS["server_name"], description="Name of the MCP server.")
    server_description: str = Field(default=MCP_SERVER_DEFAULTS["server_description"], description="Description of the MCP server.")
    server_version: str = Field(default=MCP_SERVER_DEFAULTS["server_version"], description="Version of the MCP server implementation.")
    auth_enabled: bool = Field(default=MCP_SERVER_DEFAULTS["auth_enabled"], description="Enable API key authentication for MCP requests.") # Default to False for easier local dev?
    api_keys: List[APIKeyEntry] = Field(default_factory=list, description="List of valid API keys and their permissions.")
    
    # FastAPI/Uvicorn specific settings
    workers: int = Field(default=MCP_SERVER_DEFAULTS["workers"], ge=1, le=8, description="Number of Uvicorn worker processes")
    logs_dir: str = Field(default=MCP_SERVER_DEFAULTS["logs_dir"], description="Directory for server log files")
    pid_file: str = Field(default=MCP_SERVER_DEFAULTS["pid_file"], description="File to store the server process ID")
    cli_config_file: str = Field(default=MCP_SERVER_DEFAULTS["cli_config_file"], description="Path to CLI configuration file")
    enable_cors: bool = Field(default=MCP_SERVER_DEFAULTS["enable_cors"], description="Enable CORS middleware")
    cors_origins: List[str] = Field(default=MCP_SERVER_DEFAULTS["cors_origins"], description="Allowed origins for CORS")
    cors_methods: List[str] = Field(default=MCP_SERVER_DEFAULTS["cors_methods"], description="Allowed HTTP methods for CORS")
    cors_headers: List[str] = Field(default=MCP_SERVER_DEFAULTS["cors_headers"], description="Allowed HTTP headers for CORS")
    cors_allow_credentials: bool = Field(default=MCP_SERVER_DEFAULTS["cors_allow_credentials"], description="Allow credentials for CORS requests")
    keep_alive: int = Field(default=MCP_SERVER_DEFAULTS["keep_alive"], ge=1, le=30, description="Keep-alive timeout in seconds")
    graceful_shutdown_timeout: int = Field(default=MCP_SERVER_DEFAULTS["graceful_shutdown_timeout"], ge=1, le=60, description="Graceful shutdown timeout in seconds")
    
    # Capability negotiation settings
    require_negotiation: bool = Field(default=MCP_SERVER_DEFAULTS["require_negotiation"], description="Whether to require capability negotiation for all requests")
    session_timeout_seconds: int = Field(default=MCP_SERVER_DEFAULTS["session_timeout_seconds"], ge=300, le=86400, description="Session timeout in seconds")


# CLI specific settings
class CLIConfig(BaseModel):
    """CLI-specific configuration settings."""
    output_format: str = Field(default=CLI_DEFAULTS["output_format"], description="Output format for CLI responses (text, json, markdown, html)")
    color: bool = Field(default=CLI_DEFAULTS["color"], description="Use colored output in terminal")
    progress_bar: bool = Field(default=CLI_DEFAULTS["progress_bar"], description="Show progress bars for long-running operations")
    cache_dir: str = Field(default=CLI_DEFAULTS["cache_dir"], description="Directory for CLI-specific cache data")
    api_key: str = Field(default=CLI_DEFAULTS["api_key"], description="API key for client authentication with MCP server")

    @validator('output_format')
    def validate_output_format(cls, v):
        allowed = ["text", "json", "markdown", "html"]
        if v not in allowed:
            # Remove fallback and raise exception instead
            raise ValueError(f"Output format must be one of: {allowed}")
        return v

    @validator('cache_dir', pre=True, always=True)
    def expand_cache_dir(cls, v):
        try:
            return os.path.expanduser(v)
        except Exception as e:
            logger.error(f"Could not expand cache directory path '{v}': {e}")
            # Raise exception instead of providing fallback
            raise ValueError(f"Invalid cache directory path: {v}")

class ComponentEnabledConfig(BaseModel):
    """Configuration for enabling/disabling individual components."""
    config_manager: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["config_manager"], description="Enable configuration manager component")
    file_access: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["file_access"], description="Enable file access component")
    database: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["database"], description="Enable database component")
    fs_monitor: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["fs_monitor"], description="Enable file system monitor component")
    llm_coordinator: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["llm_coordinator"], description="Enable LLM coordinator component (required for MCP server LLM functions)")
    mcp_server: bool = Field(default=COMPONENT_ENABLED_DEFAULTS["mcp_server"], description="Enable MCP server component")

class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    general: GeneralConfig = Field(default_factory=GeneralConfig, description="General application settings")
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    project: ProjectConfig = Field(default_factory=ProjectConfig, description="Project settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    file_access: FileAccessConfig = Field(default_factory=FileAccessConfig, description="File Access settings")
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig, description="MCP Server Integration settings")
    cli: CLIConfig = Field(default_factory=CLIConfig, description="CLI-specific settings")
    aws: AWSConfig = Field(default_factory=AWSConfig, description="AWS service configuration settings")
    component_enabled: ComponentEnabledConfig = Field(default_factory=ComponentEnabledConfig, description="Component enablement settings")


    class Config:
        validate_assignment = True # Re-validate on attribute assignment
