# Phase 2: Integration & Component Updates

This document details the integration of the new component registration system with the existing lifecycle manager and updating component implementations to use the new dependency injection approach.

## 1. Update LifecycleManager

File: `src/dbp/core/lifecycle.py`

### Current Implementation Summary

Currently, the LifecycleManager:
- Directly imports component classes
- Manually instantiates components and registers them with the ComponentSystem
- Uses a `register_if_enabled` function to conditionally register components based on configuration
- Component dependencies are defined in each component class's `dependencies` property

### Required Changes

1. Add ComponentRegistry integration:

```python
from .registry import ComponentRegistry

def __init__(self, cli_args: Optional[List[str]] = None):
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

    # Create the component system
    self.system = ComponentSystem(self.config, logger)
    
    # Register components from registry with the system
    self.registry.register_with_system(self.system)

    # Setup signal handling for graceful shutdown
    self._setup_signal_handlers()
```

2. Replace `_register_components` with a new `_register_components_with_registry` method:

```python
def _register_components_with_registry(self) -> None:
    """
    [Function intent]
    Registers all application components with the component registry
    with explicit dependency declarations.
    
    [Implementation details]
    Registers component classes with explicit dependencies.
    Respects component enablement configuration.
    
    [Design principles]
    Centralized component registration with explicit dependencies.
    Selective component registration based on configuration.
    Clear separation between component definition and dependency declaration.
    """
    logger.info("Registering components with registry...")
    
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
    if self.config_manager:
        try:
            from ..config.component import ConfigManagerComponent
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
        except ImportError as e:
            logger.error(f"Failed to import ConfigManagerComponent: {e}")
    
    # Register all other components with explicit dependencies
    # For each component, specify:
    # - Import path
    # - Component class name
    # - Component name (must match what the component's name property returns)
    # - List of dependencies
    
    # Core components
    register_component_class("dbp.core.file_access_component", "FileAccessComponent", "file_access", [])
    
    # Database component
    register_component_class("dbp.database.database", "DatabaseComponent", "database", ["config_manager"])
    
    # File system monitoring components
    register_component_class("dbp.fs_monitor.component", "FileSystemMonitorComponent", "fs_monitor", ["config_manager"])
    register_component_class("dbp.fs_monitor.filter", "FilterComponent", "filter", ["config_manager"])
    register_component_class("dbp.fs_monitor.queue", "ChangeQueueComponent", "change_queue", ["fs_monitor"])
    
    # Memory cache component
    register_component_class("dbp.memory_cache.component", "MemoryCacheComponent", "memory_cache", ["database"])
    
    # Consistency analysis component
    register_component_class(
        "dbp.consistency_analysis.component", 
        "ConsistencyAnalysisComponent", 
        "consistency_analysis", 
        ["database", "doc_relationships", "metadata_extraction"]
    )
    
    # Document relationships component
    register_component_class(
        "dbp.doc_relationships.component", 
        "DocRelationshipsComponent", 
        "doc_relationships", 
        ["database"]
    )
    
    # Recommendation generator component
    register_component_class(
        "dbp.recommendation_generator.component", 
        "RecommendationGeneratorComponent", 
        "recommendation_generator", 
        ["consistency_analysis"]
    )
    
    # Scheduler component
    register_component_class("dbp.scheduler.component", "SchedulerComponent", "scheduler", ["config_manager"])
    
    # Metadata extraction component
    register_component_class(
        "dbp.metadata_extraction.component", 
        "MetadataExtractionComponent", 
        "metadata_extraction", 
        ["database"]
    )
    
    # LLM coordinator component
    register_component_class(
        "dbp.llm_coordinator.component", 
        "LLMCoordinatorComponent", 
        "llm_coordinator", 
        ["config_manager"]
    )
    
    # MCP server component
    register_component_class(
        "dbp.mcp_server.component", 
        "MCPServerComponent", 
        "mcp_server", 
        ["consistency_analysis", "recommendation_generator"]
    )
    
    logger.info(f"Registered {len(self.registry.get_all_component_names())} components with registry")
```

3. Update backward compatibility until all components are migrated:

```python
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
```

## 2. Update Component Implementations

Each component needs to be updated to use the new initialize method signature and dependencies parameter. Here's an example for `MetadataExtractionComponent`:

File: `src/dbp/metadata_extraction/component.py`

```python
def initialize(self, context: InitializationContext, dependencies: Optional[Dict[str, Component]] = None) -> None:
    """
    [Function intent]
    Initializes the metadata extraction component and its internal services.
    
    [Implementation details]
    Uses the strongly-typed configuration for component setup.
    Uses directly injected dependencies if provided, falling back to context.get_component()
    Creates internal sub-components for metadata extraction.
    Sets the _initialized flag when initialization succeeds.
    
    [Design principles]
    Explicit initialization with strong typing.
    Dependency injection for improved performance and testability.
    
    Args:
        context: Initialization context with typed configuration and resources
        dependencies: Optional dictionary of pre-resolved dependencies {name: component_instance}
    """
    if self._initialized:
        logger.warning(f"Component '{self.name}' already initialized.")
        return

    self.logger = context.logger # Use logger from context
    self.logger.info(f"Initializing component '{self.name}'...")

    try:
        # Get strongly-typed configuration
        config = context.get_typed_config()
        component_config = getattr(config, self.name)

        # Get dependent components - use dependencies dict if provided, otherwise fall back to get_component
        if dependencies:
            self.logger.debug("Using injected dependencies")
            db_component = self.get_dependency(dependencies, "database")
        else:
            self.logger.debug("Using context.get_component() to fetch dependencies")
            db_component = context.get_component("database")
            
            if not db_component:
                raise KeyError("Required dependency 'database' not found")

        # Get database manager using the method
        db_manager = db_component.get_manager()

        # Instantiate internal services, passing relevant config parts
        prompt_manager = LLMPromptManager(config=context.config, logger_override=self.logger.getChild("prompts"))
        bedrock_client = BedrockClient(config=context.config, logger_override=self.logger.getChild("bedrock"))
        response_parser = ResponseParser(logger_override=self.logger.getChild("parser"))
        result_processor = ExtractionResultProcessor(logger_override=self.logger.getChild("processor"))
        db_writer = DatabaseWriter(db_manager=db_manager, logger_override=self.logger.getChild("db_writer"))

        # Instantiate the main service
        self._service = MetadataExtractionService(
            prompt_manager=prompt_manager,
            bedrock_client=bedrock_client,
            response_parser=response_parser,
            result_processor=result_processor,
            db_writer=db_writer,
            config=component_config, 
            logger_override=self.logger.getChild("service")
        )

        self._initialized = True
        self.logger.info(f"Component '{self.name}' initialized successfully.")

    except KeyError as e:
         self.logger.error(f"Initialization failed: Missing dependency '{e}'. Ensure it's registered.")
         self._initialized = False
         raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
    except Exception as e:
        self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
        self._initialized = False
        # Re-raise the exception to signal failure to the orchestrator
        raise RuntimeError(f"Failed to initialize {self.name}") from e
```

Similar updates will be needed for other component implementations:

### ConsistencyAnalysisComponent Example:

File: `src/dbp/consistency_analysis/component.py`

```python
def initialize(self, context: InitializationContext, dependencies: Optional[Dict[str, Component]] = None) -> None:
    """
    [Function intent]
    Initializes the Consistency Analysis component and its sub-components.
    
    [Implementation details]
    Uses the strongly-typed configuration for component setup.
    Uses directly injected dependencies if provided, falling back to context.get_component()
    Creates internal sub-components and registers consistency analyzers.
    Sets the _initialized flag when initialization succeeds.
    
    [Design principles]
    Explicit initialization with strong typing.
    Dependency injection for improved performance and testability.
    
    Args:
        context: Initialization context with typed configuration and resources
        dependencies: Optional dictionary of pre-resolved dependencies {name: component_instance}
    """
    if self._initialized:
        logger.warning(f"Component '{self.name}' already initialized.")
        return

    self.logger = context.logger # Use logger from context
    self.logger.info(f"Initializing component '{self.name}'...")

    try:
        # Get strongly-typed configuration
        config = context.get_typed_config()
        component_config = getattr(config, self.name)

        # Get dependent components - use dependencies dict if provided, otherwise fall back to get_component
        if dependencies:
            self.logger.debug("Using injected dependencies")
            db_component = self.get_dependency(dependencies, "database")
            doc_relationships_component = self.get_dependency(dependencies, "doc_relationships")
            metadata_extraction_component = self.get_dependency(dependencies, "metadata_extraction")
        else:
            self.logger.debug("Using context.get_component() to fetch dependencies")
            db_component = context.get_component("database")
            doc_relationships_component = context.get_component("doc_relationships")
            metadata_extraction_component = context.get_component("metadata_extraction")
            
            # Validate dependencies are available
            if not db_component:
                raise KeyError("Required dependency 'database' not found")
            if not doc_relationships_component:
                raise KeyError("Required dependency 'doc_relationships' not found")
            if not metadata_extraction_component:
                raise KeyError("Required dependency 'metadata_extraction' not found")

        # Get database manager using the method instead of accessing attribute
        db_manager = db_component.get_manager()

        # Instantiate sub-components
        self._repository = InconsistencyRepository(db_manager=db_manager, logger_override=self.logger.getChild("repository"))
        self._registry = AnalysisRegistry(logger_override=self.logger.getChild("registry"))
        self._engine = RuleEngine(analysis_registry=self._registry, logger_override=self.logger.getChild("engine"))
        self._impact_analyzer = ConsistencyImpactAnalyzer(doc_relationships_component=doc_relationships_component, logger_override=self.logger.getChild("impact"))
        self._report_generator = ReportGenerator(logger_override=self.logger.getChild("reporter"))

        # Register all available analyzers
        self._register_analyzers(metadata_extraction_component, doc_relationships_component)

        self._initialized = True
        self.logger.info(f"Component '{self.name}' initialized successfully.")

    except KeyError as e:
         self.logger.error(f"Initialization failed: Missing dependency '{e}'. Ensure it's registered.")
         self._initialized = False
         raise RuntimeError(f"Missing dependency during {self.name} initialization: {e}") from e
    except Exception as e:
        self.logger.error(f"Initialization failed for component '{self.name}': {e}", exc_info=True)
        self._initialized = False
        raise RuntimeError(f"Failed to initialize {self.name}") from e
```

## Component Update Procedure

For each component, apply this update procedure:

1. Update the `initialize` method to accept the new parameters
2. Modify the dependency retrieval code:
   - Check for direct dependency injection
   - Fall back to context.get_component() for compatibility
3. Use the Component base class's `get_dependency` helper method for safer access
4. Keep the dependencies property for backward compatibility during migration

### Components to Update

Here's a list of all components that need to be updated:

1. ConfigManagerComponent (src/dbp/config/component.py)
2. DatabaseComponent (src/dbp/database/database.py)
3. FileSystemMonitorComponent (src/dbp/fs_monitor/component.py)
4. FilterComponent (src/dbp/fs_monitor/filter.py)
5. ChangeQueueComponent (src/dbp/fs_monitor/queue.py)
6. MemoryCacheComponent (src/dbp/memory_cache/component.py)
7. ConsistencyAnalysisComponent (src/dbp/consistency_analysis/component.py)
8. DocRelationshipsComponent (src/dbp/doc_relationships/component.py)
9. RecommendationGeneratorComponent (src/dbp/recommendation_generator/component.py)
10. SchedulerComponent (src/dbp/scheduler/component.py)
11. MetadataExtractionComponent (src/dbp/metadata_extraction/component.py)
12. LLMCoordinatorComponent (src/dbp/llm_coordinator/component.py)
13. MCPServerComponent (src/dbp/mcp_server/component.py)
14. FileAccessComponent (src/dbp/core/file_access_component.py)

## Benefits of This Approach

1. **Gradual Migration**: Components can be updated one at a time
2. **Backward Compatibility**: Old components will still work during the transition
3. **Clear Dependency Management**: Component dependencies are explicitly declared in one place
4. **Improved Initialization**: Components receive their dependencies directly
5. **Better Testability**: Direct dependency injection makes components more testable

## Implementation Timeline

1. First update the core components:
   - ConfigManagerComponent
   - FileAccessComponent
   - DatabaseComponent

2. Then update the foundational system components:
   - FileSystemMonitorComponent
   - MemoryCacheComponent
   - SchedulerComponent

3. Finally update the higher-level components:
   - MetadataExtractionComponent
   - ConsistencyAnalysisComponent
   - DocRelationshipsComponent
   - RecommendationGeneratorComponent
   - LLMCoordinatorComponent
   - MCPServerComponent

## Testing Recommendations

1. After each component update, verify initialization still works
2. Ensure that components can access their dependencies through both methods
3. Test edge cases like missing dependencies
4. Verify that components with circular dependencies are detected properly
5. Test initialization order to ensure dependencies are initialized before dependents
