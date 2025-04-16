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
# Provides example component implementations that demonstrate how to use the
# simplified Component interface in practice. Includes sample components with
# different dependency patterns and initialization behaviors.
###############################################################################
# [Source file design principles]
# - Clear examples of component implementation patterns
# - Proper dependency declaration and initialization
# - Appropriate error handling and reporting
# - Realistic but simplified component behaviors
###############################################################################
# [Source file constraints]
# - Example-only implementations not for production use
# - Simplified examples focused on initialization patterns
# - Mock behaviors to demonstrate initialization flow
###############################################################################
# [Reference documentation]
# - doc/DESIGN.md
# - doc/design/COMPONENT_INITIALIZATION.md
###############################################################################
# [GenAI tool change history]
# 2025-04-16T15:38:04Z : Initial creation of example component implementations by CodeAssistant
# * Created sample database, cache, and monitoring components
###############################################################################

import logging
import sqlite3
import os
import time
from typing import Any, Dict, List, Optional

# Import the Component base class
from .component import Component

# Example 1: Simple component with no dependencies
class LoggingComponent(Component):
    """
    [Class intent]
    A simple component that provides enhanced logging capabilities.
    This example shows a component with no dependencies.
    
    [Implementation details]
    Configures a specialized logger during initialization.
    In a real implementation, might set up log rotation, filtering, etc.
    
    [Design principles]
    Simple initialization with no dependencies.
    Clean resource management in shutdown.
    """
    
    @property
    def name(self) -> str:
        return "logging"
    
    @property
    def dependencies(self) -> List[str]:
        # No dependencies
        return []
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the logging component with configuration.
        
        [Implementation details]
        Sets up specialized logging based on configuration.
        
        [Design principles]
        Simple initialization with clear status indication.
        """
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing logging component")
        
        try:
            # Get logging config or use defaults
            log_config = getattr(config, "logging", {})
            log_level_name = log_config.get("level", "INFO").upper()
            log_level = getattr(logging, log_level_name, logging.INFO)
            
            # Configure specialized logger
            self.app_logger = logging.getLogger("DBP")
            self.app_logger.setLevel(log_level)
            
            # In a real implementation, might set up log handlers, formatters, etc.
            self.logger.info(f"Logging configured at level {log_level_name}")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize logging: {e}")
            raise
            
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the logging component.
        
        [Implementation details]
        Closes any log handlers and releases resources.
        
        [Design principles]
        Clean resource release with clear status indication.
        """
        if hasattr(self, "app_logger"):
            self.logger.info("Shutting down logging component")
            
            # In a real implementation, might close file handlers, etc.
            for handler in self.app_logger.handlers[:]:
                handler.close()
                self.app_logger.removeHandler(handler)
        
        self._initialized = False


# Example 2: Component with a single dependency
class DatabaseComponent(Component):
    """
    [Class intent]
    Provides database connectivity and management for the application.
    This example shows a component with a single dependency on configuration.
    
    [Implementation details]
    Creates and manages a SQLite connection during initialization.
    Provides methods for database operations.
    
    [Design principles]
    Clear dependency declaration.
    Explicit resource management.
    Simple error handling with clear messages.
    """
    
    @property
    def name(self) -> str:
        return "database"
    
    @property
    def dependencies(self) -> List[str]:
        # Depends on configuration
        return ["config_manager"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the database connection based on configuration.
        
        [Implementation details]
        Creates SQLite database file if not exists.
        Establishes connection and sets connection parameters.
        
        [Design principles]
        Clear initialization with proper error handling.
        """
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing database component")
        
        try:
            # Get database config or use defaults
            db_config = getattr(config, "database", {})
            db_path = db_config.get("path", "dbp_data.db")
            
            # Create parent directory if needed
            os.makedirs(os.path.dirname(os.path.abspath(db_path)), exist_ok=True)
            
            # Connect to database
            self.connection = sqlite3.connect(db_path)
            self.connection.row_factory = sqlite3.Row  # Use dictionary-like rows
            
            # Set connection parameters
            self.connection.execute("PRAGMA foreign_keys = ON")
            
            # Verify connection
            self.connection.execute("SELECT 1").fetchone()
            self.logger.info(f"Database initialized at {db_path}")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize database: {e}")
            if hasattr(self, "connection"):
                self.connection.close()
            raise
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Closes database connection and releases resources.
        
        [Implementation details]
        Commits any pending transactions and closes connection.
        
        [Design principles]
        Clean resource release with error handling.
        """
        if hasattr(self, "connection"):
            self.logger.info("Shutting down database component")
            try:
                self.connection.commit()  # Commit any pending transactions
                self.connection.close()
            except Exception as e:
                self.logger.error(f"Error closing database connection: {e}")
        
        self._initialized = False


# Example 3: Component with multiple dependencies
class CacheComponent(Component):
    """
    [Class intent]
    Provides in-memory caching for the application to improve performance.
    This example shows a component with multiple dependencies.
    
    [Implementation details]
    Creates an in-memory cache with configurable size and expiration.
    Provides methods for cache get/set operations.
    
    [Design principles]
    Clear multiple dependency declaration.
    Memory-aware resource allocation.
    Clean shutdown behavior.
    """
    
    @property
    def name(self) -> str:
        return "cache"
    
    @property
    def dependencies(self) -> List[str]:
        # Depends on both configuration and database
        return ["config_manager", "database"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes the cache with configuration parameters.
        
        [Implementation details]
        Sets up in-memory cache with size limits and expiration.
        Pre-loads critical data from database.
        
        [Design principles]
        Clear initialization with database integration.
        Memory-aware resource allocation.
        """
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing cache component")
        
        try:
            # Get cache config or use defaults
            cache_config = getattr(config, "cache", {})
            self.max_size = cache_config.get("max_size", 1000)
            self.expiration = cache_config.get("expiration_seconds", 300)
            
            # Create cache structures
            self.cache: Dict[str, Dict[str, Any]] = {}
            self.cache_times: Dict[str, float] = {}
            
            # Preload critical data
            self._preload_data()
            
            self.logger.info(f"Cache initialized (max size: {self.max_size}, expiration: {self.expiration}s)")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize cache: {e}")
            raise
    
    def _preload_data(self) -> None:
        """
        [Function intent]
        Pre-loads critical data into the cache from the database.
        
        [Implementation details]
        Example implementation that would normally load frequently accessed data.
        
        [Design principles]
        Initialization-time data preloading for performance.
        """
        # This is a simplified example
        self.logger.info("Pre-loading critical data into cache")
        self.cache["system"] = {"startup_time": time.time()}
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the cache component and releases resources.
        
        [Implementation details]
        Clears cache data structures and marks as not initialized.
        
        [Design principles]
        Clean memory release during shutdown.
        """
        if hasattr(self, "cache"):
            self.logger.info("Shutting down cache component")
            self.cache.clear()
            self.cache_times.clear()
        
        self._initialized = False


# Example 4: Component with circular dependency detection
class MonitoringComponent(Component):
    """
    [Class intent]
    Provides system monitoring capabilities for the application.
    This example demonstrates circular dependency detection.
    
    [Implementation details]
    Sets up monitoring for system metrics and component status.
    
    [Design principles]
    Clear dependency declaration that would create a circular dependency.
    Simple monitoring implementation.
    """
    
    @property
    def name(self) -> str:
        return "monitoring"
    
    @property
    def dependencies(self) -> List[str]:
        # This creates a circular dependency if analytics depends on monitoring
        return ["config_manager", "analytics"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes monitoring with configuration parameters.
        
        [Implementation details]
        Sets up monitoring intervals and metrics collection.
        
        [Design principles]
        Clear initialization with configuration integration.
        """
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing monitoring component")
        
        try:
            # Get monitoring config
            mon_config = getattr(config, "monitoring", {})
            self.interval = mon_config.get("interval_seconds", 60)
            
            # Setup monitoring
            self.metrics = {}
            self.start_time = time.time()
            
            self.logger.info(f"Monitoring initialized (interval: {self.interval}s)")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize monitoring: {e}")
            raise
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the monitoring component and releases resources.
        
        [Implementation details]
        Stops metrics collection and clears data.
        
        [Design principles]
        Clean resource release during shutdown.
        """
        if hasattr(self, "metrics"):
            self.logger.info("Shutting down monitoring component")
            self.metrics.clear()
        
        self._initialized = False


# Example 5: Component with circular dependency detection
class AnalyticsComponent(Component):
    """
    [Class intent]
    Provides analytics capabilities for the application.
    This example demonstrates circular dependency with monitoring.
    
    [Implementation details]
    Collects and processes analytics data from system operations.
    
    [Design principles]
    Clear dependency declaration that creates a circular dependency.
    Simple analytics implementation.
    """
    
    @property
    def name(self) -> str:
        return "analytics"
    
    @property
    def dependencies(self) -> List[str]:
        # This creates a circular dependency with monitoring
        return ["monitoring"]
    
    def initialize(self, config: Any) -> None:
        """
        [Function intent]
        Initializes analytics with configuration parameters.
        
        [Implementation details]
        Sets up analytics collection and storage.
        
        [Design principles]
        Clear initialization with monitoring integration.
        """
        self.logger = logging.getLogger(f"DBP.{self.name}")
        self.logger.info("Initializing analytics component")
        
        try:
            # Get analytics config
            analytics_config = getattr(config, "analytics", {})
            
            # Setup analytics
            self.data = {}
            
            self.logger.info("Analytics initialized")
            
            # Mark as initialized
            self._initialized = True
            
        except Exception as e:
            self.logger.error(f"Failed to initialize analytics: {e}")
            raise
    
    def shutdown(self) -> None:
        """
        [Function intent]
        Shuts down the analytics component and releases resources.
        
        [Implementation details]
        Persists analytics data and clears memory resources.
        
        [Design principles]
        Clean resource release during shutdown.
        """
        if hasattr(self, "data"):
            self.logger.info("Shutting down analytics component")
            self.data.clear()
        
        self._initialized = False
