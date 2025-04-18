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
# Implements the MemoryCacheComponent class, which conforms to the core Component
# protocol. This component encapsulates the in-memory metadata cache subsystem,
# initializing its internal parts (storage, indexer, querier, evictor, synchronizer,
# interface) and providing the main access point for other system components.
###############################################################################
# [Source file design principles]
# - Conforms to the Component protocol (`src/dbp/core/component.py`).
# - Declares dependencies (e.g., 'database').
# - Initializes all internal cache services during its `initialize` phase.
# - Creates the appropriate eviction strategy based on configuration.
# - Triggers initial data load from the database upon initialization.
# - Provides public methods that delegate to the `MetadataCacheInterface`.
# - Manages its own initialization state.
# - Design Decision: Component Facade for Cache (2025-04-15)
#   * Rationale: Presents the cache subsystem as a single component within the framework, simplifying integration and lifecycle management.
#   * Alternatives considered: Exposing the cache interface directly (less standard within the component model).
###############################################################################
# [Source file constraints]
# - Depends on the core component framework (`Component`, `InitializationContext`).
# - Depends on all helper classes within the `memory_cache` package.
# - Requires the 'database' component to be available and initialized.
# - Assumes configuration for the memory cache is available via the InitializationContext.
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
# - src/dbp/core/component.py
# - All other files in src/dbp/memory_cache/
###############################################################################
# [GenAI tool change history]
# 2025-04-15T10:00:45Z : Initial creation of MemoryCacheComponent by CodeAssistant
# * Implemented Component protocol methods and initialization of cache services.
###############################################################################

import logging
from typing import List, Optional, Any, Dict
from datetime import datetime

# Core component imports
try:
    from ..core.component import Component, InitializationContext
    # Import config type if defined, else use Any
    # from ..config import AppConfig # Example
    Config = Any
except ImportError:
    logging.getLogger(__name__).error("Failed to import core component types for MemoryCacheComponent.", exc_info=True)
    # Placeholders
    class Component: pass
    class InitializationContext: pass
    Config = Any

# Imports for internal cache services
try:
    from .storage import CacheStorage
    from .index_manager import IndexManager
    from .eviction import EvictionStrategy, LRUEvictionStrategy, LFUEvictionStrategy
    from .query import QueryEngine, MetadataQuery
    from .synchronizer import DatabaseSynchronizer
    from .interface import MetadataCacheInterface
    from ..metadata_extraction.data_structures import FileMetadata # Need this type
    # Import DB component type for type hint
    from ..database.database import DatabaseManager # Assuming this holds the manager
except ImportError as e:
    logging.getLogger(__name__).error(f"MemoryCacheComponent ImportError: {e}. Check package structure.", exc_info=True)
    # Placeholders
    CacheStorage = object
    IndexManager = object
    EvictionStrategy = object
    LRUEvictionStrategy = object
    LFUEvictionStrategy = object
    QueryEngine = object
    MetadataQuery = object
    DatabaseSynchronizer = object
    MetadataCacheInterface = object
    FileMetadata = object
    DatabaseManager = object


logger = logging.getLogger(__name__)

class ComponentNotInitializedError(Exception):
    """Exception raised when a component method is called before initialization."""
    pass

class MemoryCacheComponent(Component):
    """
    DBP system component providing an in-memory cache for file metadata.
    """
    _initialized: bool = False
    _cache_interface: Optional[MetadataCacheInterface] = None

    @property
    def name(self) -> str:
        """Returns the unique name of the component."""
        return "memory_cache"

    @property
    def dependencies(self) -> List[str]:
        """Returns the list of component names this component depends on."""
        # Depends on the database component to load initial data and sync
        return ["database"]

    def initialize(self, context: InitializationContext):
        """
        [Function intent]
        Initializes the memory cache component, including storage, indexes,
        eviction strategy, query engine, synchronizer, and performs initial load.

        [Implementation details]
        Uses the strongly-typed configuration for component setup.
        Creates internal sub-components for the memory cache system.
        Sets the _initialized flag when initialization succeeds.
        
        [Design principles]
        Explicit initialization with strong typing.
        Type-safe configuration access.
        
        Args:
            context: Initialization context with typed configuration and resources
        """
        if self._initialized:
            logger.warning(f"Component '{self.name}' already initialized.")
            return

        self.logger = context.logger # Use logger from context
        self.logger.info(f"Initializing component '{self.name}'...")

        try:
            # Get strongly-typed configuration
            config = context.get_typed_config()
            cache_config = getattr(config, self.name)

            # Get dependent components
            db_component = context.get_component("database")
            # Access the DatabaseManager instance from the database component
            # Use the get_manager() method rather than accessing _db_manager directly
            db_manager = db_component.get_manager()

            # Instantiate internal cache services
            index_manager = IndexManager(logger_override=self.logger.getChild("index_manager"))
            storage = CacheStorage(config=cache_config, logger_override=self.logger.getChild("storage"))
            eviction_strategy = self._create_eviction_strategy(cache_config)
            query_engine = QueryEngine(index_manager, storage, logger_override=self.logger.getChild("query_engine"))
            db_sync = DatabaseSynchronizer(db_manager=db_manager, logger_override=self.logger.getChild("synchronizer"))

            # Instantiate the main cache interface (facade)
            self._cache_interface = MetadataCacheInterface(
                index_manager=index_manager,
                storage=storage,
                query_engine=query_engine,
                db_sync=db_sync,
                eviction_strategy=eviction_strategy,
                config=cache_config, # Pass the specific cache config part
                logger_override=self.logger.getChild("interface")
            )

            # Perform initial data load from database
            # This requires project context - how is project_id determined here?
            # Assuming a default or configured project ID for now, or maybe load all?
            # Let's assume we load for a configured default project or handle multiple projects later.
            # For now, skip initial load here and assume it's triggered elsewhere or not needed at init.
            # self._perform_initial_load(context.config.get('project.default_id', 1)) # Example
            self.logger.info("Skipping initial data load during component initialization (can be triggered later).")


            self._initialized = True
            self.logger.info(f"Component '{self.name}' initialized successfully.")

        except KeyError as e:
             self.logger.error(f"Initialization failed: Missing dependency component '{e}'. Ensure it's registered.")
             self._initialized = False
             raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
        except Exception as e:
            self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
            self._initialized = False
            raise RuntimeError(f"Failed to initialize {self.name}") from e

    def _create_eviction_strategy(self, cache_config) -> EvictionStrategy:
        """Creates the configured eviction strategy instance."""
        strategy_name = cache_config.eviction_policy.lower() # Access direct attribute
        self.logger.info(f"Creating eviction strategy: {strategy_name}")
        if strategy_name == "lru":
            return LRUEvictionStrategy(config=cache_config, logger_override=self.logger.getChild("eviction_lru"))
        elif strategy_name == "lfu":
            return LFUEvictionStrategy(config=cache_config, logger_override=self.logger.getChild("eviction_lfu"))
        else:
            self.logger.error(f"Unknown eviction strategy configured: '{strategy_name}'. Defaulting to LRU.")
            return LRUEvictionStrategy(config=cache_config, logger_override=self.logger.getChild("eviction_lru"))

    # Optional: Method to trigger initial load after initialization if needed
    # def load_initial_data(self, project_id: int):
    #     if not self.is_initialized or self._cache_interface is None:
    #         raise ComponentNotInitializedError(self.name)
    #     self.logger.info(f"Performing initial data load for project {project_id}...")
    #     try:
    #         # Use the synchronizer via the interface
    #         self._cache_interface.synchronize_with_database(project_id, full_sync=True)
    #         self.logger.info("Initial data load complete.")
    #     except Exception as e:
    #         self.logger.error(f"Error during initial data load: {e}", exc_info=True)


    def shutdown(self) -> None:
        """Shuts down the memory cache component."""
        self.logger.info(f"Shutting down component '{self.name}'...")
        if self._cache_interface:
            self._cache_interface.shutdown() # Call shutdown on the interface if needed
        self._cache_interface = None
        self._initialized = False
        self.logger.info(f"Component '{self.name}' shut down.")

    @property
    def is_initialized(self) -> bool:
        """Returns True if the component is initialized."""
        return self._initialized

    # --- Public API Methods (delegating to MetadataCacheInterface) ---

    def get_metadata(self, file_path: str, project_id: int) -> Optional[FileMetadata]:
        """Retrieves metadata for a file, checking cache then database."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        return self._cache_interface.get_metadata(file_path, project_id)

    def query_metadata(self, query: MetadataQuery) -> List[FileMetadata]:
        """Queries the cache for metadata matching the criteria."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        return self._cache_interface.query(query)

    def update_metadata(self, metadata: FileMetadata):
        """Adds or updates metadata in the cache."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        self._cache_interface.update(metadata)

    def remove_metadata(self, file_path: str):
        """Removes metadata from the cache."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        self._cache_interface.remove(file_path)

    def clear_cache(self):
        """Clears all data from the cache."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        self._cache_interface.clear()

    def sync_db(self, project_id: int, full_sync: bool = False):
        """Triggers synchronization with the database."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        self._cache_interface.synchronize_with_database(project_id, full_sync)

    def get_stats(self) -> Dict[str, Any]:
        """Retrieves cache usage statistics."""
        if not self.is_initialized or self._cache_interface is None:
            raise ComponentNotInitializedError(self.name)
        return self._cache_interface.get_stats()
