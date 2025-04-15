# Configuration Management Implementation Plan

## Overview

This plan details the implementation of the configuration management system for the Documentation-Based Programming MCP Server. The configuration system will handle loading, validation, and access to configuration parameters across the application.

## Documentation Context

The configuration management implementation is informed by these key documentation files:
- [doc/CONFIGURATION.md](../../doc/CONFIGURATION.md) - Defines configuration parameters and structure
- [doc/DESIGN.md](../../doc/DESIGN.md) - Architectural principles affecting configuration
- [doc/SECURITY.md](../../doc/SECURITY.md) - Security considerations for configuration
- [doc/design/COMPONENT_INITIALIZATION.md](../../doc/design/COMPONENT_INITIALIZATION.md) - Initialization sequence

## Implementation Requirements

### Functional Requirements

1. Support for multiple configuration sources in priority order:
   - Command-line parameters
   - Environment variables
   - Project-specific configuration file
   - User configuration file
   - System-wide configuration file
   - Default values

2. Configuration validation against defined schemas
3. Access to configuration values from any component
4. Runtime updates to configuration parameters
5. Type conversion for configuration values
6. Project-specific configuration isolation
7. Integration with Cline's configuration system

### Non-Functional Requirements

1. Fast access to frequently used configuration values
2. Efficient loading and parsing of configuration files
3. Thread-safe access to configuration
4. Descriptive error messages for validation failures
5. Low memory footprint
6. Secure handling of sensitive configuration values

## Configuration Sources

### 1. Default Values

- Hardcoded reasonable defaults for all parameters
- Available without any external configuration
- Located in configuration definition class

### 2. Configuration Files

- Support for JSON and YAML formats
- Multiple locations in priority order:
  - System-wide: `/etc/dbp/config.{json,yaml}`
  - User-specific: `~/.config/dbp/config.{json,yaml}`
  - Project-specific: `<project_root>/.dbp/config.{json,yaml}`

### 3. Environment Variables

- Format: `DBP_UPPER_CASE_PARAMETER`
- Example: `DBP_SERVER_PORT=7000`
- Automatic conversion to appropriate types

### 4. Command-line Parameters

- Format: `--parameter.name=value`
- Example: `--server.port=7000`
- Support for nested parameters using dot notation

## Configuration Schema

The configuration schema will use Pydantic for validation and type conversion, with the following structure:

```python
# config_schema.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Union, Any
import os

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
        if v not in ["json", "yaml", "formatted"]:
            raise ValueError(f"Format must be one of: json, yaml, formatted")
        return v
    
    @validator('verbosity')
    def validate_verbosity(cls, v):
        if v not in ["minimal", "normal", "detailed"]:
            raise ValueError(f"Verbosity must be one of: minimal, normal, detailed")
        return v

class HistoryConfig(BaseModel):
    """Command history settings."""
    enabled: bool = Field(default=True, description="Enable command history")
    size: int = Field(default=100, ge=10, le=1000, description="Maximum number of commands to store")
    file: str = Field(default="~/.mcp_cli_history", description="File location for persistent history")
    save_failed: bool = Field(default=True, description="Include failed commands in history")
    
    @validator('file')
    def expand_path(cls, v):
        return os.path.expanduser(v)

class ScriptConfig(BaseModel):
    """Script settings."""
    directories: List[str] = Field(default=["~/.mcp_scripts"], description="Directories to search for custom scripts")
    autoload: bool = Field(default=True, description="Automatically load scripts at startup")
    allow_remote: bool = Field(default=False, description="Allow loading scripts from remote URLs")
    
    @validator('directories')
    def expand_paths(cls, v):
        return [os.path.expanduser(dir) for dir in v]

class SchedulerConfig(BaseModel):
    """Background task scheduler settings."""
    enabled: bool = Field(default=True, description="Enable the background scheduler")
    delay_seconds: int = Field(default=10, ge=1, le=60, description="Debounce delay before processing changes")
    max_delay_seconds: int = Field(default=120, ge=30, le=600, description="Maximum delay for any file")
    worker_threads: int = Field(default=2, ge=1, le=8, description="Number of worker threads")
    max_queue_size: int = Field(default=1000, ge=100, le=10000, description="Maximum size of change queue")
    batch_size: int = Field(default=20, ge=1, le=100, description="Files processed in one batch")

class MonitorConfig(BaseModel):
    """File system monitoring settings."""
    enabled: bool = Field(default=True, description="Enable file system monitoring")
    ignore_patterns: List[str] = Field(default=["*.tmp", "*.log"], description="Additional patterns to ignore")
    recursive: bool = Field(default=True, description="Monitor subdirectories recursively")

class DatabaseConfig(BaseModel):
    """Database settings."""
    type: str = Field(default="sqlite", description="Database backend to use")
    path: str = Field(default="~/.dbp/metadata.db", description="Path to SQLite database file")
    connection_string: Optional[str] = Field(default=None, description="PostgreSQL connection string")
    max_size_mb: int = Field(default=500, ge=10, le=10000, description="Maximum database size in megabytes")
    vacuum_threshold: int = Field(default=20, ge=5, le=50, description="Threshold for automatic vacuum")
    connection_timeout: int = Field(default=5, ge=1, le=30, description="Database connection timeout in seconds")
    max_connections: int = Field(default=4, ge=1, le=16, description="Maximum number of concurrent connections")
    use_wal_mode: bool = Field(default=True, description="Use Write-Ahead Logging mode for SQLite")
    
    @validator('path')
    def expand_path(cls, v):
        return os.path.expanduser(v)
    
    @validator('type')
    def validate_type(cls, v):
        if v not in ["sqlite", "postgresql"]:
            raise ValueError(f"Database type must be one of: sqlite, postgresql")
        return v

class RecommendationConfig(BaseModel):
    """Recommendation settings."""
    auto_purge_enabled: bool = Field(default=True, description="Enable automatic purging of old recommendations")
    purge_age_days: int = Field(default=7, ge=1, le=365, description="Age in days after which recommendations are purged")
    purge_decisions_with_recommendations: bool = Field(default=True, description="Also purge related developer decisions")
    auto_invalidate: bool = Field(default=True, description="Invalidate recommendation on codebase change")

class InitializationConfig(BaseModel):
    """Initialization settings."""
    timeout_seconds: int = Field(default=180, ge=30, le=600, description="Maximum time allowed for full initialization")
    retry_attempts: int = Field(default=3, ge=0, le=10, description="Number of retry attempts for failed components")
    retry_delay_seconds: int = Field(default=5, ge=1, le=30, description="Delay between retry attempts")
    verification_level: str = Field(default="normal", description="Level of verification during initialization")
    startup_mode: str = Field(default="normal", description="System startup mode")
    
    @validator('verification_level')
    def validate_verification_level(cls, v):
        if v not in ["minimal", "normal", "thorough"]:
            raise ValueError(f"Verification level must be one of: minimal, normal, thorough")
        return v
    
    @validator('startup_mode')
    def validate_startup_mode(cls, v):
        if v not in ["normal", "maintenance", "recovery", "minimal"]:
            raise ValueError(f"Startup mode must be one of: normal, maintenance, recovery, minimal")
        return v

class AppConfig(BaseModel):
    """Root configuration model."""
    server: ServerConfig = Field(default_factory=ServerConfig, description="Server connection settings")
    output: OutputConfig = Field(default_factory=OutputConfig, description="Output formatting settings")
    history: HistoryConfig = Field(default_factory=HistoryConfig, description="Command history settings")
    script: ScriptConfig = Field(default_factory=ScriptConfig, description="Script settings")
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig, description="Background task scheduler settings")
    monitor: MonitorConfig = Field(default_factory=MonitorConfig, description="File system monitoring settings")
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database settings")
    recommendations: RecommendationConfig = Field(default_factory=RecommendationConfig, description="Recommendation settings")
    initialization: InitializationConfig = Field(default_factory=InitializationConfig, description="Initialization settings")
```

## Configuration Manager Implementation

The Configuration Manager will be implemented as a singleton that provides access to configuration parameters:

```python
# config_manager.py
import os
import json
import yaml
import logging
import argparse
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
import threading

from pydantic import ValidationError
from .config_schema import AppConfig

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """Manager for loading, validating, and accessing configuration."""
    
    _instance = None
    _lock = threading.RLock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(ConfigurationManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        # Configuration data
        self._config = AppConfig()
        self._cli_args = {}
        self._env_vars = {}
        self._config_files = {}
        self._initialized = True
    
    def initialize(self, args=None):
        """Initialize configuration from all sources."""
        with self._lock:
            # Create default configuration
            self._config = AppConfig()
            
            # Load configuration from files
            self._load_config_files()
            
            # Load environment variables
            self._load_environment_variables()
            
            # Load command-line arguments
            self._load_command_line_args(args)
            
            # Apply configuration hierarchy
            self._apply_configuration_hierarchy()
            
            logger.info("Configuration initialized successfully")
    
    def _load_config_files(self):
        """Load configuration from files."""
        config_paths = [
            # System-wide configuration
            Path("/etc/dbp/config.json"),
            Path("/etc/dbp/config.yaml"),
            Path("/etc/dbp/config.yml"),
            
            # User configuration
            Path(os.path.expanduser("~/.config/dbp/config.json")),
            Path(os.path.expanduser("~/.config/dbp/config.yaml")),
            Path(os.path.expanduser("~/.config/dbp/config.yml")),
        ]
        
        # Load from each path if exists
        for path in config_paths:
            if path.exists() and path.is_file():
                try:
                    data = self._load_config_file(path)
                    logger.info(f"Loaded configuration from {path}")
                    self._config_files[str(path)] = data
                except Exception as e:
                    logger.warning(f"Failed to load configuration from {path}: {e}")
    
    def _load_config_file(self, path: Path) -> Dict[str, Any]:
        """Load configuration from a single file."""
        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                return yaml.safe_load(f)
            elif path.suffix.lower() == '.json':
                return json.load(f)
            else:
                raise ValueError(f"Unsupported configuration file format: {path.suffix}")
    
    def _load_environment_variables(self):
        """Load configuration from environment variables."""
        prefix = "DBP_"
        self._env_vars = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert DBP_SERVER_PORT to server.port
                config_key = key[len(prefix):].lower().replace('_', '.')
                self._env_vars[config_key] = value
    
    def _load_command_line_args(self, args=None):
        """Load configuration from command line arguments."""
        parser = argparse.ArgumentParser(description='Documentation-Based Programming MCP Server')
        parser.add_argument('--config', help='Path to configuration file')
        
        # Parse known args to extract config file path if provided
        known_args, _ = parser.parse_known_args(args)
        
        # Load additional config file if specified
        if known_args.config:
            path = Path(known_args.config)
            if path.exists() and path.is_file():
                try:
                    data = self._load_config_file(path)
                    logger.info(f"Loaded configuration from {path}")
                    self._config_files[str(path)] = data
                except Exception as e:
                    logger.warning(f"Failed to load configuration from {path}: {e}")
        
        # Parse all args as key=value pairs
        self._cli_args = {}
        if args:
            for arg in args:
                if arg.startswith('--') and '=' in arg:
                    key, value = arg[2:].split('=', 1)
                    self._cli_args[key] = value
    
    def _apply_configuration_hierarchy(self):
        """Apply configuration from all sources in priority order."""
        # Start with default configuration
        config_dict = {}
        
        # Apply configuration files in order
        for file_path, file_data in self._config_files.items():
            self._merge_dict(config_dict, file_data)
        
        # Apply environment variables
        env_dict = self._nested_dict_from_keys(self._env_vars)
        self._merge_dict(config_dict, env_dict)
        
        # Apply command-line arguments
        cli_dict = self._nested_dict_from_keys(self._cli_args)
        self._merge_dict(config_dict, cli_dict)
        
        # Create new configuration object
        try:
            self._config = AppConfig(**config_dict)
        except ValidationError as e:
            logger.error(f"Configuration validation failed: {e}")
            # Keep default configuration but log error
            self._config = AppConfig()
    
    def _nested_dict_from_keys(self, flat_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Convert flat dictionary with dot-notation keys to nested dictionary."""
        nested = {}
        for key, value in flat_dict.items():
            parts = key.split('.')
            current = nested
            for part in parts[:-1]:
                if part not in current:
                    current[part] = {}
                current = current[part]
            current[parts[-1]] = self._convert_value(value)
        return nested
    
    def _convert_value(self, value: str) -> Any:
        """Convert string value to appropriate type."""
        # Try to convert to bool if matches
        if value.lower() in ['true', 'yes', '1']:
            return True
        if value.lower() in ['false', 'no', '0']:
            return False
        
        # Try to convert to int
        try:
            return int(value)
        except ValueError:
            pass
        
        # Try to convert to float
        try:
            return float(value)
        except ValueError:
            pass
        
        # Keep as string
        return value
    
    def _merge_dict(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """Recursively merge source dictionary into target dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_dict(target[key], value)
            else:
                target[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key using dot notation."""
        try:
            parts = key.split('.')
            value = self._config
            for part in parts:
                value = getattr(value, part)
            return value
        except (AttributeError, KeyError):
            return default
    
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value by key using dot notation."""
        with self._lock:
            try:
                # Convert to dict for modification
                config_dict = self._config.dict()
                
                # Navigate to the right location
                parts = key.split('.')
                current = config_dict
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                
                # Set the value
                current[parts[-1]] = value
                
                # Revalidate configuration
                try:
                    self._config = AppConfig(**config_dict)
                    return True
                except ValidationError as e:
                    logger.error(f"Configuration validation failed while setting {key}={value}: {e}")
                    # Revert to previous configuration
                    return False
            except Exception as e:
                logger.error(f"Failed to set configuration {key}={value}: {e}")
                return False
    
    def load_project_config(self, project_root: str) -> None:
        """Load project-specific configuration."""
        with self._lock:
            project_config_paths = [
                Path(project_root) / ".dbp" / "config.json",
                Path(project_root) / ".dbp" / "config.yaml",
                Path(project_root) / ".dbp" / "config.yml",
            ]
            
            for path in project_config_paths:
                if path.exists() and path.is_file():
                    try:
                        data = self._load_config_file(path)
                        logger.info(f"Loaded project configuration from {path}")
                        
                        # Store project configuration
                        self._config_files[str(path)] = data
                        
                        # Re-apply configuration hierarchy
                        self._apply_configuration_hierarchy()
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load project configuration from {path}: {e}")
    
    def as_dict(self) -> Dict[str, Any]:
        """Return the entire configuration as a dictionary."""
        return self._config.dict()
    
    def validate(self) -> List[str]:
        """Validate the current configuration and return list of errors."""
        try:
            # Try to validate by creating a new config object
            AppConfig(**self._config.dict())
            return []
        except ValidationError as e:
            return [str(error) for error in e.errors()]
```

## Project-Specific Configuration Management

The system will handle project-specific configuration:

```python
# project_config.py
import os
import logging
from pathlib import Path

from .config_manager import ConfigurationManager

logger = logging.getLogger(__name__)

class ProjectConfigManager:
    """Manager for project-specific configuration."""
    
    def __init__(self, config_manager=None):
        """Initialize with optional configuration manager."""
        self.config_manager = config_manager or ConfigurationManager()
        self.current_project = None
    
    def set_project(self, project_root: str) -> bool:
        """Set the current project and load its configuration."""
        if not os.path.isdir(project_root):
            logger.error(f"Project root directory does not exist: {project_root}")
            return False
        
        try:
            # Load project-specific configuration
            self.config_manager.load_project_config(project_root)
            
            # Store current project
            self.current_project = project_root
            
            logger.info(f"Set current project to: {project_root}")
            return True
        except Exception as e:
            logger.error(f"Failed to set project: {e}")
            return False
    
    def get_project(self) -> str:
        """Get the current project root path."""
        return self.current_project
    
    def clear_project(self) -> None:
        """Clear the current project."""
        self.current_project = None
        
        # Reset configuration to defaults
        self.config_manager.initialize()
        logger.info("Project configuration cleared")
```

## Configuration CLI

The system will include a CLI for viewing and managing configuration:

```python
# config_cli.py
import argparse
import json
import yaml
import sys
from typing import Dict, Any, Optional

from .config_manager import ConfigurationManager

class ConfigCLI:
    """Command-line interface for configuration management."""
    
    def __init__(self, config_manager=None):
        """Initialize with optional configuration manager."""
        self.config_manager = config_manager or ConfigurationManager()
    
    def run(self, args=None):
        """Run the CLI with provided or system args."""
        parser = self._create_parser()
        parsed_args = parser.parse_args(args)
        
        if not hasattr(parsed_args, 'func'):
            parser.print_help()
            return 1
        
        return parsed_args.func(parsed_args)
    
    def _create_parser(self):
        """Create argument parser."""
        parser = argparse.ArgumentParser(description='Documentation-Based Programming Configuration CLI')
        subparsers = parser.add_subparsers(dest='command', help='Commands')
        
        # Get command
        get_parser = subparsers.add_parser('get', help='Get configuration value')
        get_parser.add_argument('key', help='Configuration key in dot notation')
        get_parser.set_defaults(func=self._handle_get)
        
        # Set command
        set_parser = subparsers.add_parser('set', help='Set configuration value')
        set_parser.add_argument('key', help='Configuration key in dot notation')
        set_parser.add_argument('value', help='Value to set')
        set_parser.set_defaults(func=self._handle_set)
        
        # List command
        list_parser = subparsers.add_parser('list', help='List configuration values')
        list_parser.add_argument('--format', choices=['json', 'yaml'], default='yaml', help='Output format')
        list_parser.add_argument('--prefix', help='Limit listing to keys with this prefix')
        list_parser.set_defaults(func=self._handle_list)
        
        # Validate command
        validate_parser = subparsers.add_parser('validate', help='Validate configuration')
        validate_parser.set_defaults(func=self._handle_validate)
        
        return parser
    
    def _handle_get(self, args):
        """Handle the get command."""
        value = self.config_manager.get(args.key)
        if value is None:
            print(f"Configuration key not found: {args.key}")
            return 1
        print(value)
        return 0
    
    def _handle_set(self, args):
        """Handle the set command."""
        success = self.config_manager.set(args.key, args.value)
        if not success:
            print(f"Failed to set configuration value: {args.key}={args.value}")
            return 1
        print(f"Configuration value set: {args.key}={args.value}")
        return 0
    
    def _handle_list(self, args):
        """Handle the list command."""
        config_dict = self.config_manager.as_dict()
        
        # Filter by prefix if provided
        if args.prefix:
            config_dict = self._filter_dict_by_prefix(config_dict, args.prefix)
        
        # Output in requested format
        if args.format == 'json':
            print(json.dumps(config_dict, indent=2))
        else:
            print(yaml.dump(config_dict, default_flow_style=False))
        
        return 0
    
    def _filter_dict_by_prefix(self, d: Dict[str, Any], prefix: str) -> Dict[str, Any]:
        """Filter dictionary by key prefix."""
        prefix_parts = prefix.split('.')
        result = {}
        
        # If prefix is empty, return the whole dict
        if not prefix:
            return d
        
        # Navigate to the dict at prefix
        current = d
        for part in prefix_parts:
            if part not in current or not isinstance(current[part], dict):
                return {}
            current = current[part]
        
        # If we're at a leaf node or the requested prefix, return its value
        if not prefix_parts:
            return current
        
        # Create result dict with the same structure
        target = result
        for part in prefix_parts[:-1]:
            target[part] = {}
            target = target[part]
        
        target[prefix_parts[-1]] = current
        return result
    
    def _handle_validate(self, args):
        """Handle the validate command."""
        errors = self.config_manager.validate()
        
        if not errors:
            print("Configuration is valid.")
            return 0
        
        print("Configuration validation errors:")
        for error in errors:
            print(f"- {error}")
        
        return 1
```

## Environment Detection and Integration

The system will detect and integrate with its environment:

```python
# environment.py
import os
import sys
import platform
import logging
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class EnvironmentDetector:
    """Detects and provides information about the runtime environment."""
    
    def __init__(self):
        """Initialize the environment detector."""
        self._env_info = self._detect_environment()
    
    def _detect_environment(self) -> Dict[str, Any]:
        """Detect environment information."""
        info = {
            'os_type': platform.system(),
            'os_version': platform.version(),
            'hostname': platform.node(),
            'python_version': platform.python_version(),
            'is_windows': os.name == 'nt',
            'is_linux': os.name == 'posix' and platform.system() != 'Darwin',
            'is_macos': platform.system() == 'Darwin',
            'is_wsl': False,
            'is_container': False,
            'home_dir': str(Path.home()),
            'temp_dir': os.path.abspath(os.getenv('TEMP', os.getenv('TMP', '/tmp'))),
            'cpu_count': os.cpu_count() or 1,
        }
        
        # Detect WSL
        if info['is_linux'] and os.path.exists('/proc/version'):
            try:
                with open('/proc/version', 'r') as f:
                    version_info = f.read().lower()
                    if 'microsoft' in version_info:
                        info['is_wsl'] = True
            except:
                pass
        
        # Detect container
        if info['is_linux']:
            # Check for container environment variables
            if any(env in os.environ for env in ['KUBERNETES_SERVICE_HOST', 'DOCKER_CONTAINER']):
                info['is_container'] = True
            # Check for .dockerenv file
            elif os.path.exists('/.dockerenv'):
                info['is_container'] = True
            # Check cgroup
            elif os.path.exists('/proc/self/cgroup'):
                try:
                    with open('/proc/self/cgroup', 'r') as f:
                        if 'docker' in f.read() or 'kubepods' in f.read():
                            info['is_container'] = True
                except:
                    pass
        
        # Detect Cline integration
        info['is_cline_integrated'] = 'CLINE_ROOT' in os.environ
        if info['is_cline_integrated']:
            info['cline_root'] = os.environ['CLINE_ROOT']
        
        logger.debug(f"Environment detected: {info}")
        return info
    
    def get_info(self) -> Dict[str, Any]:
        """Get all environment information."""
        return self._env_info.copy()
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get specific environment information."""
        return self._env_info.get(key, default)
    
    def is_windows(self) -> bool:
        """Check if running on Windows."""
        return self._env_info['is_windows']
    
    def is_linux(self) -> bool:
        """Check if running on Linux."""
        return self._env_info['is_linux']
    
    def is_macos(self) -> bool:
        """Check if running on macOS."""
        return self._env_info['is_macos']
    
    def is_wsl(self) -> bool:
        """Check if running on Windows Subsystem for Linux."""
        return self._env_info['is_wsl']
    
    def is_container(self) -> bool:
        """Check if running in a container."""
        return self._env_info['is_container']
    
    def is_cline_integrated(self) -> bool:
        """Check if integrated with Cline."""
        return self._env_info['is_cline_integrated']
    
    def get_os_specific_config_path(self) -> Path:
        """Get OS-specific configuration directory path."""
        if self.is_windows():
            # Windows: %APPDATA%\dbp
            appdata = os.environ.get('APPDATA')
            if appdata:
                return Path(appdata) / 'dbp'
            return Path.home() / 'AppData' / 'Roaming' / 'dbp'
        elif self.is_macos():
            # macOS: ~/Library/Application Support/dbp
            return Path.home() / 'Library' / 'Application Support' / 'dbp'
        else:
            # Linux/Unix: ~/.config/dbp
            xdg_config = os.environ.get('XDG_CONFIG_HOME')
            if xdg_config:
                return Path(xdg_config) / 'dbp'
            return Path.home() / '.config' / 'dbp'
    
    def get_system_temp_dir(self) -> Path:
        """Get system-specific temporary directory."""
