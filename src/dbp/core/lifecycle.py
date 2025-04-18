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
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-18T17:02:00Z : Fixed component registration import mechanism by CodeAssistant
# * Changed relative imports to absolute imports to solve "No module named '.'" errors
# * Updated register_if_enabled to handle absolute imports correctly
# * Improved log messages to show component dependencies for better debugging
# 2025-04-17T17:28:22Z : Standardized log format for consistency by CodeAssistant
# * Ensured log format follows standard: 2025-04-17 17:24:30,221 - dbp.core.lifecycle - <LOGLEVEL> - <message>
# * Verified that _setup_logging is using the centralized formatter from log_utils
# 2025-04-17T17:03:30Z : Updated to use centralized log formatter by CodeAssistant
# * Modified _setup_logging to use MillisecondFormatter from log_utils
# * Added proper handling of milliseconds in log timestamps
# 2025-04-15T09:49:00Z : Initial creation of LifecycleManager class by CodeAssistant
# * Implemented setup, component registration, start/shutdown methods, and basic signal handling.
###############################################################################

import logging
import signal
import sys
import threading
import traceback
from typing import Optional, List

from .log_utils import setup_application_logging

# Import core components
from .system import ComponentSystem
from .component import Component
from .file_access_component import FileAccessComponent

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

        # Create the simplified component system
        self.system = ComponentSystem(self.config, logger)

        # Register components
        self._register_components()

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

    def _register_components(self) -> None:
        """
        [Function intent]
        Registers all application components directly with the component system.
        Respects component enablement configuration settings.
        
        [Implementation details]
        Creates and registers component instances directly in code.
        Checks enablement status from config before registering each component.
        Uses a registration helper to avoid code duplication.
        
        [Design principles]
        Direct component registration without factories.
        Clear error reporting for registration failures.
        Selective component registration based on configuration.
        DRY (Don't Repeat Yourself) implementation.
        """
        logger.info("Registering components...")
        
        # Get component enablement configuration
        try:
            enabled_config = self.config_manager.get('component_enabled', False) if self.config_manager else {}
            logger.info(f"Using component enablement configuration")
        except Exception as e:
            logger.warning(f"Failed to get component enablement configuration: {e}, using defaults")
            enabled_config = {}
        
        # Helper function to check if component is enabled
        def is_component_enabled(name):
            if not isinstance(enabled_config, dict):
                return True  # Default to enabled if config is invalid
            return enabled_config.get(name, True)  # Default to enabled if not specified
        
        # Helper function to register a component if it's enabled
        def register_if_enabled(component_name, import_path, component_class, info=None):
            if not is_component_enabled(component_name):
                logger.info(f"Component '{component_name}' disabled by configuration")
                return False
                
            try:
                # Use absolute imports instead of relative imports
                import_path = import_path.replace("..", "dbp")
                module = __import__(import_path, fromlist=[component_class])
                component = getattr(module, component_class)()
                self.system.register(component)
                logger.info(f"Registered component: '{component_name}' with dependencies: {component.dependencies}")
                return True
            except ImportError as e:
                logger.error(f"Failed to register {component_name} component: {e}")
                return False
            except Exception as e:
                logger.error(f"Failed to register {component_name} component: {e}")
                return False
        
        # Register config manager component if available (always enabled as it's required)
        if ConfigManagerComponent and self.config_manager:
            self.system.register(ConfigManagerComponent(self.config_manager))
            logger.info(f"Registered component: 'config_manager' with dependencies: []")
        
        # Register all other components using the helper function
        register_if_enabled("file_access", "dbp.core.file_access_component", "FileAccessComponent")
        register_if_enabled("database", "dbp.database.database", "DatabaseComponent")
        register_if_enabled("fs_monitor", "dbp.fs_monitor.component", "FileSystemMonitorComponent")
        register_if_enabled("filter", "dbp.fs_monitor.filter", "FilterComponent")
        register_if_enabled("change_queue", "dbp.fs_monitor.queue", "ChangeQueueComponent")
        register_if_enabled("memory_cache", "dbp.memory_cache.component", "MemoryCacheComponent")
        register_if_enabled("consistency_analysis", "dbp.consistency_analysis.component", "ConsistencyAnalysisComponent")
        register_if_enabled("doc_relationships", "dbp.doc_relationships.component", "DocRelationshipsComponent")
        register_if_enabled("recommendation_generator", "dbp.recommendation_generator.component", "RecommendationGeneratorComponent")
        register_if_enabled("scheduler", "dbp.scheduler.component", "SchedulerComponent")
        register_if_enabled("metadata_extraction", "dbp.metadata_extraction.component", "MetadataExtractionComponent")
        register_if_enabled("llm_coordinator", "dbp.llm_coordinator.component", "LLMCoordinatorComponent", "Manage query processing")
        register_if_enabled("mcp_server", "dbp.mcp_server.component", "MCPServerComponent")
                

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
