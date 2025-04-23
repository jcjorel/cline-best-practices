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
# Centralizes all default configuration values for the DBP system.
# This file serves as the single source of truth for default configuration
# values, making it easier to maintain, update, and document system defaults.
###############################################################################
# [Source file design principles]
# - Single Responsibility: This file is responsible only for defining default config values
# - Single Source of Truth: All default config values must be defined here, not in schema models
# - Hierarchical Organization: Values organized in nested dictionaries matching config structure
# - Documentation: Each section and value includes description comments
# - Design Decision: Centralized Default Configuration Values (2025-04-16)
#   * Rationale: Improves maintainability by consolidating all defaults in one place
#   * Alternatives considered: Keeping defaults in schema models (less maintainable)
###############################################################################
# [Source file constraints]
# - Must match the structure of the AppConfig model in config_schema.py
# - Changes to default values here must be reflected in doc/CONFIGURATION.md
# - Must keep naming conventions consistent with Pydantic model field names
###############################################################################
# [Dependencies]
# codebase:- doc/CONFIGURATION.md
# codebase:- doc/DESIGN.md
###############################################################################
# [GenAI tool change history]
# 2025-04-17T15:16:00Z : Reorganized configuration structure for clarity by CodeAssistant
# * Renamed SERVER_DEFAULTS to CLI_SERVER_CONNECTION_DEFAULTS
# * Renamed OUTPUT_DEFAULTS to CLI_OUTPUT_DEFAULTS
# * Renamed HISTORY_DEFAULTS to CLI_HISTORY_DEFAULTS
# * Updated COORDINATOR_LLM_DEFAULTS to reference Nova Lite model
# * Grouped all CLI-related defaults at the end of file
# 2025-04-17T14:46:00Z : Added CLI-specific settings to defaults by CodeAssistant
# * Increased server timeout from 5 to 30 seconds for CLI compatibility
# * Added CLI specific settings for output formatting and progress display
# 2025-04-17T11:44:31Z : Updated default file paths for all components by CodeAssistant
# * Changed all file paths to use .dbp/ directory structure
# * Added server logs_dir, pid_file, and cli_config_file configurations
###############################################################################

"""
Default configuration values for the DBP system.

This module contains all default configuration values used throughout the system,
serving as the single source of truth. Configuration schema files should import
and reference these values rather than hardcoding defaults directly.
"""

import os
# Default component enablement settings - only essential components for LLM coordinator are enabled
COMPONENT_ENABLED_DEFAULTS = {
    # Essential components required for LLM coordinator functionality
    "config_manager": True,   # Required for configuration
    "file_access": True,      # Required for file access operations
    "database": True,         # Required for database operations
    "llm_coordinator": True,  # Main component we want to keep
    "mcp_server": True,       # Required for API access
    
    # Non-essential components disabled by default
    "fs_monitor": False,      # Not needed for basic LLM coordinator functioning
    "filter": False,          # Part of monitoring system
    "change_queue": False,    # Part of monitoring system
    "memory_cache": False,    # Can be disabled to reduce memory usage
    "consistency_analysis": False,    # Non-essential for LLM coordinator
    "doc_relationships": False,       # Non-essential for LLM coordinator
    "recommendation_generator": False, # Non-essential for LLM coordinator
    "scheduler": False,       # Non-essential background tasks can be disabled
    "metadata_extraction": False,     # Non-essential for basic LLM operation
}

# General application settings
GENERAL_DEFAULTS = {
    "base_dir": ".dbp"  # Base directory for all DBP files, relative to Git root
}

# Project settings - root_path will be set dynamically during initialization
PROJECT_DEFAULTS = {
    "name": "dbp_project",
    "description": "Documentation-Based Programming Project",
}

# Script settings
SCRIPT_DEFAULTS = {
    "directories": ["~/.dbp_scripts"],
    "autoload": True,
    "allow_remote": False,
}

# Background task scheduler settings
SCHEDULER_DEFAULTS = {
    "enabled": True,
    "delay_seconds": 10,
    "max_delay_seconds": 120,
    "worker_threads": 2,  # Will be capped at CPU count
    "max_queue_size": 1000,
    "batch_size": 20,
}

# File system monitoring settings
MONITOR_DEFAULTS = {
    "enabled": True,
    "ignore_patterns": ["*.tmp", "*.log", "*.swp", "*~", ".git/", ".hg/", ".svn/", "__pycache__/"],
    "recursive": True,
}

# Database settings
DATABASE_DEFAULTS = {
    "type": "sqlite",
    "path": "${general.base_dir}/database.sqlite",
    "connection_string": None,
    "max_size_mb": 500,
    "vacuum_threshold": 20,
    "connection_timeout": 5,
    "max_connections": 4,
    "use_wal_mode": True,
    "echo_sql": False,
    "alembic_ini_path": "alembic.ini",
    "verbose_migrations": True,  # When True, enables detailed logging for database migrations
}

# Recommendation settings
RECOMMENDATIONS_DEFAULTS = {
    "auto_purge_enabled": True,
    "purge_age_days": 7,
    "purge_decisions_with_recommendations": True,
    "auto_invalidate": True,
}

# Initialization settings
INITIALIZATION_DEFAULTS = {
    "timeout_seconds": 180,
    "retry_attempts": 3,
    "retry_delay_seconds": 5,
    "verification_level": "normal",
    "startup_mode": "normal",
    "watchdog_timeout": 20,  # Timeout in seconds for the initialization watchdog
}

# LLM Coordinator settings - Coordinator LLM
COORDINATOR_LLM_DEFAULTS = {
    "model_id": "amazon.titan-text-express-v1",
    "model_name": "nova-lite",
    "temperature": 0.0,
    "max_tokens": 4096,
    "prompt_templates_dir": "doc/llm/prompts",
    "response_format": "json",
}

# LLM Coordinator settings
LLM_COORDINATOR_DEFAULTS = {
    "default_max_execution_time_ms": 30000,
    "default_max_cost_budget": 1.0,
    "job_wait_timeout_seconds": 60,
    "max_parallel_jobs": 5,
}

# Internal Tools settings - Nova Lite
NOVA_LITE_DEFAULTS = {
    "model_id": "amazon.titan-text-lite-v1",
    "temperature": 0.0,
    "max_tokens": 4096,
    "retry_limit": 3,
    "retry_delay_seconds": 1,
}

# Internal Tools settings - Claude
CLAUDE_DEFAULTS = {
    "model_id": "anthropic.claude-3-sonnet-20240229-v1:0",
    "temperature": 0.1,
    "max_tokens": 4096,
    "retry_limit": 3, 
    "retry_delay_seconds": 1,
}

# Consistency Analysis settings
CONSISTENCY_ANALYSIS_DEFAULTS = {
    "enabled_analyzers": ["code_doc_metadata", "cross_reference_consistency"],
    "high_severity_threshold": 0.8,
    "medium_severity_threshold": 0.5,
    "background_check_interval_minutes": 60,
    "max_inconsistencies_per_report": 1000,
}

# Recommendation Generator settings
RECOMMENDATION_GENERATOR_DEFAULTS = {
    "enabled_strategies": ["doc_link_fix", "doc_content_update", "code_comment_update"],
    "llm_timeout_seconds": 30,
    "auto_apply_recommendations": False,
    "max_recommendations_per_batch": 50,
}

# MCP Server Integration settings
MCP_SERVER_DEFAULTS = {
    "host": "0.0.0.0",
    "port": 6231,
    "server_name": "dbp-mcp-server",
    "server_description": "MCP Server for Documentation-Based Programming",
    "server_version": "1.0.0",
    "auth_enabled": False,
    "workers": 1,
    "logs_dir": "${general.base_dir}/logs",
    "pid_file": "${general.base_dir}/mcp_server.pid",
    "cli_config_file": "${general.base_dir}/cli_config.json",
    "enable_cors": False,
    "cors_origins": ["*"],
    "cors_methods": ["*"],
    "cors_headers": ["*"],
    "cors_allow_credentials": False,
    "keep_alive": 5,
    "graceful_shutdown_timeout": 10,
}

# Metadata Extraction settings
METADATA_EXTRACTION_DEFAULTS = {
    "model_id": "amazon.titan-text-lite-v1",
    "temperature": 0.0,
    "max_tokens": 4096,
    "max_file_size_kb": 1024,
    "extraction_timeout_seconds": 30,
    "batch_size": 10,
    "max_retries": 3,
    "retry_delay": 1.0,
    "enabled": True,
}

# Memory Cache settings
MEMORY_CACHE_DEFAULTS = {
    "enabled": True,
    "max_size_mb": 512,
    "ttl_seconds": 3600,
    "cleanup_interval_seconds": 300,
    "persist_to_disk": True,
    "eviction_policy": "lru",
}

# AWS settings
AWS_DEFAULTS = {
    "region": "us-east-1",
    "endpoint_url": None,
    "credentials_profile": None,
}

# === CLI-specific settings ===

# CLI server connection settings
CLI_SERVER_CONNECTION_DEFAULTS = {
    "default": "local",
    "port": 6231,
    "timeout": 30,  # Increased from 5 to 30 seconds for compatibility with CLI
    "retry_attempts": 3,
    "retry_interval": 2,
}

# CLI output formatting settings
CLI_OUTPUT_DEFAULTS = {
    "format": "formatted",
    "color": True,
    "verbosity": "normal",
    "max_width": None,  # Will default to terminal width
}

# CLI command history settings
CLI_HISTORY_DEFAULTS = {
    "enabled": True,
    "size": 100,
    "file": "${general.base_dir}/cli_history",
    "save_failed": True,
}

# CLI general settings
CLI_DEFAULTS = {
    "output_format": "text",  # text, json, markdown, html
    "color": True,
    "progress_bar": True,
    "cache_dir": "~/.dbp/cli_cache",  # Cache dir for CLI specific data
    "api_key": "CHANGE_ME!"  # Default placeholder API key for client authentication
}
