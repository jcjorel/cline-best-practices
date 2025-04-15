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
# - Provides sensible default values as specified in doc/CONFIGURATION.md.
# - Uses validators for custom validation logic (e.g., path expansion, enum checks).
# - Design Decision: Use Pydantic for Schema Definition (2025-04-14)
#   * Rationale: Simplifies configuration loading, validation, and access; integrates well with type hinting; reduces boilerplate code.
#   * Alternatives considered: Manual validation (error-prone), JSON Schema (less integrated with Python).
###############################################################################
# [Source file constraints]
# - Requires Pydantic library.
# - Schema must be kept consistent with doc/CONFIGURATION.md.
# - Field names should align with the hierarchical structure used in config files/env vars/CLI args.
###############################################################################
# [Reference documentation]
# - doc/CONFIGURATION.md
# - doc/DESIGN.md
# - scratchpad/dbp_implementation_plan/plan_config_management.md
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:35:40Z : Initial creation of configuration schema models by CodeAssistant
# * Defined all Pydantic models based on plan_config_management.md.
###############################################################################

from pydantic import BaseModel, Field, validator, DirectoryPath, FilePath
from typing import List, Optional, Dict, Union, Any
import os
import logging

logger = logging.getLogger(__name__)

class ServerConfig(BaseModel):
    """Server configuration settings."""
    default: str = Field(default="local", description="Default MCP server to connect to")
    port: int = Field(default=6231, ge=1024, le=65535, description="Port to use when connecting to MCP servers")
    timeout: int = Field(default=5, ge=1, le=60, description="Connection timeout in seconds")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of connection retry attempts")
    retry_interval: int = Field(default=2, ge=1, le=30, description="Seconds between retry attempts")

class OutputConfig(BaseModel):
    """Output formatting settings."""
    format: str = Field(default="formatted", description="Default output format for responses")
    color: bool = Field(default=True, description="Use colored output in terminal")
    verbosity: str = Field(default="normal", description="Level of detail in output")
    max_width: Optional[int] = Field(default=None, ge=80, le=1000, description="Maximum width for formatted output")

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
    enabled: bool = Field(default=True, description="Enable command history")
    size: int = Field(default=100, ge=10, le=1000, description="Maximum number of commands to store")
    file: str = Field(default="~/.dbp_cli_history", description="File location for persistent history")
    save_failed: bool = Field(default=True, description="Include failed commands in history")

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
    directories: List[str] = Field(default=["~/.dbp_scripts"], description="Directories to search for custom scripts")
    autoload: bool = Field(default=True, description="Automatically load scripts at startup")
    allow_remote: bool = Field(default=False, description="Allow loading scripts from remote URLs")

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
    enabled: bool = Field(default=True, description="Enable the background scheduler")
    delay_seconds: int = Field(default=10, ge=1, le=60, description="Debounce delay before processing changes")
    max_delay_seconds: int = Field(default=120, ge=30, le=600, description="Maximum delay for any file")
    worker_threads: int = Field(default=2, ge=1, le=os.cpu_count() or 1, description="Number of worker threads (max CPU cores)")
    max_queue_size: int = Field(default=1000, ge=100, le=10000, description="Maximum size of change queue")
    batch_size: int = Field(default=20, ge=1, le=100, description="Files processed in one batch")

class MonitorConfig(BaseModel):
    """File system monitoring settings."""
    enabled: bool = Field(default=True, description="Enable file system monitoring")
    ignore_patterns: List[str] = Field(default=["*.tmp", "*.log", "*.swp", "*~", ".git/", ".hg/", ".svn/", "__pycache__/"], description="Glob patterns to ignore during monitoring")
    recursive: bool = Field(default=True, description="Monitor subdirectories recursively")

class DatabaseConfig(BaseModel):
    """Database settings."""
    type: str = Field(default="sqlite", description="Database backend to use ('sqlite' or 'postgresql')")
    path: str = Field(default="~/.dbp/metadata.db", description="Path to SQLite database file (if type is sqlite)")
    connection_string: Optional[str] = Field(default=None, description="PostgreSQL connection string (if type is postgresql)")
    max_size_mb: int = Field(default=500, ge=10, le=10000, description="Approximate maximum database size in MB (informational)")
    vacuum_threshold: int = Field(default=20, ge=5, le=50, description="Fragmentation % threshold for automatic vacuum (SQLite only)")
    connection_timeout: int = Field(default=5, ge=1, le=30, description="Database connection timeout in seconds")
    max_connections: int = Field(default=4, ge=1, le=16, description="Maximum number of concurrent connections in the pool")
    use_wal_mode: bool = Field(default=True, description="Use Write-Ahead Logging mode for SQLite (recommended)")
    echo_sql: bool = Field(default=False, description="Log SQL statements executed by SQLAlchemy")

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
    auto_purge_enabled: bool = Field(default=True, description="Enable automatic purging of old non-active recommendations")
    purge_age_days: int = Field(default=7, ge=1, le=365, description="Age in days after which non-active recommendations are purged")
    purge_decisions_with_recommendations: bool = Field(default=True, description="Also purge related developer decisions when purging recommendations")
    auto_invalidate: bool = Field(default=True, description="Invalidate the active recommendation on any codebase change")

class InitializationConfig(BaseModel):
    """Initialization settings."""
    timeout_seconds: int = Field(default=180, ge=30, le=600, description="Maximum time allowed for full system initialization")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts for failed components during init")
    retry_delay_seconds: int = Field(default=5, ge=1, le=30, description="Delay between initialization retry attempts")
    verification_level: str = Field(default="normal", description="Level of verification during initialization ('minimal', 'normal', 'thorough')")
    startup_mode: str = Field(default="normal", description="System startup mode ('normal', 'maintenance', 'recovery', 'minimal')")

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
    model_id: str = Field(default="amazon.titan-text-lite-v1", description="AWS Bedrock model ID for the coordinator LLM (e.g., amazon.titan-text-lite-v1, anthropic.claude-3-sonnet-20240229-v1:0)")
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Temperature parameter for LLM generation (0.0 for deterministic)")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Maximum tokens for LLM response") # Adjusted max based on typical limits
    prompt_templates_dir: str = Field(default="doc/llm/prompts", description="Directory containing prompt templates for the coordinator")
    response_format: str = Field(default="json", description="Expected response format from coordinator LLM ('json' or 'text')")

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
    default_max_execution_time_ms: int = Field(default=30000, ge=1000, le=300000, description="Default maximum total execution time for a coordinator request in milliseconds")
    default_max_cost_budget: float = Field(default=1.0, ge=0.01, le=10.0, description="Default maximum cost budget (e.g., in USD) for a coordinator request") # Units need definition
    job_wait_timeout_seconds: int = Field(default=60, ge=10, le=300, description="Maximum time to wait for individual internal tool jobs to complete in seconds")
    max_parallel_jobs: int = Field(default=5, ge=1, le=10, description="Maximum number of internal tool jobs to run in parallel")

# --- Internal LLM Tools Configuration ---

class NovaLiteConfig(BaseModel):
    """Configuration for Amazon Nova Lite LLM instance used by internal tools."""
    model_id: str = Field(default="amazon.titan-text-lite-v1", description="AWS Bedrock model ID for Nova Lite") # Example, adjust as needed
    temperature: float = Field(default=0.0, ge=0.0, le=1.0, description="Temperature for generation")
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Maximum tokens for response")
    retry_limit: int = Field(default=3, ge=0, le=5, description="Maximum retry attempts for Bedrock API calls")
    retry_delay_seconds: int = Field(default=1, ge=0, le=10, description="Base delay between retries in seconds")

class ClaudeConfig(BaseModel):
    """Configuration for Anthropic Claude LLM instance used by internal tools."""
    model_id: str = Field(default="anthropic.claude-3-sonnet-20240229-v1:0", description="AWS Bedrock model ID for Claude") # Example, adjust as needed
    temperature: float = Field(default=0.1, ge=0.0, le=1.0, description="Temperature for generation") # Slightly higher default for Claude?
    max_tokens: int = Field(default=4096, ge=1, le=8192, description="Maximum tokens for response")
    retry_limit: int = Field(default=3, ge=0, le=5, description="Maximum retry attempts for Bedrock API calls")
    retry_delay_seconds: int = Field(default=1, ge=0, le=10, description="Base delay between retries in seconds")

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
    monitor: MonitorConfig = Field(default_factory=MonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")

# --- Consistency Analysis Configuration ---

class ConsistencyAnalysisConfig(BaseModel):
    """Configuration for the Consistency Analysis component."""
    enabled_analyzers: List[str] = Field(default=["code_doc_metadata", "cross_reference_consistency"], description="List of analyzer IDs to enable.")
    # Thresholds below are currently placeholders, actual usage depends on analyzer implementations
    high_severity_threshold: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence threshold for classifying an inconsistency as high severity.")
    medium_severity_threshold: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence threshold for classifying an inconsistency as medium severity.")
    background_check_interval_minutes: int = Field(default=60, ge=5, le=1440, description="Interval in minutes for periodic background consistency checks.")
    max_inconsistencies_per_report: int = Field(default=1000, ge=10, le=10000, description="Maximum number of inconsistencies to include in a single report.")


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    monitor: MonitorConfig = Field(default_factory=MonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    consistency_analysis: ConsistencyAnalysisConfig = Field(default_factory=ConsistencyAnalysisConfig, description="Consistency Analysis settings")

# --- Recommendation Generator Configuration ---

class RecommendationGeneratorConfig(BaseModel):
    """Configuration for the Recommendation Generator component."""
    enabled_strategies: List[str] = Field(default=["doc_link_fix", "doc_content_update", "code_comment_update"], description="List of strategy names to enable for generating recommendations.")
    llm_timeout_seconds: int = Field(default=30, ge=5, le=300, description="Timeout in seconds for LLM calls made during recommendation generation.")
    auto_apply_recommendations: bool = Field(default=False, description="If true, automatically apply generated recommendations without user confirmation (Use with caution!).")
    max_recommendations_per_batch: int = Field(default=50, ge=1, le=1000, description="Maximum number of recommendations to generate in a single batch.")
    # Add strategy-specific configs if needed, e.g., nested models


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    monitor: MonitorConfig = Field(default_factory=MonitorConfig, description="File system monitoring settings")
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
    host: str = Field(default="0.0.0.0", description="Host address for the MCP server to bind to.")
    port: int = Field(default=6231, ge=1024, le=65535, description="Port number for the MCP server.") # Default MCP port
    server_name: str = Field(default="dbp-mcp-server", description="Name of the MCP server.")
    server_description: str = Field(default="MCP Server for Documentation-Based Programming", description="Description of the MCP server.")
    server_version: str = Field(default="1.0.0", description="Version of the MCP server implementation.")
    auth_enabled: bool = Field(default=False, description="Enable API key authentication for MCP requests.") # Default to False for easier local dev?
    api_keys: List[APIKeyEntry] = Field(default_factory=list, description="List of valid API keys and their permissions.")


class AppConfig(BaseModel):
    """Root configuration model for the DBP application."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    monitor: MonitorConfig = Field(default_factory=MonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings") # Renamed from plan for consistency
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
    llm_coordinator: LLMCoordinatorConfig = Field(default_factory=LLMCoordinatorConfig, description="LLM Coordinator settings")
    internal_tools: InternalToolsConfig = Field(default_factory=InternalToolsConfig, description="Internal LLM Tools settings")
    consistency_analysis: ConsistencyAnalysisConfig = Field(default_factory=ConsistencyAnalysisConfig, description="Consistency Analysis settings")
    recommendation_generator: RecommendationGeneratorConfig = Field(default_factory=RecommendationGeneratorConfig, description="Recommendation Generator settings")
    mcp_server: MCPServerConfig = Field(default_factory=MCPServerConfig, description="MCP Server Integration settings")


    class Config:
        validate_assignment = True # Re-validate on attribute assignment
