# Memory Cache Implementation Plan

## Overview

This document outlines the implementation plan for the Memory Cache component, which provides a fast, in-memory representation of metadata for efficient access by other components in the Documentation-Based Programming system.

## Documentation Context

This implementation is based on the following documentation:
- [DESIGN.md](../../doc/DESIGN.md) - Documentation Monitoring section
- [DATA_MODEL.md](../../doc/DATA_MODEL.md) - Database Implementation section
- [SECURITY.md](../../doc/SECURITY.md) - Security considerations
- [design/BACKGROUND_TASK_SCHEDULER.md](../../doc/design/BACKGROUND_TASK_SCHEDULER.md) - In-Memory Metadata Cache

## Requirements

The Memory Cache component must:
1. Provide fast, thread-safe access to frequently used metadata
2. Implement efficient data structures for quick lookups
3. Maintain consistency with the database through synchronization
4. Implement cache invalidation strategies
5. Balance memory usage with access performance
6. Prevent memory leaks and manage resource usage
7. Support querying by various keys (path, language, etc.)
8. Adhere to all security principles defined in SECURITY.md

## Design

### Architecture Overview

The Memory Cache component follows a multi-layered caching architecture:

```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│                     │      │                     │      │                     │
│ Metadata Cache      │─────▶│  Index Manager     │─────▶│   Cache Storage     │
│   Interface         │      │                     │      │                     │
└─────────────────────┘      └─────────────────────┘      └─────────────────────┘
          │                                                        │
          │                                                        │
          ▼                                                        ▼
┌─────────────────────┐                                 ┌─────────────────────┐
│                     │                                 │                     │
│  Query Engine       │◀────────────────────────────────│  Eviction Strategy  │
│                     │                                 │                     │
└─────────────────────┘                                 └─────────────────────┘
          │
          │
          ▼
┌─────────────────────┐
│                     │
│ Database Sync       │
│                     │
└─────────────────────┘
```

### Core Classes and Interfaces

1. **MemoryCacheComponent**

```python
class MemoryCacheComponent(Component):
    """Component providing in-memory caching of metadata."""
    
    @property
    def name(self) -> str:
        return "memory_cache"
    
    @property
    def dependencies(self) -> list[str]:
        return ["database"]
    
    def initialize(self, context: InitializationContext) -> None:
        """Initialize the memory cache component."""
        self.config = context.config.memory_cache
        self.logger = context.logger.get_child("memory_cache")
        self.db_component = context.get_component("database")
        
        # Create cache managers
        self.index_manager = IndexManager(self.logger)
        self.storage = CacheStorage(self.config, self.logger)
        self.eviction_strategy = self._create_eviction_strategy()
        self.query_engine = QueryEngine(self.index_manager, self.storage, self.logger)
        self.db_sync = DatabaseSynchronizer(self.db_component, self.logger)
        
        # Initialize the cache interface
        self.cache_interface = MetadataCacheInterface(
            index_manager=self.index_manager,
            storage=self.storage,
            query_engine=self.query_engine,
            db_sync=self.db_sync,
            eviction_strategy=self.eviction_strategy,
            config=self.config,
            logger=self.logger
        )
        
        # Initial loading of data from database
        self._perform_initial_load()
        
        self._initialized = True
    
    def _create_eviction_strategy(self) -> EvictionStrategy:
        """Create the appropriate eviction strategy based on configuration."""
        strategy_name = self.config.eviction_strategy
        if strategy_name == "lru":
            return LRUEvictionStrategy(self.config, self.logger)
        elif strategy_name == "lfu":
            return LFUEvictionStrategy(self.config, self.logger)
        else:
            raise ValueError(f"Unknown eviction strategy: {strategy_name}")
    
    def _perform_initial_load(self) -> None:
        """Perform initial loading of data from database."""
        self.logger.info("Starting initial metadata load from database")
        try:
            self.db_sync.perform_full_sync()
            self.logger.info("Initial metadata load complete")
        except Exception as e:
            self.logger.error(f"Error during initial metadata load: {e}")
            # Continue with empty cache rather than failing initialization
    
    def get_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """
        Get metadata for a file from the cache.
        
        Args:
            file_path: Path to the file
        
        Returns:
            FileMetadata object or None if not found
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.cache_interface.get_metadata(file_path)
    
    def get_metadata_by_query(self, query: MetadataQuery) -> List[FileMetadata]:
        """
        Query for metadata based on various criteria.
        
        Args:
            query: Query parameters
        
        Returns:
            List of matching FileMetadata objects
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.cache_interface.query(query)
    
    def update_metadata(self, metadata: FileMetadata) -> None:
        """
        Update or add metadata to the cache.
        
        Args:
            metadata: FileMetadata object to update
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.cache_interface.update(metadata)
    
    def remove_metadata(self, file_path: str) -> None:
        """
        Remove metadata for a file from the cache.
        
        Args:
            file_path: Path to the file to remove
        """
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.cache_interface.remove(file_path)
    
    def clear_cache(self) -> None:
        """Clear all metadata from the cache."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.cache_interface.clear()
    
    def synchronize_with_database(self) -> None:
        """Synchronize the cache with the database."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        self.cache_interface.sync_with_database()
    
    def shutdown(self) -> None:
        """Shutdown the component gracefully."""
        self.logger.info("Shutting down memory cache component")
        if hasattr(self, 'cache_interface'):
            self.cache_interface.shutdown()
    
    @property
    def is_initialized(self) -> bool:
        return self._initialized
    
    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        if not self._initialized:
            raise ComponentNotInitializedError(self.name)
        
        return self.cache_interface.get_stats()
```

2. **MetadataCacheInterface**

```python
class MetadataCacheInterface:
    """Main interface for the metadata cache."""
    
    def __init__(
        self,
        index_manager: IndexManager,
        storage: CacheStorage,
        query_engine: QueryEngine,
        db_sync: DatabaseSynchronizer,
        eviction_strategy: EvictionStrategy,
        config: MemoryCacheConfig,
        logger: Logger
    ):
        self.index_manager = index_manager
        self.storage = storage
        self.query_engine = query_engine
        self.db_sync = db_sync
        self.eviction_strategy = eviction_strategy
        self.config = config
        self.logger = logger
        self._lock = threading.RLock()
        
        # Statistics tracking
        self._stats = {
            "hits": 0,
            "misses": 0,
            "updates": 0,
            "removals": 0,
            "evictions": 0,
            "last_sync": None,
            "items_count": 0,
        }
    
    def get_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """Get metadata for a specific file path."""
        with self._lock:
            # Check if in cache
            metadata = self.storage.get(file_path)
            
            if metadata:
                # Cache hit
                self._stats["hits"] += 1
                self.eviction_strategy.record_access(file_path)
                return metadata
            else:
                # Cache miss
                self._stats["misses"] += 1
                
                # Try to load from database
                metadata = self.db_sync.get_metadata_from_db(file_path)
                
                if metadata:
                    # Store in cache for future use
                    self._store_metadata(metadata)
                
                return metadata
    
    def query(self, query: MetadataQuery) -> List[FileMetadata]:
        """Query metadata based on various criteria."""
        with self._lock:
            return self.query_engine.execute_query(query)
    
    def update(self, metadata: FileMetadata) -> None:
        """Update or add metadata to the cache."""
        with self._lock:
            self._stats["updates"] += 1
            self._store_metadata(metadata)
    
    def remove(self, file_path: str) -> None:
        """Remove metadata for a file from the cache."""
        with self._lock:
            if self.storage.contains(file_path):
                self.storage.remove(file_path)
                self.index_manager.remove_from_indexes(file_path)
                self._stats["removals"] += 1
                self._stats["items_count"] = self.storage.count()
    
    def clear(self) -> None:
        """Clear all metadata from the cache."""
        with self._lock:
            self.storage.clear()
            self.index_manager.clear_indexes()
            self._stats["items_count"] = 0
            self.logger.info("Cache cleared")
    
    def sync_with_database(self) -> None:
        """Synchronize the cache with the database."""
        with self._lock:
            try:
                self.db_sync.perform_incremental_sync(self.storage, self.index_manager)
                self._stats["last_sync"] = datetime.now()
                self._stats["items_count"] = self.storage.count()
                self.logger.debug("Cache synchronized with database")
            except Exception as e:
                self.logger.error(f"Error during cache synchronization: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            return self._stats.copy()
    
    def _store_metadata(self, metadata: FileMetadata) -> None:
        """Store metadata in the cache, handling eviction if needed."""
        # Check if we need to evict items
        if self.storage.count() >= self.config.max_items:
            evicted_paths = self.eviction_strategy.select_for_eviction(
                count=max(1, self.config.eviction_batch_size)
            )
            
            for path in evicted_paths:
                self.storage.remove(path)
                self.index_manager.remove_from_indexes(path)
                self._stats["evictions"] += 1
        
        # Store the new item
        self.storage.put(metadata.path, metadata)
        self.index_manager.index_metadata(metadata)
        self._stats["items_count"] = self.storage.count()
        self.eviction_strategy.record_access(metadata.path)
    
    def shutdown(self) -> None:
        """Shutdown the cache interface."""
        with self._lock:
            # Nothing specific to clean up
            pass
```

3. **IndexManager**

```python
class IndexManager:
    """Manages indexes for different metadata attributes."""
    
    def __init__(self, logger: Logger):
        self.logger = logger
        self._lock = threading.RLock()
        
        # Primary index by path
        self._path_index: Dict[str, str] = {}
        
        # Secondary indexes
        self._language_index: Dict[str, Set[str]] = {}  # language -> set of paths
        self._reference_doc_index: Dict[str, Set[str]] = {}  # doc path -> set of referencing paths
        self._function_index: Dict[str, Set[str]] = {}  # function name -> set of paths
        self._class_index: Dict[str, Set[str]] = {}  # class name -> set of paths
    
    def index_metadata(self, metadata: FileMetadata) -> None:
        """
        Index a metadata object by various attributes.
        
        Args:
            metadata: FileMetadata object to index
        """
        with self._lock:
            path = metadata.path
            
            # Add to path index
            self._path_index[path] = path
            
            # Add to language index
            language = metadata.language
            if language not in self._language_index:
                self._language_index[language] = set()
            self._language_index[language].add(path)
            
            # Add to reference doc index
            for ref_doc in metadata.header_sections.reference_documentation:
                if ref_doc not in self._reference_doc_index:
                    self._reference_doc_index[ref_doc] = set()
                self._reference_doc_index[ref_doc].add(path)
            
            # Add to function index
            for func in metadata.functions:
                if func.name not in self._function_index:
                    self._function_index[func.name] = set()
                self._function_index[func.name].add(path)
            
            # Add to class index
            for cls in metadata.classes:
                if cls.name not in self._class_index:
                    self._class_index[cls.name] = set()
                self._class_index[cls.name].add(path)
    
    def remove_from_indexes(self, path: str) -> None:
        """
        Remove a path from all indexes.
        
        Args:
            path: Path to remove
        """
        with self._lock:
            # Remove from path index
            if path in self._path_index:
                del self._path_index[path]
            
            # Remove from language index
            for language_paths in self._language_index.values():
                language_paths.discard(path)
            
            # Remove from reference doc index
            for ref_doc_paths in self._reference_doc_index.values():
                ref_doc_paths.discard(path)
            
            # Remove from function index
            for func_paths in self._function_index.values():
                func_paths.discard(path)
            
            # Remove from class index
            for cls_paths in self._class_index.values():
                cls_paths.discard(path)
    
    def clear_indexes(self) -> None:
        """Clear all indexes."""
        with self._lock:
            self._path_index.clear()
            self._language_index.clear()
            self._reference_doc_index.clear()
            self._function_index.clear()
            self._class_index.clear()
    
    def get_paths_by_language(self, language: str) -> Set[str]:
        """Get all file paths for a specific language."""
        with self._lock:
            return self._language_index.get(language, set()).copy()
    
    def get_paths_by_reference_doc(self, reference_doc: str) -> Set[str]:
        """Get all file paths that reference a specific documentation file."""
        with self._lock:
            return self._reference_doc_index.get(reference_doc, set()).copy()
    
    def get_paths_by_function(self, function_name: str) -> Set[str]:
        """Get all file paths that contain a specific function name."""
        with self._lock:
            return self._function_index.get(function_name, set()).copy()
    
    def get_paths_by_class(self, class_name: str) -> Set[str]:
        """Get all file paths that contain a specific class name."""
        with self._lock:
            return self._class_index.get(class_name, set()).copy()
```

4. **CacheStorage**

```python
class CacheStorage:
    """Storage for cache items."""
    
    def __init__(self, config: MemoryCacheConfig, logger: Logger):
        self.config = config
        self.logger = logger
        self._cache: Dict[str, FileMetadata] = {}
        self._lock = threading.RLock()
    
    def get(self, key: str) -> Optional[FileMetadata]:
        """Get a metadata object by key."""
        with self._lock:
            return self._cache.get(key)
    
    def put(self, key: str, value: FileMetadata) -> None:
        """Store a metadata object."""
        with self._lock:
            self._cache[key] = value
    
    def remove(self, key: str) -> None:
        """Remove a metadata object."""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all stored metadata."""
        with self._lock:
            self._cache.clear()
    
    def contains(self, key: str) -> bool:
        """Check if key exists in storage."""
        with self._lock:
            return key in self._cache
    
    def count(self) -> int:
        """Get the number of items in storage."""
        with self._lock:
            return len(self._cache)
    
    def get_all_keys(self) -> Set[str]:
        """Get all keys in storage."""
        with self._lock:
            return set(self._cache.keys())
    
    def get_all(self) -> Dict[str, FileMetadata]:
        """Get all items in storage."""
        with self._lock:
            return self._cache.copy()
```

5. **EvictionStrategy**

```python
class EvictionStrategy(ABC):
    """Abstract base class for cache eviction strategies."""
    
    def __init__(self, config: MemoryCacheConfig, logger: Logger):
        self.config = config
        self.logger = logger
    
    @abstractmethod
    def record_access(self, key: str) -> None:
        """Record access to a cache item."""
        pass
    
    @abstractmethod
    def select_for_eviction(self, count: int) -> List[str]:
        """Select items for eviction."""
        pass


class LRUEvictionStrategy(EvictionStrategy):
    """Least Recently Used eviction strategy."""
    
    def __init__(self, config: MemoryCacheConfig, logger: Logger):
        super().__init__(config, logger)
        self._access_times: Dict[str, float] = {}
        self._lock = threading.RLock()
    
    def record_access(self, key: str) -> None:
        """Record access time for a cache item."""
        with self._lock:
            self._access_times[key] = time.time()
    
    def select_for_eviction(self, count: int) -> List[str]:
        """Select least recently used items for eviction."""
        with self._lock:
            if not self._access_times:
                return []
            
            # Sort by access time (oldest first)
            sorted_keys = sorted(
                self._access_times.keys(),
                key=lambda k: self._access_times.get(k, 0)
            )
            
            # Select the oldest items
            to_evict = sorted_keys[:count]
            
            # Remove evicted items from access times
            for key in to_evict:
                del self._access_times[key]
            
            return to_evict


class LFUEvictionStrategy(EvictionStrategy):
    """Least Frequently Used eviction strategy."""
    
    def __init__(self, config: MemoryCacheConfig, logger: Logger):
        super().__init__(config, logger)
        self._access_counts: Dict[str, int] = {}
        self._lock = threading.RLock()
    
    def record_access(self, key: str) -> None:
        """Increment access count for a cache item."""
        with self._lock:
            self._access_counts[key] = self._access_counts.get(key, 0) + 1
    
    def select_for_eviction(self, count: int) -> List[str]:
        """Select least frequently used items for eviction."""
        with self._lock:
            if not self._access_counts:
                return []
            
            # Sort by access count (least frequent first)
            sorted_keys = sorted(
                self._access_counts.keys(),
                key=lambda k: self._access_counts.get(k, 0)
            )
            
            # Select the least frequently used items
            to_evict = sorted_keys[:count]
            
            # Remove evicted items from access counts
            for key in to_evict:
                del self._access_counts[key]
            
            return to_evict
```

6. **QueryEngine**

```python
class MetadataQuery:
    """Query parameters for metadata search."""
    
    def __init__(self, **kwargs):
        self.language = kwargs.get('language')
        self.reference_doc = kwargs.get('reference_doc')
        self.function_name = kwargs.get('function_name')
        self.class_name = kwargs.get('class_name')
        self.path_pattern = kwargs.get('path_pattern')
        self.limit = kwargs.get('limit')


class QueryEngine:
    """Engine for querying metadata in the cache."""
    
    def __init__(self, index_manager: IndexManager, storage: CacheStorage, logger: Logger):
        self.index_manager = index_manager
        self.storage = storage
        self.logger = logger
        self._lock = threading.RLock()
    
    def execute_query(self, query: MetadataQuery) -> List[FileMetadata]:
        """
        Execute a metadata query.
        
        Args:
            query: Query parameters
        
        Returns:
            List of matching FileMetadata objects
        """
        with self._lock:
            # Determine which paths match the query
            matching_paths = self._find_matching_paths(query)
            
            # Retrieve metadata for matching paths
            result = []
            for path in matching_paths:
                metadata = self.storage.get(path)
                if metadata:
                    result.append(metadata)
            
            # Apply limit if specified
            if query.limit is not None and len(result) > query.limit:
                result = result[:query.limit]
            
            return result
    
    def _find_matching_paths(self, query: MetadataQuery) -> Set[str]:
        """Find paths matching the query criteria."""
        candidate_paths = set()
        applied_filters = False
        
        # Apply language filter
        if query.language:
            candidate_paths = self.index_manager.get_paths_by_language(query.language)
            applied_filters = True
        
        # Apply reference doc filter
        if query.reference_doc:
            reference_paths = self.index_manager.get_paths_by_reference_doc(query.reference_doc)
            if applied_filters:
                candidate_paths &= reference_paths
            else:
                candidate_paths = reference_paths
                applied_filters = True
        
        # Apply function name filter
        if query.function_name:
            function_paths = self.index_manager.get_paths_by_function(query.function_name)
            if applied_filters:
                candidate_paths &= function_paths
            else:
                candidate_paths = function_paths
                applied_filters = True
        
        # Apply class name filter
        if query.class_name:
            class_paths = self.index_manager.get_paths_by_class(query.class_name)
            if applied_filters:
                candidate_paths &= class_paths
            else:
                candidate_paths = class_paths
                applied_filters = True
        
        # If no filters applied, get all paths
        if not applied_filters:
            candidate_paths = self.storage.get_all_keys()
        
        # Apply path pattern filter if specified
        if query.path_pattern:
            try:
                pattern = re.compile(query.path_pattern)
                candidate_paths = {path for path in candidate_paths if pattern.search(path)}
            except re.error as e:
                self.logger.error(f"Invalid path pattern: {e}")
        
        return candidate_paths
```

7. **DatabaseSynchronizer**

```python
class DatabaseSynchronizer:
    """Synchronizes the cache with the database."""
    
    def __init__(self, db_component: Component, logger: Logger):
        self.db_component = db_component
        self.logger = logger
        self._lock = threading.RLock()
    
    def get_metadata_from_db(self, file_path: str) -> Optional[FileMetadata]:
        """Get metadata for a specific file from the database."""
        with self._lock:
            try:
                # Get database session
                session = self.db_component.get_session()
                
                with session.begin():
                    # Query for file metadata
                    result = session.query(FileMetadataORM).filter_by(path=file_path).first()
                    
                    if result:
                        # Convert ORM object to FileMetadata
                        return self._convert_to_file_metadata(result)
                    else:
                        return None
            
            except Exception as e:
                self.logger.error(f"Error fetching metadata from database: {e}")
                return None
    
    def perform_full_sync(self) -> None:
        """Perform a full synchronization from the database."""
        with self._lock:
            try:
                # Get database session
                session = self.db_component.get_session()
                
                with session.begin():
                    # Query for all file metadata
                    results = session.query(FileMetadataORM).all()
                    
                    # Return as FileMetadata objects
                    return [self._convert_to_file_metadata(result) for result in results]
            
            except Exception as e:
                self.logger.error(f"Error performing full database sync: {e}")
                return []
    
    def perform_incremental_sync(self, storage: CacheStorage, index_manager: IndexManager) -> None:
        """
        Perform an incremental synchronization with the database.
        
        This method updates the cache based on database changes (new, modified, or deleted files).
        """
        with self._lock:
            try:
                # Implementation depends on specific ORM schema
                # Will be implemented based on database schema plan
                pass
            
            except Exception as e:
                self.logger.error(f"Error performing incremental sync: {e}")
    
    def _convert_to_file_metadata(self, orm_obj: Any) -> FileMetadata:
        """Convert an ORM object to a FileMetadata object."""
        # Implementation depends on specific ORM schema
        # Will be implemented based on database schema plan
        pass
```

### Configuration Parameters

The Memory Cache component will be configured through these parameters:

```python
@dataclass
class MemoryCacheConfig:
    """Configuration for memory cache."""
    max_items: int  # Maximum number of items to store in cache
    eviction_strategy: str  # Strategy for evicting items when cache is full
    eviction_batch_size: int  # Number of items to evict in one batch
    sync_interval_seconds: int  # Interval between database synchronizations
```

Default configuration values (will be integrated with CONFIGURATION.md):

| Parameter | Description | Default | Valid Values |
|-----------|-------------|---------|-------------|
| `max_items` | Maximum number of items to store | `10000` | `100-1000000` |
| `eviction_strategy` | Strategy for evicting items | `"lru"` | `"lru", "lfu"` |
| `eviction_batch_size` | Number of items to evict in one batch | `100` | `1-1000` |
| `sync_interval_seconds` | Interval between synchronizations | `300` | `10-3600` |

## Implementation Plan

### Phase 1: Core Structure
1. Implement MemoryCacheComponent as a system component
2. Define MetadataCacheInterface for the main interface
3. Create configuration class for memory cache
4. Implement basic cache operations (get, update, remove, clear)

### Phase 2: Storage and Indexing
1. Implement CacheStorage for storing metadata objects
2. Create IndexManager for maintaining indexes on different attributes
3. Implement eviction strategies (LRU and LFU)
4. Add thread safety mechanisms

### Phase 3: Query Engine
1. Implement MetadataQuery for defining query parameters
2. Create QueryEngine for efficient metadata lookups
3. Add support for various query criteria
4. Implement result filtering and sorting

### Phase 4: Database Synchronization
1. Implement DatabaseSynchronizer for database interaction
2. Create methods for full and incremental synchronization
3. Add ORM object conversion logic
4. Implement periodic sync mechanism

### Phase 5: Testing and Optimization
1. Create unit tests for each component
2. Implement performance benchmarks
3. Optimize memory usage and performance
4. Add comprehensive error handling

## Security Considerations

The Memory Cache component implements these security measures:
- All data stored only in memory, never persisted to disk directly
- No external access to cached data
- Thread safety for concurrent access
- Proper error handling and containment
- Resource limitation through configuration parameters
- No arbitrary code execution from cached data

## Testing Strategy

### Unit Tests
- Test each class in isolation with mock dependencies
- Test thread safety with concurrent operations
- Test eviction strategies with various scenarios
- Test error handling for edge cases

### Integration Tests
- Test integration with Database component
- Test full and incremental synchronization
- Test cache operations with real metadata objects
- Test query engine with complex queries

### Performance Tests
- Benchmark cache operations with large datasets
- Test memory usage under various loads
- Test cache hit/miss rates with different access patterns
- Test synchronization performance

## Dependencies on Other Plans

This plan depends on:
- Database Schema plan (for database integration)
- Component Initialization plan (for component framework)
- Metadata Extraction plan (for working with FileMetadata objects)

## Implementation Timeline

1. Core Structure - 1 day
2. Storage and Indexing - 2 days
3. Query Engine - 2 days
4. Database Synchronization - 2 days
5. Testing and Optimization - 1 day

Total: 8 days
