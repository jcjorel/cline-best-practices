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
# Implements the simplified LifecycleManager class, which manages the overall
# application lifecycle (startup, shutdown) using the ultra-simple component system.
# Serves as the main entry point for the DBP application.
###############################################################################
# [Source file design principles]
# - Ultra-simple application lifecycle management
# - Direct component registration rather than through factories
# - Clear and straightforward startup/shutdown processes
# - Minimal error handling focused on clear reporting
# - Single responsibility for application lifecycle
###############################################################################
# [Source file constraints]
# - Must handle basic signal interrupts for graceful shutdown
# - Uses direct import of components rather than factories
# - Initialization errors fail fast with clear reporting
# - Maintains backward compatibility with existing entry points
###############################################################################
# [Dependencies]
# codebase:- doc/DESIGN.md
# codebase:- doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-25T13:21:47Z : Fixed component enablement configuration handling by CodeAssistant
# * Updated is_component_enabled to properly access Pydantic model attributes instead of treating it as a dictionary
# * Improved error handling to throw explicit errors when component names are missing from configuration
# * Removed fallback behavior to align with project's fail-fast error handling approach
# 2025-04-25T13:12:00Z : Fixed component registration to skip disabled components by CodeAssistant
# * Modified _register_components_with_registry to skip registering disabled components 
# * Updated component registration to properly respect the enablement configuration
# * Maintained existing logging for disabled components
# 2025-04-25T09:11:14Z : Centralized component dependencies by CodeAssistant
# * Created new component_dependencies.py to store component declarations
# * Modified _register_components_with_registry to use the centralized declarations
# * Improved documentation to reflect the new component registration approach
# * Added type hints for better code quality and IDE support
# 2025-04-20T19:21:00Z : Added watchdog keepalive calls by CodeAssistant
# * Added keepalive before and after component registration
# * Added keepalive at the start of the initialization process
# * Fixed issue with watchdog not detecting deadlocks during component initialization
# * Maintained KISS approach with simple, strategic keepalive calls
# 2025-04-19T23:43:00Z : Added ComponentRegistry integration by CodeAssistant
# * Added ComponentRegistry import and initialization
# * Replaced _register_components with _register_components_with_registry
# * Implemented explicit dependency declaration for all components
# * Added support for component factories with config_manager as an example
# 2025-04-18T17:02:00Z : Fixed component registration import mechanism by CodeAssistant
# * Changed relative imports to absolute imports to solve "No module named '.'" errors
# * Updated register_if_enabled to handle absolute imports correctly
# * Improved log messages to show component dependencies for better debugging
###############################################################################

import logging
import signal
import sys
import threading
import traceback
from typing import Optional, List, Dict, Any

from .component_dependencies import COMPONENT_DECLARATIONS

from .log_utils import setup_application_logging

# Import core components
from .system import ComponentSystem
from .component import Component
from .file_access_component import FileAccessComponent
from .registry import ComponentRegistry

# Import core components
try:
    from ..config.config_manager import ConfigurationManager
    from ..config.component import ConfigManagerComponent
except ImportError as e:
    logging.error(f"Failed to import configuration modules: {e}")
    ConfigurationManager = None
    ConfigManagerComponent = None

logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    [Class intent]
    Manages the overall lifecycle (startup, shutdown) of the DBP application
    using the ultra-simple component system.
    
    [Implementation details]
    Handles basic setup, component registration, signal handling,
    and startup/shutdown processes with minimal complexity.
    
    [Design principles]
    Ultra-simple lifecycle management with clear processes.
    Direct component registration rather than through factories.
    Minimal error handling focused on clear reporting.
    """

    def __init__(self, cli_args: Optional[List[str]] = None):
        """
        [Function intent]
        Initializes the LifecycleManager with minimal setup.
        
        [Implementation details]
        Sets up logging, configuration, signals, and the component system.
        
        [Design principles]
        Minimal initialization with clear setup steps.
        
        Args:
            cli_args: Optional list of command-line arguments
        """
        # Setup basic state tracking
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        self._is_running = False

        # Initialize essential services
        self._setup_logging()
        self.config_manager = self._load_config(cli_args)
        self.config = self.config_manager._config if self.config_manager else {}

        # Create the component registry
        self.registry = ComponentRegistry()
        
        # Register components with the registry
        self._register_components_with_registry()

        # Create the simplified component system
        self.system = ComponentSystem(self.config, logger)
        
        # Register components from registry with the system
        self.registry.register_with_system(self.system)
        
        # Update watchdog keepalive after component registration
        from .watchdog import keep_alive
        keep_alive()

        # Setup signal handling for graceful shutdown
        self._setup_signal_handlers()

    def _setup_logging(self) -> None:
        """
        [Function intent]
        Sets up basic logging configuration.
        
        [Implementation details]
        Uses centralized setup_application_logging from log_utils module.
        Reads log level from environment or defaults to INFO.
        
        [Design principles]
        Simple logging setup with consistent formatting across all components.
        """
        import os
        
        # Get log level from environment or default to INFO
        log_level_name = os.environ.get("DBP_LOG_LEVEL", "INFO").upper()
        
        # Use the centralized logging setup function
        setup_application_logging(log_level=log_level_name)
        
        logger.debug(f"Logging initialized at level {log_level_name} with consistent formatting")

    def _load_config(self, cli_args: Optional[List[str]]) -> Optional[ConfigurationManager]:
        """
        [Function intent]
        Loads application configuration.
        
        [Implementation details]
        Creates and initializes the ConfigurationManager.
        
        [Design principles]
        Simple configuration loading with clear error reporting.
        
        Args:
            cli_args: Optional command-line arguments
            
        Returns:
            ConfigurationManager instance or None if loading fails
        """
        if ConfigurationManager is None:
            logger.error("ConfigurationManager class not available")
            return None
            
        try:
            logger.info("Loading application configuration...")
            config_manager = ConfigurationManager()
            config_manager.initialize(args=cli_args)
            return config_manager
        except Exception as e:
            logger.critical(f"Failed to load configuration: {e}", exc_info=True)
            return None

    def _setup_signal_handlers(self) -> None:
        """
        [Function intent]
        Sets up handlers for termination signals.
        
        [Implementation details]
        Registers handlers for SIGINT and SIGTERM signals.
        
        [Design principles]
        Simple signal handling for graceful shutdown.
        """
        try:
            for sig in [signal.SIGINT, signal.SIGTERM]:
                signal.signal(sig, self._handle_shutdown_signal)
                logger.debug(f"Registered handler for signal {sig}")
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not setup signal handlers: {e}")

    def _handle_shutdown_signal(self, signum, frame) -> None:
        """
        [Function intent]
        Handles termination signals by initiating shutdown.
        
        [Implementation details]
        Logs signal information and calls shutdown method.
        
        [Design principles]
        Clean signal handling with explicit shutdown.
        
        Args:
            signum: Signal number received
            frame: Current stack frame
        """
        try:
            signal_name = signal.Signals(signum).name
            logger.warning(f"Received signal {signal_name} ({signum}). Shutting down...")
        except (ValueError, AttributeError):
            logger.warning(f"Received signal {signum}. Shutting down...")
            
        # Initiate shutdown
        self.shutdown()
        sys.exit(0)

    def _register_components_with_registry(self) -> None:
        """
        [Function intent]
        Registers only enabled application components with the component registry
        with explicit dependency declarations.
        
        [Implementation details]
        Uses the centralized component declarations from component_dependencies.py.
        Checks component enablement configuration before registration.
        Skips disabled components entirely to prevent unnecessary imports.
        Registers component classes with explicit dependencies.
        
        [Design principles]
        Centralized component registration with explicit dependencies.
        Selective component registration based on configuration.
        Clear separation between component definition and dependency declaration.
        """
        from .watchdog import keep_alive
        
        # Update watchdog keepalive before starting component registration
        keep_alive()
        logger.info("Registering components with registry...")
        
        # Get component enablement configuration
        try:
            if self.config_manager:
                typed_config = self.config_manager.get_typed_config()
                # Direct attribute access with no fallbacks
                enabled_config = typed_config.component_enabled
                logger.info(f"Using component enablement configuration")
            else:
                # Config manager not available, raise to the exception handler
                raise ValueError("Configuration manager not available")
        except Exception as e:
            logger.warning(f"Failed to get component enablement configuration: {e}, using defaults")
            # Raise to notify that this is a critical issue that needs fixing
            raise RuntimeError(f"Failed to access required configuration: component_enabled") from e
        
        # Helper function to check if component is enabled
        def is_component_enabled(name):
            # Access component enablement directly as an attribute of the Pydantic model
            if not hasattr(enabled_config, name):
                raise AttributeError(f"Component '{name}' not found in component_enabled configuration")
            return getattr(enabled_config, name)
        
        # Helper function to register a component class with the registry
        def register_component_class(import_path, component_class, name, dependencies=None, info=None):
            enabled = is_component_enabled(name)
            if not enabled:
                logger.info(f"Component '{name}' disabled by configuration")
                return False
                
            try:
                # Import the component class
                module_path = import_path.replace("..", "dbp")
                module = __import__(module_path, fromlist=[component_class])
                component_cls = getattr(module, component_class)
                
                # Register with the registry
                self.registry.register_component(component_cls, dependencies=dependencies, enabled=enabled)
                
                logger.info(f"Registered component class: '{name}' with dependencies: {dependencies}")
                return True
            except ImportError as e:
                logger.error(f"Failed to import component class '{name}': {e}")
                return False
            except Exception as e:
                logger.error(f"Failed to register component '{name}': {e}")
                return False
        
        # Register ConfigManagerComponent directly since it needs special handling
        if ConfigManagerComponent and self.config_manager:
            try:
                # Create a factory function that will create the component with the config_manager
                def config_manager_factory():
                    return ConfigManagerComponent(self.config_manager)
                
                # Register the factory with no dependencies
                self.registry.register_component_factory(
                    name="config_manager",
                    factory=config_manager_factory,
                    dependencies=[],
                    enabled=True
                )
                logger.info("Registered component factory: 'config_manager' with dependencies: []")
            except Exception as e:
                logger.error(f"Failed to register config_manager component: {e}")
        
        # Register only enabled components from the centralized COMPONENT_DECLARATIONS list
        for component_info in COMPONENT_DECLARATIONS:
            name = component_info["name"]
            enabled = is_component_enabled(name)
            
            if not enabled:
                logger.info(f"Component '{name}' disabled by configuration - skipping registration")
                continue
                
            register_component_class(
                component_info["import_path"],
                component_info["component_class"],
                name,
                component_info["dependencies"]
            )
        
        logger.info(f"Registered {len(self.registry.get_all_component_names())} components with registry")
                

    def start(self) -> bool:
        """
        [Function intent]
        Starts the application by initializing all components.
        
        [Implementation details]
        Acquires lock, initializes components through the component system,
        and handles initialization failures.
        
        [Design principles]
        Simple startup process with clear status reporting.
        
        Returns:
            bool: True if startup succeeded, False otherwise
        """
        # Update watchdog keepalive before starting initialization
        from .watchdog import keep_alive
        keep_alive()

        with self._lock:
            if self._is_running:
                logger.warning("Application is already running")
                return True
                
            logger.info("Starting Documentation-Based Programming system...")
            
        try:
            # Initialize all components via the component system
            success = self.system.initialize_all()
            
            if success:
                with self._lock:
                    self._is_running = True
                logger.info("System startup complete. Application is running.")
                return True
            else:
                logger.error("System startup failed due to component initialization errors.")
                return False
                
        except Exception as e:
            logger.critical(f"A critical error occurred during system startup: {e}", exc_info=True)
            return False

    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the application by stopping all components.
        
        [Implementation details]
        Acquires lock, shuts down components through the component system,
        and clears running state.
        
        [Design principles]
        Simple shutdown process with clear status reporting.
        
        Returns:
            None
        """
        with self._lock:
            if not self._is_running:
                logger.info("Application not running, shutdown not needed.")
                return
                
            logger.info("Initiating system shutdown...")
            self._shutdown_event.set()

        try:
            # Shutdown components via the component system
            self.system.shutdown_all()
            logger.info("System shutdown complete.")
            
        except Exception as e:
            logger.error(f"An error occurred during system shutdown: {e}", exc_info=True)
            
        finally:
            with self._lock:
                self._is_running = False


# Example usage:
def run_application(cli_args: Optional[List[str]] = None) -> int:
    """
    [Function intent]
    Runs the application with the simplified lifecycle management.
    
    [Implementation details]
    Creates lifecycle manager, starts components, waits for shutdown signal.
    
    [Design principles]
    Simple application entry point with clear lifecycle.
    
    Args:
        cli_args: Optional command-line arguments
        
    Returns:
        int: Exit code (0 for success, non-zero for errors)
    """
    try:
        # Create and start the lifecycle manager
        manager = LifecycleManager(cli_args)
        
        if not manager.start():
            logger.error("Application failed to start")
            return 1
            
        # For interactive applications, wait for shutdown signal
        # For CLI tools, can return immediately after start
        
        # Example: Wait for signal or other shutdown trigger
        try:
            # Replace with appropriate wait mechanism for your app type
            manager._shutdown_event.wait()
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        
        # Shutdown gracefully
        manager.shutdown()
        return 0
        
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        return 1


# Entry point
if __name__ == "__main__":
    sys.exit(run_application(sys.argv[1:]))
