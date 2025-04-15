# Python CLI Client Implementation Plan

## Overview

This document outlines the implementation plan for the Python CLI Client, which provides a command-line interface for users to interact with the Documentation-Based Programming system. The CLI client communicates with the MCP server to execute operations and present results to users in a clean, intuitive interface.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - User Interface section
- [API.md](../../doc/API.md) - API specifications for client integration
- [CONFIGURATION.md](../../doc/CONFIGURATION.md) - Configuration parameters

## Requirements

The Python CLI Client must:
1. Provide a user-friendly command-line interface for the Documentation-Based Programming system
2. Connect to the MCP server and handle authentication
3. Support all core operations (consistency analysis, recommendations, relationship tracking)
4. Display results in a clean, formatted manner (text, tables, diagrams)
5. Support both interactive and non-interactive usage modes
6. Allow configuration via command-line parameters and config files
7. Provide detailed help documentation
8. Support OS-appropriate output coloring and formatting
9. Handle errors gracefully and provide clear error messages
10. Support batch operations and scripting integration

## Design

### CLI Client Architecture

The Python CLI Client follows a layered architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│  Command Line       │─────▶│  Command            │─────▶│  MCP Client         │
│    Parser           │      │    Handler          │      │    API              │
│                     │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
                                       │                            │
                                       │                            ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Authentication     │
                               ┌─────────────────────┐    │    Manager          │
                               │                     │    │                     │
                               │  Output             │    └─────────────────────┘
                               │    Formatter        │               │
                               │                     │               │
                               └─────────────────────┘               ▼
                                       │                  ┌─────────────────────┐
                                       │                  │                     │
                                       ▼                  │  Configuration      │
                               ┌─────────────────────┐    │    Manager          │
                               │                     │    │                     │
                               │  Progress           │    └─────────────────────┘
                               │    Indicator        │
                               │                     │
                               └─────────────────────┘
```

### Core Classes and Interfaces

1. **CLI Main Application**

```python
class DocumentationProgrammingCLI:
    """Main CLI application class."""
    
    def __init__(self):
        # Set up components
        self.config_manager = ConfigurationManager()
        self.auth_manager = AuthenticationManager(self.config_manager)
        self.mcp_client = MCPClientAPI(self.auth_manager)
        self.output_formatter = OutputFormatter()
        self.progress_indicator = ProgressIndicator()
        
        # Set up command handlers
        self.command_handlers = {
            "analyze": AnalyzeCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "recommend": RecommendCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "apply": ApplyCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "relationships": RelationshipsCommandHandler(self.mcp_client, self.output_formatter, self.progress_indicator),
            "config": ConfigCommandHandler(self.config_manager, self.output_formatter),
            "status": StatusCommandHandler(self.mcp_client, self.output_formatter),
        }
        
        # Create parser
        self.parser = self._create_parser()
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create command line argument parser."""
        parser = argparse.ArgumentParser(
            description="Documentation-Based Programming CLI",
            formatter_class=argparse.RawDescriptionHelpFormatter
        )
        
        # Global options
        parser.add_argument(
            "--config", 
            metavar="FILE", 
            help="Path to configuration file"
        )
        parser.add_argument(
            "--server", 
            metavar="URL", 
            help="MCP server URL"
        )
        parser.add_argument(
            "--api-key", 
            metavar="KEY", 
            help="API key for authentication"
        )
        parser.add_argument(
            "--verbose", 
            "-v", 
            action="count", 
            default=0,
            help="Increase verbosity level"
        )
        parser.add_argument(
            "--quiet", 
            "-q", 
            action="store_true",
            help="Suppress all non-error output"
        )
        parser.add_argument(
            "--output", 
            "-o", 
            choices=["text", "json", "markdown", "html"],
            default="text",
            help="Output format"
        )
        
        # Create subparsers for commands
        subparsers = parser.add_subparsers(dest="command", help="Command to execute")
        
        # Add command-specific parsers
        self._add_analyze_parser(subparsers)
        self._add_recommend_parser(subparsers)
        self._add_apply_parser(subparsers)
        self._add_relationships_parser(subparsers)
        self._add_config_parser(subparsers)
        self._add_status_parser(subparsers)
        
        return parser
    
    def _add_analyze_parser(self, subparsers) -> None:
        """Add parser for analyze command."""
        analyze_parser = subparsers.add_parser(
            "analyze", 
            help="Analyze consistency between documentation and code"
        )
        
        # Add arguments for code and documentation files
        analyze_parser.add_argument(
            "code_file", 
            nargs="?", 
            help="Path to code file"
        )
        analyze_parser.add_argument(
            "doc_file", 
            nargs="?", 
            help="Path to documentation file"
        )
        
        # Add options for specifying directories
        analyze_parser.add_argument(
            "--code-dir", 
            help="Directory containing code files"
        )
        analyze_parser.add_argument(
            "--doc-dir", 
            help="Directory containing documentation files"
        )
        
        # Add options for filtering
        analyze_parser.add_argument(
            "--severity", 
            choices=["high", "medium", "low", "all"],
            default="all",
            help="Filter by severity"
        )
        analyze_parser.add_argument(
            "--type", 
            help="Filter by inconsistency type"
        )
        
        # Add options for output formatting
        analyze_parser.add_argument(
            "--summary-only", 
            action="store_true", 
            help="Show only summary, not individual inconsistencies"
        )
        analyze_parser.add_argument(
            "--sort-by", 
            choices=["severity", "file", "type"],
            default="severity",
            help="Sort results by"
        )
    
    def _add_recommend_parser(self, subparsers) -> None:
        """Add parser for recommend command."""
        recommend_parser = subparsers.add_parser(
            "recommend", 
            help="Generate recommendations for fixing inconsistencies"
        )
        
        # Add arguments
        recommend_parser.add_argument(
            "--inconsistency-id", 
            help="Inconsistency ID to get recommendations for"
        )
        recommend_parser.add_argument(
            "--file", 
            help="File path to get recommendations for"
        )
        recommend_parser.add_argument(
            "--severity", 
            choices=["high", "medium", "low", "all"],
            default="all",
            help="Filter by severity"
        )
        recommend_parser.add_argument(
            "--limit", 
            type=int, 
            default=10,
            help="Maximum number of recommendations to show"
        )
        recommend_parser.add_argument(
            "--show-code", 
            action="store_true", 
            help="Show code snippets in recommendations"
        )
        recommend_parser.add_argument(
            "--show-doc", 
            action="store_true", 
            help="Show documentation snippets in recommendations"
        )
    
    def _add_apply_parser(self, subparsers) -> None:
        """Add parser for apply command."""
        apply_parser = subparsers.add_parser(
            "apply", 
            help="Apply a recommendation"
        )
        
        # Add arguments
        apply_parser.add_argument(
            "recommendation_id", 
            help="Recommendation ID to apply"
        )
        apply_parser.add_argument(
            "--dry-run", 
            action="store_true", 
            help="Show changes without applying them"
        )
        apply_parser.add_argument(
            "--backup", 
            action="store_true", 
            help="Create backup files before applying changes"
        )
    
    def _add_relationships_parser(self, subparsers) -> None:
        """Add parser for relationships command."""
        relationships_parser = subparsers.add_parser(
            "relationships", 
            help="Analyze document relationships"
        )
        
        # Add arguments
        relationships_parser.add_argument(
            "document", 
            nargs="?",
            help="Path to document for relationship analysis"
        )
        relationships_parser.add_argument(
            "--directory", 
            help="Directory to analyze relationships in"
        )
        relationships_parser.add_argument(
            "--diagram", 
            action="store_true", 
            help="Generate a Mermaid diagram"
        )
        relationships_parser.add_argument(
            "--save-diagram", 
            metavar="FILE", 
            help="Save diagram to file"
        )
        relationships_parser.add_argument(
            "--depth", 
            type=int, 
            default=1,
            help="Relationship depth"
        )
    
    def _add_config_parser(self, subparsers) -> None:
        """Add parser for config command."""
        config_parser = subparsers.add_parser(
            "config", 
            help="Configure CLI settings"
        )
        
        # Add arguments
        config_parser.add_argument(
            "action", 
            choices=["get", "set", "list", "reset"],
            help="Configuration action"
        )
        config_parser.add_argument(
            "key", 
            nargs="?",
            help="Configuration key"
        )
        config_parser.add_argument(
            "value", 
            nargs="?",
            help="Configuration value"
        )
    
    def _add_status_parser(self, subparsers) -> None:
        """Add parser for status command."""
        status_parser = subparsers.add_parser(
            "status", 
            help="Check status of the Documentation-Based Programming system"
        )
        
        # Add arguments
        status_parser.add_argument(
            "--check-server", 
            action="store_true", 
            help="Check server connectivity"
        )
        status_parser.add_argument(
            "--check-auth", 
            action="store_true", 
            help="Check authentication"
        )
        status_parser.add_argument(
            "--show-settings", 
            action="store_true", 
            help="Show current settings"
        )
    
    def run(self, args=None) -> int:
        """Run the CLI application with the given arguments."""
        # Parse arguments
        args = self.parser.parse_args(args)
        
        # Configure from args
        if args.config:
            self.config_manager.load_from_file(args.config)
        
        # Override configuration with command line options
        if args.server:
            self.config_manager.set("mcp_server.url", args.server)
        
        if args.api_key:
            self.config_manager.set("mcp_server.api_key", args.api_key)
        
        # Set logging level based on verbosity
        log_level = logging.WARNING
        if args.verbose == 1:
            log_level = logging.INFO
        elif args.verbose >= 2:
            log_level = logging.DEBUG
        
        if args.quiet:
            log_level = logging.ERROR
        
        logging.basicConfig(level=log_level, format='%(levelname)s: %(message)s')
        
        # Set output format
        self.output_formatter.set_format(args.output)
        
        # Execute command
        if not args.command:
            self.parser.print_help()
            return 1
        
        try:
            # Initialize MCP client
            self.mcp_client.initialize()
            
            # Get command handler
            handler = self.command_handlers.get(args.command)
            
            if not handler:
                self.output_formatter.error(f"Unknown command: {args.command}")
                return 1
            
            # Execute command
            return handler.execute(args)
            
        except AuthenticationError as e:
            self.output_formatter.error(f"Authentication error: {e}")
            return 2
        except ConnectionError as e:
            self.output_formatter.error(f"Connection error: {e}")
            return 3
        except Exception as e:
            self.output_formatter.error(f"Error: {e}")
            if log_level <= logging.DEBUG:
                import traceback
                traceback.print_exc()
            return 4

def main():
    """Entry point for the CLI application."""
    cli = DocumentationProgrammingCLI()
    sys.exit(cli.run())

if __name__ == "__main__":
    main()
```

2. **Configuration Manager**

```python
class ConfigurationManager:
    """Manages CLI configuration."""
    
    # Default configuration
    DEFAULT_CONFIG = {
        "mcp_server": {
            "url": "http://localhost:3000",
            "api_key": None,
            "timeout": 30
        },
        "cli": {
            "output_format": "text",
            "color": True,
            "progress_bar": True,
            "cache_dir": "~/.dbp/cache"
        },
        "analysis": {
            "default_severity": "all",
            "default_limit": 10,
            "show_code_snippets": True,
            "show_doc_snippets": True
        }
    }
    
    def __init__(self):
        self.config = copy.deepcopy(self.DEFAULT_CONFIG)
        
        # Load configuration from default locations
        self._load_configuration()
    
    def _load_configuration(self) -> None:
        """Load configuration from default locations."""
        # Load from system-wide config
        system_config = "/etc/dbp/config.json"
        if os.path.isfile(system_config):
            self.load_from_file(system_config)
        
        # Load from user config
        user_config = os.path.expanduser("~/.dbp/config.json")
        if os.path.isfile(user_config):
            self.load_from_file(user_config)
        
        # Load from current directory
        local_config = "./.dbp.json"
        if os.path.isfile(local_config):
            self.load_from_file(local_config)
    
    def load_from_file(self, file_path: str) -> None:
        """Load configuration from file."""
        try:
            with open(file_path, "r") as f:
                config_data = json.load(f)
                
                # Update configuration (deep merge)
                self._deep_update(self.config, config_data)
        
        except Exception as e:
            logging.warning(f"Error loading configuration from {file_path}: {e}")
    
    def _deep_update(self, target: Dict, source: Dict) -> Dict:
        """Deep update a nested dictionary."""
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._deep_update(target[key], value)
            else:
                target[key] = value
        
        return target
    
    def save_to_file(self, file_path: str) -> None:
        """Save configuration to file."""
        # Create directory if it doesn't exist
        directory = os.path.dirname(file_path)
        if directory and not os.path.exists(directory):
            os.makedirs(directory)
        
        # Save configuration
        with open(file_path, "w") as f:
            json.dump(self.config, f, indent=2)
    
    def get(self, key_path: str, default=None) -> Any:
        """
        Get configuration value by key path.
        
        Args:
            key_path: Dot-separated path to the configuration value
            default: Default value if the key doesn't exist
            
        Returns:
            Configuration value or default
        """
        parts = key_path.split(".")
        
        # Start from the root
        current = self.config
        
        # Traverse the path
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
        
        return current
    
    def set(self, key_path: str, value: Any) -> None:
        """
        Set configuration value by key path.
        
        Args:
            key_path: Dot-separated path to the configuration value
            value: New value
        """
        parts = key_path.split(".")
        
        # Start from the root
        current = self.config
        
        # Traverse the path (except the last part)
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        # Set the value
        current[parts[-1]] = value
    
    def reset(self, key_path: str = None) -> None:
        """
        Reset configuration to default.
        
        Args:
            key_path: Optional dot-separated path to reset
        """
        if key_path is None:
            # Reset all configuration
            self.config = copy.deepcopy(self.DEFAULT_CONFIG)
            return
        
        # Reset specific path
        parts = key_path.split(".")
        
        # Get the default value
        default_value = self.DEFAULT_CONFIG
        for part in parts:
            if isinstance(default_value, dict) and part in default_value:
                default_value = default_value[part]
            else:
                # Key doesn't exist in defaults, no need to reset
                return
        
        # Set the value
        self.set(key_path, copy.deepcopy(default_value))
```

3. **Authentication Manager**

```python
class AuthenticationManager:
    """Manages authentication with the MCP server."""
    
    def __init__(self, config_manager: ConfigurationManager):
        self.config_manager = config_manager
        self.api_key = None
        self.cached_token = None
        self.token_expiry = None
    
    def initialize(self) -> None:
        """Initialize the authentication manager."""
        # Get API key from configuration
        self.api_key = self.config_manager.get("mcp_server.api_key")
        
        if not self.api_key:
            # Try to load from environment variable
            self.api_key = os.environ.get("DBP_API_KEY")
        
        if not self.api_key:
            # Try to load from keyring if available
            try:
                import keyring
                self.api_key = keyring.get_password("dbp", "api_key")
            except ImportError:
                pass
    
    def get_auth_headers(self) -> Dict[str, str]:
        """
        Get authentication headers for API requests.
        
        Returns:
            Dictionary of authentication headers
        """
        if not self.api_key:
            raise AuthenticationError("No API key configured")
        
        return {
            "X-API-Key": self.api_key
        }
    
    def set_api_key(self, api_key: str, save: bool = True) -> None:
        """
        Set API key.
        
        Args:
            api_key: API key
            save: Whether to save to configuration
        """
        self.api_key = api_key
        
        if save:
            # Save to configuration
            self.config_manager.set("mcp_server.api_key", api_key)
            
            # Try to save to keyring if available
            try:
                import keyring
                keyring.set_password("dbp", "api_key", api_key)
            except ImportError:
                pass
    
    def is_authenticated(self) -> bool:
        """
        Check if authenticated.
        
        Returns:
            True if authenticated, False otherwise
        """
        return self.api_key is not None
```

4. **MCP Client API**

```python
class MCPClientAPI:
    """API client for the MCP server."""
    
    def __init__(self, auth_manager: AuthenticationManager):
        self.auth_manager = auth_manager
        self.config_manager = auth_manager.config_manager
        self.server_url = None
        self.timeout = None
        self._initialized = False
    
    def initialize(self) -> None:
        """Initialize the API client."""
        # Get server URL from configuration
        self.server_url = self.config_manager.get("mcp_server.url")
        self.timeout = self.config_manager.get("mcp_server.timeout", 30)
        
        if not self.server_url:
            raise ConfigurationError("MCP server URL not configured")
        
        self._initialized = True
    
    def _check_initialized(self) -> None:
        """Check if the client is initialized."""
        if not self._initialized:
            raise ClientError("MCP client not initialized")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict:
        """
        Make an API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            
        Returns:
            API response
        """
        self._check_initialized()
        
        # Build URL
        url = f"{self.server_url}/{endpoint}"
        
        # Get authentication headers
        headers = self.auth_manager.get_auth_headers()
        headers["Content-Type"] = "application/json"
        
        # Make request
        try:
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=self.timeout
            )
            
            # Check for errors
            response.raise_for_status()
            
            # Parse response
            return response.json()
        
        except requests.exceptions.HTTPError as e:
            # Handle API errors
            try:
                error_data = e.response.json()
                error_code = error_data.get("error", {}).get("code", "UNKNOWN_ERROR")
                error_message = error_data.get("error", {}).get("message", str(e))
                
                if error_code == "AUTHENTICATION_FAILED":
                    raise AuthenticationError(error_message)
                elif error_code == "AUTHORIZATION_FAILED":
                    raise AuthorizationError(error_message)
                else:
                    raise APIError(f"{error_code}: {error_message}")
            
            except (ValueError, KeyError):
                # Failed to parse error response
                raise APIError(str(e))
        
        except requests.exceptions.ConnectionError as e:
            raise ConnectionError(f"Failed to connect to MCP server: {e}")
        
        except requests.exceptions.Timeout as e:
            raise TimeoutError(f"Request timed out: {e}")
        
        except requests.exceptions.RequestException as e:
            raise APIError(f"Request failed: {e}")
    
    def analyze_consistency(self, code_file_path: str, doc_file_path: str) -> Dict:
        """
        Analyze consistency between code and documentation files.
        
        Args:
            code_file_path: Path to code file
            doc_file_path: Path to documentation file
            
        Returns:
            Analysis results
        """
        data = {
            "code_file_path": code_file_path,
            "doc_file_path": doc_file_path
        }
        
        response = self._make_request(
            method="POST",
            endpoint="tools/analyze_document_consistency",
            data=data
        )
        
        return response.get("result", {})
    
    def get_recommendations(self, inconsistency_id: str = None, file_path: str = None, severity: str = None, limit: int = 10) -> Dict:
        """
        Get recommendations for fixing inconsistencies.
        
        Args:
            inconsistency_id: Inconsistency ID (optional)
            file_path: File path (optional)
            severity: Severity filter (optional)
            limit: Maximum number of recommendations (optional)
            
        Returns:
            Recommendations
        """
        data = {
            "limit": limit
        }
        
        if inconsistency_id:
            data["inconsistency_id"] = inconsistency_id
        
        if file_path:
            data["file_path"] = file_path
        
        if severity and severity != "all":
            data["severity"] = severity
        
        response = self._make_request(
            method="POST",
            endpoint="tools/generate_recommendations",
            data=data
        )
        
        return response.get("result", {})
    
    def apply_recommendation(self, recommendation_id: str, dry_run: bool = False) -> Dict:
        """
        Apply a recommendation.
        
        Args:
            recommendation_id: Recommendation ID
            dry_run: Whether to perform a dry run
            
        Returns:
            Application result
        """
        data = {
            "recommendation_id": recommendation_id,
            "dry_run": dry_run
        }
        
        response = self._make_request(
            method="POST",
            endpoint="tools/apply_recommendation",
            data=data
        )
        
        return response.get("result", {})
    
    def analyze_document_relationships(self, document_path: str = None, directory: str = None, depth: int = 1) -> Dict:
        """
        Analyze document relationships.
        
        Args:
            document_path: Path to document (optional)
            directory: Directory to analyze (optional)
            depth: Relationship depth
            
        Returns:
            Relationship analysis results
        """
        data = {
            "depth": depth
        }
        
        if document_path:
            data["document_path"] = document_path
        
        if directory:
            data["directory"] = directory
        
        response = self._make_request(
            method="POST",
            endpoint="tools/analyze_document_relationships",
            data=data
        )
        
        return response.get("result", {})
    
    def generate_mermaid_diagram(self, document_paths: List[str] = None, directory: str = None) -> Dict:
        """
        Generate a Mermaid diagram of document relationships.
        
        Args:
            document_paths: List of document paths (optional)
            directory: Directory to analyze (optional)
            
        Returns:
            Mermaid diagram
        """
        data = {}
        
        if document_paths:
            data["document_paths"] = document_paths
        
        if directory:
            data["directory"] = directory
        
        response = self._make_request(
            method="POST",
            endpoint="tools/generate_mermaid_diagram",
            data=data
        )
        
        return response.get("result", {})
    
    def check_server_status(self) -> Dict:
        """
        Check server status.
        
        Returns:
            Server status information
        """
        response = self._make_request(
            method="GET",
            endpoint="status"
        )
        
        return response
```

5. **Output Formatter**

```python
class OutputFormatter:
    """Formats output for the CLI."""
    
    def __init__(self):
        self.format = "text"
        self._init_colors()
    
    def _init_colors(self) -> None:
        """Initialize colored output."""
        # Use colorama if available
        try:
            import colorama
            colorama.init()
            self.colors = {
                "reset": colorama.Style.RESET_ALL,
                "bold": colorama.Style.BRIGHT,
                "red": colorama.Fore.RED,
                "green": colorama.Fore.GREEN,
                "yellow": colorama.Fore.YELLOW,
                "blue": colorama.Fore.BLUE,
                "magenta": colorama.Fore.MAGENTA,
                "cyan": colorama.Fore.CYAN,
            }
        except ImportError:
            # Fallback to ANSI escape codes
            self.colors = {
                "reset": "\033[0m",
                "bold": "\033[1m",
                "red": "\033[31m",
                "green": "\033[32m",
                "yellow": "\033[33m",
                "blue": "\033[34m",
                "magenta": "\033[35m",
                "cyan": "\033[36m",
            }
    
    def set_format(self, format: str) -> None:
        """
        Set output format.
        
        Args:
            format: Output format (text, json, markdown, html)
        """
        self.format = format
    
    def print(self, message: str) -> None:
        """
        Print a message.
        
        Args:
            message: Message to print
        """
        print(message)
    
    def error(self, message: str) -> None:
        """
        Print an error message.
        
        Args:
            message: Error message
        """
        print(f"{self.colors['red']}Error: {message}{self.colors['reset']}", file=sys.stderr)
    
    def warning(self, message: str) -> None:
        """
        Print a warning message.
        
        Args:
            message: Warning message
        """
        print(f"{self.colors['yellow']}Warning: {message}{self.colors['reset']}", file=sys.stderr)
    
    def success(self, message: str) -> None:
        """
        Print a success message.
        
        Args:
            message: Success message
        """
        print(f"{self.colors['green']}{message}{self.colors['reset']}")
    
    def info(self, message: str) -> None:
        """
        Print an info message.
        
        Args:
            message: Info message
        """
        print(f"{self.colors['blue']}{message}{self.colors['reset']}")
    
    def format_output(self, data: Any) -> None:
        """
        Format and print output based on the current format.
        
        Args:
            data: Data to format
        """
        if self.format == "json":
            self.print(json.dumps(data, indent=2))
        elif self.format == "markdown":
            self.print(self._format_as_markdown(data))
        elif self.format == "html":
            self.print(self._format_as_html(data))
        else:  # Default to text
            self.print(self._format_as_text(data))
    
    def _format_as_text(self, data: Any) -> str:
        """Format data as text."""
        if isinstance(data, str):
            return data
        
        if isinstance(data, dict):
            if "inconsistencies" in data:
                return self._format_inconsistencies_as_text(data)
            elif "recommendations" in data:
                return self._format_recommendations_as_text(data)
            elif "relationships" in data:
                return self._format_relationships_as_text(data)
            else:
                return self._format_dict_as_text(data)
        
        if isinstance(data, list):
            return self._format_list_as_text(data)
        
        # Fallback to string representation
        return str(data)
    
    def _format_dict_as_text(self, data: Dict) -> str:
        """Format dictionary as text."""
        result = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(f"{key}:")
                for k, v in value.items():
                    result.append(f"  {k}: {v}")
            else:
                result.append(f"{key}: {value}")
        
        return "\n".join(result)
    
    def _format_list_as_text(self, data: List) -> str:
        """Format list as text."""
        result = []
        
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                result.append(f"{i}.")
                for key, value in item.items():
                    result.append(f"  {key}: {value}")
                result.append("")
            else:
                result.append(f"{i}. {item}")
        
        return "\n".join(result)
    
    def _format_inconsistencies_as_text(self, data: Dict) -> str:
        """Format inconsistencies as text."""
        result = []
        
        # Add summary
        if "summary" in data:
            result.append(f"{self.colors['bold']}INCONSISTENCY SUMMARY{self.colors['reset']}")
            result.append(f"Total: {data['summary']['total']}")
            
            if "by_severity" in data["summary"]:
                result.append("By Severity:")
                for severity, count in data["summary"]["by_severity"].items():
                    color = self._severity_color(severity)
                    result.append(f"  {color}{severity}{self.colors['reset']}: {count}")
            
            if "by_type" in data["summary"]:
                result.append("By Type:")
                for type_name, count in data["summary"]["by_type"].items():
                    result.append(f"  {type_name}: {count}")
            
            result.append("")
        
        # Add inconsistencies
        if "inconsistencies" in data:
            result.append(f"{self.colors['bold']}INCONSISTENCIES{self.colors['reset']}")
            
            for i, inconsistency in enumerate(data["inconsistencies"], 1):
                severity = inconsistency.get("severity", "unknown")
                color = self._severity_color(severity)
                
                result.append(f"{i}. {color}[{severity.upper()}]{self.colors['reset']} {inconsistency.get('description')}")
                result.append(f"   ID: {inconsistency.get('id')}")
                result.append(f"   Type: {inconsistency.get('type')}")
                result.append(f"   Source: {inconsistency.get('source_file')}")
                result.append(f"   Target: {inconsistency.get('target_file')}")
                result.append("")
        
        return "\n".join(result)
    
    def _format_recommendations_as_text(self, data: Dict) -> str:
        """Format recommendations as text."""
        result = []
        
        # Add summary
        if "summary" in data:
            result.append(f"{self.colors['bold']}RECOMMENDATION SUMMARY{self.colors['reset']}")
            result.append(f"Total: {data['summary']['total']}")
            
            if "by_severity" in data["summary"]:
                result.append("By Severity:")
                for severity, count in data["summary"]["by_severity"].items():
                    color = self._severity_color(severity)
                    result.append(f"  {color}{severity}{self.colors['reset']}: {count}")
            
            result.append("")
        
        # Add recommendations
        if "recommendations" in data:
            result.append(f"{self.colors['bold']}RECOMMENDATIONS{self.colors['reset']}")
            
            for i, recommendation in enumerate(data["recommendations"], 1):
                severity = recommendation.get("severity", "unknown")
                color = self._severity_color(severity)
                
                result.append(f"{i}. {color}[{severity.upper()}]{self.colors['reset']} {recommendation.get('title')}")
                result.append(f"   ID: {recommendation.get('id')}")
                result.append(f"   Description: {recommendation.get('description')}")
                
                # Add code snippet if available and requested
                if "code_snippet" in recommendation and recommendation["code_snippet"]:
                    result.append("   Code Snippet:")
                    for line in recommendation["code_snippet"].split("\n"):
                        result.append(f"     {line}")
                
                # Add doc snippet if available and requested
                if "doc_snippet" in recommendation and recommendation["doc_snippet"]:
                    result.append("   Documentation Snippet:")
                    for line in recommendation["doc_snippet"].split("\n"):
                        result.append(f"     {line}")
                
                result.append("")
        
        return "\n".join(result)
    
    def _format_relationships_as_text(self, data: Dict) -> str:
        """Format relationships as text."""
        result = []
        
        # Add summary
        if "count" in data:
            result.append(f"{self.colors['bold']}RELATIONSHIP SUMMARY{self.colors['reset']}")
            result.append(f"Total Relationships: {data['count']}")
            result.append("")
        
        # Add relationships
        if "relationships" in data:
            result.append(f"{self.colors['bold']}RELATIONSHIPS{self.colors['reset']}")
            
            for i, relationship in enumerate(data["relationships"], 1):
                result.append(f"{i}. {relationship.get('source')} -> {relationship.get('target')}")
                result.append(f"   Type: {relationship.get('type')}")
                result.append(f"   Topic: {relationship.get('topic')}")
                
                if "scope" in relationship:
                    result.append(f"   Scope: {relationship.get('scope')}")
                
                result.append("")
        
        # Add diagram if available
        if "diagram" in data:
            result.append(f"{self.colors['bold']}MERMAID DIAGRAM{self.colors['reset']}")
            result.append("```mermaid")
            result.append(data["diagram"])
            result.append("```")
        
        return "\n".join(result)
    
    def _format_as_markdown(self, data: Any) -> str:
        """Format data as markdown."""
        if isinstance(data, str):
            return data
        
        if isinstance(data, dict):
            if "inconsistencies" in data:
                return self._format_inconsistencies_as_markdown(data)
            elif "recommendations" in data:
                return self._format_recommendations_as_markdown(data)
            elif "relationships" in data:
                return self._format_relationships_as_markdown(data)
            else:
                return self._format_dict_as_markdown(data)
        
        if isinstance(data, list):
            return self._format_list_as_markdown(data)
        
        # Fallback to string representation
        return f"```\n{str(data)}\n```"
    
    def _format_dict_as_markdown(self, data: Dict) -> str:
        """Format dictionary as markdown."""
        result = []
        
        for key, value in data.items():
            if isinstance(value, dict):
                result.append(f"### {key}")
                for k, v in value.items():
                    result.append(f"- **{k}**: {v}")
            else:
                result.append(f"**{key}**: {value}")
        
        return "\n".join(result)
    
    def _format_list_as_markdown(self, data: List) -> str:
        """Format list as markdown."""
        result = []
        
        for item in data:
            if isinstance(item, dict):
                for key, value in item.items():
                    if key == "name" or key == "title":
                        result.append(f"### {value}")
                    else:
                        result.append(f"- **{key}**: {value}")
                result.append("")
            else:
                result.append(f"- {item}")
        
        return "\n".join(result)
    
    def _format_inconsistencies_as_markdown(self, data: Dict) -> str:
        """Format inconsistencies as markdown."""
        result = []
        
        # Add summary
        if "summary" in data:
            result.append("# Inconsistency Summary")
            result.append(f"Total: **{data['summary']['total']}**")
            
            if "by_severity" in data["summary"]:
                result.append("## By Severity")
                for severity, count in data["summary"]["by_severity"].items():
                    result.append(f"- **{severity}**: {count}")
            
            if "by_type" in data["summary"]:
                result.append("## By Type")
                for type_name, count in data["summary"]["by_type"].items():
                    result.append(f"- **{type_name}**: {count}")
            
            result.append("")
        
        # Add inconsistencies
        if "inconsistencies" in data:
            result.append("# Inconsistencies")
            
            for inconsistency in data["inconsistencies"]:
                severity = inconsistency.get("severity", "unknown")
                
                result.append(f"## [{severity.upper()}] {inconsistency.get('description')}")
                result.append(f"ID: `{inconsistency.get('id')}`")
                result.append(f"Type: `{inconsistency.get('type')}`")
                result.append(f"Source: `{inconsistency.get('source_file')}`")
                result.append(f"Target: `{inconsistency.get('target_file')}`")
                result.append("")
        
        return "\n".join(result)
    
    def _format_as_html(self, data: Any) -> str:
        """Format data as HTML."""
        # Simple HTML conversion as a placeholder
        # In a real implementation, this would be more sophisticated
        markdown = self._format_as_markdown(data)
        
        # Very basic markdown to HTML conversion
        html = markdown.replace("\n\n", "<br><br>")
        html = html.replace("# ", "<h1>")
        html = html.replace("## ", "<h2>")
        html = html.replace("### ", "<h3>")
        html = html.replace("\n- ", "<br>• ")
        html = re.sub(r"\*\*(.*?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"`(.*?)`", r"<code>\1</code>", html)
        
        return f"<!DOCTYPE html><html><head><style>body {{ font-family: Arial, sans-serif; }}</style></head><body>{html}</body></html>"
    
    def _severity_color(self, severity: str) -> str:
        """Get color for severity."""
        if severity == "high":
            return self.colors["red"]
        elif severity == "medium":
            return self.colors["yellow"]
        elif severity == "low":
            return self.colors["green"]
        else:
            return self.colors["reset"]
```

6. **ProgressIndicator**

```python
class ProgressIndicator:
    """Progress indicator for long-running operations."""
    
    def __init__(self):
        self.spinner_chars = "|/-\\"
        self.current_char = 0
        self.active = False
        self.thread = None
        self.message = ""
    
    def start(self, message: str = "Processing") -> None:
        """
        Start progress indicator.
        
        Args:
            message: Message to display
        """
        if self.active:
            return
        
        self.active = True
        self.message = message
        
        # Create and start thread
        self.thread = threading.Thread(target=self._animate, daemon=True)
        self.thread.start()
    
    def stop(self) -> None:
        """Stop progress indicator."""
        self.active = False
        
        if self.thread:
            self.thread.join(1.0)  # Wait up to 1 second for thread to finish
            self.thread = None
        
        # Clear progress line
        sys.stdout.write("\r" + " " * (len(self.message) + 10) + "\r")
        sys.stdout.flush()
    
    def _animate(self) -> None:
        """Animate the progress indicator."""
        while self.active:
            # Print spinner
            sys.stdout.write(f"\r{self.message} {self.spinner_chars[self.current_char]} ")
            sys.stdout.flush()
            
            # Update spinner position
            self.current_char = (self.current_char + 1) % len(self.spinner_chars)
            
            # Sleep
            time.sleep(0.1)
```

7. **CommandHandler (Base Class)**

```python
class CommandHandler(ABC):
    """Base class for command handlers."""
    
    def __init__(self, mcp_client: MCPClientAPI, output_formatter: OutputFormatter, progress_indicator: ProgressIndicator):
        self.mcp_client = mcp_client
        self.output_formatter = output_formatter
        self.progress_indicator = progress_indicator
    
    @abstractmethod
    def execute(self, args: argparse.Namespace) -> int:
        """
        Execute the command.
        
        Args:
            args: Command arguments
            
        Returns:
            Exit code (0 for success)
        """
        pass
```

8. **AnalyzeCommandHandler**

```python
class AnalyzeCommandHandler(CommandHandler):
    """Handler for analyze command."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the analyze command."""
        # Check arguments
        if not args.code_file and not args.code_dir:
            self.output_formatter.error("No code file or directory specified")
            return 1
        
        if not args.doc_file and not args.doc_dir:
            self.output_formatter.error("No documentation file or directory specified")
            return 1
        
        try:
            if args.code_file and args.doc_file:
                # Analyze specific files
                self.output_formatter.info(f"Analyzing consistency between {args.code_file} and {args.doc_file}")
                
                # Start progress indicator
                self.progress_indicator.start("Analyzing consistency")
                
                try:
                    # Call API
                    result = self.mcp_client.analyze_consistency(args.code_file, args.doc_file)
                    
                    # Filter results if needed
                    if args.severity and args.severity != "all":
                        result["inconsistencies"] = [
                            i for i in result.get("inconsistencies", []) 
                            if i.get("severity") == args.severity
                        ]
                        
                        # Update summary
                        if "summary" in result:
                            result["summary"]["total"] = len(result["inconsistencies"])
                    
                    if args.type:
                        result["inconsistencies"] = [
                            i for i in result.get("inconsistencies", []) 
                            if i.get("type") == args.type
                        ]
                        
                        # Update summary
                        if "summary" in result:
                            result["summary"]["total"] = len(result["inconsistencies"])
                    
                    # Sort results if requested
                    if args.sort_by:
                        result["inconsistencies"] = sorted(
                            result.get("inconsistencies", []),
                            key=lambda i: i.get(args.sort_by, "")
                        )
                    
                    # Show only summary if requested
                    if args.summary_only and "inconsistencies" in result:
                        del result["inconsistencies"]
                    
                    # Format and print results
                    self.output_formatter.format_output(result)
                    
                    return 0
                    
                finally:
                    # Stop progress indicator
                    self.progress_indicator.stop()
            
            else:
                # Analyze directories
                self.output_formatter.error("Directory analysis not implemented yet")
                return 1
        
        except Exception as e:
            self.progress_indicator.stop()
            self.output_formatter.error(str(e))
            return 1
```

9. **Additional Command Handlers (Examples)**

```python
class RecommendCommandHandler(CommandHandler):
    """Handler for recommend command."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the recommend command."""
        try:
            # Start progress indicator
            self.progress_indicator.start("Generating recommendations")
            
            try:
                # Call API
                result = self.mcp_client.get_recommendations(
                    inconsistency_id=args.inconsistency_id,
                    file_path=args.file,
                    severity=args.severity,
                    limit=args.limit
                )
                
                # Format and print results
                self.output_formatter.format_output(result)
                
                return 0
                
            finally:
                # Stop progress indicator
                self.progress_indicator.stop()
        
        except Exception as e:
            self.progress_indicator.stop()
            self.output_formatter.error(str(e))
            return 1

class ApplyCommandHandler(CommandHandler):
    """Handler for apply command."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the apply command."""
        try:
            # Start progress indicator
            self.progress_indicator.start("Applying recommendation")
            
            try:
                # Call API
                result = self.mcp_client.apply_recommendation(
                    recommendation_id=args.recommendation_id,
                    dry_run=args.dry_run
                )
                
                # Format and print results
                self.output_formatter.format_output(result)
                
                if result.get("applied"):
                    self.output_formatter.success("Recommendation applied successfully")
                else:
                    self.output_formatter.warning("Failed to apply recommendation")
                
                return 0 if result.get("applied") else 1
                
            finally:
                # Stop progress indicator
                self.progress_indicator.stop()
        
        except Exception as e:
            self.progress_indicator.stop()
            self.output_formatter.error(str(e))
            return 1

class RelationshipsCommandHandler(CommandHandler):
    """Handler for relationships command."""
    
    def execute(self, args: argparse.Namespace) -> int:
        """Execute the relationships command."""
        try:
            # Start progress indicator
            self.progress_indicator.start("Analyzing relationships")
            
            try:
                if args.diagram:
                    # Generate Mermaid diagram
                    if args.document:
                        result = self.mcp_client.generate_mermaid_diagram(
                            document_paths=[args.document]
                        )
                    elif args.directory:
                        result = self.mcp_client.generate_mermaid_diagram(
                            directory=args.directory
                        )
                    else:
                        self.output_formatter.error("No document or directory specified")
                        return 1
                    
                    # Save diagram to file if requested
                    if args.save_diagram and "diagram" in result:
                        try:
                            with open(args.save_diagram, "w") as f:
                                f.write("```mermaid\n")
                                f.write(result["diagram"])
                                f.write("\n```\n")
                            
                            self.output_formatter.success(f"Diagram saved to {args.save_diagram}")
                        
                        except Exception as e:
                            self.output_formatter.error(f"Failed to save diagram: {e}")
                            return 1
                else:
                    # Analyze relationships
                    result = self.mcp_client.analyze_document_relationships(
                        document_path=args.document,
                        directory=args.directory,
                        depth=args.depth
                    )
                
                # Format and print results
                self.output_formatter.format_output(result)
                
                return 0
                
            finally:
                # Stop progress indicator
                self.progress_indicator.stop()
        
        except Exception as e:
            self.progress_indicator.stop()
            self.output_formatter.error(str(e))
            return 1
```

10. **Exceptions**

```python
class CLIError(Exception):
    """Base exception for CLI errors."""
    pass

class ConfigurationError(CLIError):
    """Configuration error."""
    pass

class AuthenticationError(CLIError):
    """Authentication error."""
    pass

class AuthorizationError(CLIError):
    """Authorization error."""
    pass

class ConnectionError(CLIError):
    """Connection error."""
    pass

class APIError(CLIError):
    """API error."""
    pass

class ClientError(CLIError):
    """Client error."""
    pass
```

### Package Structure

```
dbp_cli/
├── __init__.py
├── __main__.py         # Entry point
├── cli.py              # Main CLI application
├── config.py           # Configuration management
├── auth.py             # Authentication management
├── api.py              # MCP client API
├── output.py           # Output formatting
├── progress.py         # Progress indication
├── commands/           # Command handlers
│   ├── __init__.py
│   ├── base.py         # Base command handler
│   ├── analyze.py      # Analyze command handler
│   ├── recommend.py    # Recommend command handler
│   ├── apply.py        # Apply command handler
│   ├── relationships.py # Relationships command handler
│   ├── config.py       # Config command handler
│   └── status.py       # Status command handler
└── exceptions.py       # Exception classes
```

### Setup and Distribution

```python
# setup.py
from setuptools import setup, find_packages

setup(
    name="dbp-cli",
    version="0.1.0",
    description="Documentation-Based Programming CLI",
    author="Documentation-Based Programming Team",
    packages=find_packages(),
    install_requires=[
        "requests>=2.25.0",
        "colorama>=0.4.4",
        "keyring>=23.0.0",
        "tabulate>=0.8.9",
    ],
    entry_points={
        "console_scripts": [
            "dbp=dbp_cli.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
)
```

## Implementation Plan

### Phase 1: Core Framework
1. Set up project structure
2. Implement ConfigurationManager
3. Implement AuthenticationManager
4. Implement base exceptions
5. Create basic CLI structure with argument parsing

### Phase 2: MCP API Integration
1. Implement MCPClientAPI class
2. Implement API connectivity and error handling
3. Add authentication and authorization handling
4. Implement request and response handling

### Phase 3: Output and Progress
1. Implement OutputFormatter with different formats
2. Create ProgressIndicator for long-running operations
3. Add support for colored output

### Phase 4: Command Handlers
1. Implement base CommandHandler
2. Create specialized command handlers for each operation
3. Implement argument parsing for commands
4. Add error handling and validation

### Phase 5: Testing and Packaging
1. Implement unit tests
2. Set up CI/CD pipeline
3. Create setup script and package configuration
4. Add documentation and examples

## Usage Examples

### Basic Usage

```bash
# Check system status
dbp status

# Analyze consistency between a code file and a documentation file
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md

# Generate recommendations for an inconsistency
dbp recommend --inconsistency-id 123456

# Apply a recommendation
dbp apply abc123 --dry-run

# Analyze document relationships
dbp relationships doc/DESIGN.md --diagram --save-diagram design_relationships.md

# Configure CLI settings
dbp config set mcp_server.url http://localhost:3000
```

### Advanced Usage

```bash
# Analyze with filtering and sorting
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md --severity high --sort-by file

# Analyze all files in directories
dbp analyze --code-dir src/auth --doc-dir doc/auth

# Generate recommendations with customization
dbp recommend --file src/auth/user.py --severity high --limit 5 --show-code --show-doc

# Apply a recommendation with backup
dbp apply abc123 --backup

# Get document relationships with custom depth
dbp relationships doc/DESIGN.md --depth 3

# Output as JSON for programmatic use
dbp analyze src/auth/user.py doc/auth/USER_MODEL.md --output json > analysis.json
```

### Script Integration

```bash
# Bash script example
#!/bin/bash
# Run consistency analysis and apply high severity recommendations automatically

# Run analysis
analysis_result=$(dbp analyze src/auth/user.py doc/auth/USER_MODEL.md --output json)

# Extract inconsistency IDs for high severity issues
high_severity_ids=$(echo "$analysis_result" | jq -r '.inconsistencies[] | select(.severity == "high") | .id')

# Generate and apply recommendations for each high severity inconsistency
for id in $high_severity_ids; do
    recommendations=$(dbp recommend --inconsistency-id "$id" --output json)
    recommendation_id=$(echo "$recommendations" | jq -r '.recommendations[0].id')
    
    if [ ! -z "$recommendation_id" ]; then
        dbp apply "$recommendation_id"
    fi
done
```

## Security Considerations

The Python CLI Client implements these security measures:
- Secure handling of API keys using keyring when available
- Support for environment variables for secrets
- Secure storage of configuration data
- Proper error handling to avoid information leakage
- Validation of server responses
- Input validation before making API requests
- Secure handling of temporary files

## Testing Strategy

### Unit Tests
- Test configuration management
- Test authentication handling
- Test output formatting
- Test command handlers

### Integration Tests
- Test MCP API client
- Test end-to-end command execution
- Test error handling and recovery

### System Tests
- Test real-world usage scenarios
- Test performance with large projects
- Test different output formats

## Dependencies on Other Plans

This plan depends on:
- MCP Server Integration plan (for API endpoints)
- Consistency Analysis plan (for data structures)
- Recommendation Generator plan (for data structures)
- Documentation Relationships plan (for data structures)

## Implementation Timeline

1. Core Framework - 2 days
2. MCP API Integration - 2 days
3. Output and Progress - 1 day
4. Command Handlers - 2 days
5. Testing and Packaging - 1 day

Total: 8 days
