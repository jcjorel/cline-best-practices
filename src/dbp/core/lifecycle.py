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
# Implements the LifecycleManager class, which serves as the main entry point
# and control center for the DBP application's lifecycle. It initializes core
# services like logging and configuration, registers all system components,
# and uses the InitializationOrchestrator to manage the startup and shutdown sequences.
###############################################################################
# [Source file design principles]
# - Provides a high-level interface (`start`, `shutdown`) for managing the application.
# - Encapsulates the setup of essential services (logging, config).
# - Responsible for registering all known system components with the registry.
# - Delegates the actual initialization/shutdown process to the orchestrator.
# - Includes basic signal handling for graceful shutdown on termination signals.
# - Design Decision: Central Lifecycle Manager (2025-04-15)
#   * Rationale: Creates a single, clear entry point for the application, simplifying deployment and management.
#   * Alternatives considered: Managing lifecycle directly in the main script (less organized).
###############################################################################
# [Source file constraints]
# - Requires access to configuration management (`ConfigurationManager`).
# - Requires component registry and orchestrator (`ComponentRegistry`, `InitializationOrchestrator`).
# - Assumes the existence of concrete component classes or factories to register.
# - Signal handling might behave differently across operating systems.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - scratchpad/dbp_implementation_plan/plan_component_init.md
# - src/dbp/core/registry.py
# - src/dbp/core/orchestrator.py
###############################################################################
# [GenAI tool change history]
# 2025-04-15T09:49:00Z : Initial creation of LifecycleManager class by CodeAssistant
# * Implemented setup, component registration, start/shutdown methods, and basic signal handling.
###############################################################################

import logging
import signal
import sys
import threading
from typing import Optional, List, Type

# Assuming core components are accessible
try:
    from .registry import ComponentRegistry
    from .orchestrator import InitializationOrchestrator
    # Assuming config manager is in a sibling package 'config'
    from ..config import ConfigurationManager, AppConfig
    # Import component implementations (or factories) - adjust paths as needed
    # These imports might need to be more dynamic or centralized if components live elsewhere
    from ..database.database import DatabaseManager # Example concrete dependency
    # Add imports for other component classes/factories here
    # from ..fs_monitor import FileSystemMonitorFactory # Example
    # ... other component imports
except ImportError as e:
    logging.basicConfig(level=logging.WARNING) # Basic logging for import errors
    logger = logging.getLogger(__name__)
    logger.error(f"LifecycleManager ImportError: {e}. Check package structure and dependencies.", exc_info=True)
    # Define placeholders if imports fail, to allow class definition
    ComponentRegistry = object
    InitializationOrchestrator = object
    ConfigurationManager = object
    AppConfig = object
    DatabaseManager = object # Placeholder
    # FileSystemMonitorFactory = object # Placeholder


logger = logging.getLogger(__name__)

# --- Placeholder Component Implementations ---
# Replace these with actual imports or implementations of your components
# These need to conform to the Component protocol defined in component.py

class PlaceholderComponent:
     """ Placeholder for actual system components. """
     _is_initialized = False
     def __init__(self, name: str, dependencies: List[str] = None):
          self._name = name
          self._dependencies = dependencies or []
          self.logger = logging.getLogger(f"component.{self._name}")

     @property
     def name(self) -> str: return self._name
     @property
     def dependencies(self) -> List[str]: return self._dependencies
     def initialize(self, context) -> None:
          self.logger.info(f"Initializing placeholder component: {self.name}")
          # Simulate using context
          _ = context.config
          _ = context.component_registry
          if self.dependencies:
               for dep_name in self.dependencies:
                    try:
                         dep_comp = context.get_component(dep_name)
                         self.logger.debug(f"Accessed dependency '{dep_name}': {type(dep_comp).__name__}")
                    except KeyError:
                         self.logger.error(f"Missing dependency '{dep_name}' during initialization of '{self.name}'")
                         raise RuntimeError(f"Missing dependency: {dep_name}")
          self._is_initialized = True
          self.logger.info(f"Placeholder component initialized: {self.name}")
     def shutdown(self) -> None:
          self.logger.info(f"Shutting down placeholder component: {self.name}")
          self._is_initialized = False
     @property
     def is_initialized(self) -> bool: return self._is_initialized

# --- End Placeholder Components ---


class LifecycleManager:
    """
    Manages the overall lifecycle (startup, shutdown) of the DBP application,
    orchestrating the initialization and termination of its components.
    """

    def __init__(self, cli_args: Optional[List[str]] = None):
        """
        Initializes the LifecycleManager.

        Args:
            cli_args: Optional list of command-line arguments passed to the application.
        """
        self._shutdown_event = threading.Event()
        self._lock = threading.RLock()
        self._is_running = False

        # Initialize essential services first
        self.logger = self._setup_logger() # Setup logging ASAP
        self.config_manager = self._load_config(cli_args)
        self.config: AppConfig = self.config_manager._config # Get validated config

        # Initialize core lifecycle components
        self.registry = ComponentRegistry()
        self.orchestrator = InitializationOrchestrator(self.registry, self.config, self.logger)

        # Register components (factories preferred for lazy loading)
        self._register_components()

        # Setup signal handling for graceful shutdown
        self._setup_signal_handlers()

    def _setup_logger(self) -> logging.Logger:
        """Sets up and configures the root logger for the application."""
        # Basic configuration, replace with more robust setup if needed
        log_level_str = os.environ.get("DBP_LOG_LEVEL", "INFO").upper()
        log_level = getattr(logging, log_level_str, logging.INFO)
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Configure specific loggers if necessary
        # logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        return logging.getLogger("DBP_LifecycleManager") # Return a specific logger

    def _load_config(self, cli_args: Optional[List[str]]) -> ConfigurationManager:
        """Loads application configuration using the ConfigurationManager."""
        self.logger.info("Loading application configuration...")
        try:
            # Use the singleton instance
            config_manager = ConfigurationManager()
            # Pass CLI args during initialization
            config_manager.initialize(args=cli_args) # Assuming project_root comes from config or later step
            return config_manager
        except Exception as e:
            self.logger.critical(f"Failed to load configuration: {e}. Application cannot start.", exc_info=True)
            sys.exit(1) # Exit if config fails critically

    def _register_components(self):
        """Registers all known system components with the ComponentRegistry."""
        self.logger.info("Registering system components...")
        try:
            # Register factories for lazy instantiation
            # Replace Placeholders with actual component classes/factories
            self.registry.register_factory("database", lambda: PlaceholderComponent("database"))
            self.registry.register_factory("config_manager_comp", lambda: PlaceholderComponent("config_manager_comp", dependencies=[])) # Example if config manager itself is a component
            self.registry.register_factory("fs_monitor", lambda: PlaceholderComponent("fs_monitor", dependencies=["config_manager_comp"]))
            self.registry.register_factory("change_queue", lambda: PlaceholderComponent("change_queue", dependencies=["config_manager_comp"]))
            self.registry.register_factory("filter", lambda: PlaceholderComponent("filter", dependencies=["config_manager_comp"]))
            self.registry.register_factory("background_scheduler", lambda: PlaceholderComponent("background_scheduler", dependencies=["change_queue", "filter"]))
            self.registry.register_factory("metadata_extraction", lambda: PlaceholderComponent("metadata_extraction", dependencies=["database", "llm_coordinator"])) # Example dependency
            self.registry.register_factory("memory_cache", lambda: PlaceholderComponent("memory_cache", dependencies=["database"]))
            self.registry.register_factory("consistency_analyzer", lambda: PlaceholderComponent("consistency_analyzer", dependencies=["database", "memory_cache"]))
            self.registry.register_factory("recommendation_generator", lambda: PlaceholderComponent("recommendation_generator", dependencies=["consistency_analyzer", "llm_coordinator"]))
            self.registry.register_factory("llm_coordinator", lambda: PlaceholderComponent("llm_coordinator", dependencies=["config_manager_comp"])) # Example
            self.registry.register_factory("mcp_server", lambda: PlaceholderComponent("mcp_server", dependencies=["llm_coordinator", "database"])) # Example

            # Add other components as defined in the architecture
            self.logger.info(f"Registered components: {self.registry.get_all_names()}")

        except Exception as e:
            self.logger.critical(f"Failed to register components: {e}. Application cannot start.", exc_info=True)
            sys.exit(1)

    def _setup_signal_handlers(self):
        """Sets up handlers for termination signals (SIGINT, SIGTERM)."""
        signals_to_handle = [signal.SIGINT, signal.SIGTERM]
        for sig in signals_to_handle:
            try:
                signal.signal(sig, self._handle_shutdown_signal)
                self.logger.debug(f"Registered shutdown handler for signal {sig}.")
            except ValueError:
                 # May happen if run in an environment where signals can't be set (e.g., some Windows setups)
                 self.logger.warning(f"Could not register handler for signal {sig}. Graceful shutdown via signals might not work.")
            except Exception as e:
                 self.logger.error(f"Error registering signal handler for {sig}: {e}", exc_info=True)


    def _handle_shutdown_signal(self, signum, frame):
        """Signal handler function to initiate graceful shutdown."""
        signal_name = signal.Signals(signum).name
        self.logger.warning(f"Received signal {signal_name} ({signum}). Initiating graceful shutdown...")
        # Use the shutdown event to signal the main loop (if any) or trigger shutdown directly
        self.shutdown()
        # Optionally, re-raise the signal if needed for parent processes
        # signal.signal(signum, signal.SIG_DFL)
        # os.kill(os.getpid(), signum)
        sys.exit(0) # Exit after shutdown attempt


    def start(self):
        """
        Starts the application: initializes all components in the correct order.
        This method blocks if the application runs a main loop, or returns after init.
        """
        with self._lock:
            if self._is_running:
                 logger.warning("Application is already running.")
                 return
            self._is_running = True

        try:
            self.logger.info("Starting Documentation-Based Programming system...")
            # Initialize components via the orchestrator
            success = self.orchestrator.initialize_all()

            if success:
                self.logger.info("System startup complete. Application is running.")
                # If this were a long-running server, start the main loop here.
                # For a CLI or batch tool, startup might be all that's needed.
                # Example: Keep running until shutdown signal
                # while not self._shutdown_event.is_set():
                #     time.sleep(1)
                # self.logger.info("Shutdown signal received, exiting main loop.")

            else:
                 self.logger.error("System startup failed due to component initialization errors.")
                 self._is_running = False # Mark as not running on failed start
                 # Shutdown might have already been called by orchestrator's rollback
                 # self.shutdown() # Ensure shutdown is called if rollback didn't happen
                 sys.exit(1) # Exit with error code

        except (CircularDependencyError, RuntimeError, Exception) as e:
            self.logger.critical(f"A critical error occurred during system startup: {e}", exc_info=True)
            self._is_running = False
            # Attempt shutdown even on critical error during startup
            self.shutdown()
            sys.exit(1)
        # except KeyboardInterrupt:
        #      self.logger.warning("Keyboard interrupt received during startup.")
        #      self.shutdown()
        #      sys.exit(1)


    def shutdown(self):
        """
        Shuts down the application gracefully by terminating components
        in the reverse order of initialization.
        """
        with self._lock:
             if not self._is_running and not self.orchestrator._initialized_components:
                  logger.info("Application not running or no components initialized, shutdown not needed.")
                  return
             logger.info("Initiating system shutdown...")
             self._shutdown_event.set() # Signal any waiting loops

        # Perform shutdown via the orchestrator
        try:
            self.orchestrator.shutdown_all()
            self.logger.info("System shutdown complete.")
        except Exception as e:
            self.logger.error(f"An error occurred during system shutdown: {e}", exc_info=True)
        finally:
             self._is_running = False


# Example of how to run the application
# if __name__ == "__main__":
#     # Pass command line arguments (excluding script name)
#     lifecycle_manager = LifecycleManager(cli_args=sys.argv[1:])
#     try:
#         lifecycle_manager.start()
#         # If start() doesn't block, potentially wait here or do other work
#         # For example, wait indefinitely until shutdown signal
#         print("Application started. Press Ctrl+C to exit.")
#         while True:
#              time.sleep(3600) # Sleep for a long time, waiting for signals
#     except KeyboardInterrupt:
#          print("\nCtrl+C detected. Shutting down...")
#          lifecycle_manager.shutdown()
#     except Exception as e:
#          print(f"\nApplication exited due to error: {e}")
#          # Shutdown might have already been called in start() on error
#          # lifecycle_manager.shutdown() # Ensure shutdown happens
#          sys.exit(1)
#     finally:
#          print("Application finished.")
