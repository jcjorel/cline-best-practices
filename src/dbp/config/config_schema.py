###############################################################################
# IMPORTANT: This header comment is designed for GenAI code review and maintenance
# Any GenAI tool working with this file MUST preserve and update this header
###############################################################################
# [GenAI coding tool directive]
# - Maintain this header with all modifications
# - Update History section with each change
# - Keep only the 4 most recent records in the history section. Sort from older to newer.
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
###############################################################################
# [Source file constraints]
# - Requires Pydantic library.
# - Schema must be kept consistent with doc/CONFIGURATION.md.
# - Field names should align with the hierarchical structure used in config files/env vars/CLI args.
# - Default values should always come from default_config.py, not hardcoded here.
###############################################################################
# [Reference documentation]
# - doc/CONFIGURATION.md
# - doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-17T16:46:00Z : Renamed MonitorConfig to FSMonitorConfig for component name consistency by CodeAssistant
# * Renamed MonitorConfig class to FSMonitorConfig to match fs_monitor component name
# * Updated AppConfig to use fs_monitor field instead of monitor
# * Fixed "Configuration key 'fs_monitor' not found" error during server startup
# * Aligned configuration schema with component naming conventions
# 2025-04-17T16:17:00Z : Added database.alembic_ini_path configuration field by CodeAssistant
# * Added missing alembic_ini_path field to DatabaseConfig class
# * Fixed "Configuration key 'database.alembic_ini_path' not found" error
# * Enabled successful execution of database migrations during server startup
# 2025-04-17T16:04:00Z : Added GeneralConfig class and fixed missing configuration by CodeAssistant
# * Added new GeneralConfig class to expose general.base_dir configuration setting
# * Added general field to main AppConfig class to make it accessible
# * Fixed "Configuration key 'general.base_dir' not found" errors during server startup
# * Fixed database and MCP server component access to configuration values
# 2025-04-17T15:29:00Z : Updated imports and references to match renamed config keys by CodeAssistant
# * Changed imports to use CLI_SERVER_CONNECTION_DEFAULTS instead of SERVER_DEFAULTS
# * Changed imports to use CLI_OUTPUT_DEFAULTS instead of OUTPUT_DEFAULTS
# * Changed imports to use CLI_HISTORY_DEFAULTS instead of HISTORY_DEFAULTS
# * Updated all model field references to use the new config key names
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
    SCHEDULER_DEFAULTS,
    MONITOR_DEFAULTS,
    DATABASE_DEFAULTS,
    RECOMMENDATIONS_DEFAULTS,
    INITIALIZATION_DEFAULTS,
    COORDINATOR_LLM_DEFAULTS,
    LLM_COORDINATOR_DEFAULTS,
    NOVA_LITE_DEFAULTS,
    CLAUDE_DEFAULTS,
    CONSISTENCY_ANALYSIS_DEFAULTS,
    RECOMMENDATION_GENERATOR_DEFAULTS,
    MCP_SERVER_DEFAULTS,
    CLI_DEFAULTS,
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
    root_path: str = Field(default="", description="Git root path for the project")

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
            logger.warning(f"Invalid output format '{v}'. Defaulting to 'formatted'. Allowed: {allowed}")
            return "formatted"
            # raise ValueError(f"Format must be one of: {allowed}")
        return v

    @validator('verbosity')
    def validate_verbosity(cls, v):
        allowed = ["minimal", "normal", "detailed"]
        if v not in allowed:
            logger.warning(f"Invalid verbosity level '{v}'. Defaulting to 'normal'. Allowed: {allowed}")
            return "normal"
            # raise ValueError(f"Verbosity must be one of: {allowed}")
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
            # Fallback to a default path if expansion fails
            return os.path.expanduser("~/.dbp_cli_history_fallback")


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
                    # Optionally skip invalid paths or use a default
            return expanded_paths
        # Handle case where default is passed directly
        elif isinstance(v, str):
             try:
                 return [os.path.expanduser(v)]
             except Exception as e:
                 logger.error(f"Could not expand script directory path '{v}': {e}")
                 return []
        return []


class SchedulerConfig(BaseModel):
    """Background task scheduler settings."""
    enabled: bool = Field(default=SCHEDULER_DEFAULTS["enabled"], description="Enable the background scheduler")
    delay_seconds: int = Field(default=SCHEDULER_DEFAULTS["delay_seconds"], ge=1, le=60, description="Debounce delay before processing changes")
    max_delay_seconds: int = Field(default=SCHEDULER_DEFAULTS["max_delay_seconds"], ge=30, le=600, description="Maximum delay for any file")
    worker_threads: int = Field(default=SCHEDULER_DEFAULTS["worker_threads"], ge=1, le=os.cpu_count() or 1, description="Number of worker threads (max CPU cores)")
    max_queue_size: int = Field(default=SCHEDULER_DEFAULTS["max_queue_size"], ge=100, le=10000, description="Maximum size of change queue")
    batch_size: int = Field(default=SCHEDULER_DEFAULTS["batch_size"], ge=1, le=100, description="Files processed in one batch")

class FSMonitorConfig(BaseModel):
    """File system monitoring settings."""
    enabled: bool = Field(default=MONITOR_DEFAULTS["enabled"], description="Enable file system monitoring")
    ignore_patterns: List[str] = Field(default=MONITOR_DEFAULTS["ignore_patterns"], description="Glob patterns to ignore during monitoring")
    recursive: bool = Field(default=MONITOR_DEFAULTS["recursive"], description="Monitor subdirectories recursively")

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

    @validator('path', pre=True, always=True)
    def expand_path(cls, v):
        try:
            return os.path.expanduser(v)
        except Exception as e:
            logger.error(f"Could not expand database path '{v}': {e}")
            return os.path.expanduser("~/.dbp/metadata_fallback.db")

    @validator('type')
    def validate_type(cls, v):
        allowed = ["sqlite", "postgresql"]
        if v not in allowed:
            logger.warning(f"Invalid database type '{v}'. Defaulting to 'sqlite'. Allowed: {allowed}")
            return "sqlite"
            # raise ValueError(f"Database type must be one of: {allowed}")
        return v

class RecommendationConfig(BaseModel):
    """Recommendation settings."""
    auto_purge_enabled: bool = Field(default=RECOMMENDATIONS_DEFAULTS["auto_purge_enabled"], description="Enable automatic purging of old non-active recommendations")
    purge_age_days: int = Field(default=RECOMMENDATIONS_DEFAULTS["purge_age_days"], ge=1, le=365, description="Age in days after which non-active recommendations are purged")
    purge_decisions_with_recommendations: bool = Field(default=RECOMMENDATIONS_DEFAULTS["purge_decisions_with_recommendations"], description="Also purge related developer decisions when purging recommendations")
    auto_invalidate: bool = Field(default=RECOMMENDATIONS_DEFAULTS["auto_invalidate"], description="Invalidate the active recommendation on any codebase change")

class InitializationConfig(BaseModel):
    """Initialization settings."""
    timeout_seconds: int = Field(default=INITIALIZATION_DEFAULTS["timeout_seconds"], ge=30, le=600, description="Maximum time allowed for full system initialization")
    retry_attempts: int = Field(default=INITIALIZATION_DEFAULTS["retry_attempts"], ge=0, le=10, description="Number of retry attempts for failed components during init")
    retry_delay_seconds: int = Field(default=INITIALIZATION_DEFAULTS["retry_delay_seconds"], ge=1, le=30, description="Delay between initialization retry attempts")
    verification_level: str = Field(default=INITIALIZATION_DEFAULTS["verification_level"], description="Level of verification during initialization ('minimal', 'normal', 'thorough')")
    startup_mode: str = Field(default=INITIALIZATION_DEFAULTS["startup_mode"], description="System startup mode ('normal', 'maintenance', 'recovery', 'minimal')")

    @validator('verification_level')
    def validate_verification_level(cls, v):
        allowed = ["minimal", "normal", "thorough"]
        if v not in allowed:
            logger.warning(f"Invalid verification level '{v}'. Defaulting to 'normal'. Allowed: {allowed}")
            return "normal"
            # raise ValueError(f"Verification level must be one of: {allowed}")
        return v

    @validator('startup_mode')
    def validate_startup_mode(cls, v):
        allowed = ["normal", "maintenance", "recovery", "minimal"]
        if v not in allowed:
            logger.warning(f"Invalid startup mode '{v}'. Defaulting to 'normal'. Allowed: {allowed}")
            return "normal"
            # raise ValueError(f"Startup mode must be one of: {allowed}")
        return v

# --- LLM Coordinator Configuration ---

class CoordinatorLLMConfig(BaseModel):
    """Configuration specific to the Coordinator LLM instance."""
    model_id: str = Field(default=COORDINATOR_LLM_DEFAULTS["model_id"], description="AWS Bedrock model ID for the coordinator LLM (e.g., amazon.titan-text-lite-v1, anthropic.claude-3-sonnet-20240229-v1:0)")
    temperature: float = Field(default=COORDINATOR_LLM_DEFAULTS["temperature"], ge=0.0, le=1.0, description="Temperature parameter for LLM generation (0.0 for deterministic)")
    max_tokens: int = Field(default=COORDINATOR_LLM_DEFAULTS["max_tokens"], ge=1, le=8192, description="Maximum tokens for LLM response") # Adjusted max based on typical limits
    prompt_templates_dir: str = Field(default=COORDINATOR_LLM_DEFAULTS["prompt_templates_dir"], description="Directory containing prompt templates for the coordinator")
    response_format: str = Field(default=COORDINATOR_LLM_DEFAULTS["response_format"], description="Expected response format from coordinator LLM ('json' or 'text')")

    @validator('response_format')
    def validate_response_format(cls, v):
        allowed = ["json", "text"]
        if v not in allowed:
            logger.warning(f"Invalid coordinator LLM response format '{v}'. Defaulting to 'json'. Allowed: {allowed}")
            return "json"
        return v

    @validator('prompt_templates_dir', pre=True, always=True)
    def expand_prompt_dir(cls, v):
        try:
            # Assume relative to project root or CWD if not absolute
            # This might need adjustment based on where config is loaded
            return os.path.abspath(os.path.expanduser(v))
        except Exception as e:
            logger.error(f"Could not expand prompt template directory path '{v}': {e}")
            # Fallback to a default relative path
            return "doc/llm/prompts"


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
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")

# --- Consistency Analysis Configuration ---

class ConsistencyAnalysisConfig(BaseModel):
    """Configuration for the Consistency Analysis component."""
    enabled_analyzers: List[str] = Field(default=CONSISTENCY_ANALYSIS_DEFAULTS["enabled_analyzers"], description="List of analyzer IDs to enable.")
    # Thresholds below are currently placeholders, actual usage depends on analyzer implementations
    high_severity_threshold: float = Field(default=CONSISTENCY_ANALYSIS_DEFAULTS["high_severity_threshold"], ge=0.0, le=1.0, description="Confidence threshold for classifying an inconsistency as high severity.")
    medium_severity_threshold: float = Field(default=CONSISTENCY_ANALYSIS_DEFAULTS["medium_severity_threshold"], ge=0.0, le=1.0, description="Confidence threshold for classifying an inconsistency as medium severity.")
    background_check_interval_minutes: int = Field(default=CONSISTENCY_ANALYSIS_DEFAULTS["background_check_interval_minutes"], ge=5, le=1440, description="Interval in minutes for periodic background consistency checks.")
    max_inconsistencies_per_report: int = Field(default=CONSISTENCY_ANALYSIS_DEFAULTS["max_inconsistencies_per_report"], ge=10, le=10000, description="Maximum number of inconsistencies to include in a single report.")


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    consistency_analysis: ConsistencyAnalysisConfig = Field(default_factory=ConsistencyAnalysisConfig, description="Consistency Analysis settings")

# --- Recommendation Generator Configuration ---

class RecommendationGeneratorConfig(BaseModel):
    """Configuration for the Recommendation Generator component."""
    enabled_strategies: List[str] = Field(default=RECOMMENDATION_GENERATOR_DEFAULTS["enabled_strategies"], description="List of strategy names to enable for generating recommendations.")
    llm_timeout_seconds: int = Field(default=RECOMMENDATION_GENERATOR_DEFAULTS["llm_timeout_seconds"], ge=5, le=300, description="Timeout in seconds for LLM calls made during recommendation generation.")
    auto_apply_recommendations: bool = Field(default=RECOMMENDATION_GENERATOR_DEFAULTS["auto_apply_recommendations"], description="If true, automatically apply generated recommendations without user confirmation (Use with caution!).")
    max_recommendations_per_batch: int = Field(default=RECOMMENDATION_GENERATOR_DEFAULTS["max_recommendations_per_batch"], ge=1, le=1000, description="Maximum number of recommendations to generate in a single batch.")
    # Add strategy-specific configs if needed, e.g., nested models


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings") # Renamed from plan for consistency
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    consistency_analysis: ConsistencyAnalysisConfig = Field(default_factory=ConsistencyAnalysisConfig, description="Consistency Analysis settings")
    recommendation_generator: RecommendationGeneratorConfig = Field(default_factory=RecommendationGeneratorConfig, description="Recommendation Generator settings")

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
            logger.warning(f"Invalid output format '{v}'. Defaulting to 'text'. Allowed: {allowed}")
            return "text"
        return v

    @validator('cache_dir', pre=True, always=True)
    def expand_cache_dir(cls, v):
        try:
            return os.path.expanduser(v)
        except Exception as e:
            logger.error(f"Could not expand cache directory path '{v}': {e}")
            return os.path.expanduser("~/.dbp/cli_cache_fallback")

class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    general: GeneralConfig = Field(default_factory=GeneralConfig, description="General application settings")
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    project: ProjectConfig = Field(default_factory=ProjectConfig, description="Project settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    fs_monitor: FSMonitorConfig = Field(default_factory=FSMonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings") # Renamed from plan for consistency
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    consistency_analysis: ConsistencyAnalysisConfig = Field(default_factory=ConsistencyAnalysisConfig, description="Consistency Analysis settings")
    recommendation_generator: RecommendationGeneratorConfig = Field(default_factory=RecommendationGeneratorConfig, description="Recommendation Generator settings")
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig, description="MCP Server Integration settings")
    cli: CLIConfig = Field(default_factory=CLIConfig, description="CLI-specific settings")


    class Config:
        validate_assignment = True # Re-validate on attribute assignment
